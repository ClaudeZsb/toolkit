#!/usr/bin/env python3
"""
Base Fee Calculator and Drawer using Exponential model
Reads block data from CSV and calculates base fee for each block with different speed_limit and inertia values
"""

from math import e
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import argparse
import os
from datetime import datetime
from decimal import Decimal, getcontext

# Set precision for decimal arithmetic
getcontext().prec = 50

# Exponential formula constants
TOLERANCE = 10
BLOCK_TIME = 2  # seconds per block

def calculate_base_fee_exponential(min_base_fee, gas_backlog, speed_limit, tolerance, inertia):
    """
    Calculate base fee using exponential formula based on accumulated gas backlog
    
    Args:
        min_base_fee: Minimum base fee in wei
        gas_backlog: Accumulated gas backlog
        speed_limit: Speed limit for the exponential formula
        tolerance: Tolerance for the exponential formula
        inertia: Inertia for the exponential formula
    
    Returns:
        New base fee in wei for the current block
    """
        
    if gas_backlog <= tolerance * speed_limit:
        return min_base_fee
    
    # Calculate the power based on the accumulated gas backlog
    power = (gas_backlog - tolerance * speed_limit) / (inertia * speed_limit)
    
    # Limit the power to prevent overflow (e^700 is approximately the limit for float64)
    max_power = 700
    power = min(power, max_power)
    
    # Apply the exponential formula with inertia and speed limit
    new_base_fee = min_base_fee * (e ** power)
    
    return new_base_fee

def wei_to_gwei(wei):
    """Convert wei to gwei"""
    return wei / 1e9

def gwei_to_wei(gwei):
    """Convert gwei to wei"""
    return int(gwei * 1e9)

def calculate_base_fees_for_speed_limit(df_clean, initial_base_fee_gwei, speed_limit, inertia, tolerance=None):
    """Calculate base fees for a specific speed_limit value"""
    if tolerance is None:
        tolerance = TOLERANCE
        
    base_fees_gwei = []
    gas_backlog = 0  # Start with no backlog
    min_base_fee_wei = gwei_to_wei(initial_base_fee_gwei)
    
    for idx, row in df_clean.iterrows():
        if idx == 0:
            # First block uses initial base fee
            base_fee_wei = min_base_fee_wei
        else:
            # Get parent block's gas used (previous row)
            parent_gas_used = df_clean.iloc[idx - 1]['Gas Used']
            
            # Update gas backlog: last_backlog + parent_block_gas_used - block_time * speed_limit
            gas_backlog = gas_backlog + parent_gas_used - BLOCK_TIME * speed_limit
            
            # Ensure backlog doesn't go negative
            gas_backlog = max(gas_backlog, 0)
            
            # Calculate base fee using exponential formula
            base_fee_wei = calculate_base_fee_exponential(min_base_fee_wei, gas_backlog, speed_limit, tolerance, inertia)
        
        base_fees_gwei.append(wei_to_gwei(base_fee_wei))
    
    return base_fees_gwei

def calculate_base_fees_for_inertia(df_clean, initial_base_fee_gwei, speed_limit, inertia, tolerance=None):
    """Calculate base fees for a specific inertia value"""
    if tolerance is None:
        tolerance = TOLERANCE
        
    base_fees_gwei = []
    gas_backlog = 0  # Start with no backlog
    min_base_fee_wei = gwei_to_wei(initial_base_fee_gwei)
    
    for idx, row in df_clean.iterrows():
        if idx == 0:
            # First block uses initial base fee
            base_fee_wei = min_base_fee_wei
        else:
            # Get parent block's gas used (previous row)
            parent_gas_used = df_clean.iloc[idx - 1]['Gas Used']
            
            # Update gas backlog: last_backlog + parent_block_gas_used - block_time * speed_limit
            gas_backlog = gas_backlog + parent_gas_used - BLOCK_TIME * speed_limit
            
            # Ensure backlog doesn't go negative
            gas_backlog = max(gas_backlog, 0)
            
            # Calculate base fee using exponential formula
            base_fee_wei = calculate_base_fee_exponential(min_base_fee_wei, gas_backlog, speed_limit, tolerance, inertia)
        
        base_fees_gwei.append(wei_to_gwei(base_fee_wei))
    
    return base_fees_gwei

