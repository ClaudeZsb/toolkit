#!/usr/bin/env python3
"""
Pre-Arsia vs Post-Arsia Transaction Cost Comparison Tool

Interactive tool with sliders to customize ETH price, MNT price,
daily tx count, and post-Arsia L2 gas price. Shows per-transaction
cost for different gasused values.

Formulas:
  Pre-Arsia cost (MNT)  = 0.02 gwei * gasused * eth_price / mnt_price
  Post-Arsia cost (MNT) = x gwei * gasused + operator_fee
  operator_fee = (100 + 531.78*0.58)/daily_tx_count + (-0.000017)*0.58 + 0.0000000318*0.58*gasused
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, CheckButtons

# ── Regression constants (from analyze_relationship.py, filtered model) ──
# Trained on total_tx and total_gas (including system txs)
BPGU_INTERCEPT_REGRESSION = 531.78
BPGU_COEF_TX = -0.000017
BPGU_COEF_GAS = 0.0000000318
BPGU_PRICE_USD = 0.58          # cost per BPGU in USD
FIXED_DAILY_COST_USD = 100     # fixed daily operator overhead in USD

# ── L1 info system tx constants ──────────────────────────────────────────
L1_INFO_TX_PER_DAY = 43_200            # 1 per block, 43200 blocks/day
L1_INFO_GAS_PER_TX = 51_000            # gas consumed per L1 info tx

# When system txs share cost, use the regression intercept directly:
#   bpgus = 531.78 + coef_tx*(user_tx+43200) + coef_gas*(user_gas+43200*51000)
#   denominator = user_tx + 43200
BPGU_INTERCEPT_SHARED = BPGU_INTERCEPT_REGRESSION

# When only user txs pay, absorb system tx costs into a bigger intercept:
#   bpgus = [531.78 + coef_tx*43200 + coef_gas*43200*51000] + coef_tx*user_tx + coef_gas*user_gas
#   denominator = user_tx only
BPGU_INTERCEPT_USER_ONLY = (BPGU_INTERCEPT_REGRESSION
                            + BPGU_COEF_TX * L1_INFO_TX_PER_DAY
                            + BPGU_COEF_GAS * L1_INFO_TX_PER_DAY * L1_INFO_GAS_PER_TX)

# Average gas per user tx (Q1 2026: avg_gas / avg_tx = 4,918,467,626 / 33,832)
AVG_GAS_PER_USER_TX = 145_379

# Average priority fee per gas (gwei, in MNT)
AVG_PRIORITY_FEE_GWEI = 102.874

# ── Default parameter values ─────────────────────────────────────────────
DEFAULT_ETH_PRICE = 1800       # USD
DEFAULT_MNT_PRICE = 0.80       # USD
DEFAULT_DAILY_TX = 35_000      # user tx count (excluding system txs)
DEFAULT_POST_GWEI = 10         # post-Arsia L2 gas price in gwei (MNT)

# ── Gas used range ───────────────────────────────────────────────────────
GAS_MIN = 0
GAS_MAX = 500_000
GASUSED = np.linspace(GAS_MIN, GAS_MAX, 1000)


def pre_arsia_cost(gasused, eth_price, mnt_price, include_priority_fee=False):
    """Pre-Arsia tx cost in MNT = 0.02 gwei (MNT) * gasused * eth_price / mnt_price."""
    cost = 0.02e-9 * gasused * eth_price / mnt_price
    if include_priority_fee:
        cost = cost + AVG_PRIORITY_FEE_GWEI * 1e-9 * gasused
    return cost


def operator_fee(gasused, daily_tx_count, mnt_price, share_system_tx=False):
    """Per-tx operator fee in MNT derived from the BPGU regression model.

    The fee components are in USD, so divide by mnt_price to get MNT.
    When share_system_tx=True, system L1 info txs share the fixed cost,
    using adjusted intercept and expanded tx count denominator.
    """
    if share_system_tx:
        intercept = BPGU_INTERCEPT_SHARED
        total_tx = daily_tx_count + L1_INFO_TX_PER_DAY
    else:
        intercept = BPGU_INTERCEPT_USER_ONLY
        total_tx = daily_tx_count
    fixed_per_tx = (FIXED_DAILY_COST_USD + intercept * BPGU_PRICE_USD) / total_tx
    tx_component = BPGU_COEF_TX * BPGU_PRICE_USD
    gas_component = BPGU_COEF_GAS * BPGU_PRICE_USD * gasused
    return (fixed_per_tx + tx_component + gas_component) / mnt_price


def post_arsia_cost_direct(gasused, x_gwei, fee_constant, fee_scalar):
    """Post-Arsia tx cost in MNT using fee params directly.

    cost = gasprice * gasused + operatorFeeConstant + operatorFeeScalar * 100 * gasused
    """
    return x_gwei * 1e-9 * gasused + fee_constant + fee_scalar * 100 * gasused


def find_breakeven_direct(eth_price, mnt_price, x_gwei, fee_constant, fee_scalar,
                          include_priority_fee=False):
    """Solve for gasused where pre == post cost.

    pre  = (0.02e-9 * eth/mnt [+ 102.874e-9]) * gas
    post = x*1e-9 * gas + feeConstant + feeScalar * 100 * gas

    Setting pre = post:
      slope_diff * gas = feeConstant
    """
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


def calc_operator_fee_params(daily_tx_count, mnt_price, share_system_tx=False):
    """Calculate operatorFeeConstant and operatorFeeScalar.

    operatorFee = a*tx_count + b*gas_used + c  (daily, in USD)
      a = BPGU_COEF_TX * BPGU_PRICE_USD
      b = BPGU_COEF_GAS * BPGU_PRICE_USD
      c = FIXED_DAILY_COST_USD + intercept * BPGU_PRICE_USD

    Per-tx: operatorFeeConstant = (c / total_tx + a) / mnt_price  (MNT)
            operatorFeeScalar   = b / 100 / mnt_price             (MNT per gas)

    share_system_tx=False: intercept absorbs system tx costs (USER_ONLY),
        c spread over user txs only → fee covers total cost → surplus = 0.
    share_system_tx=True: base intercept (SHARED),
        c spread over all txs (user + system) → fee covers user share only
        → surplus = −system tx cost.
    """
    if share_system_tx:
        intercept = BPGU_INTERCEPT_SHARED
        total_tx = daily_tx_count + L1_INFO_TX_PER_DAY
    else:
        intercept = BPGU_INTERCEPT_USER_ONLY
        total_tx = daily_tx_count
    a = BPGU_COEF_TX * BPGU_PRICE_USD
    b = BPGU_COEF_GAS * BPGU_PRICE_USD
    c = FIXED_DAILY_COST_USD + intercept * BPGU_PRICE_USD

    fee_constant = (c / total_tx + a) / mnt_price   # MNT per tx
    fee_scalar = b / 100 / mnt_price                # MNT per gas unit
    return fee_constant, fee_scalar


def calc_daily_pnl(daily_tx_count, mnt_price, fee_constant, fee_scalar, x_gwei):
    """Calculate daily operator P&L with cost breakdown (in MNT).

    Uses the full regression model (all txs) to compute total cost, then
    splits into user-tx cost and system-tx cost proportionally by tx count.

    Revenue = base fee (gas price × gas) + operator fee.

    Returns (total_cost, user_cost, system_cost,
             base_fee_rev, operator_fee_rev, surplus).
    """
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


def main():
    # ── Compute initial fee params ───────────────────────────────────────
    init_fc, init_fs = calc_operator_fee_params(DEFAULT_DAILY_TX, DEFAULT_MNT_PRICE)

    # ── Build the figure ─────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(14, 9))
    plt.subplots_adjust(bottom=0.40, right=0.62)  # chart on left, info panel on right

    y_pre = pre_arsia_cost(GASUSED, DEFAULT_ETH_PRICE, DEFAULT_MNT_PRICE)
    y_post = post_arsia_cost_direct(GASUSED, DEFAULT_POST_GWEI, init_fc, init_fs)

    line_pre, = ax.plot(GASUSED, y_pre, color='steelblue', linewidth=2, label='Pre-Arsia')
    line_post, = ax.plot(GASUSED, y_post, color='tomato', linewidth=2, label='Post-Arsia')

    # Shaded regions
    ax.fill_between(GASUSED, y_pre, y_post,
                    where=(y_pre > y_post), interpolate=True,
                    color='green', alpha=0.12, label='Post-Arsia cheaper')
    ax.fill_between(GASUSED, y_pre, y_post,
                    where=(y_pre < y_post), interpolate=True,
                    color='red', alpha=0.12, label='Post-Arsia more expensive')

    # Breakeven annotation
    be_gas = find_breakeven_direct(DEFAULT_ETH_PRICE, DEFAULT_MNT_PRICE,
                                   DEFAULT_POST_GWEI, init_fc, init_fs)
    be_line = ax.axvline(x=be_gas if be_gas else -1, color='gray',
                         linestyle='--', linewidth=1, alpha=0.7)
    be_text = ax.text(0, 0, '', fontsize=9, color='gray',
                      ha='left', va='bottom',
                      bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='gray', alpha=0.8))

    # Typical tx type reference lines
    TX_TYPES = [
        (21_000,  'Native Transfer',  '#9467bd'),
        (50_000,  'ERC20 Transfer',   '#2ca02c'),
        (200_000, 'DEX Swap',         '#d62728'),
    ]
    tx_type_texts = []
    for gas_val, label, color in TX_TYPES:
        ax.axvline(x=gas_val, color=color, linestyle=':', linewidth=1.2, alpha=0.7)
        txt = ax.text(gas_val, 0, f' {label}\n {gas_val:,} gas',
                      fontsize=8, color=color, ha='left', va='top',
                      transform=ax.get_xaxis_transform(),
                      bbox=dict(boxstyle='round,pad=0.2', fc='white', ec=color, alpha=0.85))
        tx_type_texts.append(txt)

    ax.set_xlabel('Gas Used per Transaction', fontsize=12)
    ax.set_ylabel('Transaction Cost (MNT)', fontsize=12)
    ax.set_title('Pre-Arsia vs Post-Arsia Transaction Cost', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10, loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(GAS_MIN, GAS_MAX)

    # Operator fee params + P&L panel (right of chart)
    params_text = fig.text(0.65, 0.92, '', fontsize=10, fontfamily='monospace',
                           ha='left', va='top',
                           bbox=dict(boxstyle='round,pad=0.5', fc='lightyellow',
                                     ec='orange', alpha=0.9))

    # ── Sliders ──────────────────────────────────────────────────────────
    slider_left = 0.15
    slider_width = 0.45
    ax_eth = plt.axes([slider_left, 0.28, slider_width, 0.025])
    ax_mnt = plt.axes([slider_left, 0.24, slider_width, 0.025])
    ax_tx  = plt.axes([slider_left, 0.20, slider_width, 0.025])
    ax_x   = plt.axes([slider_left, 0.16, slider_width, 0.025])
    ax_fc  = plt.axes([slider_left, 0.10, slider_width, 0.025])
    ax_fs  = plt.axes([slider_left, 0.06, slider_width, 0.025])

    s_eth = Slider(ax_eth, 'ETH Price ($)', 500, 5000,
                   valinit=DEFAULT_ETH_PRICE, valstep=50, color='steelblue')
    s_mnt = Slider(ax_mnt, 'MNT Price ($)', 0.05, 3.0,
                   valinit=DEFAULT_MNT_PRICE, valstep=0.05, color='orange')
    s_tx  = Slider(ax_tx,  'Daily Tx Count', 10_000, 200_000,
                   valinit=DEFAULT_DAILY_TX, valstep=5000, color='green')
    s_x   = Slider(ax_x,   'Post Gas (gwei)', 0.01, 100,
                   valinit=DEFAULT_POST_GWEI, valstep=0.01, color='tomato')
    s_fc  = Slider(ax_fc,  'FeeConstant (MNT)', 0, 0.02,
                   valinit=init_fc, valfmt='%.6f', color='darkorange')
    s_fs  = Slider(ax_fs,  'FeeScalar (×1e-10)', 0, 50,
                   valinit=init_fs * 1e10, valfmt='%.2f', color='darkorange')

    # Separator label between model sliders and fee param sliders
    fig.text(slider_left, 0.135, '── Operator Fee Params (auto-synced from model, or adjust manually) ──',
             fontsize=8, color='gray', style='italic')

    # ── Checkboxes ───────────────────────────────────────────────────────
    ax_chk = plt.axes([0.65, 0.04, 0.18, 0.15])
    chk = CheckButtons(ax_chk, ['System Tx\nShare Cost', 'Include\nPriority Fee'], [False, False])
    fig.text(0.84, 0.14, 'Priority fee: 102.874 gwei\n(affects Pre-Arsia only)',
             fontsize=7, color='gray', style='italic')

    # ── Sync / update logic ──────────────────────────────────────────────
    _syncing = [False]  # flag to prevent feedback loops

    def sync_fee_sliders(_val):
        """Recalculate fee params from model and push to fee sliders."""
        if _syncing[0]:
            return
        _syncing[0] = True
        share = chk.get_status()[0]
        fc, fs = calc_operator_fee_params(s_tx.val, s_mnt.val, share)
        s_fc.set_val(fc)
        s_fs.set_val(fs * 1e10)
        _syncing[0] = False

    def update(_val):
        """Redraw chart from current slider values."""
        eth   = s_eth.val
        mnt   = s_mnt.val
        tx    = s_tx.val
        x     = s_x.val
        fc    = s_fc.val
        fs    = s_fs.val * 1e-10  # convert back from ×1e-10
        share = chk.get_status()[0]
        prio  = chk.get_status()[1]

        y_pre_new = pre_arsia_cost(GASUSED, eth, mnt, prio)
        y_post_new = post_arsia_cost_direct(GASUSED, x, fc, fs)

        line_pre.set_ydata(y_pre_new)
        line_post.set_ydata(y_post_new)

        # Update shaded regions - remove old PolyCollections
        for coll in list(ax.collections):
            coll.remove()
        ax.fill_between(GASUSED, y_pre_new, y_post_new,
                        where=(y_pre_new > y_post_new), interpolate=True,
                        color='green', alpha=0.12)
        ax.fill_between(GASUSED, y_pre_new, y_post_new,
                        where=(y_pre_new < y_post_new), interpolate=True,
                        color='red', alpha=0.12)

        # Update breakeven
        be = find_breakeven_direct(eth, mnt, x, fc, fs, prio)
        if be and GAS_MIN <= be <= GAS_MAX:
            be_line.set_xdata([be, be])
            be_cost = pre_arsia_cost(be, eth, mnt, prio)
            be_text.set_position((be + (GAS_MAX - GAS_MIN) * 0.01, be_cost))
            be_text.set_text(f'Breakeven\n{format_gas(be)} gas\n{be_cost:.6f} MNT')
            be_line.set_visible(True)
            be_text.set_visible(True)
        else:
            be_line.set_visible(False)
            be_text.set_visible(False)

        # Auto-scale y axis
        y_all = np.concatenate([y_pre_new, y_post_new])
        y_min, y_max = y_all.min(), y_all.max()
        margin = (y_max - y_min) * 0.05 or 0.001
        ax.set_ylim(y_min - margin, y_max + margin)

        # Update operator fee params + daily P&L display
        total_cost, user_cost, system_cost, base_rev, op_rev, surplus = calc_daily_pnl(
            tx, mnt, fc, fs, x)
        color = 'green' if surplus >= 0 else 'red'
        total_rev = base_rev + op_rev
        pre_rev = tx * pre_arsia_cost(AVG_GAS_PER_USER_TX, eth, mnt, prio)
        rev_diff = total_rev - pre_rev
        params_text.set_text(
            f'Operator Fee Params (MNT)\n'
            f'Constant: {fc:.10f}\n'
            f'Scalar:   {fs:.15f}\n'
            f'─────────────────────────────────\n'
            f'Daily ZKP Cost:   {total_cost:>12.2f} MNT\n'
            f'  User Tx:        {user_cost:>12.2f} MNT\n'
            f'  System Tx:      {system_cost:>12.2f} MNT\n'
            f'Post-Arsia Rev:   {total_rev:>12.2f} MNT\n'
            f'  Base Fee:       {base_rev:>12.2f} MNT\n'
            f'  Operator Fee:   {op_rev:>12.2f} MNT\n'
            f'Pre-Arsia Rev:    {pre_rev:>12.2f} MNT\n'
            f'Rev Difference:   {rev_diff:>+12.2f} MNT\n'
            f'Post-Arsia P&L:   {surplus:>+12.2f} MNT'
        )
        params_text.get_bbox_patch().set_edgecolor(color)

        fig.canvas.draw_idle()

    # Model sliders → sync fee sliders, then update chart
    s_eth.on_changed(update)
    s_mnt.on_changed(lambda v: (sync_fee_sliders(v), update(v)))
    s_tx.on_changed(lambda v: (sync_fee_sliders(v), update(v)))
    s_x.on_changed(update)
    chk.on_clicked(lambda v: (sync_fee_sliders(v), update(v)))

    # Fee sliders → update chart directly (no sync back)
    s_fc.on_changed(update)
    s_fs.on_changed(update)

    # Trigger initial layout
    update(None)

    plt.show()


if __name__ == '__main__':
    main()
