#!/usr/bin/env python3
"""
Pre-Arsia vs Post-Arsia Transaction Cost Comparison Tool (Streamlit version)

Run: streamlit run compare_costs_app.py
"""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

# ── Regression constants (from analyze_relationship.py, filtered model) ──
BPGU_INTERCEPT_REGRESSION = 531.78
BPGU_COEF_TX = -0.000017
BPGU_COEF_GAS = 0.0000000318
BPGU_PRICE_USD = 0.58
FIXED_DAILY_COST_USD = 100

# ── L1 info system tx constants ──────────────────────────────────────────
L1_INFO_TX_PER_DAY = 43_200
L1_INFO_GAS_PER_TX = 51_000

BPGU_INTERCEPT_SHARED = BPGU_INTERCEPT_REGRESSION
BPGU_INTERCEPT_USER_ONLY = (BPGU_INTERCEPT_REGRESSION
                            + BPGU_COEF_TX * L1_INFO_TX_PER_DAY
                            + BPGU_COEF_GAS * L1_INFO_TX_PER_DAY * L1_INFO_GAS_PER_TX)

# Average gas per user tx (Q1 2026: avg_gas / avg_tx = 4,918,467,626 / 33,832)
AVG_GAS_PER_USER_TX = 145_379

# Average priority fee per gas (gwei, in MNT)
AVG_PRIORITY_FEE_GWEI = 102.874

# ── Gas used range ───────────────────────────────────────────────────────
GAS_MIN = 0
GAS_MAX = 500_000
GASUSED = np.linspace(GAS_MIN, GAS_MAX, 1000)


def pre_arsia_cost(gasused, eth_price, mnt_price, include_priority_fee=False):
    cost = 0.02e-9 * gasused * eth_price / mnt_price
    if include_priority_fee:
        cost = cost + AVG_PRIORITY_FEE_GWEI * 1e-9 * gasused
    return cost


def calc_operator_fee_params(daily_tx_count, mnt_price, share_system_tx=False):
    if share_system_tx:
        intercept = BPGU_INTERCEPT_SHARED
        total_tx = daily_tx_count + L1_INFO_TX_PER_DAY
    else:
        intercept = BPGU_INTERCEPT_USER_ONLY
        total_tx = daily_tx_count
    a = BPGU_COEF_TX * BPGU_PRICE_USD
    b = BPGU_COEF_GAS * BPGU_PRICE_USD
    c = FIXED_DAILY_COST_USD + intercept * BPGU_PRICE_USD

    fee_constant = (c / total_tx + a) / mnt_price
    fee_scalar = b / 100 / mnt_price
    return fee_constant, fee_scalar


def calc_daily_pnl(daily_tx_count, mnt_price, fee_constant, fee_scalar, x_gwei):
    # Full regression with all txs
    total_tx = daily_tx_count + L1_INFO_TX_PER_DAY
    user_gas = daily_tx_count * AVG_GAS_PER_USER_TX
    system_gas = L1_INFO_TX_PER_DAY * L1_INFO_GAS_PER_TX
    total_gas = user_gas + system_gas

    bpgus_daily = (BPGU_INTERCEPT_REGRESSION
                   + BPGU_COEF_TX * total_tx
                   + BPGU_COEF_GAS * total_gas)
    total_cost = (FIXED_DAILY_COST_USD + bpgus_daily * BPGU_PRICE_USD) / mnt_price

    # Cost breakdown: system txs share base/fixed cost proportionally by tx count
    a = BPGU_COEF_TX * BPGU_PRICE_USD
    b = BPGU_COEF_GAS * BPGU_PRICE_USD
    base_cost_usd = FIXED_DAILY_COST_USD + BPGU_INTERCEPT_REGRESSION * BPGU_PRICE_USD

    system_cost = (base_cost_usd * L1_INFO_TX_PER_DAY / total_tx
                   + a * L1_INFO_TX_PER_DAY
                   + b * system_gas) / mnt_price
    user_cost = total_cost - system_cost

    # Revenue: base fee (gas price) + operator fee (only user txs pay)
    base_fee_rev = x_gwei * 1e-9 * user_gas
    operator_fee_rev = daily_tx_count * fee_constant + fee_scalar * 100 * user_gas
    total_rev = base_fee_rev + operator_fee_rev

    return total_cost, user_cost, system_cost, base_fee_rev, operator_fee_rev, total_rev - total_cost


def post_arsia_cost_direct(gasused, x_gwei, fee_constant, fee_scalar):
    return x_gwei * 1e-9 * gasused + fee_constant + fee_scalar * 100 * gasused


