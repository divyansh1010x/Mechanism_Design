"""Part 2: first-price sealed-bid auction with n bidders (Shoham & Leyton-Brown, Thm 7.10).

All values ~ U[0,1]. Bidders 2..n play the symmetric equilibrium bid (n-1)/n * v.
Bidder 1 deviates and bids k * v for k on a grid 0.10..2.00. The highest bid wins
and pays its own bid.

For each k we estimate:
  * bidder 1's expected (ex-ante, v1 ~ U[0,1]) utility, with a closed-form check;
  * "could have paid less and still won": the winner's slack = winning bid minus
    second-highest bid. Any slack > 0 means the winner overpaid.

Run:  python part2_fpa.py          -> figures/part2_*.png + markdown tables on stdout
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

FIG = Path(__file__).parent / "figures"
FIG.mkdir(exist_ok=True)

NS = (2, 3, 4)
# 0.10..2.00 step 0.05, plus 2/3 so every equilibrium (n-1)/n is on the grid
KS = np.union1d(np.round(np.arange(0.10, 2.0001, 0.05), 2), [2 / 3])
N_SIMS = 200_000
CENT = 0.01  # "meaningful" overpayment threshold
SEED = 11


def analytic_utility(n, k, grid=200_001):
    """E_v[ v(1-k) * P(win) ],  P(win | v) = min(1, n k v / (n-1))^(n-1)."""
    v = np.linspace(0, 1, grid)
    integrand = v * (1 - k) * np.minimum(1.0, n * k * v / (n - 1)) ** (n - 1)
    return np.trapezoid(integrand, v)


def simulate(n, rng):
    """Return a dict of per-k arrays. Common random numbers across k."""
    values = rng.random((n, N_SIMS))
    v1 = values[0]
    others = (n - 1) / n * values[1:]
    max_other = others.max(axis=0)
    second_other = np.sort(others, axis=0)[-2] if n > 2 else np.zeros(N_SIMS)

    res = {key: [] for key in ("eu", "se", "win", "frac_all", "frac_cent", "slack_all", "frac_b1", "slack_b1")}
    for k in KS:
        b1 = k * v1
        win1 = b1 > max_other  # ties have probability 0
        u1 = np.where(win1, v1 - b1, 0.0)
        # slack of whoever wins: highest bid minus second-highest bid among all n bids
        top = np.maximum(b1, max_other)
        second = np.where(win1, max_other, np.maximum(b1, second_other))
        slack = top - second

        res["eu"].append(u1.mean())
        res["se"].append(u1.std() / np.sqrt(N_SIMS))
        res["win"].append(win1.mean())
        res["frac_all"].append((slack > 0).mean())
        res["frac_cent"].append((slack >= CENT).mean())
        res["slack_all"].append(slack.mean())
        res["frac_b1"].append((slack[win1] > 0).mean() if win1.any() else np.nan)
        res["slack_b1"].append(slack[win1].mean() if win1.any() else np.nan)
    return {key: np.array(val) for key, val in res.items()}


def main():
    rng = np.random.default_rng(SEED)
    results = {n: simulate(n, rng) for n in NS}
    exact = {n: np.array([analytic_utility(n, k) for k in KS]) for n in NS}

    print(f"\n### Part 2: first-price auction, {N_SIMS:,} auctions per k\n")
    print("| n | equilibrium k=(n-1)/n | best k (sim) | E[u] at best k | best k (closed form) | E[u] at k=1 | E[u] at k=2 |")
    print("|---|---|---|---|---|---|---|")
    for n in NS:
        r, ex = results[n], exact[n]
        assert np.all(np.abs(r["eu"] - ex) < 5 * r["se"] + 1e-9), f"simulation disagrees with closed form, n={n}"
        i1, i2 = np.searchsorted(KS, 1.0), np.searchsorted(KS, 2.0)
        print(f"| {n} | {(n - 1) / n:.3f} | {KS[r['eu'].argmax()]:.2f} | {r['eu'].max():.4f} "
              f"| {KS[ex.argmax()]:.2f} | {r['eu'][i1]:.4f} | {r['eu'][i2]:.4f} |")

    print("\n#### Could the winner have paid less and still won?\n")
    print("Slack = winning bid - second-highest bid. Shown at selected k.\n")
    print("| n | k | P(bidder 1 wins) | frac. slack > 0 (all auctions) | frac. slack >= 0.01 | mean slack (all) | frac. slack > 0 (bidder 1 won) | mean slack (bidder 1 won) |")
    print("|---|---|---|---|---|---|---|---|")
    for n in NS:
        r = results[n]
        for k in sorted({0.5, round((n - 1) / n, 2), 1.0, 1.5}):
            i = int(np.argmin(np.abs(KS - k)))
            print(f"| {n} | {KS[i]:.2f} | {r['win'][i]:.3f} | {r['frac_all'][i]:.4f} | {r['frac_cent'][i]:.4f} "
                  f"| {r['slack_all'][i]:.4f} | {r['frac_b1'][i]:.4f} | {r['slack_b1'][i]:.4f} |")

    # utility plot
    fig, ax = plt.subplots(figsize=(8, 5))
    for n, color in zip(NS, ("tab:blue", "tab:orange", "tab:green")):
        r = results[n]
        ax.plot(KS, r["eu"], "o", ms=4, color=color, label=f"n={n} simulated")
        ax.plot(KS, exact[n], "-", lw=1, color=color, label=f"n={n} closed form")
        ax.axvline((n - 1) / n, ls=":", color=color)
    ax.axhline(0, color="grey", lw=0.5)
    ax.set_xlabel("bidder 1 shading factor k (bid = k·v)")
    ax.set_ylabel("bidder 1 expected utility")
    ax.set_title("First-price auction: bidder 1 deviates, others bid (n-1)/n·v\n(dotted lines: equilibrium k)")
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(FIG / "part2_utility.png", dpi=130)
    plt.close(fig)

    # overpayment plot
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for n, color in zip(NS, ("tab:blue", "tab:orange", "tab:green")):
        r = results[n]
        axes[0].plot(KS, r["frac_all"], color=color, label=f"n={n}: slack > 0")
        axes[0].plot(KS, r["frac_cent"], "--", color=color, label=f"n={n}: slack ≥ 0.01")
        axes[1].plot(KS, r["slack_all"], color=color, label=f"n={n}: all auctions")
        axes[1].plot(KS, r["slack_b1"], "--", color=color, label=f"n={n}: bidder 1 won")
        axes[2].plot(KS, r["win"], color=color, label=f"n={n}")
    axes[0].set_title("Fraction of auctions where winner could pay less")
    axes[1].set_title("Mean overpayment (winning bid - 2nd bid)")
    axes[2].set_title("P(bidder 1 wins)")
    for ax in axes:
        ax.set_xlabel("k")
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "part2_overpayment.png", dpi=130)
    plt.close(fig)
    print("\nFigures: figures/part2_utility.png, figures/part2_overpayment.png")


if __name__ == "__main__":
    main()
