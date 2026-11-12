"""Part 3: VCG mechanism for buying the cheapest A->F path (Shoham & Leyton-Brown, Fig 7.3).

Each directed edge is an agent with a private cost c. Its valuation for an
outcome is -c if its edge is on the chosen path, else 0. VCG picks the
cost-minimising path and charges each agent i (book sign convention)

    p_i = sum_{j!=i} v_j(x(v_-i)) - sum_{j!=i} v_j(x(v))
        = (others' cost on the chosen path) - (cost of best path without i)

so a negative p_i means the mechanism pays i. Agent utility = -p_i - c_i * [i on path].

Tie-break between equal-cost paths: lexicographically smallest node string.

Run:  python part3_vcg.py          -> figures/part3_misreport.png + markdown tables on stdout
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

FIG = Path(__file__).parent / "figures"
FIG.mkdir(exist_ok=True)

# Figure 7.3 (directed edges, true costs)
TRUE_COSTS = {"AB": 3, "AC": 2, "BD": 2, "BE": 1, "CE": 3, "CF": 5, "DF": 2, "EF": 1}
SOURCE, TARGET = "A", "F"
REPORTS = np.arange(0, 10.0001, 0.5)


def all_paths(edges, node=SOURCE, seen=SOURCE):
    """All simple directed paths from node to TARGET, as node strings like 'ABEF'."""
    if node == TARGET:
        return [seen]
    return [p for e in edges if e[0] == node and e[1] not in seen for p in all_paths(edges, e[1], seen + e[1])]


PATHS = all_paths(TRUE_COSTS)


def path_edges(path):
    return [path[i : i + 2] for i in range(len(path) - 1)]


def path_cost(path, costs):
    return sum(costs[e] for e in path_edges(path))


def best_path(costs, exclude=None):
    """Cheapest A->F path not using edge `exclude`. Returns (path, cost)."""
    candidates = [p for p in PATHS if exclude not in path_edges(p)]
    path = min(candidates, key=lambda p: (path_cost(p, costs), p))
    return path, path_cost(path, costs)


def vcg(declared):
    """Run VCG on declared costs. Returns (chosen path, {edge: p_i})."""
    chosen, total = best_path(declared)
    payments = {}
    for e in declared:
        others_cost_with_i = total - (declared[e] if e in path_edges(chosen) else 0)
        _, cost_without_i = best_path(declared, exclude=e)
        payments[e] = others_cost_with_i - cost_without_i  # = (-without) - (-others_with)
    return chosen, payments


def utility(edge, report, true_costs=TRUE_COSTS):
    """Utility of `edge` when it declares `report` and everyone else is truthful."""
    declared = dict(true_costs, **{edge: report})
    chosen, payments = vcg(declared)
    on_path = edge in path_edges(chosen)
    return -payments[edge] - (true_costs[edge] if on_path else 0), on_path, chosen


def main():
    chosen, payments = vcg(TRUE_COSTS)

    # reproduce the book: path ABEF, AB paid 4, BE paid 2, EF paid 3, others 0
    assert chosen == "ABEF"
    assert payments == {"AB": -4, "AC": 0, "BD": 0, "BE": -2, "CE": 0, "CF": 0, "DF": 0, "EF": -3}, payments

    print("\n### Part 3: VCG on Figure 7.3 (truthful reports)\n")
    print(f"Candidate paths: {', '.join(f'{p} ({path_cost(p, TRUE_COSTS)})' for p in PATHS)}")
    print(f"Chosen path: **{chosen}** (cost {path_cost(chosen, TRUE_COSTS)})\n")
    print("| edge | true cost | on path | best path without edge | p_i (book sign) | mechanism pays edge | utility |")
    print("|---|---|---|---|---|---|---|")
    for e, c in TRUE_COSTS.items():
        alt, alt_cost = best_path(TRUE_COSTS, exclude=e)
        u, on, _ = utility(e, c)
        print(f"| {e} | {c} | {'yes' if on else 'no'} | {alt} ({alt_cost}) | {payments[e]:g} | {-payments[e]:g} | {u:g} |")

    # misreport sweep: AB on the path, CE off it (plus all edges as a summary)
    print("\n#### Misreport sweep, reported cost 0, 0.5, ..., 10\n")
    sweeps = {e: [utility(e, r) for r in REPORTS] for e in TRUE_COSTS}
    for e in ("AB", "CE"):
        print(f"**{e}** (true cost {TRUE_COSTS[e]})\n")
        print("| reported cost | chosen path | edge on path | utility | change vs truthful |")
        print("|---|---|---|---|---|")
        u_true = utility(e, TRUE_COSTS[e])[0]
        for r, (u, on, path) in zip(REPORTS, sweeps[e]):
            print(f"| {r:g} | {path} | {'yes' if on else 'no'} | {u:g} | {u - u_true:+g} |")
        print()

    print("**All edges**: does any misreport beat the truthful utility?\n")
    print("| edge | true cost | truthful utility | best misreport utility | worst misreport utility | gain possible? |")
    print("|---|---|---|---|---|---|")
    for e, c in TRUE_COSTS.items():
        us = np.array([u for u, _, _ in sweeps[e]])
        u_true = utility(e, c)[0]
        assert us.max() <= u_true + 1e-12, f"{e} can gain by lying"
        print(f"| {e} | {c} | {u_true:g} | {us.max():g} | {us.min():g} | {'YES' if us.max() > u_true else 'no'} |")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, e, where in zip(axes, ("AB", "CE"), ("on", "off")):
        u = [s[0] for s in sweeps[e]]
        on = np.array([s[1] for s in sweeps[e]])
        ax.step(REPORTS, u, where="mid", lw=2, color="tab:blue")
        ax.scatter(REPORTS[on], np.array(u)[on], color="tab:green", zorder=3, label="edge on chosen path")
        ax.scatter(REPORTS[~on], np.array(u)[~on], color="tab:grey", zorder=3, label="edge not chosen")
        ax.axvline(TRUE_COSTS[e], color="tab:red", ls=":", label=f"true cost = {TRUE_COSTS[e]}")
        ax.axhline(0, color="grey", lw=0.5)
        ax.set_title(f"Edge {e} ({where} the truthful path ABEF)")
        ax.set_xlabel("reported cost")
        ax.legend(fontsize=8)
    axes[0].set_ylabel("edge utility (payment received − true cost)")
    fig.suptitle("VCG shortest path: utility vs misreported cost")
    fig.tight_layout()
    fig.savefig(FIG / "part3_misreport.png", dpi=130)
    plt.close(fig)
    print("\nFigure: figures/part3_misreport.png")


if __name__ == "__main__":
    main()
