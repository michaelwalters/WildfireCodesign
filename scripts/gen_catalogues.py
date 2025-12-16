#!/usr/bin/env python3
"""Generate catalogue YAMLs for the wildfire MCDP.

Key convention (important!):
- Functionality (F): things where "more is better" (e.g., area controlled).
- Resources (R): things where "less is better" (e.g., cost, logistics load, response time).

So response_time is a RESOURCE everywhere (it gets minimized / bounded above in queries).
"""

from pathlib import Path
import random

random.seed(7)

ROOT = Path("wildfire.mcdplib/catalogues")
ROOT.mkdir(parents=True, exist_ok=True)


def write_yaml(path: Path, text: str):
    path.write_text(text.strip() + "\n", encoding="utf-8")
    print(f"Wrote {path}")


def gen_aircraft(n: int = 100) -> str:
    """Aircraft catalogue.

    F:  [ha]
    R:  [USD, kg, min]
    """
    area_bins = [10, 15, 20, 25, 30, 35, 40, 45, 50]
    time_bins = [6, 8, 10, 12, 15, 18, 22, 26, 30]

    rows = []
    for _ in range(n):
        area = random.choice(area_bins)
        time = random.choice(time_bins)

        # Simple synthetic relationship:
        # - more area => higher cost & load
        # - faster (smaller time) => higher cost & load
        cost = (
            150_000
            + area * 25_000
            + max(0, 22 - time) * 40_000
            + random.randint(-25_000, 25_000)
        )
        load = (
            1200
            + area * 55
            + max(0, 22 - time) * 95
            + random.randint(-200, 200)
        )

        cost = max(int(cost), 120_000)
        load = max(int(load), 500)
        rows.append((area, cost, load, time))

    # A couple anchors (helps shape the front)
    rows += [
        (10, 250_000, 1500, 30),   # slow/cheap-ish
        (50, 2_000_000, 7000, 6),  # fast/expensive/heavy
    ]

    impl = []
    for k, (a, c, l, t) in enumerate(rows):
        impl.append(
            f"""  model{k}:
    f_max:
      - \"{a} ha\"
    r_min:
      - \"{c} USD\"
      - \"{l} kg\"
      - \"{t} min\"
"""
        )

    return f"""# Catalogue of aircraft options
F: [ha]
R:
  - USD
  - kg
  - min

implementations:
{''.join(impl)}
"""


def gen_crews(n: int = 100) -> str:
    """Ground crews catalogue.

    F: [ha]
    R: [USD, min]
    """
    area_bins = [20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120]
    time_bins = [10, 15, 18, 20, 25, 30, 35, 40, 45, 60]

    rows = []
    for _ in range(n):
        area = random.choice(area_bins)
        time = random.choice(time_bins)

        cost = (
            80_000
            + area * 6_500
            + max(0, 45 - time) * 8_000
            + random.randint(-12_000, 12_000)
        )
        cost = max(int(cost), 60_000)
        rows.append((area, cost, time))

    rows += [
        (20, 150_000, 60),
        (120, 1_050_000, 10),
    ]

    impl = []
    for k, (a, c, t) in enumerate(rows):
        impl.append(
            f"""  model{k}:
    f_max:
      - \"{a} ha\"
    r_min:
      - \"{c} USD\"
      - \"{t} min\"
"""
        )

    return f"""# Catalogue of ground crew options
F: [ha]
R:
  - USD
  - min

implementations:
{''.join(impl)}
"""


def gen_retardant(n: int = 40) -> str:
    """Retardant/supply catalogue.

    F: [kg]
    R: [USD]
    """
    load_bins = [1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000]

    rows = []
    for _ in range(n):
        load = random.choice(load_bins)
        cost = 20_000 + load * 18 + random.randint(-3_000, 3_000)
        cost = max(int(cost), 10_000)
        rows.append((load, cost))

    rows += [(2000, 50_000), (6000, 50_000)]

    impl = []
    for k, (l, c) in enumerate(rows):
        impl.append(
            f"""  model{k}:
    f_max:
      - \"{l} kg\"
    r_min:
      - \"{c} USD\"
"""
        )

    return f"""# Catalogue of retardant/supply options
F: [kg]
R: [USD]

implementations:
{''.join(impl)}
"""


if __name__ == "__main__":
    write_yaml(ROOT / "aircraft_catalogue.yaml", gen_aircraft(100))
    write_yaml(ROOT / "crews_catalogue.yaml", gen_crews(100))
    write_yaml(ROOT / "retardant_catalogue.yaml", gen_retardant(40))
