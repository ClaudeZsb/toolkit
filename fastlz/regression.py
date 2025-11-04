import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import datetime
import matplotlib.pyplot as plt

dt = np.dtype([('block', '<u4'), ('best', '<u4'), ('fastlz', '<u4'), ('zeroes', '<u4'), ('ones', '<u4')])
op_mainnet = np.fromfile('./data/fastlz.bin', dtype=dt)
input_array = np.array(op_mainnet.tolist())
print(f'input_array length: {len(input_array)}')
# base_mainnet = np.fromfile('./base-mainnet.bin', dtype=dt)
# input_array = np.concatenate((input_array, np.array(base_mainnet.tolist())))

op_mainnet_genesis_time = datetime.datetime.fromtimestamp(1728130312)
op_mainnet_genesis_block = 70000000
block_time = 2
signature_omitted = False

blocks_per_day = 60*60*24 // block_time

# Group data by month
# Calculate month index (year*12 + month) for each block
genesis_timestamp = int(op_mainnet_genesis_time.timestamp())
month_indices = []
for block_num in input_array[:, 0]:
    block_timestamp = genesis_timestamp + (block_num - op_mainnet_genesis_block) * block_time
    block_date = datetime.datetime.fromtimestamp(block_timestamp).date()
    month_idx = block_date.year * 12 + block_date.month - 1
    month_indices.append(month_idx)

month_indices = np.array(month_indices)
unique_months = np.sort(np.unique(month_indices))

# Regression on all data
print("\n=== Regression on All Data ===")
x_all = input_array[:, 2].reshape(-1, 1)  # fastlz column, reshaped to 2D
y_all = input_array[:, 1]  # best column

all_data_model = LinearRegression().fit(x_all, y_all)
y_pred_all = all_data_model.predict(x_all)
r2_all = r2_score(y_all, y_pred_all)
rmse_all = np.sqrt(mean_squared_error(y_all, y_pred_all))
mae_all = mean_absolute_error(y_all, y_pred_all)

print(f'All Data Model: zlib_best = {all_data_model.intercept_:.6f} + {all_data_model.coef_[0]:.6f} * fastlz')
print(f'R² Score: {r2_all:.6f}')
print(f'RMSE: {rmse_all:.6f}')
print(f'MAE: {mae_all:.6f}')
print(f'Sample Count: {len(input_array)}')

# Store regression results for plotting
month_labels = []
intercepts = []
coefficients = []
sample_counts = []
r2_scores = []
rmse_scores = []
mae_scores = []

print("\n=== Monthly Regression Results ===")
print(f'month,intercept,coefficient,sample_count,r2_score,rmse,mae')
for month_idx in unique_months:
    # Get data for this month
    month_mask = month_indices == month_idx
    month_data = input_array[month_mask]
    
    if len(month_data) == 0:
        continue
    
    # Prepare training data
    x_month = month_data[:, 2].reshape(-1, 1)  # fastlz column, reshaped to 2D
    y_month = month_data[:, 1]  # best column
    
    # Train fastlz model for this month
    fastlz_model = LinearRegression().fit(x_month, y_month)
    
    # Calculate metrics
    y_pred_month = fastlz_model.predict(x_month)
    r2_month = r2_score(y_month, y_pred_month)
    rmse_month = np.sqrt(mean_squared_error(y_month, y_pred_month))
    mae_month = mean_absolute_error(y_month, y_pred_month)
    
    # Get month date for display (convert month_idx back to year-month)
    year = month_idx // 12
    month = (month_idx % 12) + 1
    month_str = f"{year}-{month:02d}"
    
    # Store results
    month_labels.append(month_str)
    intercepts.append(fastlz_model.intercept_)
    coefficients.append(fastlz_model.coef_[0])
    sample_counts.append(len(month_data))
    r2_scores.append(r2_month)
    rmse_scores.append(rmse_month)
    mae_scores.append(mae_month)
    
    print(f'{month_str},{fastlz_model.intercept_:.6f},{fastlz_model.coef_[0]:.6f},{len(month_data)},{r2_month:.6f},{rmse_month:.6f},{mae_month:.6f}')

# Create visualizations
print("\nCreating monthly regression visualization...")

# Create figure with two subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

# Convert month labels to datetime for better x-axis formatting
month_dates = [datetime.datetime.strptime(label, "%Y-%m") for label in month_labels]

