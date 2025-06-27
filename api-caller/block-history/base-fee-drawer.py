#!/usr/bin/env python3
"""
Base Fee Calculator and Drawer using EIP-1559 model
Reads block data from CSV and calculates base fee for each block with different elasticity values
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import argparse
import os
from datetime import datetime
from decimal import Decimal, getcontext

# Set precision for decimal arithmetic
getcontext().prec = 50

# EIP-1559 constants
DENOMINATOR = 250           # denominator for base fee calculation

def calculate_base_fee(parent_base_fee, parent_gas_used, parent_gas_limit, elasticity, denominator=None):
    """
    Calculate base fee using EIP-1559 formula based on parent block's data
    
    Args:
        parent_base_fee: Parent block's base fee in wei
        parent_gas_used: Parent block's gas used
        parent_gas_limit: Parent block's gas limit
        elasticity: Elasticity multiplier
        denominator: Denominator value (defaults to global DENOMINATOR if None)
    
    Returns:
        New base fee in wei for the current block
    """
    if denominator is None:
        denominator = DENOMINATOR
        
    target_gas_used = parent_gas_limit // elasticity
    
    if parent_gas_used == target_gas_used:
        return parent_base_fee
    
    # Convert to Decimal for arbitrary-precision arithmetic
    parent_base_fee_dec = Decimal(str(parent_base_fee))
    gas_used_delta_dec = Decimal(str(abs(parent_gas_used - target_gas_used)))
    target_gas_used_dec = Decimal(str(target_gas_used))
    denominator_dec = Decimal(str(denominator))
    
    # Calculate the adjustment factor based on parent block's data
    if parent_gas_used > target_gas_used:
        # Parent block used more gas than target, increase base fee
        base_fee_delta = int((parent_base_fee_dec * gas_used_delta_dec) / (target_gas_used_dec * denominator_dec))
        return parent_base_fee + max(base_fee_delta, 1)
    else:
        # Parent block used less gas than target, decrease base fee
        base_fee_delta = int((parent_base_fee_dec * gas_used_delta_dec) / (target_gas_used_dec * denominator_dec))
        return max(parent_base_fee - base_fee_delta, 0)

def wei_to_gwei(wei):
    """Convert wei to gwei"""
    return wei / 1e9

def gwei_to_wei(gwei):
    """Convert gwei to wei"""
    return int(gwei * 1e9)

def calculate_base_fees_for_elasticity(df_clean, initial_base_fee_gwei, elasticity, denominator=None):
    """Calculate base fees for a specific elasticity value"""
    base_fees_gwei = []
    prev_base_fee_wei = gwei_to_wei(initial_base_fee_gwei)
    
    for idx, row in df_clean.iterrows():
        if idx == 0:
            # First block uses initial base fee
            base_fee_wei = prev_base_fee_wei
        else:
            # Get parent block's data (previous row)
            parent_row = df_clean.iloc[idx - 1]
            # Calculate base fee using EIP-1559 formula based on parent block's data
            base_fee_wei = calculate_base_fee(
                prev_base_fee_wei, 
                parent_row['Gas Used'], 
                parent_row['Gas Limit'],
                elasticity,
                denominator
            )
        
        base_fees_gwei.append(wei_to_gwei(base_fee_wei))
        prev_base_fee_wei = base_fee_wei
    
    return base_fees_gwei

def calculate_base_fees_for_elasticity_and_denominator(df_clean, initial_base_fee_gwei, elasticity, denominator):
    """Calculate base fees for a specific elasticity and denominator combination"""
    base_fees_gwei = []
    prev_base_fee_wei = gwei_to_wei(initial_base_fee_gwei)
    
    for idx, row in df_clean.iterrows():
        if idx == 0:
            # First block uses initial base fee
            base_fee_wei = prev_base_fee_wei
        else:
            # Get parent block's data (previous row)
            parent_row = df_clean.iloc[idx - 1]
            # Calculate base fee using EIP-1559 formula based on parent block's data with custom denominator
            base_fee_wei = calculate_base_fee(
                prev_base_fee_wei, 
                parent_row['Gas Used'], 
                parent_row['Gas Limit'],
                elasticity,
                denominator
            )
        
        base_fees_gwei.append(wei_to_gwei(base_fee_wei))
        prev_base_fee_wei = base_fee_wei
    
    return base_fees_gwei

def main():
    parser = argparse.ArgumentParser(description='Calculate and draw base fee from block data with different elasticity values')
    parser.add_argument('--csv', type=str, help='CSV file with block data', required=True)
    parser.add_argument('--initial-base-fee', type=float, default=0.02, 
                       help='Initial base fee in gwei (default: 0.02)')
    parser.add_argument('--output', type=str, default='base_fee_elasticity_comparison.png',
                       help='Output plot filename (default: base_fee_elasticity_comparison.png)')
    parser.add_argument('--show-gas-usage', action='store_true',
                       help='Show gas usage ratio on secondary y-axis')
    
    args = parser.parse_args()
    
    # Define elasticity values to test
    # elasticity_values = [2, 5, 10, 20, 50]
    # elasticity_values = [72, 74, 75, 76, 77, 78, 79, 80]
    elasticity_values = [75]
    
    # Define denominator values to test
    # When elasticity_values has >1 element, denominator_values should have only 1 element
    # When elasticity_values has 1 element, denominator_values can have multiple elements
    denominator_values = [100, 200, 250, 300, 400]
    
    # Validate the configuration
    if len(elasticity_values) > 1 and len(denominator_values) > 1:
        print("Error: When comparing multiple elasticities, only one denominator value should be specified")
        print("Current: {} elasticities, {} denominators".format(len(elasticity_values), len(denominator_values)))
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
    df_clean = df_clean.sort_values('Block Number').reset_index(drop=True)
    
    print("Processing {} valid blocks".format(len(df_clean)))
    
    # Determine if we're comparing elasticities or denominators
    if len(elasticity_values) == 1:
        # Compare different denominators with same elasticity
        single_elasticity = elasticity_values[0]
        print("Comparing denominators with elasticity = {}".format(single_elasticity))
        
        # Calculate base fees for each denominator value
        all_base_fees = {}
        for denominator in denominator_values:
            print("Calculating base fees for denominator = {}".format(denominator))
            base_fees = calculate_base_fees_for_elasticity_and_denominator(df_clean, args.initial_base_fee, single_elasticity, denominator)
            all_base_fees[denominator] = base_fees
        
        # Update plot labels and titles
        plot_labels = ['D={}'.format(d) for d in denominator_values]
        comparison_type = "Denominator"
        comparison_values = denominator_values
    else:
        # Compare different elasticities with same denominator
        single_denominator = denominator_values[0]
        print("Comparing elasticities with denominator = {}".format(single_denominator))
        
        # Calculate base fees for each elasticity value
        all_base_fees = {}
        for elasticity in elasticity_values:
            print("Calculating base fees for elasticity = {}".format(elasticity))
            base_fees = calculate_base_fees_for_elasticity(df_clean, args.initial_base_fee, elasticity, single_denominator)
            all_base_fees[elasticity] = base_fees
        
        # Update plot labels and titles
        plot_labels = ['E={}'.format(e) for e in elasticity_values]
        comparison_type = "Elasticity"
        comparison_values = elasticity_values
    
    # Create the plot with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), height_ratios=[2, 1])
    
    # Define colors for different elasticity values
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
    
    # Plot base fee for each elasticity value on main plot
    for i, elasticity in enumerate(comparison_values):
        color = colors[i % len(colors)]
        ax1.plot(df_clean['Block Number'], all_base_fees[elasticity], 
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
    for i, elasticity in enumerate(comparison_values):
        color = colors[i % len(colors)]
        tail_base_fees = all_base_fees[elasticity][tail_start:]
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
        ax1_twin.set_ylabel('Gas Usage Ratio', color=color2, fontsize=12)
        gas_usage_ratio = df_clean['Gas Used'] / df_clean['Gas Limit']
        line2 = ax1_twin.plot(df_clean['Block Number'], gas_usage_ratio, 
                        color=color2, linewidth=1, alpha=0.7, label='Gas Usage Ratio')
        ax1_twin.tick_params(axis='y', labelcolor=color2)
        
        # Add horizontal lines for target ratios of different elasticity values
        for i, value in enumerate(comparison_values):
            if comparison_type == "Elasticity":
                target_ratio = 1.0 / value
                label = 'Target E={} ({:.1%})'.format(value, target_ratio)
            else:  # Denominator comparison
                target_ratio = 1.0 / single_elasticity  # Same target for all denominators
                label = 'Target E={} ({:.1%})'.format(single_elasticity, target_ratio)
            ax1_twin.axhline(y=target_ratio, color=colors[i % len(colors)], linestyle='--', alpha=0.3, 
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
    if len(elasticity_values) == 1:
        # Comparing denominators, show the single elasticity
        single_param = "E={}".format(elasticity_values[0])
    else:
        # Comparing elasticities, show the single denominator
        single_param = "D={}".format(denominator_values[0])
    
    fig.suptitle('Base Fee Evolution Comparison (EIP-1559)\nInitial: {} gwei, {}'.format(args.initial_base_fee, single_param), 
                 fontsize=14, fontweight='bold')
    
    # Adjust layout
    plt.tight_layout()
    
    # Save plot
    plt.savefig(args.output, dpi=300, bbox_inches='tight')
    print("Plot saved as {}".format(args.output))
    
    # Print statistics for each elasticity value
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
    for elasticity in comparison_values:
        df_output['Base_Fee_{}'.format(plot_labels[comparison_values.index(elasticity)])] = all_base_fees[elasticity]
    df_output.to_csv(output_csv, index=False)
    print("\nCalculated data saved as {}".format(output_csv))
    
    plt.show()

if __name__ == "__main__":
    main()
