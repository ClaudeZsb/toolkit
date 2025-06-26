import numpy as np
from sklearn.linear_model import LinearRegression
import datetime
import matplotlib.pyplot as plt

dt = np.dtype([('block', '<u4'), ('best', '<u4'), ('fastlz', '<u4'), ('zeroes', '<u4'), ('ones', '<u4')])
op_mainnet = np.fromfile('./data/fastlz.bin', dtype=dt)
input_array = np.array(op_mainnet.tolist())

# base_mainnet = np.fromfile('./base-mainnet.bin', dtype=dt)
# input_array = np.concatenate((input_array, np.array(base_mainnet.tolist())))

op_mainnet_genesis_time = datetime.datetime.fromtimestamp(1686068905)
op_mainnet_genesis_block = 105235064
block_time = 2
signature_omitted = False
# training_start = datetime.datetime(2023, 10, 1)
# training_end = datetime.datetime(2023, 11, 1)

training_block_start = 81265001
training_block_end = input_array[:, 0].max()  # Use the maximum block available in the data
training_index_start = next(i for i,v in enumerate(input_array) if v[0] == training_block_start)
training_index_end = next(i for i,v in enumerate(input_array) if v[0] == training_block_end)

first_day = datetime.timedelta(days=1) + datetime.datetime.combine(
    op_mainnet_genesis_time.date(), datetime.datetime.min.time())
blocks_on_first_day = (int(first_day.timestamp()) - int(op_mainnet_genesis_time.timestamp())) // block_time
blocks_per_day = 60*60*24 // block_time

# use first 10% of data for regression calculation
x = np.delete(input_array, [0,1], 1)[training_index_end:training_index_start]
y = input_array[:, 1][training_index_end:training_index_start]
fastlz_model = LinearRegression().fit(x, y)
print(f'fastlz_model: {fastlz_model.intercept_} {fastlz_model.coef_}')

x_zeros_ones_combined = np.copy(x)
x_zeros_ones_combined[:, 1] += x_zeros_ones_combined[:, 2]
x_zeros_ones_combined = np.delete(x_zeros_ones_combined, [2], 1)
fastlz_combined_model = LinearRegression().fit(x_zeros_ones_combined, y)
print(f'fastlz_combined_model: {fastlz_combined_model.intercept_} {fastlz_combined_model.coef_}')

x_simple = np.delete(x, [1,2], 1)
fastlz_simple_model = LinearRegression().fit(x_simple, y)
print(f'fastlz_simple_model: {fastlz_simple_model.intercept_} {fastlz_simple_model.coef_}')

x_naive = np.delete(x, [0], 1)
naive_model = LinearRegression().fit(x_naive, y)
print(f'naive_model: {naive_model.intercept_} {naive_model.coef_}')

naive_scalar = np.sum(y) / (np.sum(x[:, 1]*4+x[:, 2]*16)/16)
fastlz_scalar = np.sum(y) / np.sum(x[:, 0])

print(f'naive_scalar: {naive_scalar}')
print(f'fastlz_scalar: {fastlz_scalar}')

normalized = input_array + [blocks_per_day - op_mainnet_genesis_block - blocks_on_first_day, 0, 0, 0, 0]
grouped = normalized // [blocks_per_day, 1, 1, 1, 1]
sorted = grouped[grouped[:, 0].argsort()]
split = np.split(sorted, np.unique(sorted[:, 0], return_index=True)[1][1:])

