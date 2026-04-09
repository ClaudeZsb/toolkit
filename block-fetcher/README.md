# Block Fetcher

A reusable Go module for fetching Ethereum blocks from an RPC endpoint. It provides a concurrent, configurable block fetcher that streams results through a channel.

## Features

- **Concurrent fetching**: Configurable concurrent requests with semaphore-based rate limiting
- **Retry logic**: Automatic retries with configurable delays
- **Context support**: Cancellation and timeout support via context
- **Type-safe**: Well-defined types for block data and results
- **Configurable**: Flexible configuration for different use cases

## Usage

### Basic Usage

```go
package main

import (
    "fmt"
    "log"
    
    "block-fetcher"
)

func main() {
    config := blockfetcher.Config{
        RPCURL:        "https://rpc.ankr.com/eth",
        StartBlock:    10000000,
        EndBlock:      10000100,
        MaxConcurrent: 20,
    }
    
    resultChan, err := blockfetcher.CreateFromConfig(config)
    if err != nil {
        log.Fatal(err)
    }
    
    for result := range resultChan {
        if result.Error != nil {
            fmt.Printf("Error fetching block %d: %v\n", result.BlockNumber, result.Error)
            continue
        }
        
        fmt.Printf("Block %d: GasUsed=%d, GasLimit=%d\n", 
            result.Data.Number, result.Data.GasUsed, result.Data.GasLimit)
    }
}
```

### With Context

```go
ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()

config := blockfetcher.NewSimpleConfig("https://rpc.ankr.com/eth", 10000000, 10000100)
resultChan, err := blockfetcher.CreateFromConfigWithContext(ctx, config)
if err != nil {
    log.Fatal(err)
}

for result := range resultChan {
    // Process results
}
```

### Advanced Configuration

```go
config := blockfetcher.Config{
    RPCURL:         "https://rpc.ankr.com/eth",
    StartBlock:     10000000,
    EndBlock:       10000100,
    MaxConcurrent:  10,
    FetchInterval:  50 * time.Millisecond,
    MaxRetries:     5,
    RetryDelay:     1 * time.Second,
    RequestTimeout: 15 * time.Second,
}

fetcher, err := blockfetcher.New(config)
if err != nil {
    log.Fatal(err)
}

resultChan := fetcher.FetchBlocks(context.Background())
```

## Configuration Options

- `RPCURL`: Ethereum RPC endpoint URL (required)
- `StartBlock`: Starting block number (inclusive)
- `EndBlock`: Ending block number (inclusive)
- `MaxConcurrent`: Maximum concurrent requests (default: 20)
- `FetchInterval`: Delay between starting workers (default: 100ms)
- `MaxRetries`: Maximum retry attempts (default: 3)
- `RetryDelay`: Delay between retries (default: 2s)
- `RequestTimeout`: HTTP request timeout (default: 10s)

## Types

### BlockData
```go
type BlockData struct {
    Number    uint64
    GasUsed   uint64
    GasLimit  uint64
    Timestamp uint64
    Hash      string
}
```

### BlockResult
```go
type BlockResult struct {
    BlockNumber uint64
    Data        *BlockData
    Error       error
}
```

## Error Handling

The fetcher returns errors through the `BlockResult.Error` field. Common errors:
- `ErrMissingRPCURL`: RPC URL not provided
- `ErrBlockNotFound`: Block not found on chain
- Context cancellation errors

## Examples

See the `examples/` directory for more usage examples.

