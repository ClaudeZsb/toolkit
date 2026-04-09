#!/usr/bin/env python3

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import matplotlib.pyplot as plt
import seaborn as sns

def main():
    # Read the CSV files
    proofs_df = pd.read_csv('succinct_2026q1.csv')
    input_df = pd.read_csv('mantle_2026q1.csv')

    # Compute bpgus from gas_used (billion proving gas units)
    proofs_df['bpgus'] = proofs_df['gas_used'] / 1e9

    # Normalize date columns for merging
    proofs_df['date'] = pd.to_datetime(proofs_df['date']).dt.strftime('%Y-%m-%d')
    input_df['date'] = pd.to_datetime(input_df['day']).dt.strftime('%Y-%m-%d')

    # Compute Tx Count and Gas Consumed
    input_df['Tx Count'] = input_df['total_tx']
    input_df['Gas Consumed'] = input_df['total_nonsystem_gas_eth'] + 51000 * 43200

    # Merge on date
    merged_df = pd.merge(
        proofs_df,
        input_df,
        on='date',
        how='inner'
    )
    
    print("=" * 60)
    print("DATA SUMMARY")
    print("=" * 60)
    print(f"Total matching dates: {len(merged_df)}")
    print(f"\nDate range: {merged_df['date'].min()} to {merged_df['date'].max()}")
    print("\nFirst few rows:")
    print(merged_df[['date', 'bpgus', 'Tx Count', 'Gas Consumed']].head())
    print("\n" + "=" * 60)
    
    # Multiple regression: bpgus ~ Tx Count + Gas Consumed
    y = merged_df['bpgus'].values
    print("\n" + "=" * 60)
    print("MULTIPLE REGRESSION: bpgus ~ Tx Count + Gas Consumed")
    print("=" * 60)
    
    X_multi = merged_df[['Tx Count', 'Gas Consumed']].values
    model_multi = LinearRegression()
    model_multi.fit(X_multi, y)
    y_pred_multi = model_multi.predict(X_multi)
    r2_multi = r2_score(y, y_pred_multi)
    
    print(f"\nLinear Model: bpgus = {model_multi.intercept_:.2f} + {model_multi.coef_[0]:.6f} * Tx_Count + {model_multi.coef_[1]:.10f} * Gas_Consumed")
    print(f"R² Score: {r2_multi:.4f}")
    print(f"Mean Absolute Error: {np.mean(np.abs(y - y_pred_multi)):.2f}")
    
    # Calculate residuals and find outliers
    merged_df['Predicted_bpgus'] = y_pred_multi
    merged_df['Residual'] = merged_df['bpgus'] - merged_df['Predicted_bpgus']
    merged_df['Abs_Residual'] = merged_df['Residual'].abs()
    
    # Find the 3 dates with largest absolute residuals
    outliers = merged_df.nlargest(3, 'Abs_Residual')[['date', 'bpgus', 'Tx Count', 'Gas Consumed', 'Predicted_bpgus', 'Residual']]
    
    print("\n" + "=" * 60)
    print("OUTLIERS: Top 3 dates with largest prediction errors")
    print("=" * 60)
    outlier_dates = outliers['date'].values
    for idx, row in outliers.iterrows():
        print(f"\nDate: {row['date']}")
        print(f"  Actual bpgus: {row['bpgus']:.2f}")
        print(f"  Predicted bpgus: {row['Predicted_bpgus']:.2f}")
        print(f"  Residual (error): {row['Residual']:.2f}")
        print(f"  Tx Count: {row['Tx Count']:,}")
        print(f"  Gas Consumed: {row['Gas Consumed']:,}")
    
    # Retrain model without outliers
    print("\n" + "=" * 60)
    print("MODEL RETRAINED WITHOUT OUTLIERS")
    print("=" * 60)
    
    # Create filtered dataset without outliers
    filtered_df = merged_df[~merged_df['date'].isin(outlier_dates)].copy()
    y_filtered = filtered_df['bpgus'].values
    X_filtered = filtered_df[['Tx Count', 'Gas Consumed']].values
    
    # Train new model on filtered data
    model_filtered = LinearRegression()
    model_filtered.fit(X_filtered, y_filtered)
    y_pred_filtered_train = model_filtered.predict(X_filtered)
    r2_filtered_train = r2_score(y_filtered, y_pred_filtered_train)
    
    # Predict on full dataset (including outliers) with filtered model for visualization
    y_pred_filtered_full = model_filtered.predict(X_multi)
    
    # Add predictions from filtered model to dataframe (for visualization, including outliers)
    merged_df['Predicted_bpgus_filtered'] = y_pred_filtered_full
    merged_df['Residual_filtered'] = merged_df['bpgus'] - merged_df['Predicted_bpgus_filtered']
    
    print(f"\nModel trained on {len(filtered_df)} data points (removed {len(outlier_dates)} outliers)")
    print(f"\nLinear Model (without outliers): bpgus = {model_filtered.intercept_:.2f} + {model_filtered.coef_[0]:.6f} * Tx_Count + {model_filtered.coef_[1]:.10f} * Gas_Consumed")
    print(f"\nPerformance (without outliers):")
    print(f"  R² Score: {r2_filtered_train:.4f}")
    print(f"  Mean Absolute Error: {np.mean(np.abs(y_filtered - y_pred_filtered_train)):.2f}")
    
    # Calculate mean transaction count and gas consumed per day for filtered data
    mean_tx_count = filtered_df['Tx Count'].mean()
    mean_gas_consumed = filtered_df['Gas Consumed'].mean()
    print(f"\nMean transaction count per day (without outliers): {mean_tx_count:,.2f}")
    print(f"Mean gas consumed per day (without outliers): {mean_gas_consumed:,.2f}")
    print(f"Mean gas consumed per transaction (without outliers): {mean_gas_consumed / mean_tx_count:,.2f}")
    
    print("\n" + "=" * 60)
    print("COMPARISON: Original vs Filtered Model")
    print("=" * 60)
    print(f"\nOriginal Model (trained and tested on full data):")
    print(f"  R² Score: {r2_multi:.4f}")
    print(f"  Mean Absolute Error: {np.mean(np.abs(y - y_pred_multi)):.2f}")
    print(f"\nFiltered Model (trained and tested without outliers):")
    print(f"  R² Score: {r2_filtered_train:.4f}")
    print(f"  Mean Absolute Error: {np.mean(np.abs(y_filtered - y_pred_filtered_train)):.2f}")
    
    # Create visualizations
    print("\n" + "=" * 60)
    print("Generating visualizations...")
    print("=" * 60)
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    outlier_mask = merged_df['date'].isin(outlier_dates).values
    
    # Plot 1: Original model - predicted vs actual (with outliers highlighted)
    axes[0, 0].scatter(y, y_pred_multi, alpha=0.6, label='All data', color='blue')
    axes[0, 0].scatter(y[outlier_mask], y_pred_multi[outlier_mask], 
                      color='red', s=100, marker='x', label='Outliers', zorder=5)
    axes[0, 0].plot([y.min(), y.max()], [y.min(), y.max()], 'r--', label='Perfect prediction', alpha=0.5)
    axes[0, 0].set_xlabel('Actual bpgus')
    axes[0, 0].set_ylabel('Predicted bpgus')
    axes[0, 0].set_title(f'Original Model (R² = {r2_multi:.3f})')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Plot 2: Filtered model - predicted vs actual (all data including outliers for visualization)
    axes[0, 1].scatter(y, y_pred_filtered_full, alpha=0.6, label='All data', color='green')
    axes[0, 1].scatter(y[outlier_mask], y_pred_filtered_full[outlier_mask], 
                      color='red', s=100, marker='x', label='Outliers', zorder=5)
    axes[0, 1].plot([y.min(), y.max()], [y.min(), y.max()], 'r--', label='Perfect prediction', alpha=0.5)
    axes[0, 1].set_xlabel('Actual bpgus')
    axes[0, 1].set_ylabel('Predicted bpgus')
    axes[0, 1].set_title(f'Filtered Model (R² = {r2_filtered_train:.3f}, on non-outliers)')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # Plot 3: Residuals - Original model
    indices = np.arange(len(merged_df))
    axes[1, 0].scatter(indices, merged_df['Residual'], alpha=0.6, color='blue')
    outlier_positions = indices[outlier_mask]
    axes[1, 0].scatter(outlier_positions, merged_df.loc[merged_df['date'].isin(outlier_dates), 'Residual'], 
                      color='red', s=100, marker='x', label='Outliers', zorder=5)
    axes[1, 0].axhline(y=0, color='r', linestyle='--', alpha=0.5)
    axes[1, 0].set_xlabel('Data Point Index')
    axes[1, 0].set_ylabel('Residual (Actual - Predicted)')
    axes[1, 0].set_title(f'Original Model Residuals (MAE = {np.mean(np.abs(merged_df["Residual"])):.2f})')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Plot 4: Residuals - Filtered model (all data including outliers for visualization)
    axes[1, 1].scatter(indices, merged_df['Residual_filtered'], alpha=0.6, color='green')
    axes[1, 1].scatter(outlier_positions, merged_df.loc[merged_df['date'].isin(outlier_dates), 'Residual_filtered'], 
                      color='red', s=100, marker='x', label='Outliers', zorder=5)
    axes[1, 1].axhline(y=0, color='r', linestyle='--', alpha=0.5)
    # Calculate MAE only on non-outliers
    non_outlier_mask = ~outlier_mask
    filtered_residuals_non_outliers = merged_df.loc[non_outlier_mask, 'Residual_filtered'].values
    axes[1, 1].set_xlabel('Data Point Index')
    axes[1, 1].set_ylabel('Residual (Actual - Predicted)')
    axes[1, 1].set_title(f'Filtered Model Residuals (MAE = {np.mean(np.abs(filtered_residuals_non_outliers)):.2f}, on non-outliers)')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('bpgus_relationship_analysis.png', dpi=300, bbox_inches='tight')
    print("\nVisualization saved to: bpgus_relationship_analysis.png")
    
    # Save detailed results to CSV
    output_df = merged_df[['date', 'bpgus', 'Tx Count', 'Gas Consumed', 
                           'Predicted_bpgus', 'Residual',
                           'Predicted_bpgus_filtered', 'Residual_filtered']].copy()
    output_df.to_csv('bpgus_analysis_results.csv', index=False)
    print("Detailed results saved to: bpgus_analysis_results.csv")
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    main()

