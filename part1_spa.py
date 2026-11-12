"""Part 1: second-price sealed-bid auction (Shoham & Leyton-Brown, Thm 7.9).

Bidder 1 has a fixed value v in {0.2, 0.5, 0.8} and sweeps its bid b over
0.00..1.00. Rivals draw values ~ U[0,1] and bid by one of three strategies.
Winner pays the highest rival bid. Ties are split 50/50 (only possible in the
fixed-rival-bid experiments, where b can hit the rival bid exactly).

Run:  python part1_spa.py          -> figures/part1_*.png + markdown tables on stdout
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

FIG = Path(__file__).parent / "figures"
FIG.mkdir(exist_ok=True)

VALUES = (0.2, 0.5, 0.8)
BIDS = np.arange(101) / 100  # exact decimals: 40/100 == 0.4, so ties with fixed rival bids are exact
N_SIMS = 100_000
SEED = 7

# rival strategy -> (bid sampler, upper bound c of the rival-bid distribution U[0,c])
STRATEGIES = {
    "truthful": (lambda rng, shape: rng.random(shape), 1.0),
    "half": (lambda rng, shape: 0.5 * rng.random(shape), 0.5),
    # value is drawn but ignored, so only the independent U[0,1] bid matters
    # (same distribution as "truthful": the two curves differ only by sampling noise)
    "random": (lambda rng, shape: rng.random(shape), 1.0),
}


def spa_utility(v, b, max_rival):
    """Bidder 1 utility in a second-price auction (broadcasts over b and max_rival)."""
    return np.where(b > max_rival, v - max_rival, np.where(b == max_rival, 0.5 * (v - max_rival), 0.0))


def analytic_utility(v, b, m, c):
    """E[u(b)] when m rivals bid i.i.d. U[0,c]:  v*t^m - m*c*t^(m+1)/(m+1),  t = min(b,c)/c."""
    t = np.minimum(b, c) / c
    return v * t**m - m * c * t ** (m + 1) / (m + 1)


def sweep(v, strategy, n_rivals, rng):
    """Mean and SE of bidder-1 utility for every bid, N_SIMS auctions per bid.

    Common random numbers: the same N_SIMS rival draws are reused for every bid,
    so differences between bids are not masked by sampling noise.
    """
    sampler, _ = STRATEGIES[strategy]
    max_rival = sampler(rng, (n_rivals, N_SIMS)).max(axis=0)
    u = np.array([spa_utility(v, b, max_rival) for b in BIDS])  # (101, N_SIMS)
    return u.mean(axis=1), u.std(axis=1) / np.sqrt(N_SIMS)


def argmax_set(u, tol=1e-12):
    """Bids achieving the max, formatted as compact intervals."""
    idx = np.flatnonzero(u >= u.max() - tol)
    runs, start = [], idx[0]
    for a, b in zip(idx, np.append(idx[1:], -1)):
        if b != a + 1:
            runs.append(f"{BIDS[start]:.2f}" if start == a else f"[{BIDS[start]:.2f}, {BIDS[a]:.2f}]")
            start = b
    return ", ".join(runs)


def part_a(n_rivals, rng):
    label = "A" if n_rivals == 1 else "C-A"
    fig, axes = plt.subplots(3, 3, figsize=(13, 10), sharex=True)
    print(f"\n### Part 1{label}: {n_rivals} rival(s), random rival values, {N_SIMS:,} auctions per bid\n")
    print("| v | rival strategy | sim argmax b | u(b=v) sim | max u sim | u(b=v) within 3 SE of max? |")
    print("|---|---|---|---|---|---|")
    for i, v in enumerate(VALUES):
        for j, strat in enumerate(STRATEGIES):
            mean, se = sweep(v, strat, n_rivals, rng)
            exact = analytic_utility(v, BIDS, n_rivals, STRATEGIES[strat][1])
            iv = int(round(v * 100))
            ok = mean[iv] >= mean.max() - 3 * se[iv]
            assert ok, (v, strat, n_rivals)
            assert np.all(np.abs(mean - exact) < 5 * se + 1e-9), "simulation disagrees with closed form"
            print(f"| {v} | {strat} | {BIDS[mean.argmax()]:.2f} | {mean[iv]:.4f} | {mean.max():.4f} | {'yes' if ok else 'NO'} |")

            ax = axes[i, j]
            ax.plot(BIDS, mean, lw=2, label="simulated")
            ax.fill_between(BIDS, mean - 2 * se, mean + 2 * se, alpha=0.25)
            ax.plot(BIDS, exact, "k--", lw=1, label="closed form")
            ax.axvline(v, color="tab:red", ls=":", label="b = v")
            ax.axhline(0, color="grey", lw=0.5)
            ax.set_title(f"v = {v}, rivals: {strat}")
            if i == 2:
                ax.set_xlabel("bidder 1 bid b")
            if j == 0:
                ax.set_ylabel("average utility")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle(f"Second-price auction, {n_rivals} rival(s): bidder 1 average utility vs bid")
    fig.tight_layout()
    out = FIG / f"part1{'a' if n_rivals == 1 else 'c_a'}_{n_rivals}rival.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"\nFigure: {out.relative_to(FIG.parent)}")


def part_b(rival_sets, tag):
    """Rival bids fixed. rival_sets: list of tuples of fixed rival bids."""
    fig, axes = plt.subplots(3, len(rival_sets), figsize=(4.3 * len(rival_sets), 10), sharex=True)
    print(f"\n### Part 1{tag}: fixed rival bids\n")
    print("| v | rival bids | u(b=v) | max u | argmax set of b | b=v optimal? |")
    print("|---|---|---|---|---|---|")
    for i, v in enumerate(VALUES):
        for j, rivals in enumerate(rival_sets):
            u = spa_utility(v, BIDS, max(rivals))
            iv = int(round(v * 100))
            ok = u[iv] >= u.max() - 1e-12
            assert ok, (v, rivals)
            print(f"| {v} | {rivals} | {u[iv]:.2f} | {u.max():.2f} | {argmax_set(u)} | {'yes' if ok else 'NO'} |")

            ax = axes[i, j]
            ax.step(BIDS, u, where="post", lw=2)
            ax.axvline(v, color="tab:red", ls=":", label="b = v")
            ax.axvline(max(rivals), color="grey", ls="--", lw=1, label="highest rival bid")
            ax.axhline(0, color="grey", lw=0.5)
            ax.set_title(f"v = {v}, rival bids = {rivals}")
            if i == 2:
                ax.set_xlabel("bidder 1 bid b")
            if j == 0:
                ax.set_ylabel("utility")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Second-price auction with fixed rival bid(s): bidder 1 utility vs bid")
    fig.tight_layout()
    out = FIG / f"part1{tag.lower().replace('-', '_')}_fixed.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"\nFigure: {out.relative_to(FIG.parent)}")


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    part_a(1, rng)
    part_b([(0.1,), (0.4,), (0.9,)], "B")
    part_a(2, rng)
    part_b([(0.1, 0.1), (0.4, 0.4), (0.9, 0.9), (0.1, 0.9)], "C-B")
