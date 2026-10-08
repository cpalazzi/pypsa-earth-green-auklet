"""Appendix F of the green-caribou paper: co2-zero-nh3 at 1 h against 3 h resolution.

Usage: .venv/bin/python notebooks/resolution_check.py [DEA30|TD30]

DEA30 compares the March pair in results/europe-year-140/networks/_resolution_sensitivity/ (September
input set, network before isolated fragments were connected; both resolutions shed the same lost
load, which the system cost excludes). TD30 compares the current 3 h run with the 1 h run, once
arc/submit_td30_1h.sh has been run and its result fetched.
"""
import sys
from pathlib import Path

import pandas as pd
import pypsa

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paper_metrics import metrics  # noqa: E402

NETWORKS = Path(__file__).resolve().parents[1] / "results/europe-year-140/networks"
SET = sys.argv[1] if len(sys.argv) > 1 else "DEA30"
FOLDER = NETWORKS / "_resolution_sensitivity" if SET == "DEA30" else NETWORKS

rows = {}
for res in ("3h", "1h"):
    n = pypsa.Network(str(FOLDER / f"elec_s_140_ec_lcopt_Co2zero-{res}-NH3-{SET}.nc"))
    row = metrics(n)
    gens = n.generators[n.generators.carrier != "load shedding"].groupby("carrier").p_nom_opt.sum() / 1e3
    row["battery_charger_GW"] = n.links.p_nom_opt[n.links.carrier == "battery charger"].sum() / 1e3
    for carrier in ("solar", "onwind", "nuclear"):
        row[f"{carrier}_GW"] = gens.get(carrier, 0.0)
    rows[res] = row

keep = ["LCOE_EUR_per_MWh", "lost_load_TWh", "capacity_battery_GWh", "battery_charger_GW", "capacity_H2_GWh",
        "capacity_NH3_GWh", "delivered_NH3_TWh", "solar_GW", "onwind_GW", "nuclear_GW"]
table = pd.DataFrame(rows).loc[keep].astype(float)
table["change_%"] = 100 * (table["1h"] / table["3h"] - 1)
print(table.round(2).to_string())
