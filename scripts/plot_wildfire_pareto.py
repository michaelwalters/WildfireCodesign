#!/usr/bin/env python3
"""
Plot wildfire tradespace from mcdp-solve-query out-query/output.yaml.

This project optimizes 3 resources:
- total_cost [USD]
- logistics_load [kg]
- response_time [min]

So the Pareto set is 3D. This script plots a 2D projection:
X: logistics_load [kg]
Y: total_cost [USD]
Color: response_time [min]

Shading modes:
- none: no shading
- projection: 2D dominated region based on the 2D Pareto frontier in (load, cost),
              ignoring response_time.
- slice: same as projection, but first filters points by response_time <= --time-max

Note: In 3D, “dominated region” is not well-defined in 2D without either projecting or slicing.
"""

from __future__ import annotations

import argparse
from decimal import Decimal
from typing import List, Sequence, Tuple

import matplotlib.pyplot as plt
import yaml


def load_antichain(path: str = "out-query/output.yaml", which: str = "optimistic"):
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    raw = data[which]["minimals"]
    antichain = eval(raw, {"Decimal": Decimal, "frozenset": frozenset}, {})

    pts = list(antichain)
    if not pts:
        return [], [], []

    # Expect tuples like (cost, load, time)
    pts.sort(key=lambda p: (float(p[1]), float(p[0]), float(p[2]) if len(p) > 2 else 0.0))

    loads = [float(p[1]) for p in pts]
    costs = [float(p[0]) for p in pts]
    times = [float(p[2]) for p in pts] if len(pts[0]) >= 3 else [0.0 for _ in pts]
    return loads, costs, times


def pareto_2d_min(loads: Sequence[float], costs: Sequence[float]) -> List[int]:
    """
    Compute indices of the 2D Pareto frontier for minimization in (load, cost).
    Returns indices of nondominated points.
    """
    pts = list(enumerate(zip(loads, costs)))
    # Sort by load ascending, then cost ascending
    pts.sort(key=lambda t: (t[1][0], t[1][1]))

    frontier: List[int] = []
    best_cost = float("inf")
    for idx, (l, c) in pts:
        if c < best_cost:
            frontier.append(idx)
            best_cost = c
    return frontier


def shade_dominated_region(
    ax,
    frontier_loads: Sequence[float],
    frontier_costs: Sequence[float],
    x_max: float,
    y_max: float,
    label: str,
):
    """
    Shade the region dominated in 2D minimization (top-right of the 2D Pareto front),
    but fill up to plot bounds so the shading stays visible even if the frontier
    is a single point.
    """
    if not frontier_loads:
        return

    frontier = sorted(zip(frontier_loads, frontier_costs), key=lambda p: p[0])
    fx = [p[0] for p in frontier]
    fy = [p[1] for p in frontier]

    # Fill above the frontier to the top/right plot bounds
    poly_x = [fx[0]] + fx + [x_max]
    poly_y = [y_max] + fy + [y_max]

    ax.fill(poly_x, poly_y, alpha=0.18, zorder=1, label=label)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--path", default="out-query/output.yaml", help="Path to output.yaml")
    p.add_argument("--which", default="optimistic", choices=["optimistic", "pessimistic"])
    p.add_argument(
        "--time-max",
        type=float,
        default=None,
        help="If set, keep only points with response_time <= time-max (min)",
    )
    p.add_argument(
        "--shade",
        default="none",
        choices=["none", "projection", "slice"],
        help="Shading mode for dominated region in 2D (see module docstring).",
    )
    p.add_argument("--output", default="wildfire_tradespace.png", help="Output PNG")
    p.add_argument(
        "--label-max",
        type=int,
        default=25,
        help="Max number of point labels to draw (to avoid clutter).",
    )
    return p.parse_args()


def main():
    args = parse_args()
    loads, costs, times = load_antichain(args.path, args.which)

    if not loads:
        raise RuntimeError("No Pareto points found (empty antichain).")

    # Optional time slice
    if args.time_max is not None:
        filtered = [(l, c, t) for (l, c, t) in zip(loads, costs, times) if t <= args.time_max]
        loads = [x[0] for x in filtered]
        costs = [x[1] for x in filtered]
        times = [x[2] for x in filtered]
        if not loads:
            raise RuntimeError(f"No points remain after filtering with response_time <= {args.time_max:g} min")

    fig, ax = plt.subplots(figsize=(8, 6))

    # Scatter colored by time
    sc = ax.scatter(
        loads,
        costs,
        s=70,
        c=times,
        zorder=10,
        label="Pareto points (3D nondominated)",
    )
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label("Response time [min]")

    # Utopia marker (explicit color, so it never inherits colormap)
    ax.scatter(
        [0.0],
        [0.0],
        marker="*",
        s=360,
        color="gold",
        edgecolor="black",
        linewidth=1.2,
        zorder=999,
        label="Utopia (0,0)",
    )

    # Labels: up to N points, evenly spaced
    n = len(loads)
    if n <= args.label_max:
        idxs = range(n)
    else:
        step = max(1, n // args.label_max)
        idxs = range(0, n, step)

    for i in idxs:
        ax.annotate(
            f"${int(costs[i]):,}, {int(loads[i])}kg, {int(times[i])}min",
            xy=(loads[i], costs[i]),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=9,
            zorder=11,
        )

    # Axes + title
    ax.set_xlabel("Logistics load [kg]")
    ax.set_ylabel("Total cost [USD]")
    title = "Wildfire tradespace (cost vs load, colored by response time)"
    if args.time_max is not None:
        title += f"  |  response_time ≤ {args.time_max:g} min"
    ax.set_title(title)
    ax.grid(True, linestyle="--", alpha=0.4)

    # Set limits (used by shading)
    x_right = max(loads) * 1.05
    y_top = max(costs) * 1.05
    ax.set_xlim(left=-0.05 * max(loads), right=x_right)
    ax.set_ylim(bottom=-0.05 * max(costs), top=y_top)

    # Shading (use plot bounds so it stays visible)
    if args.shade != "none":
        if args.shade == "slice" and args.time_max is None:
            raise RuntimeError("--shade slice requires --time-max (defines the slice).")

        front_idxs = pareto_2d_min(loads, costs)
        f_loads = [loads[i] for i in front_idxs]
        f_costs = [costs[i] for i in front_idxs]

        if args.shade == "projection":
            shade_label = "Dominated region (2D projection; ignores time)"
        else:
            shade_label = f"Dominated region (2D; response_time ≤ {args.time_max:g} min)"

        shade_dominated_region(
            ax,
            f_loads,
            f_costs,
            x_max=x_right,
            y_max=y_top,
            label=shade_label,
        )

    ax.legend(loc="lower right", framealpha=0.9)
    fig.tight_layout()
    fig.savefig(args.output, dpi=150)
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