print()
print(f'date,rms_fastlz_zeroes_ones,rms_fastlz_txsize,rms_fastlz_only,rms_fastlz_no_intercept,rms_naive_with_intercept,rms_naive_no_intercept,ma_fastlz_zeroes_ones,ma_fastlz_txsize,ma_fastlz_only,ma_fastlz_no_intercept,ma_naive_with_intercept,ma_naive_no_intercept,total_fastlz_zeroes_ones,total_fastlz_txsize,total_fastlz_only,total_fastlz_no_intercept,total_naive_with_intercept,total_naive_no_intercept,total_best')
for day in split:
    xd = np.delete(day, [0,1], 1)
    yd = day[:, 1]
    rms = np.sqrt(np.sum(np.power(fastlz_model.predict(xd) - yd, 2)) / np.size(yd))
    ma = np.sum(np.absolute(fastlz_model.predict(xd) - yd)) / np.size(yd)
    total = np.sum(fastlz_model.predict(xd)) + (68*np.size(yd) if signature_omitted else 0)

    xd_zeros_ones_combined = np.copy(xd)
    xd_zeros_ones_combined[:, 1] += xd_zeros_ones_combined[:, 2]
    xd_zeros_ones_combined = np.delete(xd_zeros_ones_combined, [2], 1)
    rms_combined = np.sqrt(np.sum(np.power(fastlz_combined_model.predict(xd_zeros_ones_combined) - yd, 2)) / np.size(yd))
    ma_combined = np.sum(np.absolute(fastlz_combined_model.predict(xd_zeros_ones_combined) - yd)) / np.size(yd)
    total_combined = np.sum(fastlz_combined_model.predict(xd_zeros_ones_combined)) + (68*np.size(yd) if signature_omitted else 0)

    xd_simple = np.delete(xd, [1,2], 1)
    rms_simple = np.sqrt(np.sum(np.power(fastlz_simple_model.predict(xd_simple) - yd, 2)) / np.size(yd))
    ma_simple = np.sum(np.absolute(fastlz_simple_model.predict(xd_simple) - yd)) / np.size(yd)
    total_simple = np.sum(fastlz_simple_model.predict(xd_simple)) + (68*np.size(yd) if signature_omitted else 0)

    rms_fastlz_cheap = np.sqrt(np.sum(np.power(yd - xd[:, 0]*fastlz_scalar, 2)) / np.size(yd))
    ma_fastlz_cheap = np.sum(np.absolute(yd - xd[:, 0]*fastlz_scalar)) / np.size(yd)
    total_fastlz_cheap = np.sum(xd[:, 0]*fastlz_scalar) + (68*np.size(yd) if signature_omitted else 0)

    xd_naive = np.delete(xd, [0], 1)
    rms_naive = np.sqrt(np.sum(np.power(naive_model.predict(xd_naive) - yd, 2)) / np.size(yd))
    ma_naive = np.sum(np.absolute(naive_model.predict(xd_naive) - yd)) / np.size(yd)
    total_naive = np.sum(naive_model.predict(xd_naive)) + (68*np.size(yd) if signature_omitted else 0)

    rms_naive_cheap = np.sqrt(np.sum(np.power(yd - (xd[:, 1]*4+xd[:, 2]*16)/16*naive_scalar, 2)) / np.size(yd))
    ma_naive_cheap = np.sum(np.absolute(yd - (xd[:, 1]*4+xd[:, 2]*16)/16*naive_scalar)) / np.size(yd)
    total_naive_cheap = np.sum((xd[:, 1]*4+xd[:, 2]*16)/16*naive_scalar) + (68*np.size(yd) if signature_omitted else 0)

    total_best = np.sum(yd) + (68*np.size(yd) if signature_omitted else 0)

    print(f'{(op_mainnet_genesis_time+datetime.timedelta(days=int(day[0][0]))).date()},{rms:.2f},{rms_combined:.2f},{rms_simple:.2f},{rms_fastlz_cheap:.2f},{rms_naive:.2f},{rms_naive_cheap:.2f},{ma:.2f},{ma_combined:.2f},{ma_simple:.2f},{ma_fastlz_cheap:.2f},{ma_naive:.2f},{ma_naive_cheap:.2f},{total:.2f},{total_combined:.2f},{total_simple:.2f},{total_fastlz_cheap:.2f},{total_naive:.2f},{total_naive_cheap:.2f},{total_best:.2f}')

# Create visualization of RMSE per block
print("\nCreating RMSE visualization...")

# Group by 100 unique blocks and calculate RMSE for each group
block_group_size = 100
unique_blocks = np.unique(input_array[:, 0])
num_groups = len(unique_blocks) // block_group_size

print(f"Total blocks in data: {len(input_array)}")
print(f"Block range: {input_array[:, 0].min()} to {input_array[:, 0].max()}")
print(f"Number of unique blocks: {len(unique_blocks)}")
print(f"Number of groups (100 unique blocks each): {num_groups}")

group_blocks = []
rmse_simple_per_group = []
rmse_naive_scalar_per_group = []

for i in range(num_groups):
    # Get the block numbers for this group
    group_block_numbers = unique_blocks[i*block_group_size:(i+1)*block_group_size]
    # Mask for all transactions in these blocks
    mask = np.isin(input_array[:, 0], group_block_numbers)
    group_data = input_array[mask]
    
    # Use the first block number as the x-axis value
    first_block = group_block_numbers[0]
    group_blocks.append(first_block)
    
    # Collect all predictions and actual values for this group
    group_predictions_simple = []
    group_predictions_naive_scalar = []
    group_actual_values = []
    
    for block_data in group_data:
        # Simple model prediction (using only fastlz)
        x_simple_block = np.array([[block_data[2]]])  # only fastlz
        pred_simple = fastlz_simple_model.predict(x_simple_block)[0]
        group_predictions_simple.append(pred_simple)
        
        # Naive scalar model prediction
        pred_naive_scalar = (block_data[3]*4 + block_data[4]*16)/16 * naive_scalar
        group_predictions_naive_scalar.append(pred_naive_scalar)
        
        # Actual value
        group_actual_values.append(block_data[1])
    
    # Calculate one RMSE for the entire group
    rmse_simple = np.sqrt(np.mean(np.power(np.array(group_predictions_simple) - np.array(group_actual_values), 2)))
    rmse_naive_scalar = np.sqrt(np.mean(np.power(np.array(group_predictions_naive_scalar) - np.array(group_actual_values), 2)))
    
    rmse_simple_per_group.append(rmse_simple)
    rmse_naive_scalar_per_group.append(rmse_naive_scalar)

# Create the plot
plt.figure(figsize=(12, 6))

# Plot both RMSE lines on the same graph with proper line connections
plt.plot(group_blocks, rmse_simple_per_group, color='blue', alpha=0.8, linewidth=1.5, label='FastLZ Model RMSE')
plt.plot(group_blocks, rmse_naive_scalar_per_group, color='red', alpha=0.8, linewidth=1.5, label='Naive Scalar Model RMSE')

plt.xlabel('Block Number (first block of each 100-block group)')
plt.ylabel('RMSE per 100-block group')
plt.title('RMSE per 100-Block Groups - FastLZ Model vs Naive Scalar Model')
plt.legend()
plt.grid(True, alpha=0.3)

# Format x-axis to show full block numbers without scientific notation
plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))

plt.tight_layout()
plt.savefig('rmse_per_block.png', dpi=300, bbox_inches='tight')
# plt.show()  # Removed to prevent popup

print(f"RMSE visualization saved as 'rmse_per_block.png' (grouped by {block_group_size} blocks)")