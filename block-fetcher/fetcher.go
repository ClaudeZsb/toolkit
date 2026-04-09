package blockfetcher

import (
	"context"
	"errors"
	"fmt"
	"math/big"
	"strings"
	"sync"
	"time"

	"github.com/ethereum/go-ethereum"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/ethclient"
)

// Fetcher handles fetching blocks from an Ethereum RPC endpoint
type Fetcher struct {
	config Config
	// RPCURL is stored separately so each fetcher can create its own client
	rpcURL string
}

// New creates a new block fetcher with the given configuration
func New(config Config) (*Fetcher, error) {
	if err := config.Validate(); err != nil {
		return nil, fmt.Errorf("invalid config: %w", err)
	}

	return &Fetcher{
		config: config,
		rpcURL: config.RPCURL,
	}, nil
}

// FetchBlocks fetches blocks from StartBlock to EndBlock (inclusive) and returns
// results through a channel. The channel is closed when all blocks are fetched.
// Uses multiple concurrent fetchers, each with its own client, following the pattern
// from fastlz/main.go for better performance.
func (f *Fetcher) FetchBlocks(ctx context.Context) <-chan BlockResult {
	blockCount := int(f.config.EndBlock - f.config.StartBlock + 1)
	if blockCount < 0 {
		blockCount = 0
	}
	resultChan := make(chan BlockResult, blockCount)

	go func() {
		defer close(resultChan)

		// Create a channel to distribute block numbers to fetchers
		blockNumChan := make(chan uint64, f.config.MaxConcurrent*10)

		// Coordinator: generate block numbers and send to channel
		go func() {
			for blockNum := f.config.StartBlock; blockNum <= f.config.EndBlock; blockNum++ {
				select {
				case blockNumChan <- blockNum:
				case <-ctx.Done():
					return
				}
			}
			close(blockNumChan)
		}()

		// Start multiple fetcher goroutines, each with its own client
		var fetcherWg sync.WaitGroup
		for i := 0; i < f.config.MaxConcurrent; i++ {
			fetcherWg.Add(1)
			go func(fetcherID int) {
				defer fetcherWg.Done()

				// Each fetcher gets its own client
				client, err := ethclient.Dial(f.rpcURL)
				if err != nil {
					// If client creation fails, we can't fetch blocks
					// Consume remaining blocks from channel and report errors
					for blockNum := range blockNumChan {
						select {
						case resultChan <- BlockResult{
							BlockNumber: blockNum,
							Block:       nil,
							UserTxCount: 0,
							Error:       fmt.Errorf("failed to create client: %w", err),
						}:
						case <-ctx.Done():
							return
						}
					}
					return
				}

				// Fetch blocks from the channel
				for blockNum := range blockNumChan {
					select {
					case <-ctx.Done():
						return
					default:
						result := f.fetchBlockWithRetry(ctx, client, blockNum)
						resultChan <- result
					}
				}
				client.Close()
			}(i)
		}

		// Wait for all fetchers to complete
		fetcherWg.Wait()
	}()

	return resultChan
}

// fetchBlockWithRetry fetches a single block with retry logic (simplified pattern from fastlz)
func (f *Fetcher) fetchBlockWithRetry(ctx context.Context, client *ethclient.Client, blockNumber uint64) BlockResult {
	var block *types.Block
	var err error
	retryDelay := f.config.RetryDelay

	for attempt := 0; attempt <= f.config.MaxRetries; attempt++ {
		block, err = f.fetchBlock(ctx, client, blockNumber)
		if err == nil {
			break // Success, exit retry loop
		}
		// Don't retry on the last attempt
		if attempt < f.config.MaxRetries {
			select {
			case <-time.After(retryDelay):
				retryDelay *= 2 // Exponential backoff
			case <-ctx.Done():
				return BlockResult{
					BlockNumber: blockNumber,
					Block:       nil,
					UserTxCount: 0,
					Error:       ctx.Err(),
				}
			}
		}
	}

	if err != nil {
		return BlockResult{
			BlockNumber: blockNumber,
			Block:       nil,
			UserTxCount: 0,
			Error:       err,
		}
	}

	// Fetch receipts for first and second transactions if available
	var firstTxReceipt, secondTxReceipt *types.Receipt
	userTxCount := 0

	if block != nil {
		if len(block.Transactions()) > 1 {
			// Count user transactions (excluding DepositTxType)
			for _, tx := range block.Transactions() {
				if tx.Type() != types.DepositTxType {
					userTxCount++
					if secondTxReceipt == nil {
						secondTxReceipt, _ = f.fetchReceiptWithRetry(ctx, client, tx.Hash())
					}
				} else if firstTxReceipt == nil {
					// Fetch first transaction receipt
					firstTxReceipt, _ = f.fetchReceiptWithRetry(ctx, client, tx.Hash())
				}
			}
		}
	}

	return BlockResult{
		BlockNumber:     blockNumber,
		Block:           block,
		FirstTxReceipt:  firstTxReceipt,
		SecondTxReceipt: secondTxReceipt,
		UserTxCount:     userTxCount,
		Error:           nil,
	}
}

// fetchBlock fetches a single block from the RPC endpoint using the provided client
func (f *Fetcher) fetchBlock(ctx context.Context, client *ethclient.Client, blockNumber uint64) (*types.Block, error) {
	// Use context with timeout for this request
	reqCtx, cancel := context.WithTimeout(ctx, f.config.RequestTimeout)
	defer cancel()

	// Fetch block by number - if it fails, return the error as-is
	block, err := client.BlockByNumber(reqCtx, new(big.Int).SetUint64(blockNumber))
	if err != nil {
		// Check for block not found errors (404 or NotFound)
		errStr := err.Error()
		if errors.Is(err, ethereum.NotFound) ||
			strings.Contains(errStr, "404") ||
			strings.Contains(errStr, "Not Found") ||
			strings.Contains(errStr, "block not found") {
			return nil, ErrBlockNotFound
		}
		// Return the error as-is for all other errors
		return nil, err
	}

	return block, nil
}

// fetchReceiptWithRetry fetches a transaction receipt with retry logic
func (f *Fetcher) fetchReceiptWithRetry(ctx context.Context, client *ethclient.Client, txHash common.Hash) (*types.Receipt, error) {
	var receipt *types.Receipt
	var err error
	delay := f.config.RetryDelay

	for attempt := 0; attempt <= f.config.MaxRetries; attempt++ {
		reqCtx, cancel := context.WithTimeout(ctx, f.config.RequestTimeout)
		receipt, err = client.TransactionReceipt(reqCtx, txHash)
		cancel()

		if err == nil {
			return receipt, nil
		}

		// Don't retry on the last attempt
		if attempt < f.config.MaxRetries {
			select {
			case <-time.After(delay):
				delay *= 2 // Exponential backoff
			case <-ctx.Done():
				return nil, ctx.Err()
			}
		}
	}

	return nil, err
}
