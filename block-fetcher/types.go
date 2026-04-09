package blockfetcher

import (
	"errors"

	"github.com/ethereum/go-ethereum/core/types"
)

// Error definitions
var (
	ErrMissingRPCURL        = errors.New("RPC URL is required")
	ErrInvalidMaxConcurrent = errors.New("MaxConcurrent must be greater than 0")
	ErrInvalidMaxRetries    = errors.New("MaxRetries must be non-negative")
	ErrInvalidTimeout       = errors.New("RequestTimeout must be greater than 0")
	ErrInvalidBlockRange    = errors.New("EndBlock must be greater than or equal to StartBlock")
	ErrBlockNotFound        = errors.New("block not found")
)

// BlockResult represents the result of fetching a block
type BlockResult struct {
	BlockNumber     uint64
	Block           *types.Block
	FirstTxReceipt  *types.Receipt // Receipt for the first transaction
	SecondTxReceipt *types.Receipt // Receipt for the second transaction
	UserTxCount     int            // Count of user transactions (excluding DepositTxType)
	Error           error
}
