package main

import (
	"bytes"
	"context"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log"
	"math/big"
	"net/http"
	"os"
	"strconv"
	"sync"
	"time"

	"github.com/ethereum/go-ethereum/ethclient"
	"github.com/joho/godotenv"
)

type BlockData struct {
	Number    uint64
	GasUsed   uint64
	GasLimit  uint64
	Timestamp uint64
	Hash      string
}

type BlockResponse struct {
	Result struct {
		Number    string `json:"number"`
		GasUsed   string `json:"gasUsed"`
		GasLimit  string `json:"gasLimit"`
		Timestamp string `json:"timestamp"`
		Hash      string `json:"hash"`
	} `json:"result"`
}

type BlockResult struct {
	BlockNumber uint64
	Data        *BlockData
	Error       error
}

func getBlockInfo(rpcURL string, blockNumber uint64) (*BlockData, error) {
	// Create HTTP client
	httpClient := &http.Client{Timeout: 10 * time.Second}

	// Prepare the JSON-RPC request
	requestBody := map[string]interface{}{
		"jsonrpc": "2.0",
		"method":  "eth_getBlockByNumber",
		"params":  []interface{}{fmt.Sprintf("0x%x", blockNumber), false},
		"id":      1,
	}

	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %v", err)
	}

	// Make the request
	resp, err := httpClient.Post(rpcURL, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to make request: %v", err)
	}
	defer resp.Body.Close()

	// Parse the response
	var blockResp BlockResponse
	if err := json.NewDecoder(resp.Body).Decode(&blockResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %v", err)
	}

	// Check if result is empty (block not found)
	if blockResp.Result.Number == "" {
		return nil, fmt.Errorf("block not found")
	}

	// Convert hex strings to uint64
	number, _ := new(big.Int).SetString(blockResp.Result.Number[2:], 16)
	gasUsed, _ := new(big.Int).SetString(blockResp.Result.GasUsed[2:], 16)
	gasLimit, _ := new(big.Int).SetString(blockResp.Result.GasLimit[2:], 16)
	timestamp, _ := new(big.Int).SetString(blockResp.Result.Timestamp[2:], 16)

	return &BlockData{
		Number:    number.Uint64(),
		GasUsed:   gasUsed.Uint64(),
		GasLimit:  gasLimit.Uint64(),
		Timestamp: timestamp.Uint64(),
		Hash:      blockResp.Result.Hash,
	}, nil
}

func fetchBlockWorker(rpcURL string, blockNumber uint64, resultChan chan<- BlockResult, wg *sync.WaitGroup) {
	defer wg.Done()

	// Try to fetch block with retry logic
	var blockData *BlockData
	var err error
	maxBlockRetries := 3

	for retry := 0; retry < maxBlockRetries; retry++ {
		blockData, err = getBlockInfo(rpcURL, blockNumber)
		if err == nil {
			break // Success, exit retry loop
		}

		if retry < maxBlockRetries-1 {
			time.Sleep(2 * time.Second) // Wait before retry
		}
	}

	resultChan <- BlockResult{
		BlockNumber: blockNumber,
		Data:        blockData,
		Error:       err,
	}
}

