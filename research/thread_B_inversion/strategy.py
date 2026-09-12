"""0DTE day-trading system — every parameter set by measurement, not preference.

Sources for each number are in RESULTS_PART*.md:
  trade budget & range forecast  Part 7   (VIX -> range, out-of-sample R2 = 0.54)
  position sizing                Part 7   (vol-of-vol -39%)
  limit entry                    Part 3   (largest single improvement measured)
  strike selection               Part 8   (ITM: best median, best win rate)
  frequency ceiling              Part 6   (cost drag = cost x N / vol)

The signal slot is filled by IntradayMomentumSignal (Part 10). It is small, regime-
dependent and crisis-loaded. It is the only directional edge that survived.

REQUIRED SIGNAL QUALITY (measured, Part 8):
    random entries hit 2.0 ATR before 1.5 ATR  41.5% of the time -> -6.10%/trade
    breakeven needs                            46.8%
    a usable system needs                      ~50%   -> +3.65%/trade
"""
from dataclasses import dataclass

# ---- measured constants -----------------------------------------------------
VIX_RANGE_SLOPE = 0.0623      # today's range% ~= slope * VIX + intercept
VIX_RANGE_INTERCEPT = -0.148
TARGET_GROSS_SHARPE = 0.6     # what we assume is achievable; NOT what we have
ANNUAL_VOL_PCT = 15.9
COST_PCT_OF_PRICE = 0.0157    # ES round trip; option-equivalent is similar per delta


@dataclass
class DailyPlan:
    vix: float
    expected_range_pct: float
    trade_budget: int
    stop_pts: float
    target_pts: float
    risk_per_trade_pct: float
    strike_offset: int        # negative = in the money

    def __str__(self):
        return (f"VIX {self.vix:.1f} | expected range {self.expected_range_pct:.2f}% | "
                f"budget {self.trade_budget} trades\n"
                f"stop {self.stop_pts:.1f} pts | target {self.target_pts:.1f} pts | "
                f"risk {self.risk_per_trade_pct:.2f}%/trade | strike {self.strike_offset:+d}")


def prepare_day(vix_prev_close, spot, account_risk_pct=1.0):
    """Everything decided before the open, from yesterday's VIX close."""
    rng_pct = max(VIX_RANGE_SLOPE * vix_prev_close + VIX_RANGE_INTERCEPT, 0.30)
    rng_pts = rng_pct / 100 * spot

    # trade budget: how many round trips before cost drag eats the assumed Sharpe
    day_vol = ANNUAL_VOL_PCT * (rng_pct / 0.988) / 252 ** 0.5
    budget = max(1, int(TARGET_GROSS_SHARPE * ANNUAL_VOL_PCT * (rng_pct / 0.988)
                        / COST_PCT_OF_PRICE / 252))

    # stop/target scale with the day, not fixed points
    stop = 0.35 * rng_pts
    target = 0.47 * rng_pts          # 1.33:1, matching the 2.0/1.5 ATR tested

    # risk per trade shrinks as budget grows so daily risk stays constant
    risk = account_risk_pct / budget

    return DailyPlan(vix_prev_close, rng_pct, budget, stop, target, risk,
                     strike_offset=-1)


class IntradayMomentumSignal:
    """Market intraday momentum (Gao et al. JFE 2018; Baltussen et al. JFE 2021).

    Mechanism: dealers and leveraged ETFs are short gamma and must hedge in the
    direction of the day's move before the close.

    Fires ONCE per day at 15:30 ET. Thresholds fixed on 2010-2018 (Part 10):
        prior-close VIX > 17.06  AND  |prev close -> 15:30 move| > 0.665%
    Exit at 16:00. Net Sharpe 2.50 discovery / 1.67 holdout. Crisis-loaded:
    2011 and 2020 supplied most of the return; 2016, 2018, 2019 were negative.
    """
    VIX_MIN = 17.06
    MOVE_MIN_PCT = 0.665

    def evaluate(self, prev_close, price_1530, plan):
        if plan.vix <= self.VIX_MIN:
            return 0
        move = 100 * (price_1530 / prev_close - 1)
        if abs(move) <= self.MOVE_MIN_PCT:
            return 0
        return 1 if move > 0 else -1


def select_strike(spot, direction, plan, strike_increment=1):
    """ITM by ~2% of the day range: best median outcome and best win rate (Part 8)."""
    atm = round(spot / strike_increment) * strike_increment
    return atm + plan.strike_offset * direction


LOSS_AT_STOP = 0.538   # measured: a stopped-out 0DTE loses ~54% of premium, not 100%


def size_position(account_value, plan, option_premium, contract_multiplier=100):
    """Contracts such that a STOPPED-OUT trade costs the planned risk.

    Sizing on full premium loss is wrong and over-conservative: the underlying stop
    fires long before the option is worthless. Measured loss at stop is 53.8% (Part 8).
    """
    risk_dollars = account_value * plan.risk_per_trade_pct / 100
    loss_per_contract = option_premium * contract_multiplier * LOSS_AT_STOP
    if loss_per_contract <= 0:
        return 0, 0.0
    n = int(risk_dollars / loss_per_contract)
    return n, n * option_premium * contract_multiplier   # contracts, capital deployed


def entry_price(signal_price, plan, direction, pullback_frac=0.12):
    """Limit entry, never market (Part 3). Placed against the signal direction."""
    return signal_price - direction * pullback_frac * plan.stop_pts


if __name__ == "__main__":
    print("DAILY PLANS ACROSS THE VIX RANGE\n" + "=" * 62)
    for vix in [11, 13, 15, 18, 25, 35]:
        p = prepare_day(vix, spot=500)          # SPY scale
        prem = 1.20 if vix < 16 else 2.20        # ITM-10 SPY 0DTE, rough
        n, cap = size_position(50_000, p, prem)
        print(f"\n{p}")
        print(f"   -> {n} contracts @ ${prem:.2f} = ${cap:,.0f} deployed | "
              f"risk if stopped ${cap*LOSS_AT_STOP:,.0f}")

    print("\n" + "=" * 62)
    print("SIGNAL REQUIREMENT — the only unspecified component")
    print("=" * 62)
    print(f"{'TP rate':>10} {'expectancy/trade':>18}")
    for tp, e in [(41.5, -6.10), (45.0, -2.09), (46.8, 0.00), (50.0, +3.65), (55.0, +9.40)]:
        tag = "  <- random entries" if tp == 41.5 else ("  <- BREAKEVEN" if e == 0 else "")
        print(f"{tp:>9.1f}% {e:>+17.2f}%{tag}")
    print("\nThe system above is complete except for Signal.evaluate().")
    print("Everything else is measured. That one method is worth more than all of it.")
