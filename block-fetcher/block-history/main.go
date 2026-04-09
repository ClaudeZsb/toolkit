package main

import (
	"context"
	"encoding/csv"
	"flag"
	"fmt"
	"log"
	"os"
	"time"

	blockfetcher "block-fetcher"
)

func main() {
	// Command line flags
	rpcURL := flag.String("rpc", "https://rpc.ankr.com/eth", "Ethereum RPC endpoint URL")
	startBlock := flag.Uint64("start", 18500000, "Starting block number (inclusive)")
	endBlock := flag.Uint64("end", 18500010, "Ending block number (inclusive)")
	maxConcurrent := flag.Int("concurrent", 20, "Maximum concurrent requests")
	outputFile := flag.String("output", "", "Output CSV file (default: stdout)")
	flag.Parse()

	if *startBlock > *endBlock {
		log.Fatalf("Start block (%d) must be <= end block (%d)", *startBlock, *endBlock)
	}

	// Create config
	config := blockfetcher.Config{
		RPCURL:         *rpcURL,
		StartBlock:     *startBlock,
		EndBlock:       *endBlock,
		MaxConcurrent:  *maxConcurrent,
		MaxRetries:     6,
		RetryDelay:     100 * time.Millisecond,
		RequestTimeout: 10 * time.Second,
	}

	// Create fetcher
	fetcher, err := blockfetcher.New(config)
	if err != nil {
		log.Fatalf("Failed to create fetcher: %v", err)
	}

	// Create context (no timeout - let it run until completion or manual cancellation)
	ctx := context.Background()

	// Setup output
	var writer *csv.Writer
	if *outputFile != "" {
		file, err := os.Create(*outputFile)
		if err != nil {
			log.Fatalf("Failed to create output file: %v", err)
		}
		defer file.Close()
		writer = csv.NewWriter(file)
		defer writer.Flush()
	} else {
		writer = csv.NewWriter(os.Stdout)
		defer writer.Flush()
	}

	// Write CSV header
	header := []string{"Block Number", "Timestamp", "Transaction Count", "Gas Used"}
	if err := writer.Write(header); err != nil {
		log.Fatalf("Failed to write header: %v", err)
	}

	// Fetch blocks
	log.Printf("Fetching blocks %d to %d...", *startBlock, *endBlock)
	resultChan := fetcher.FetchBlocks(ctx)

	successCount := 0
	errorCount := 0
	logCounter := 0

	// Set up time-based logging (every 10 seconds)
	lastLogTime := time.Now()
	logInterval := 10 * time.Second

	for result := range resultChan {
		logCounter++

		if result.Error != nil {
			log.Printf("Error fetching block %d: %v", result.BlockNumber, result.Error)
			errorCount++
			continue
		}

		block := result.Block
		if block == nil {
			log.Printf("Block %d is nil", result.BlockNumber)
			errorCount++
			continue
		}

		// Use receipts from result
		if result.FirstTxReceipt == nil || result.SecondTxReceipt == nil || result.UserTxCount == 0 {
			continue
		}

		l1Info := result.FirstTxReceipt
		userTx := result.SecondTxReceipt

		tokenRatio := userTx.TokenRatio.Uint64()
		gasUsed := (block.GasUsed() - l1Info.GasUsed) / tokenRatio

		// Write block data using the original block type
		record := []string{
			fmt.Sprintf("%d", block.Number().Uint64()),
			fmt.Sprintf("%d", block.Time()),
			fmt.Sprintf("%d", result.UserTxCount),
			fmt.Sprintf("%d", gasUsed),
		}

		if err := writer.Write(record); err != nil {
			log.Printf("Failed to write record for block %d: %v", block.Number().Uint64(), err)
			errorCount++
			continue
		}

		successCount++

		// Log every 10 seconds
		if time.Since(lastLogTime) >= logInterval {
			log.Printf("Processed %d blocks, current block: %d (%d transactions)", logCounter, block.Number().Uint64(), len(block.Transactions()))
			lastLogTime = time.Now()
		}
	}

	log.Printf("\nCompleted: %d blocks fetched successfully, %d errors", successCount, errorCount)
}
