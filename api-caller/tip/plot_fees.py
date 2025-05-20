#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import matplotlib.ticker as ticker

# Read the CSV file
df = pd.read_csv('fees.csv')

# Convert timestamp to datetime for better x-axis labels
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Create a figure with 3 subplots (2 individual and 1 combined)
plt.style.use('bmh')  # Using a built-in style instead of seaborn
fig = plt.figure(figsize=(15, 12))

# Function to format block numbers without scientific notation
def format_block_number(x, pos):
    return f'{int(x):,}'

# Create a formatter for block numbers
block_formatter = ticker.FuncFormatter(format_block_number)

# 1. Plot eth  eth_maxPriorityFeePerGas
ax1 = plt.subplot(411)
ax1.plot(df['block_number'], df['max_priority_fee_gwei'], 'b-', label='ETH Pattern: eth_maxPriorityFeePerGas')
ax1.set_xlabel('Block Number')
ax1.set_ylabel('api result (gwei)', color='b')
ax1.tick_params(axis='y', labelcolor='b')
ax1.set_title('ETH Pattern: eth_maxPriorityFeePerGas Over Time')
ax1.grid(True)
ax1.legend()
# Apply the formatter to x-axis
ax1.xaxis.set_major_formatter(block_formatter)

# 2. Plot gas usage ratio
ax2 = plt.subplot(412)
ax2.plot(df['block_number'], df['gas_usage_ratio'] * 100, 'r-', label='Gas Usage Ratio')
ax2.set_xlabel('Block Number')
ax2.set_ylabel('Gas Usage Ratio (%)', color='r')
ax2.tick_params(axis='y', labelcolor='r')
ax2.set_title('Gas Usage Ratio Over Time')
ax2.grid(True)
ax2.legend()
# Apply the formatter to x-axis
ax2.xaxis.set_major_formatter(block_formatter)

# 3. Plot op eth_maxPriorityFeePerGas
ax3 = plt.subplot(413)
ax3.plot(df['block_number'], [0.001] * len(df), 'g-', label='OP Pattern: eth_maxPriorityFeePerGas')
ax3.set_xlabel('Block Number')
ax3.set_ylabel('api result (gwei)', color='g')
ax3.tick_params(axis='y', labelcolor='g')
ax3.set_title('OP Pattern: eth_maxPriorityFeePerGas Over Time')
ax3.grid(True)
ax3.legend()
# Apply the formatter to x-axis
ax3.xaxis.set_major_formatter(block_formatter)

# 3. Combined plot with dual y-axes
ax4 = plt.subplot(414)
# Create the first y-axis (left)
ax4.plot(df['block_number'], df['max_priority_fee_gwei'], 'b-', label='eth pattern')
ax4.set_xlabel('Block Number')
ax4.set_ylabel('api result (gwei)', color='k')
ax4.tick_params(axis='y', labelcolor='k')
# Apply the formatter to x-axis
ax4.xaxis.set_major_formatter(block_formatter)

# Create the second y-axis (right)
ax4_twin = ax4.twinx()
ax4_twin.plot(df['block_number'], [0.001] * len(df), 'g-', label='op pattern')

# ax4_twin.set_ylabel('op api result (gwei)', color='g')
# ax4_twin.tick_params(axis='y', labelcolor='g')
ax4_twin.set_yticklabels([])
ax4_twin.tick_params(axis='y', length=0)
ax4_twin.spines['right'].set_visible(False)
ax4_twin.set_ylim(ax4.get_ylim())

# Add legends
lines1, labels1 = ax4.get_legend_handles_labels()
lines2, labels2 = ax4_twin.get_legend_handles_labels()
ax4.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

ax4.set_title('ETH & OP Pattern: eth_maxPriorityFeePerGas Over Time')
ax4.grid(True)

# Adjust layout and save
plt.tight_layout()
plt.savefig('fee_analysis.png', dpi=300, bbox_inches='tight')
plt.close()

# Print some statistics
print("\nData Statistics:")
print(f"Total blocks analyzed: {len(df)}")
print(f"Time range: from {df['timestamp'].min()} to {df['timestamp'].max()}")
print("\neth_maxPriorityFeePerGas (gwei):")
print(f"  Min: {df['max_priority_fee_gwei'].min():.3f}")
print(f"  Max: {df['max_priority_fee_gwei'].max():.3f}")
print(f"  Mean: {df['max_priority_fee_gwei'].mean():.3f}")
print("\nGas Usage Ratio:")
print(f"  Min: {df['gas_usage_ratio'].min():.3f}")
print(f"  Max: {df['gas_usage_ratio'].max():.3f}")
print(f"  Mean: {df['gas_usage_ratio'].mean():.3f}") 