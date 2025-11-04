// copied from https://gist.github.com/mdehoog/0b1448223dbc67f0c6b0a0eebeb733fb

package main

import (
	"bytes"
	"compress/zlib"
	"context"
	"encoding/binary"
	"log"
	"math/big"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/ethereum/go-ethereum/cmd/utils"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/rawdb"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/ethclient"
	"github.com/ethereum/go-ethereum/ethdb"
	"github.com/ethereum/go-ethereum/node"
)

// TxResult holds the compression estimation results for a transaction
type TxResult struct {
	BlockNumber uint64
	Best        uint32
	Fastlz      uint32
	Zeroes      uint32
	NonZeroes   uint32
}

// BlockJob represents a block to be processed
type BlockJob struct {
	Block *types.Block
}

func main() {
	trimSignature := false
	bootstrapTxs := 1000
	endBlock := uint64(78980000) // OP bedrock block + 1
	//endBlock := uint64(0)
	startBlock := int64(-1) // -1 for latest

	// remote node URL or local database location:
	clientLocation := "https://rpc.mantle.xyz"
	// clientLocation := "/data/op-geth"

	output, err := os.Create("./data/fastlz.bin")
	if err != nil {
		log.Fatal(err)
	}
	defer output.Close()

	log.Printf("Starting block fetcher, processing down to block %d", endBlock)

	// Channels for coordination
	jobChan := make(chan BlockJob, 20)
	resultChan := make(chan TxResult, 1000)

	// Single worker goroutine with direct estimator access
	wg := &sync.WaitGroup{}
	wg.Add(1)
	go func() {
		defer wg.Done()

		// Worker owns the estimator - no need for channels
		zlibBestBatchEstimator := newZlibBatchEstimator()
		bootstrapCount := 0
		bootstrapDone := false

		for job := range jobChan {
			block := job.Block
			if block == nil {
				log.Printf("Worker: Received nil block")
				continue
			}

			// Process transactions
			for _, tx := range block.Transactions() {
				if tx.Type() == types.DepositTxType {
					continue
				}
				b, err := tx.MarshalBinary()
				if err != nil {
					log.Printf("Worker: Error marshaling tx: %v", err)
					continue
				}
				if trimSignature && len(b) >= 68 {
					b = b[:len(b)-68]
				}

				// Call estimator directly
				var best uint32
				if !bootstrapDone {
					// Still bootstrapping
					zlibBestBatchEstimator.write(b)
					bootstrapCount++
					if bootstrapCount >= bootstrapTxs {
						bootstrapDone = true
						log.Printf("Bootstrap complete after %d transactions", bootstrapCount)
					}
					continue // Skip writing during bootstrap
				} else {
					// Bootstrap done - get actual estimation
					best = zlibBestBatchEstimator.write(b)
				}

				fastlz := FlzCompressLen(b)
				zeroes := uint32(0)
				nonZeroes := uint32(0)
				for _, byte := range b {
					if byte == 0 {
						zeroes++
					} else {
						nonZeroes++
					}
				}

				// Send result to writer
				resultChan <- TxResult{
					BlockNumber: uint64(block.NumberU64()),
					Best:        best,
					Fastlz:      fastlz,
					Zeroes:      zeroes,
					NonZeroes:   nonZeroes,
				}
			}
		}
	}()

	// Writer goroutine
	writerDone := make(chan bool)
	go func() {
		lastPrint := time.Now()
		printInterval := 10 * time.Second
		resultCount := 0
		lastBlock := uint64(0)

		for result := range resultChan {
			// Write to file
			binary.Write(output, binary.LittleEndian, uint32(result.BlockNumber))
			binary.Write(output, binary.LittleEndian, result.Best)
			binary.Write(output, binary.LittleEndian, result.Fastlz)
			binary.Write(output, binary.LittleEndian, result.Zeroes)
			binary.Write(output, binary.LittleEndian, result.NonZeroes)

			resultCount++
			if result.BlockNumber != lastBlock {
				lastBlock = result.BlockNumber
			}

			if time.Since(lastPrint) > printInterval {
				log.Printf("Processed %d transactions, current block: %d", resultCount, lastBlock)
				lastPrint = time.Now()
			}
		}
		writerDone <- true
	}()

	// Feed jobs (concurrent fetchers - no ordering needed)
	numFetchers := 5 // Multiple concurrent fetchers (bottleneck is RPC, not processing)
	fetcherWg := &sync.WaitGroup{}

	// Create a coordinator that generates block numbers to fetch
	blockNumChan := make(chan uint64, numFetchers*10)
	go func() {
		// Get starting block number
		var tempClient Client
		if strings.HasPrefix(clientLocation, "http://") || strings.HasPrefix(clientLocation, "https://") {
			tempClient, err = ethclient.Dial(clientLocation)
		} else {
			tempClient, err = NewLocalClient(clientLocation)
		}
		if err != nil {
			log.Fatal("Coordinator: failed to create client:", err)
		}

		var startingBlock *types.Block
		if startBlock == -1 {
			startingBlock, err = tempClient.BlockByNumber(context.Background(), nil)
		} else {
			startingBlock, err = tempClient.BlockByNumber(context.Background(), big.NewInt(startBlock))
		}
		tempClient.Close()

		if err != nil {
			log.Fatal("Coordinator: failed to get starting block:", err)
		}

		startBlockNum := startingBlock.NumberU64()
		log.Printf("Starting from block %d", startBlockNum)

		// Generate block numbers in descending order
		for blockNum := startBlockNum; blockNum > endBlock; blockNum-- {
			blockNumChan <- blockNum
		}
		close(blockNumChan)
	}()

	// Start multiple fetcher goroutines - send directly to workers
	for i := 0; i < numFetchers; i++ {
		fetcherWg.Add(1)
		go func(fetcherID int) {
			defer fetcherWg.Done()

			// Each fetcher gets its own client
			var fetcherClient Client
			if strings.HasPrefix(clientLocation, "http://") || strings.HasPrefix(clientLocation, "https://") {
				fetcherClient, err = ethclient.Dial(clientLocation)
			} else {
				fetcherClient, err = NewLocalClient(clientLocation)
			}
			if err != nil {
				log.Printf("Fetcher %d: failed to create client: %v", fetcherID, err)
				return
			}
			defer fetcherClient.Close()

			for blockNum := range blockNumChan {
				// Fetch block with retry
				var block *types.Block
				maxRetries := 8
				retryDelay := 100 * time.Millisecond

				for attempt := 0; attempt < maxRetries; attempt++ {
					block, err = fetcherClient.BlockByNumber(context.Background(), big.NewInt(int64(blockNum)))
					if err == nil {
						break
					}
					if attempt < maxRetries-1 {
						time.Sleep(retryDelay)
						retryDelay *= 2
					}
				}

				if err != nil {
					log.Printf("Fetcher %d: Failed to fetch block %d: %v", fetcherID, blockNum, err)
					continue
				}

				jobChan <- BlockJob{Block: block}
			}
		}(i)
	}

	// Close jobChan when all fetchers are done
	go func() {
		fetcherWg.Wait()
		close(jobChan)
	}()

	// Wait for worker to finish
	wg.Wait()
	close(resultChan)

	// Wait for writer to finish
	<-writerDone
	log.Println("All processing complete")
}