def main():
    parser = argparse.ArgumentParser(description='Calculate and draw base fee from block data using exponential model with different speed_limit and inertia values')
    parser.add_argument('--csv', type=str, help='CSV file with block data', required=True)
    parser.add_argument('--initial-base-fee', type=float, default=0.02, 
                       help='Initial base fee in gwei (default: 0.02)')
    parser.add_argument('--output', type=str, default='base_fee_exponential_comparison.png',
                       help='Output plot filename (default: base_fee_exponential_comparison.png)')
    parser.add_argument('--show-gas-usage', action='store_true',
                       help='Show gas usage ratio on secondary y-axis')
    
    args = parser.parse_args()
    
    # Define speed_limit values to test
    speed_limit_values = [2400000000, 2600000000, 2800000000]
    # speed_limit_values = [2400000000]
    
    # Define inertia values to test
    # When speed_limit_values has >1 element, inertia_values should have only 1 element
    # When speed_limit_values has 1 element, inertia_values can have multiple elements
    inertia_values = [250]
    # inertia_values = [50, 75, 100, 125, 150]
    
    # Validate the configuration
    if len(speed_limit_values) > 1 and len(inertia_values) > 1:
        print("Error: When comparing multiple speed_limits, only one inertia value should be specified")
        print("Current: {} speed_limits, {} inertias".format(len(speed_limit_values), len(inertia_values)))
        return
    
    # Check if CSV file exists
    if not os.path.exists(args.csv):
        print("Error: CSV file '{}' not found".format(args.csv))
        return
    
    # Read CSV data
    try:
        df = pd.read_csv(args.csv)
        print("Loaded {} blocks from {}".format(len(df), args.csv))
    except Exception as e:
        print("Error reading CSV file: {}".format(e))
        return
    
    # Check required columns
    required_columns = ['Block Number', 'Gas Used', 'Gas Limit']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print("Error: Missing required columns: {}".format(missing_columns))
        return
    
    # Filter out error rows
    df_clean = df[df['Gas Used'] != 'ERROR'].copy()
    if len(df_clean) == 0:
        print("Error: No valid block data found in CSV")
        return
    
    # Convert to numeric
    df_clean['Block Number'] = pd.to_numeric(df_clean['Block Number'])
    df_clean['Gas Used'] = pd.to_numeric(df_clean['Gas Used'])
    df_clean['Gas Limit'] = pd.to_numeric(df_clean['Gas Limit'])
    
    # Sort by block number
    df_clean = df_clean.sort_values(by='Block Number', ignore_index=True)  # type: ignore
    
    print("Processing {} valid blocks".format(len(df_clean)))
    
    # Determine if we're comparing speed_limits or inertias
    if len(speed_limit_values) == 1:
        # Compare different inertias with same speed_limit
        single_speed_limit = speed_limit_values[0]
        print("Comparing inertias with speed_limit = {}".format(single_speed_limit))
        
        # Calculate base fees for each inertia value
        all_base_fees = {}
        for inertia in inertia_values:
            print("Calculating base fees for inertia = {}".format(inertia))
            base_fees = calculate_base_fees_for_inertia(df_clean, args.initial_base_fee, single_speed_limit, inertia)
            all_base_fees[inertia] = base_fees
        
        # Update plot labels and titles
        plot_labels = ['I={}'.format(i) for i in inertia_values]
        comparison_type = "Inertia"
        comparison_values = inertia_values
    else:
        # Compare different speed_limits with same inertia
        single_inertia = inertia_values[0]
        print("Comparing speed_limits with inertia = {}".format(single_inertia))
        
        # Calculate base fees for each speed_limit value
        all_base_fees = {}
        for speed_limit in speed_limit_values:
            print("Calculating base fees for speed_limit = {}".format(speed_limit))
            base_fees = calculate_base_fees_for_speed_limit(df_clean, args.initial_base_fee, speed_limit, single_inertia)
            all_base_fees[speed_limit] = base_fees
        
        # Update plot labels and titles
        plot_labels = ['SL={}'.format(sl) for sl in speed_limit_values]
        comparison_type = "Speed Limit"
        comparison_values = speed_limit_values
    
    # Create the plot with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), height_ratios=[2, 1])
    
    # Define colors for different values
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
    
    # Plot base fee for each value on main plot
    for i, value in enumerate(comparison_values):
        color = colors[i % len(colors)]
        ax1.plot(df_clean['Block Number'], all_base_fees[value], 
                color=color, linewidth=1.5, label=plot_labels[i])
    
    ax1.set_xlabel('Block Number', fontsize=12)
    ax1.set_ylabel('Base Fee (gwei)', fontsize=12)
    ax1.tick_params(axis='y')
    
    # Format x-axis to show full block numbers without scientific notation
    ax1.ticklabel_format(style='plain', axis='x', useOffset=False)
    
    # Add grid
    ax1.grid(True, alpha=0.3)
    
    # Create zoomed-in view of the tail (last 40% of blocks)
    tail_start = int(len(df_clean) * 0.6)
    tail_blocks = df_clean['Block Number'].iloc[tail_start:]
    
    # Plot tail section with exaggerated y-axis
    for i, value in enumerate(comparison_values):
        color = colors[i % len(colors)]
        tail_base_fees = all_base_fees[value][tail_start:]
        ax2.plot(tail_blocks, tail_base_fees, 
                color=color, linewidth=2, label=plot_labels[i])
    
    ax2.set_xlabel('Block Number', fontsize=12)
    ax2.set_ylabel('Base Fee (gwei) - Zoomed', fontsize=12)
    ax2.tick_params(axis='y')
    ax2.ticklabel_format(style='plain', axis='x', useOffset=False)
    ax2.grid(True, alpha=0.3)
    ax2.set_title('Zoomed View of Last 40% of Blocks', fontsize=12, fontweight='bold')
    
    if args.show_gas_usage:
        # Plot gas usage ratio on secondary y-axis of main plot
        ax1_twin = ax1.twinx()
        color2 = '#ff7f0e'
        ax1_twin.set_ylabel('Gas Usage Ratio (100-block avg)', color=color2, fontsize=12)
        
        # Calculate gas usage ratio
        gas_usage_ratio = df_clean['Gas Used'] / df_clean['Gas Limit']
        
        # Calculate average gas usage for every 100 blocks
        block_numbers = df_clean['Block Number'].to_numpy()
        gas_usage_ratio_np = gas_usage_ratio.to_numpy()
        avg_gas_usage_100 = []
        avg_block_numbers = []
        
        for i in range(0, len(gas_usage_ratio_np), 100):
            end_idx = min(i + 100, len(gas_usage_ratio_np))
            avg_ratio = np.mean(gas_usage_ratio_np[i:end_idx])
            avg_block_num = np.mean(block_numbers[i:end_idx])
            avg_gas_usage_100.append(avg_ratio)
            avg_block_numbers.append(avg_block_num)
        
        line2 = ax1_twin.plot(avg_block_numbers, avg_gas_usage_100, 
                        color=color2, linewidth=2, alpha=0.8, label='Gas Usage Ratio (100-block avg)')
        ax1_twin.tick_params(axis='y', labelcolor=color2)
        
        # Add horizontal lines for target ratios based on speed_limit
        if comparison_type == "Speed Limit":
            for i, value in enumerate(comparison_values):
                # For exponential model, target is based on speed_limit
                target_ratio = BLOCK_TIME * value / df_clean['Gas Limit'].mean()
                label = 'Target SL={} ({:.1%})'.format(value, target_ratio)
                ax1_twin.axhline(y=target_ratio, color=colors[i % len(colors)], linestyle='--', alpha=0.3, 
                           label=label)
        else:  # Inertia comparison
            # Only draw once since all inertias have the same target ratio
            target_ratio = BLOCK_TIME * single_speed_limit / df_clean['Gas Limit'].mean()
            label = 'Target SL={} ({:.1%})'.format(single_speed_limit, target_ratio)
            ax1_twin.axhline(y=target_ratio, color=colors[0], linestyle='--', alpha=0.3, 
                       label=label)
        
        # Combine legends for main plot
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax1_twin.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)
    else:
        ax1.legend(loc='upper left', fontsize=10)
    
    # Add legend for zoomed plot
    ax2.legend(loc='upper left', fontsize=10)
    
    # Set title for the entire figure
    if len(speed_limit_values) == 1:
        # Comparing inertias, show the single speed_limit
        single_param = "SL={}".format(speed_limit_values[0])
    else:
        # Comparing speed_limits, show the single inertia
        single_param = "I={}".format(inertia_values[0])
    
    fig.suptitle('Base Fee Evolution Comparison (Exponential Model)\nInitial: {} gwei, {}'.format(args.initial_base_fee, single_param), 
                 fontsize=14, fontweight='bold')
    
    # Adjust layout
    plt.tight_layout()
    
    # Save plot
    plt.savefig(args.output, dpi=300, bbox_inches='tight')
    print("Plot saved as {}".format(args.output))
    
    # Print statistics for each value
    print("\nBase Fee Statistics:")
    print("Initial Base Fee: {} gwei".format(args.initial_base_fee))
    print("\n{} | Final Base Fee | Min Base Fee | Max Base Fee | Avg Base Fee".format(comparison_type))
    print("-" * 70)
    
    for value in comparison_values:
        base_fees = all_base_fees[value]
        print("{}     | {:12.9f} | {:11.9f} | {:11.9f} | {:11.9f}".format(
            plot_labels[comparison_values.index(value)], base_fees[-1], min(base_fees), max(base_fees), np.mean(base_fees)))
    
    # Calculate and print gas usage statistics
    gas_usage_ratio = df_clean['Gas Used'] / df_clean['Gas Limit']
    avg_gas_usage = np.mean(gas_usage_ratio) * 100
    median_gas_usage = np.median(gas_usage_ratio) * 100
    
    print("\nGas Usage Statistics:")
    print("Average Block Usage: {:.3f}%".format(avg_gas_usage))
    print("Median Block Usage: {:.3f}%".format(median_gas_usage))
    print("Min Block Usage: {:.3f}%".format(np.min(gas_usage_ratio) * 100))
    print("Max Block Usage: {:.3f}%".format(np.max(gas_usage_ratio) * 100))
    print("Total Blocks Analyzed: {}".format(len(df_clean)))
    print("Start Block Number: {}".format(df_clean['Block Number'].iloc[0]))
    print("End Block Number: {}".format(df_clean['Block Number'].iloc[-1]))
    
    # Save calculated data
    output_csv = args.output.replace('.png', '_data.csv')
    df_output = df_clean[['Block Number', 'Gas Used', 'Gas Limit']].copy()
    for value in comparison_values:
        df_output['Base_Fee_{}'.format(plot_labels[comparison_values.index(value)])] = all_base_fees[value]
    df_output.to_csv(output_csv, index=False)
    print("\nCalculated data saved as {}".format(output_csv))
    
    plt.show()

if __name__ == "__main__":
    main()