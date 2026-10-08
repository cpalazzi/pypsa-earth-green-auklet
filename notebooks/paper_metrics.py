"""Metrics quoted in the green-caribou paper's PyPSA-Earth comparison (Tables 6-7, Section 3.5).

Usage: .venv/bin/python notebooks/paper_metrics.py [TD30|DEA30]

Definitions, as in the paper:
- System cost: the objective plus objective_constant (annualised cost of the existing capacity of
  extendable assets, which PyPSA keeps out of the objective), minus the lost-load penalty. LCOE is
  that cost per MWh of demand. The September paper divided the objective alone by demand, so its
  LCOE omitted existing capacity and was mostly lost-load penalty.
- Lost load: energy from load-shedding generators, reported separately with its buses.
- Generation capacity: optimised generator capacity, excluding load-shedding pseudo-generators
  (feasibility slack; the September Table 6 counted their 0.64 TW by mistake).
- Storage capacity: optimised store energy plus storage units (p_nom_opt * max_hours).
- Electricity delivered by a carrier: AC output of its reconversion links (battery discharger,
  CCGT NH3, CCGT H2).
- Cycling frequency f: energy discharged from the carrier's stores over the year divided by their
  energy capacity (equivalent full cycles).
"""
import sys
from pathlib import Path

import pandas as pd
import pypsa

RESULTS = Path(__file__).resolve().parents[1] / "results/europe-year-140/networks"
SET = sys.argv[1] if len(sys.argv) > 1 else "TD30"
SCENARIOS = {
    "co2_zero": f"Co2zero-3h-{SET}",
    "co2_zero_h2": f"Co2zero-3h-H2-{SET}",
    "co2_zero_nh3": f"Co2zero-3h-NH3-{SET}",
    "co2_price_nh3": f"Co2nocap-Ep60-3h-NH3-{SET}",
    "low_cost_batt": f"Co2zero-3h-NH3-{SET}-CheapBatt",
}
RECONVERSION = {"battery": "battery discharger", "NH3": "CCGT NH3", "H2": "CCGT H2"}


def metrics(n):
    w = n.snapshot_weightings.generators
    demand = n.loads_t.p_set.mul(n.snapshot_weightings.objective, axis=0).sum().sum()
    gens = n.generators[~n.generators.carrier.isin(["load", "load shedding"])]
    shed = n.generators.index[n.generators.carrier.isin(["load", "load shedding"])]
    shed_e = n.generators_t.p[shed].mul(w, axis=0).sum() if len(shed) else pd.Series(dtype=float)
    penalty = (shed_e * n.generators.loc[shed_e.index, "marginal_cost"]).sum()
    system_cost = n.objective + getattr(n, "objective_constant", 0.0) - penalty
    row = {
        "LCOE_EUR_per_MWh": system_cost / demand,
        "system_cost_bnEUR": system_cost / 1e9,
        "objective_bnEUR": n.objective / 1e9,
        "lost_load_penalty_bnEUR": penalty / 1e9,
        "lost_load_TWh": shed_e.sum() / 1e6,
        "lost_load_buses": " ".join(sorted(n.generators.loc[shed_e.index[shed_e > 1e3], "bus"])),
        "demand_TWh": demand / 1e6,
        "gen_TW": gens.p_nom_opt.sum() / 1e6,
        "nuclear_GW": gens.p_nom_opt[gens.carrier == "nuclear"].sum() / 1e3,
        "nuclear_existing_GW": gens.p_nom[gens.carrier == "nuclear"].sum() / 1e3,
    }
    store_e = n.stores.e_nom_opt.groupby(n.stores.carrier).sum()
    su = n.storage_units
    su_e = (su.p_nom_opt * su.max_hours).sum() if not su.empty else 0.0
    row["storage_TWh"] = (store_e.sum() + su_e) / 1e6
    row["storage_units_TWh"] = su_e / 1e6
    discharge = n.stores_t.p.clip(upper=0).abs().mul(w, axis=0).sum().groupby(n.stores.carrier).sum()
    soc = n.stores_t.e.T.groupby(n.stores.carrier).sum().T
    for carrier, link in RECONVERSION.items():
        idx = n.links.index[n.links.carrier == link]
        row[f"delivered_{carrier}_TWh"] = (-n.links_t.p1[idx]).clip(lower=0).mul(w, axis=0).sum().sum() / 1e6
        cap = store_e.get(carrier, 0.0)
        row[f"capacity_{carrier}_GWh"] = cap / 1e3
        row[f"cycles_{carrier}"] = discharge.get(carrier, 0.0) / cap if cap > 0 else float("nan")
        if carrier in soc:
            row[f"soc_min_{carrier}_GWh"] = soc[carrier].min() / 1e3
            row[f"soc_max_{carrier}_GWh"] = soc[carrier].max() / 1e3
    return row


if __name__ == "__main__":
    rows = {}
    for label, opts in SCENARIOS.items():
        path = RESULTS / f"elec_s_140_ec_lcopt_{opts}.nc"
        if path.exists():
            rows[label] = metrics(pypsa.Network(str(path)))
        else:
            print(f"missing: {path.name}")
    table = pd.DataFrame(rows).T
    pd.set_option("display.width", 200)
    print(table.T.to_string(float_format=lambda v: f"{v:,.2f}"))
    out = RESULTS.parent / f"paper_metrics_{SET}.csv"
    table.to_csv(out)
    print(f"written: {out}")