// zlibBatchEstimator simulates a zlib compressor at max compression that works on (large) tx
// batches.  Should bootstrap it before use by calling it on several samples of representative
// data.
type zlibBatchEstimator struct {
	b [2]bytes.Buffer
	w [2]*zlib.Writer
}

func newZlibBatchEstimator() *zlibBatchEstimator {
	b := &zlibBatchEstimator{}
	var err error
	for i := range b.w {
		b.w[i], err = zlib.NewWriterLevel(&b.b[i], zlib.BestCompression)
		if err != nil {
			log.Fatal(err)
		}
	}
	return b
}

func (w *zlibBatchEstimator) write(p []byte) uint32 {
	// targeting:
	//	b[0] == 0-64kb
	//	b[1] == 64kb-128kb
	before := w.b[1].Len()
	_, err := w.w[1].Write(p)
	if err != nil {
		log.Fatal(err)
	}
	err = w.w[1].Flush()
	if err != nil {
		log.Fatal(err)
	}
	after := w.b[1].Len()
	// if b[1] > 64kb, write to b[0]
	if w.b[1].Len() > 64*1024 {
		_, err = w.w[0].Write(p)
		if err != nil {
			log.Fatal(err)
		}
		err = w.w[0].Flush()
		if err != nil {
			log.Fatal(err)
		}
	}
	// if b[1] > 128kb, rotate
	if w.b[1].Len() > 128*1024 {
		w.b[1].Reset()
		w.w[1].Reset(&w.b[1])
		tb := w.b[1]
		tw := w.w[1]
		w.b[1] = w.b[0]
		w.w[1] = w.w[0]
		w.b[0] = tb
		w.w[0] = tw
	}
	if after-before-2 < 0 {
		return 0
	}
	return uint32(after - before - 2) // flush writes 2 extra "sync" bytes so don't count those
}

