from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class MonteCarloResult:
    simulations: int
    median_cagr: float
    p05_cagr: float
    p95_cagr: float
    median_max_drawdown: float


def run_monte_carlo(returns: np.ndarray, simulations: int = 10_000, seed: int = 42) -> MonteCarloResult:
    if returns.size < 252:
        raise ValueError("At least 252 daily returns are required for robustness gate.")
    rng = np.random.default_rng(seed)

    years = returns.size / 252.0
    cagr_values = []
    max_dd_values = []

    for _ in range(simulations):
        path = rng.choice(returns, size=returns.size, replace=True)
        equity = np.cumprod(1.0 + path)
        cagr = float(equity[-1] ** (1.0 / years) - 1.0)
        peaks = np.maximum.accumulate(equity)
        drawdowns = equity / peaks - 1.0
        max_dd = float(drawdowns.min())
        cagr_values.append(cagr)
        max_dd_values.append(max_dd)

    return MonteCarloResult(
        simulations=simulations,
        median_cagr=float(np.median(cagr_values)),
        p05_cagr=float(np.quantile(cagr_values, 0.05)),
        p95_cagr=float(np.quantile(cagr_values, 0.95)),
        median_max_drawdown=float(np.median(max_dd_values)),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OmegaData 10,000-simulation robustness gate")
    parser.add_argument("--prices", required=True, help="CSV/Parquet file with close_price column")
    parser.add_argument("--simulations", type=int, default=10_000)
    args = parser.parse_args()

    if args.prices.endswith(".parquet"):
        frame = pd.read_parquet(args.prices)
    else:
        frame = pd.read_csv(args.prices)

    if "close_price" not in frame.columns:
        raise ValueError("Input file must contain close_price column")

    returns = frame["close_price"].astype(float).pct_change().dropna().to_numpy()
    result = run_monte_carlo(returns=returns, simulations=args.simulations)

    print("OmegaData Robustness Gate")
    print(f"Simulations: {result.simulations}")
    print(f"Median CAGR: {result.median_cagr:.4%}")
    print(f"P05 CAGR: {result.p05_cagr:.4%}")
    print(f"P95 CAGR: {result.p95_cagr:.4%}")
    print(f"Median Max Drawdown: {result.median_max_drawdown:.4%}")


if __name__ == "__main__":
    main()
