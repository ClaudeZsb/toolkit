# Base Fee Calculator and Drawer

This Python script calculates and visualizes the base fee evolution using the EIP-1559 model from block data fetched by the Go program.

## Features

- **EIP-1559 Base Fee Calculation**: Implements the exact EIP-1559 formula with:
  - Elasticity multiplier: 2
  - Denominator: 250
- **Visualization**: Creates plots showing base fee evolution over time
- **Gas Usage Analysis**: Optional secondary axis showing gas usage ratios
- **Statistics**: Provides min, max, average, and final base fee values
- **Data Export**: Saves calculated base fees to CSV

## Installation

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

```bash
python base-fee-drawer.py --csv block_history_2025-06-26_17-11-29.csv
```

### Advanced Usage

```bash
# Custom initial base fee
python base-fee-drawer.py --csv block_history.csv --initial-base-fee 0.05

# Show gas usage ratio on secondary axis
python base-fee-drawer.py --csv block_history.csv --show-gas-usage

# Custom output filename
python base-fee-drawer.py --csv block_history.csv --output my_base_fee_plot.png

# All options together
python base-fee-drawer.py \
  --csv block_history.csv \
  --initial-base-fee 0.02 \
  --output base_fee_analysis.png \
  --show-gas-usage
```

## Command Line Arguments

- `--csv`: CSV file with block data (required)
- `--initial-base-fee`: Initial base fee in gwei (default: 0.02)
- `--output`: Output plot filename (default: base_fee_plot.png)
- `--show-gas-usage`: Show gas usage ratio on secondary y-axis

## EIP-1559 Formula

The script implements the EIP-1559 base fee calculation:

```
target_gas_used = gas_limit / 2

if gas_used == target_gas_used:
    base_fee = prev_base_fee
else:
    gas_used_delta = abs(gas_used - target_gas_used)
    target_gas_used_delta = target_gas_used
    base_fee_delta = prev_base_fee * gas_used_delta / target_gas_used_delta
    base_fee_per_gas_delta = base_fee_delta / 250
    
    if gas_used > target_gas_used:
        base_fee = prev_base_fee + base_fee_per_gas_delta
    else:
        base_fee = max(prev_base_fee - base_fee_per_gas_delta, 0)
```

## Output Files

1. **Plot Image**: PNG file showing base fee evolution
2. **Data CSV**: CSV file with calculated base fees for each block
3. **Console Output**: Statistics and progress information

## Example Output

```
Loaded 1000 blocks from block_history.csv
Processing 1000 valid blocks
Plot saved as base_fee_plot.png

Base Fee Statistics:
Initial Base Fee: 0.02 gwei
Final Base Fee: 0.045123 gwei
Min Base Fee: 0.015000 gwei
Max Base Fee: 0.078456 gwei
Average Base Fee: 0.032145 gwei
Calculated data saved as base_fee_plot_data.csv
```

## Workflow

1. **Fetch Block Data**: Use the Go program to fetch block data
   ```bash
   go run main.go
   ```

2. **Calculate Base Fees**: Use this Python script to analyze the data
   ```bash
   python base-fee-drawer.py --csv block_history_*.csv
   ```

3. **Analyze Results**: Review the plot and statistics to understand base fee dynamics

## Notes

- The script filters out blocks marked as "ERROR" in the CSV
- Base fees are calculated sequentially, with each block using the previous block's base fee
- The minimum base fee is capped at 0 (cannot go negative)
- Gas usage ratios are calculated as `gas_used / gas_limit` 