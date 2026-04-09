package blockfetcher

import (
	"context"
	"time"
)

// BlockFetcher is the main interface for creating block fetchers
type BlockFetcher interface {
	FetchBlocks(ctx context.Context) <-chan BlockResult
}

// CreateFromConfig creates a new block fetcher from a config and returns a channel
// that streams BlockResult. This is a convenience function that wraps the Fetcher.
//
// Example usage:
//
//	config := blockfetcher.Config{
//	    RPCURL:        "https://rpc.ankr.com/eth",
//	    StartBlock:    10000000,
//	    EndBlock:      10000100,
//	    MaxConcurrent: 20,
//	    FetchInterval: 100 * time.Millisecond,
//	}
//	resultChan := blockfetcher.CreateFromConfig(config)
//	for result := range resultChan {
//	    if result.Error != nil {
//	        // handle error
//	    } else {
//	        // process result.Block (type *types.Block)
//	    }
//	}
func CreateFromConfig(config Config) (<-chan BlockResult, error) {
	fetcher, err := New(config)
	if err != nil {
		return nil, err
	}

	return fetcher.FetchBlocks(context.Background()), nil
}

// CreateFromConfigWithContext creates a new block fetcher from a config with context
// and returns a channel that streams BlockResult.
func CreateFromConfigWithContext(ctx context.Context, config Config) (<-chan BlockResult, error) {
	fetcher, err := New(config)
	if err != nil {
		return nil, err
	}

	return fetcher.FetchBlocks(ctx), nil
}

// NewSimpleConfig creates a simple config with defaults for common use cases
func NewSimpleConfig(rpcURL string, startBlock, endBlock uint64) Config {
	config := DefaultConfig()
	config.RPCURL = rpcURL
	config.StartBlock = startBlock
	config.EndBlock = endBlock
	return config
}

// NewCustomConfig creates a config with custom settings
func NewCustomConfig(rpcURL string, startBlock, endBlock uint64, maxConcurrent int, fetchInterval time.Duration) Config {
	config := DefaultConfig()
	config.RPCURL = rpcURL
	config.StartBlock = startBlock
	config.EndBlock = endBlock
	config.MaxConcurrent = maxConcurrent
	config.FetchInterval = fetchInterval
	return config
}