# Plot intercept over time
ax1.plot(month_dates, intercepts, marker='o', linewidth=2, markersize=6, color='blue', alpha=0.7, label='Monthly')
ax1.axhline(y=all_data_model.intercept_, color='green', linestyle='--', linewidth=2, label=f'All Data (intercept={all_data_model.intercept_:.2f})')
ax1.set_xlabel('Month', fontsize=12)
ax1.set_ylabel('Intercept', fontsize=12)
ax1.set_title('Monthly Regression Intercept Over Time', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.tick_params(axis='x', rotation=45)
ax1.legend()

# Format x-axis dates
fig.autofmt_xdate()

# Plot coefficient over time
ax2.plot(month_dates, coefficients, marker='s', linewidth=2, markersize=6, color='red', alpha=0.7, label='Monthly')
ax2.axhline(y=all_data_model.coef_[0], color='green', linestyle='--', linewidth=2, label=f'All Data (coef={all_data_model.coef_[0]:.6f})')
ax2.set_xlabel('Month', fontsize=12)
ax2.set_ylabel('FastLZ Coefficient', fontsize=12)
ax2.set_title('Monthly Regression Coefficient (FastLZ) Over Time', fontsize=14, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.tick_params(axis='x', rotation=45)
ax2.legend()

plt.tight_layout()
plt.savefig('monthly_regression_results.png', dpi=300, bbox_inches='tight')
print(f"Visualization saved as 'monthly_regression_results.png'")

# Create a combined plot showing both metrics
fig2, ax = plt.subplots(figsize=(14, 6))

# Plot intercept on left y-axis
ax.plot(month_dates, intercepts, marker='o', linewidth=2, markersize=6, color='blue', alpha=0.7, label='Intercept (Monthly)')
ax.axhline(y=all_data_model.intercept_, color='green', linestyle='--', linewidth=2, label=f'Intercept (All Data)')
ax.set_xlabel('Month', fontsize=12)
ax.set_ylabel('Intercept', fontsize=12, color='blue')
ax.tick_params(axis='y', labelcolor='blue')
ax.tick_params(axis='x', rotation=45)

# Plot coefficient on right y-axis
ax2_right = ax.twinx()
ax2_right.plot(month_dates, coefficients, marker='s', linewidth=2, markersize=6, color='red', alpha=0.7, label='Coefficient (Monthly)')
ax2_right.axhline(y=all_data_model.coef_[0], color='orange', linestyle='--', linewidth=2, label=f'Coefficient (All Data)')
ax2_right.set_ylabel('FastLZ Coefficient', fontsize=12, color='red')
ax2_right.tick_params(axis='y', labelcolor='red')

ax.set_title('Monthly Regression Results: Intercept and Coefficient Over Time', fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3)

# Add legend
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2_right.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, loc='best')

fig2.autofmt_xdate()
plt.tight_layout()
plt.savefig('monthly_regression_combined.png', dpi=300, bbox_inches='tight')
print(f"Combined visualization saved as 'monthly_regression_combined.png'")

# Create visualization for regression quality metrics
fig3, (ax3, ax4, ax5) = plt.subplots(3, 1, figsize=(14, 12))

# Plot R² scores
ax3.plot(month_dates, r2_scores, marker='o', linewidth=2, markersize=6, color='purple', alpha=0.7)
ax3.axhline(y=r2_all, color='green', linestyle='--', linewidth=2, label=f'All Data (R²={r2_all:.6f})')
ax3.set_xlabel('Month', fontsize=12)
ax3.set_ylabel('R² Score', fontsize=12)
ax3.set_title('Monthly Regression R² Score Over Time', fontsize=14, fontweight='bold')
ax3.grid(True, alpha=0.3)
ax3.tick_params(axis='x', rotation=45)
ax3.legend()

# Plot RMSE
ax4.plot(month_dates, rmse_scores, marker='s', linewidth=2, markersize=6, color='orange', alpha=0.7)
ax4.axhline(y=rmse_all, color='green', linestyle='--', linewidth=2, label=f'All Data (RMSE={rmse_all:.2f})')
ax4.set_xlabel('Month', fontsize=12)
ax4.set_ylabel('RMSE', fontsize=12)
ax4.set_title('Monthly Regression RMSE Over Time', fontsize=14, fontweight='bold')
ax4.grid(True, alpha=0.3)
ax4.tick_params(axis='x', rotation=45)
ax4.legend()

# Plot MAE
ax5.plot(month_dates, mae_scores, marker='^', linewidth=2, markersize=6, color='brown', alpha=0.7)
ax5.axhline(y=mae_all, color='green', linestyle='--', linewidth=2, label=f'All Data (MAE={mae_all:.2f})')
ax5.set_xlabel('Month', fontsize=12)
ax5.set_ylabel('MAE', fontsize=12)
ax5.set_title('Monthly Regression MAE Over Time', fontsize=14, fontweight='bold')
ax5.grid(True, alpha=0.3)
ax5.tick_params(axis='x', rotation=45)
ax5.legend()

fig3.autofmt_xdate()
plt.tight_layout()
plt.savefig('monthly_regression_metrics.png', dpi=300, bbox_inches='tight')
print(f"Metrics visualization saved as 'monthly_regression_metrics.png'")
