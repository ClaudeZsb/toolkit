# Block History Fetcher

This Go program fetches Ethereum block data from the last 24 hours and writes it to a CSV file.

## Features

- Fetches block number, gas used, gas limit, timestamp, and block hash
- Calculates gas utilization percentage
- Writes data to a timestamped CSV file
- Supports custom RPC endpoints via environment variables
- Progress indicators during data fetching

## Prerequisites

- Go 1.21 or later
- Internet connection to access Ethereum RPC endpoints

## Installation

1. Navigate to the project directory:
   ```bash
   cd api-caller/block-history
   ```

2. Install dependencies:
   ```bash
   go mod tidy
   ```

## Usage

### Basic Usage (with demo endpoint)

```bash
go run main.go
```

This will use the default demo RPC endpoint and create a CSV file with the current timestamp.

### Using Custom RPC Endpoint

Create a `.env` file in the project directory:

```env
RPC_URL=https://your-ethereum-rpc-endpoint
```

Then run the program:

```bash
go run main.go
```

### Building the Binary

```bash
go build -o block-history main.go
./block-history
```

## Output

The program creates a CSV file named `block_history_YYYY-MM-DD_HH-MM-SS.csv` containing:

- **Block Number**: The block number
- **Gas Used**: Amount of gas used in the block
- **Gas Limit**: Maximum gas limit for the block
- **Gas Utilization %**: Percentage of gas limit that was used
- **Timestamp**: Unix timestamp of the block
- **Block Hash**: Hexadecimal hash of the block

## Example Output

```csv
Block Number,Gas Used,Gas Limit,Gas Utilization %,Timestamp,Block Hash
19000000,15000000,30000000,50.00,1703123456,0x1234...
19000001,18000000,30000000,60.00,1703123468,0x5678...
```

## Notes

- The program estimates 24 hours of blocks based on an average block time of 12 seconds
- If the RPC endpoint is rate-limited, some blocks may be skipped
- Progress is logged every 100 blocks
- The program handles connection errors gracefully and continues processing

## RPC Endpoint Options

- **Alchemy**: `https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY`
- **Infura**: `https://mainnet.infura.io/v3/YOUR_PROJECT_ID`
- **QuickNode**: `https://your-endpoint.quiknode.pro/YOUR_API_KEY/`
- **Public RPC**: Various public endpoints (may have rate limits) 