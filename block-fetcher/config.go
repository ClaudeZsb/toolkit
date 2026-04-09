package blockfetcher

import "time"

// Config holds the configuration for the block fetcher
type Config struct {
	// RPCURL is the Ethereum RPC endpoint URL
	RPCURL string

	// MaxConcurrent limits the number of concurrent block fetch requests
	MaxConcurrent int

	// FetchInterval is the delay between starting each worker (in milliseconds)
	FetchInterval time.Duration

	// MaxRetries is the maximum number of retries for failed requests
	MaxRetries int

	// RetryDelay is the delay between retries
	RetryDelay time.Duration

	// RequestTimeout is the timeout for each HTTP request
	RequestTimeout time.Duration

	// StartBlock is the starting block number (inclusive)
	StartBlock uint64

	// EndBlock is the ending block number (inclusive)
	EndBlock uint64
}

// DefaultConfig returns a config with sensible defaults
func DefaultConfig() Config {
	return Config{
		MaxConcurrent:  20,
		FetchInterval:  100 * time.Millisecond,
		MaxRetries:     3,
		RetryDelay:     2 * time.Second,
		RequestTimeout: 10 * time.Second,
	}
}

// Validate validates the configuration and returns an error if invalid
func (c *Config) Validate() error {
	if c.RPCURL == "" {
		return ErrMissingRPCURL
	}
	if c.MaxConcurrent <= 0 {
		return ErrInvalidMaxConcurrent
	}
	if c.MaxRetries < 0 {
		return ErrInvalidMaxRetries
	}
	if c.RequestTimeout <= 0 {
		return ErrInvalidTimeout
	}
	if c.EndBlock < c.StartBlock {
		return ErrInvalidBlockRange
	}
	return nil
}
