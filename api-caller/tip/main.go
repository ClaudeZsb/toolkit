package main

import (
	"bytes"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"math/big"
	"net/http"
	"os"
	"time"

	"github.com/ethereum/go-ethereum/ethclient"
)

type BlockResponse struct {
	Result struct {
		Number   string `json:"number"`
		GasUsed  string `json:"gasUsed"`
		GasLimit string `json:"gasLimit"`
	} `json:"result"`
}

func getBlockGasInfo(rpcURL string, blockNumber uint64) (uint64, uint64, error) {
	// Create HTTP client
	httpClient := &http.Client{}

	// Prepare the JSON-RPC request
	requestBody := map[string]interface{}{
		"jsonrpc": "2.0",
		"method":  "eth_getBlockByNumber",
		"params":  []interface{}{fmt.Sprintf("0x%x", blockNumber), false},
		"id":      1,
	}

	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		return 0, 0, fmt.Errorf("failed to marshal request: %v", err)
	}

	// Make the request
	resp, err := httpClient.Post(rpcURL, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return 0, 0, fmt.Errorf("failed to make request: %v", err)
	}
	defer resp.Body.Close()

	// Parse the response
	var blockResp BlockResponse
	if err := json.NewDecoder(resp.Body).Decode(&blockResp); err != nil {
		return 0, 0, fmt.Errorf("failed to decode response: %v", err)
	}

	// Convert hex strings to uint64
	gasUsed, _ := new(big.Int).SetString(blockResp.Result.GasUsed[2:], 16)
	gasLimit, _ := new(big.Int).SetString(blockResp.Result.GasLimit[2:], 16)

	return gasUsed.Uint64(), gasLimit.Uint64(), nil
}

func main() {
	// Define command line flags
	rpcURL := flag.String("rpc", "http://localhost:8545", "RPC URL")
	outputFile := flag.String("output", "fees.csv", "Output file path")
	interval := flag.Int("interval", 1, "Interval between checks in seconds")
	flag.Parse()

	// Create or open the output file in append mode
	file, err := os.OpenFile(*outputFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		log.Fatalf("Failed to open output file: %v", err)
	}
	defer file.Close()

	// Create a new client
	client, err := ethclient.Dial(*rpcURL)
	if err != nil {
		log.Fatalf("Failed to connect to RPC: %v", err)
	}
	defer client.Close()

	// Write header if file is empty
	fileInfo, err := file.Stat()
	if err != nil {
		log.Fatalf("Failed to get file info: %v", err)
	}
	if fileInfo.Size() == 0 {
		if _, err := file.WriteString("timestamp,block_number,max_priority_fee_gwei,gas_usage_ratio\n"); err != nil {
			log.Fatalf("Failed to write header: %v", err)
		}
	}

	log.Printf("Starting monitoring...")
	log.Printf("RPC URL: %s", *rpcURL)
	log.Printf("Output file: %s", *outputFile)
	log.Printf("Check interval: %d seconds", *interval)
	log.Printf("Press Ctrl+C to stop monitoring")

	var lastBlockNumber uint64

	for {
		// Get current block number
		blockNumber, err := client.BlockNumber(context.Background())
		if err != nil {
			log.Printf("Failed to get block number: %v", err)
			time.Sleep(time.Duration(*interval) * time.Second)
			continue
		}

		// Skip if block number hasn't changed
		if blockNumber == lastBlockNumber {
			time.Sleep(time.Duration(*interval) * time.Second)
			continue
		}

		// Update last block number
		lastBlockNumber = blockNumber

		// Get block gas information
		gasUsed, gasLimit, err := getBlockGasInfo(*rpcURL, blockNumber)
		if err != nil {
			log.Printf("Failed to get block gas info: %v", err)
			time.Sleep(time.Duration(*interval) * time.Second)
			continue
		}

		// Get max priority fee
		maxPriorityFee, err := client.SuggestGasTipCap(context.Background())
		if err != nil {
			log.Printf("Failed to get max priority fee: %v", err)
			time.Sleep(time.Duration(*interval) * time.Second)
			continue
		}

		// Convert max priority fee to gwei
		maxPriorityFeeGwei := float64(maxPriorityFee.Int64()) / 1e9

		// Calculate gas usage ratio
		gasUsageRatio := float64(gasUsed) / float64(gasLimit)

		// Format the data
		timestamp := time.Now().Format(time.RFC3339)
		line := fmt.Sprintf("%s,%d,%.9f,%.6f\n", timestamp, blockNumber, maxPriorityFeeGwei, gasUsageRatio)

		// Write to file
		if _, err := file.WriteString(line); err != nil {
			log.Printf("Failed to write to file: %v", err)
		} else {
			log.Printf("Block %d: max priority fee = %.9f gwei, gas usage = %d/%d (%.2f%%)",
				blockNumber, maxPriorityFeeGwei, gasUsed, gasLimit, gasUsageRatio*100)
		}

		// Wait for the next interval
		time.Sleep(time.Duration(*interval) * time.Second)
	}
}
