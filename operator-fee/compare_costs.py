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
BPGU_INTERCEPT = 531.78
BPGU_COEF_TX = -0.000017
BPGU_COEF_GAS = 0.0000000318
BPGU_PRICE_USD = 0.58          # cost per BPGU in USD
FIXED_DAILY_COST_USD = 100     # fixed daily operator overhead in USD

# ── L1 info system tx constants ──────────────────────────────────────────
L1_INFO_TX_PER_DAY = 43_200            # 1 per block, 43200 blocks/day
L1_INFO_GAS_PER_TX = 51_000            # gas consumed per L1 info tx

# Adjusted intercept when system txs share cost:
# bpgus_daily = b + (-0.000017)*(Tx+43200) + 0.0000000318*(Gas+43200*51000)
# Since total bpgus is the same, b = 531.78 - (-0.000017)*43200 - 0.0000000318*43200*51000
BPGU_INTERCEPT_SHARED = (BPGU_INTERCEPT
                         - BPGU_COEF_TX * L1_INFO_TX_PER_DAY
                         - BPGU_COEF_GAS * L1_INFO_TX_PER_DAY * L1_INFO_GAS_PER_TX)

# ── Default parameter values ─────────────────────────────────────────────
DEFAULT_ETH_PRICE = 1800       # USD
DEFAULT_MNT_PRICE = 0.80       # USD
DEFAULT_DAILY_TX = 50_000
DEFAULT_POST_GWEI = 10         # post-Arsia L2 gas price in gwei (MNT)

# ── Gas used range ───────────────────────────────────────────────────────
GAS_MIN = 0
GAS_MAX = 500_000
GASUSED = np.linspace(GAS_MIN, GAS_MAX, 1000)


def pre_arsia_cost(gasused, eth_price, mnt_price):
    """Pre-Arsia tx cost in MNT = 0.02 gwei (MNT) * gasused * eth_price / mnt_price."""
    return 0.02e-9 * gasused * eth_price / mnt_price


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
        intercept = BPGU_INTERCEPT
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


def find_breakeven_direct(eth_price, mnt_price, x_gwei, fee_constant, fee_scalar):
    """Solve for gasused where pre == post cost.

    pre  = 0.02e-9 * gas * eth_price / mnt_price
    post = x*1e-9 * gas + feeConstant + feeScalar * 100 * gas

    Setting pre = post:
      (0.02e-9 * eth/mnt - x*1e-9 - feeScalar*100) * gas = feeConstant
    """
    slope_diff = 0.02e-9 * eth_price / mnt_price - x_gwei * 1e-9 - fee_scalar * 100
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

    Per-tx: operatorFeeConstant = (c / daily_tx_count + a) / mnt_price  (MNT)
            operatorFeeScalar   = b / 100 / mnt_price                   (MNT per gas)
    """
    if share_system_tx:
        intercept = BPGU_INTERCEPT_SHARED
        total_tx = daily_tx_count + L1_INFO_TX_PER_DAY
    else:
        intercept = BPGU_INTERCEPT
        total_tx = daily_tx_count
    a = BPGU_COEF_TX * BPGU_PRICE_USD
    b = BPGU_COEF_GAS * BPGU_PRICE_USD
    c = FIXED_DAILY_COST_USD + intercept * BPGU_PRICE_USD

    fee_constant = (c / total_tx + a) / mnt_price   # MNT per tx
    fee_scalar = b / 100 / mnt_price                # MNT per gas unit
    return fee_constant, fee_scalar


def main():
    # ── Compute initial fee params ───────────────────────────────────────
    init_fc, init_fs = calc_operator_fee_params(DEFAULT_DAILY_TX, DEFAULT_MNT_PRICE)

    # ── Build the figure ─────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(14, 9))
    plt.subplots_adjust(bottom=0.40)  # room for 6 sliders + checkbox

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

    # Operator fee params text box (upper right)
    params_text = ax.text(0.98, 0.97, '', fontsize=9, fontfamily='monospace',
                          transform=ax.transAxes, ha='right', va='top',
                          bbox=dict(boxstyle='round,pad=0.5', fc='lightyellow',
                                    ec='orange', alpha=0.9))

    # ── Sliders ──────────────────────────────────────────────────────────
    slider_left = 0.15
    slider_width = 0.55
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
    s_x   = Slider(ax_x,   'Post Gas (gwei)', 0.01, 50,
                   valinit=DEFAULT_POST_GWEI, valstep=0.01, color='tomato')
    s_fc  = Slider(ax_fc,  'FeeConstant (MNT)', 0, 0.02,
                   valinit=init_fc, valfmt='%.6f', color='darkorange')
    s_fs  = Slider(ax_fs,  'FeeScalar (×1e-10)', 0, 50,
                   valinit=init_fs * 1e10, valfmt='%.2f', color='darkorange')

    # Separator label between model sliders and fee param sliders
    fig.text(slider_left, 0.135, '── Operator Fee Params (auto-synced from model, or adjust manually) ──',
             fontsize=8, color='gray', style='italic')

    # ── System tx sharing toggle ─────────────────────────────────────────
    ax_chk = plt.axes([0.78, 0.07, 0.18, 0.10])
    chk = CheckButtons(ax_chk, ['System Tx\nShare Cost'], [False])
    ax_chk.set_title('L1 Info Tx', fontsize=9, fontweight='bold')

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
        eth = s_eth.val
        mnt = s_mnt.val
        x   = s_x.val
        fc  = s_fc.val
        fs  = s_fs.val * 1e-10  # convert back from ×1e-10

        y_pre_new = pre_arsia_cost(GASUSED, eth, mnt)
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
        be = find_breakeven_direct(eth, mnt, x, fc, fs)
        if be and GAS_MIN <= be <= GAS_MAX:
            be_line.set_xdata([be, be])
            be_cost = pre_arsia_cost(be, eth, mnt)
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

        # Update operator fee params display
        params_text.set_text(
            f'Operator Fee Params (MNT)\n'
            f'Constant: {fc:.10f}\n'
            f'Scalar:   {fs:.15f}'
        )

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
