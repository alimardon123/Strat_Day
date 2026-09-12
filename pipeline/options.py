"""0DTE option pricing (COUPLED — one pricing model for every table).

Black-Scholes with r = 0 from research/thread_B_inversion/step15_odte.py (imported unchanged),
IV = k × prior-close VIX, time to expiry in minutes to the 16:00 close (ACCEPTANCE A7).
Strikes 2% ITM rounded AWAY from spot to the instrument's grid (A8). Cost per instrument (A28):
  settle="cash"  SPX/XSP — buy at the ask (half the quoted spread); proceeds at expiry are
                 intrinsic at the 16:00 print with no exit spread; an early exit pays the
                 other half.
  settle="exit"  SPY — physically settled, so the position is sold before the close and both
                 spread halves are paid.
"""
import math
import sys
from pathlib import Path

_B = Path(__file__).resolve().parents[1] / "research" / "thread_B_inversion"
sys.path.insert(0, str(_B))
from step15_odte import bs_call, bs_put  # noqa: E402  (research code, unchanged)

MINUTES_PER_YEAR = 365.0 * 24 * 60
CLOSE_MOD = 960                          # 16:00
GRID = {"SPX": 5.0, "SPY": 10.0, None: None}   # in SPX points: SPY's $1 grid = 10 SPX-equivalent points (A8/A28)


def price(S, K, mins_to_close, iv, kind):
    """Option value with `mins_to_close` minutes to expiry; intrinsic at expiry."""
    T = max(float(mins_to_close), 0.0) / MINUTES_PER_YEAR
    f = bs_call if kind == "c" else bs_put
    return f(float(S), float(K), T, float(iv))[0]


def intrinsic(S, K, kind):
    return max(S - K, 0.0) if kind == "c" else max(K - S, 0.0)


def strike(S, kind, itm=0.02, grid=None):
    """ITM by `itm` of spot; with a grid, rounded away from spot (calls down, puts up)."""
    K = S * (1 - itm) if kind == "c" else S * (1 + itm)
    if not grid:
        return K
    return math.floor(K / grid) * grid if kind == "c" else math.ceil(K / grid) * grid


def trade(S0, S1, mod0, mod1, vix_prev, kind, k=1.0, itm=0.02, spread_pts=1.0, grid=None, settle="cash"):
    """Buy at mod0 (spot S0), close at mod1 (spot S1). Returns (return on premium, premium, K).
    `spread_pts` is the QUOTED bid-ask width; half is paid on entry; the exit half depends on
    `settle` (see module docstring)."""
    K = strike(S0, kind, itm, grid)
    iv = k * float(vix_prev) / 100.0
    p0 = price(S0, K, CLOSE_MOD - mod0, iv, kind) + spread_pts / 2
    if settle == "cash" and mod1 >= CLOSE_MOD - 1:
        p1 = intrinsic(S1, K, kind)
    else:
        p1 = max(price(S1, K, CLOSE_MOD - mod1, iv, kind) - spread_pts / 2, 0.0)
    return (p1 - p0) / p0, p0, K


def trade_table(trades, k=1.0, itm=0.02, spread_pts=1.0, grid=None, settle="cash", kind_col="kind"):
    """Vectorised over a trade DataFrame with columns entry_px, exit_px, entry_mod, exit_mod,
    vix_prev and `kind_col` ('c'/'p'). Adds opt_ret, premium, K."""
    out = trades.copy()
    res = [trade(r.entry_px, r.exit_px, int(r.entry_mod), int(r.exit_mod), r.vix_prev, getattr(r, kind_col),
                 k, itm, spread_pts, grid, settle) for r in out.itertuples(index=False)]
    out["opt_ret"] = [x[0] for x in res]
    out["premium"] = [x[1] for x in res]
    out["K"] = [x[2] for x in res]
    return out


if __name__ == "__main__":
    print("2% ITM put, 60 minutes left, VIX 20, spot 4000 -> 3990 at settlement:")
    for k in (1.0, 1.3, 1.6):
        r, p0, K = trade(4000, 3990, 900, 959, 20.0, "p", k=k, grid=5.0)
        print(f"  k={k}: K={K:.0f} premium={p0:.2f} (intrinsic {K - 4000:.2f} + half spread) -> {100 * r:+.2f}%")
    print("13:00 call, 180 minutes left, VIX 30, spot 4000 -> 4000 at settlement (time value only):")
    for k in (1.0, 1.3, 1.6):
        r, p0, K = trade(4000, 4000, 780, 959, 30.0, "c", k=k, grid=5.0)
        print(f"  k={k}: K={K:.0f} premium={p0:.2f} intrinsic {4000 - K:.2f} time value {p0 - 0.5 - (4000 - K):.3f} -> {100 * r:+.2f}%")