def find_breakeven_direct(eth_price, mnt_price, x_gwei, fee_constant, fee_scalar,
                          include_priority_fee=False):
    slope_diff = 0.02e-9 * eth_price / mnt_price - x_gwei * 1e-9 - fee_scalar * 100
    if include_priority_fee:
        slope_diff += AVG_PRIORITY_FEE_GWEI * 1e-9
    if slope_diff <= 0:
        return None
    return fee_constant / slope_diff


def format_gas(val):
    if val >= 1_000_000:
        return f'{val/1_000_000:.2f}M'
    if val >= 1_000:
        return f'{val/1_000:.0f}K'
    return f'{val:.0f}'


# ── Page config ──────────────────────────────────────────────────────────
st.set_page_config(page_title="Pre vs Post Arsia Cost", layout="wide")
st.title("Pre-Arsia vs Post-Arsia Transaction Cost")
st.caption("Adjust parameters in the sidebar to compare transaction costs")

# ── Sidebar controls ─────────────────────────────────────────────────────
st.sidebar.header("Market Parameters")
eth_price = st.sidebar.slider("ETH Price ($)", 500, 5000, 1800, step=50)
mnt_price = st.sidebar.slider("MNT Price ($)", 0.05, 3.0, 0.80, step=0.05)
daily_tx = st.sidebar.slider("Daily User Tx Count", 10_000, 200_000, 35_000, step=5000)
x_gwei = st.sidebar.slider("Post-Arsia Gas Price (gwei)", 0.01, 100.0, 10.0, step=0.01)

st.sidebar.header("Options")
share_system_tx = st.sidebar.checkbox("System Tx Share Cost", value=False)
include_priority_fee = st.sidebar.checkbox("Include Priority Fee", value=False)
st.sidebar.caption("Priority fee: 102.874 gwei (affects Pre-Arsia only)")

# Compute model-suggested fee params
model_fc, model_fs = calc_operator_fee_params(daily_tx, mnt_price, share_system_tx)

st.sidebar.header("Operator Fee Params")
st.sidebar.caption("Auto-filled from model. Adjust to override.")
fee_constant = st.sidebar.number_input(
    "FeeConstant (MNT)", min_value=0.0, max_value=0.05,
    value=float(f"{model_fc:.8f}"), format="%.8f", step=0.0001
)
fee_scalar_display = st.sidebar.number_input(
    "FeeScalar (×1e-10)", min_value=0.0, max_value=50.0,
    value=float(f"{model_fs * 1e10:.2f}"), format="%.2f", step=0.1
)
fee_scalar = fee_scalar_display * 1e-10

# ── Compute costs ────────────────────────────────────────────────────────
y_pre = pre_arsia_cost(GASUSED, eth_price, mnt_price, include_priority_fee)
y_post = post_arsia_cost_direct(GASUSED, x_gwei, fee_constant, fee_scalar)
breakeven = find_breakeven_direct(eth_price, mnt_price, x_gwei, fee_constant, fee_scalar,
                                  include_priority_fee)

# ── Build Plotly chart ───────────────────────────────────────────────────
fig = go.Figure()

# Pre-Arsia line
fig.add_trace(go.Scatter(
    x=GASUSED, y=y_pre, name='Pre-Arsia',
    line=dict(color='steelblue', width=2.5),
))

# Post-Arsia line
fig.add_trace(go.Scatter(
    x=GASUSED, y=y_post, name='Post-Arsia',
    line=dict(color='tomato', width=2.5),
))

# Shaded regions
cheaper_mask = y_post < y_pre
expensive_mask = y_post >= y_pre

if cheaper_mask.any():
    fig.add_trace(go.Scatter(
        x=np.concatenate([GASUSED[cheaper_mask], GASUSED[cheaper_mask][::-1]]),
        y=np.concatenate([y_pre[cheaper_mask], y_post[cheaper_mask][::-1]]),
        fill='toself', fillcolor='rgba(0,200,0,0.08)',
        line=dict(width=0), name='Post-Arsia cheaper', showlegend=True,
    ))

if expensive_mask.any():
    fig.add_trace(go.Scatter(
        x=np.concatenate([GASUSED[expensive_mask], GASUSED[expensive_mask][::-1]]),
        y=np.concatenate([y_pre[expensive_mask], y_post[expensive_mask][::-1]]),
        fill='toself', fillcolor='rgba(255,0,0,0.08)',
        line=dict(width=0), name='Post-Arsia more expensive', showlegend=True,
    ))

# Tx type reference lines
TX_TYPES = [
    (21_000, 'Native Transfer', '#9467bd', "top left"),
    (50_000, 'ERC20 Transfer', '#2ca02c', "top right"),
    (200_000, 'DEX Swap', '#d62728', "top left"),
]
for gas_val, label, color, pos in TX_TYPES:
    fig.add_vline(x=gas_val, line_dash="dot", line_color=color, line_width=1,
                  annotation_text=f"{label}<br>{gas_val:,} gas",
                  annotation_position=pos,
                  annotation_font=dict(size=10, color=color))