func main() {
	// Load environment variables
	if err := godotenv.Load(); err != nil {
		log.Println("No .env file found, using default values")
	}

	// Get RPC URL from environment or use default
	rpcURL := os.Getenv("RPC_URL")
	if rpcURL == "" {
		rpcURL = "https://rpc.ankr.com/eth" // More reliable public endpoint
		log.Println("Using default RPC URL. Set RPC_URL environment variable for production use.")
	}

	// Get block count from environment or use default
	blockCount := 100
	if val := os.Getenv("BLOCK_COUNT"); val != "" {
		if n, err := strconv.Atoi(val); err == nil && n > 0 {
			blockCount = n
		} else {
			log.Printf("Invalid BLOCK_COUNT value '%s', using default: %d", val, blockCount)
		}
	}

	// Get fetch interval from environment or use default (in milliseconds)
	fetchInterval := 100
	if val := os.Getenv("FETCH_INTERVAL"); val != "" {
		if n, err := strconv.Atoi(val); err == nil && n >= 0 {
			fetchInterval = n
		} else {
			log.Printf("Invalid FETCH_INTERVAL value '%s', using default: %d ms", val, fetchInterval)
		}
	}

	// Get max concurrent requests from environment or use default
	maxConcurrent := 20
	if val := os.Getenv("MAX_CONCURRENT"); val != "" {
		if n, err := strconv.Atoi(val); err == nil && n > 0 {
			maxConcurrent = n
		} else {
			log.Printf("Invalid MAX_CONCURRENT value '%s', using default: %d", val, maxConcurrent)
		}
	}

	log.Printf("Will fetch %d blocks with %d ms interval, max %d concurrent requests", blockCount, fetchInterval, maxConcurrent)

	// Connect to Ethereum client for getting latest block number
	client, err := ethclient.Dial(rpcURL)
	if err != nil {
		log.Fatalf("Failed to connect to the Ethereum client: %v", err)
	}
	defer client.Close()

	// Test connection with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	chainID, err := client.ChainID(ctx)
	if err != nil {
		log.Printf("Warning: Failed to get chain ID: %v", err)
	} else {
		log.Printf("Connected to Ethereum network with Chain ID: %d", chainID)
	}

	// Get current block number with retry logic
	var latestBlockNumber uint64
	maxRetries := 3
	for i := 0; i < maxRetries; i++ {
		latestBlockNumber, err = client.BlockNumber(ctx)
		if err != nil {
			log.Printf("Attempt %d: Failed to get latest block number: %v", i+1, err)
			if i == maxRetries-1 {
				log.Fatalf("Failed to get latest block number after %d attempts", maxRetries)
			}
			time.Sleep(2 * time.Second)
			continue
		}
		break
	}

	log.Printf("Latest block number: %d", latestBlockNumber)

	// Calculate start block number
	var startBlockNumber uint64
	if latestBlockNumber >= uint64(blockCount-1) {
		startBlockNumber = latestBlockNumber - uint64(blockCount-1)
	} else {
		startBlockNumber = 0
	}

	log.Printf("Fetching blocks from %d to %d", startBlockNumber, latestBlockNumber)

	// Create CSV file and write header
	filename := fmt.Sprintf("block_history_%s.csv", time.Now().Format("2006-01-02_15-04-05"))
	file, err := os.Create(filename)
	if err != nil {
		log.Fatalf("Failed to create CSV file: %v", err)
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// Write header
	header := []string{"Block Number", "Gas Used", "Gas Limit", "Gas Utilization %", "Timestamp", "Block Hash"}
	if err := writer.Write(header); err != nil {
		log.Fatalf("Failed to write header: %v", err)
	}

	// Setup for async fetching
	resultChan := make(chan BlockResult, blockCount)
	var wg sync.WaitGroup
	semaphore := make(chan struct{}, maxConcurrent) // Limit concurrent requests

	// Start fetching blocks asynchronously
	blocksStarted := 0
	for blockNum := startBlockNumber; blockNum <= latestBlockNumber; blockNum++ {
		semaphore <- struct{}{} // Acquire semaphore
		wg.Add(1)
		go func(bn uint64) {
			defer func() { <-semaphore }() // Release semaphore
			fetchBlockWorker(rpcURL, bn, resultChan, &wg)
		}(blockNum)
		blocksStarted++

		// Add delay between starting workers to avoid overwhelming the RPC
		if fetchInterval > 0 {
			time.Sleep(time.Duration(fetchInterval) * time.Millisecond)
		}
		if blockNum%100 == 0 {
			log.Printf("Processed block %d", blockNum)
		}
	}

	// Wait for all workers to complete
	go func() {
		wg.Wait()
		close(resultChan)
	}()

	// Process results as they come in
	blocksFetched := 0
	blocksFailed := 0
	results := make(map[uint64]BlockResult)

	// Collect all results first (they may come out of order)
	for result := range resultChan {
		results[result.BlockNumber] = result
	}

	// Write results in order
	for blockNum := startBlockNumber; blockNum <= latestBlockNumber; blockNum++ {
		result, exists := results[blockNum]
		if !exists {
			log.Printf("Missing result for block %d", blockNum)
			continue
		}

		if result.Error != nil {
			log.Printf("Failed to get block %d: %v", blockNum, result.Error)
			blocksFailed++

			// Write a placeholder row for failed block
			row := []string{
				strconv.FormatUint(blockNum, 10),
				"ERROR",
				"ERROR",
				"ERROR",
				"ERROR",
				"ERROR",
			}
			if writeErr := writer.Write(row); writeErr != nil {
				log.Printf("Failed to write error row for block %d: %v", blockNum, writeErr)
			}
			continue
		}

		// Write block data to CSV
		gasUtilization := float64(result.Data.GasUsed) / float64(result.Data.GasLimit) * 100
		row := []string{
			strconv.FormatUint(result.Data.Number, 10),
			strconv.FormatUint(result.Data.GasUsed, 10),
			strconv.FormatUint(result.Data.GasLimit, 10),
			fmt.Sprintf("%.2f", gasUtilization),
			strconv.FormatUint(result.Data.Timestamp, 10),
			result.Data.Hash,
		}
		if err := writer.Write(row); err != nil {
			log.Printf("Failed to write row for block %d: %v", blockNum, err)
		} else {
			blocksFetched++
		}

		// Progress indicator
		if blockNum%100 == 0 {
			log.Printf("Wrote block %d (fetched: %d, failed: %d)", blockNum, blocksFetched, blocksFailed)
		}
	}

	log.Printf("Successfully wrote %d blocks to %s (failed: %d)", blocksFetched, filename, blocksFailed)
}