type Client interface {
	BlockByHash(ctx context.Context, hash common.Hash) (*types.Block, error)
	BlockByNumber(ctx context.Context, number *big.Int) (*types.Block, error)
	Close()
}

type LocalClient struct {
	n  *node.Node
	db ethdb.Database
}

func NewLocalClient(dataDir string) (Client, error) {
	nodeCfg := node.DefaultConfig
	nodeCfg.Name = "geth"
	nodeCfg.DataDir = dataDir
	n, err := node.New(&nodeCfg)
	if err != nil {
		return nil, err
	}
	handles := utils.MakeDatabaseHandles(1024)
	db, err := n.OpenDatabaseWithFreezer("chaindata", 512, handles, "", "", true)
	if err != nil {
		return nil, err
	}
	return &LocalClient{
		n:  n,
		db: db,
	}, nil
}

func (c *LocalClient) Close() {
	_ = c.db.Close()
	_ = c.n.Close()
}

func (c *LocalClient) BlockByHash(ctx context.Context, hash common.Hash) (*types.Block, error) {
	number := rawdb.ReadHeaderNumber(c.db, hash)
	if number == nil {
		return nil, nil
	}
	return rawdb.ReadBlock(c.db, hash, *number), nil
}

func (c *LocalClient) BlockByNumber(ctx context.Context, number *big.Int) (*types.Block, error) {
	if number.Int64() < 0 {
		return c.BlockByHash(ctx, rawdb.ReadHeadBlockHash(c.db))
	}
	hash := rawdb.ReadCanonicalHash(c.db, number.Uint64())
	if bytes.Equal(hash.Bytes(), common.Hash{}.Bytes()) {
		return nil, nil
	}
	return rawdb.ReadBlock(c.db, hash, number.Uint64()), nil
}

func FlzCompressLen(ib []byte) uint32 {
	n := uint32(0)
	ht := make([]uint32, 8192)
	u24 := func(i uint32) uint32 {
		return uint32(ib[i]) | (uint32(ib[i+1]) << 8) | (uint32(ib[i+2]) << 16)
	}
	cmp := func(p uint32, q uint32, e uint32) uint32 {
		l := uint32(0)
		for e -= q; l < e; l++ {
			if ib[p+l] != ib[q+l] {
				e = 0
			}
		}
		return l
	}
	literals := func(r uint32) {
		n += 0x21 * (r / 0x20)
		r %= 0x20
		if r != 0 {
			n += r + 1
		}
	}
	match := func(l uint32) {
		l--
		n += 3 * (l / 262)
		if l%262 >= 6 {
			n += 3
		} else {
			n += 2
		}
	}
	hash := func(v uint32) uint32 {
		return ((2654435769 * v) >> 19) & 0x1fff
	}
	setNextHash := func(ip uint32) uint32 {
		ht[hash(u24(ip))] = ip
		return ip + 1
	}
	a := uint32(0)
	ipLimit := uint32(len(ib)) - 13
	if len(ib) < 13 {
		ipLimit = 0
	}
	for ip := a + 2; ip < ipLimit; {
		r := uint32(0)
		d := uint32(0)
		for {
			s := u24(ip)
			h := hash(s)
			r = ht[h]
			ht[h] = ip
			d = ip - r
			if ip >= ipLimit {
				break
			}
			ip++
			if d <= 0x1fff && s == u24(r) {
				break
			}
		}
		if ip >= ipLimit {
			break
		}
		ip--
		if ip > a {
			literals(ip - a)
		}
		l := cmp(r+3, ip+3, ipLimit+9)
		match(l)
		ip = setNextHash(setNextHash(ip + l))
		a = ip
	}
	literals(uint32(len(ib)) - a)
	return n
}