# Breakeven line
if breakeven and GAS_MIN <= breakeven <= GAS_MAX:
    be_cost = pre_arsia_cost(breakeven, eth_price, mnt_price, include_priority_fee)
    fig.add_vline(x=breakeven, line_dash="dash", line_color="gray", line_width=1,
                  annotation_text=f"Breakeven<br>{format_gas(breakeven)} gas<br>{be_cost:.6f} MNT",
                  annotation_position="bottom right",
                  annotation_font=dict(size=10, color="gray"))

fig.update_layout(
    xaxis_title="Gas Used per Transaction",
    yaxis_title="Transaction Cost (MNT)",
    height=600,
    legend=dict(x=0.55, y=0.99, bgcolor='rgba(255,255,255,0.8)'),
    hovermode='x unified',
    margin=dict(t=40),
)

st.plotly_chart(fig, width='stretch')

# ── Info panels ──────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("operatorFeeConstant", f"{fee_constant:.10f} MNT")
with col2:
    st.metric("operatorFeeScalar", f"{fee_scalar:.15f} MNT/gas")
with col3:
    if breakeven and GAS_MIN <= breakeven <= GAS_MAX:
        st.metric("Breakeven Gas", f"{format_gas(breakeven)}")
    else:
        st.metric("Breakeven Gas", "N/A (no crossover)")

# ── Daily P&L ────────────────────────────────────────────────────────────
total_cost, user_cost, system_cost, base_rev, op_rev, surplus = calc_daily_pnl(
    daily_tx, mnt_price, fee_constant, fee_scalar, x_gwei)
total_rev = base_rev + op_rev
pre_rev = daily_tx * pre_arsia_cost(AVG_GAS_PER_USER_TX, eth_price, mnt_price, include_priority_fee)
rev_diff = total_rev - pre_rev

pcol1, pcol2, pcol3, pcol4 = st.columns(4)
with pcol1:
    st.metric("Daily ZKP Cost", f"{total_cost:,.2f} MNT")
    st.caption(f"User Tx: {user_cost:,.2f} | System Tx: {system_cost:,.2f}")
with pcol2:
    st.metric("Post-Arsia Rev", f"{total_rev:,.2f} MNT")
    st.caption(f"Base Fee: {base_rev:,.2f} | Operator Fee: {op_rev:,.2f}")
with pcol3:
    st.metric("Pre-Arsia Rev", f"{pre_rev:,.2f} MNT")
    st.metric("Rev Difference", f"{rev_diff:+,.2f} MNT",
              delta=f"{rev_diff:+,.2f}", delta_color="normal")
with pcol4:
    st.metric("Post-Arsia P&L", f"{surplus:+,.2f} MNT",
              delta=f"{surplus:+,.2f}", delta_color="normal")

# ── Cost comparison table ────────────────────────────────────────────────
st.subheader("Cost at Typical Transaction Types")
table_data = []
for label, gas_val in [("Native Transfer", 21_000), ("ERC20 Transfer", 50_000), ("DEX Swap", 200_000)]:
    pre = pre_arsia_cost(gas_val, eth_price, mnt_price, include_priority_fee)
    post = post_arsia_cost_direct(gas_val, x_gwei, fee_constant, fee_scalar)
    diff_pct = (post - pre) / pre * 100 if pre > 0 else 0
    table_data.append({
        "Tx Type": label,
        "Gas Used": f"{gas_val:,}",
        "Pre-Arsia (MNT)": f"{pre:.8f}",
        "Post-Arsia (MNT)": f"{post:.8f}",
        "Difference": f"{diff_pct:+.1f}%",
    })
st.table(table_data)

# ── Formulas ─────────────────────────────────────────────────────────────
with st.expander("Formulas"):
    st.markdown(f"""
**Pre-Arsia cost (MNT):**
```
cost = 0.02 gwei × gasUsed × ethPrice / mntPrice
```

**Post-Arsia cost (MNT):**
```
cost = gasPrice × gasUsed + operatorFeeConstant + operatorFeeScalar × 100 × gasUsed
```

**Operator Fee Params (from regression model):**
```
bpgus_daily = {BPGU_INTERCEPT_REGRESSION} + ({BPGU_COEF_TX}) × TxCount + {BPGU_COEF_GAS} × GasConsumed

operatorFeeConstant = (dailyFixedCost + intercept × bpguPrice) / dailyTxCount + txCoef × bpguPrice) / mntPrice
operatorFeeScalar   = gasCoef × bpguPrice / 100 / mntPrice
```
""")
