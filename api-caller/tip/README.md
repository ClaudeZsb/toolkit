# Priority Fee Monitor

A simple tool to continuously monitor block numbers and max priority fees from an Ethereum node, writing the data to a CSV file.

## Usage

```bash
go run main.go [flags]
```

### Flags

- `-rpc`: RPC URL (default: "http://localhost:8545")
- `-output`: Output file path (default: "fees.csv")
- `-interval`: Interval between checks in seconds (default: 1)

### Example

```bash
# Monitor with default settings
go run main.go

# Monitor with custom settings
go run main.go -rpc http://localhost:8545 -output fees.csv -interval 5
```

### Running in Background

There are several ways to run the monitor in the background:

1. Using `nohup`:
```bash
nohup go run main.go -output fees.csv > monitor.log 2>&1 &
```

2. Using `screen`:
```bash
# Create a new screen session
screen -S fee-monitor

# Run the monitor
go run main.go -output fees.csv

# Detach from screen: Press Ctrl+A, then D
# Reattach to screen: screen -r fee-monitor
```

3. Using `tmux`:
```bash
# Create a new tmux session
tmux new -s fee-monitor

# Run the monitor
go run main.go -output fees.csv

# Detach from tmux: Press Ctrl+B, then D
# Reattach to tmux: tmux attach -t fee-monitor
```

### Process Management

The monitor can be stopped gracefully using:
- Ctrl+C when running in foreground
- `kill` command when running in background:
```bash
# Find the process ID
ps aux | grep "go run main.go"

# Stop the process
kill <PID>

# Or force stop if needed
kill -9 <PID>
```

## Output Format

The tool writes data to a CSV file with the following columns:
- `timestamp`: ISO 8601 formatted timestamp
- `block_number`: Current block number
- `max_priority_fee_gwei`: Max priority fee in gwei

Example output:
```csv
timestamp,block_number,max_priority_fee_gwei
2024-03-21T10:30:00Z,12345678,1.500000000
2024-03-21T10:30:01Z,12345679,1.750000000
```

## Dependencies

- github.com/ethereum/go-ethereum

Run `go mod tidy` to install dependencies.

## Notes

- The monitor will write one data point per block
- The process can be safely stopped at any time using Ctrl+C
- When running in background, make sure to use proper process management to stop the monitor
- The output file is always opened in append mode, so it's safe to restart the monitor 