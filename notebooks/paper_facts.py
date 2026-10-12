"""Facts quoted in the text of the green-caribou paper's PyPSA-Earth comparison (Section 3.5).

Table 6 comes from paper_metrics.py; this script gives the other numbers in the text and in
Table 7: store cycling and charging/discharging times, the hydro reservoir swing, ammonia
dispatch by month, nuclear output, and gas use and CO2 under the carbon price.

Usage: .venv/bin/python notebooks/paper_facts.py [results directory]

Definitions, as in the paper:
- Cycling frequency f: energy charged into a carrier's stores over the year (equal to the energy
  discharged, since the stores are cyclic and lossless) divided by their energy capacity.
- Charging and discharging times: energy capacity divided by the charging or discharging power,
  both on the store side (charger, synthesis or compressor output; discharger or CCGT input).
"""
import sys
from pathlib import Path

import pandas as pd
import pypsa

ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results/europe-year-140/networks"
SCENARIOS = {
    "base": "Co2zero-3h-TD30",
    "base+h2": "Co2zero-3h-H2-TD30",
    "base+h2+nh3": "Co2zero-3h-NH3-TD30",
    "co2_price": "Co2nocap-Ep60-3h-NH3-TD30",
    "cheap_batteries": "Co2zero-3h-NH3-TD30-CheapBatt",
}
# store carrier: (charging link carrier, discharging link carrier)
STORE_LINKS = {
    "battery": ("battery charger", "battery discharger"),
    "NH3": ("NH3 synthesis", "CCGT NH3"),
    "H2": ("H2 compressor", "H2 store discharge"),
}
FOSSIL = ["CCGT", "OCGT", "coal", "lignite", "oil"]
CO2_PRICE = 60.0  # EUR/t in co2_price


def store_facts(n, carrier):
    w = n.snapshot_weightings.generators
    stores = n.stores.index[n.stores.carrier == carrier]
    energy = n.stores.loc[stores, "e_nom_opt"].sum()
    if energy <= 1e-3:
        return {}
    charge, discharge = STORE_LINKS[carrier]
    lc = n.links[n.links.carrier == charge]
    ld = n.links[n.links.carrier == discharge]
    charge_power = (lc.p_nom_opt * lc.efficiency).sum()
    discharge_power = ld.p_nom_opt.sum()
    charged = n.stores_t.p[stores].clip(upper=0).abs().mul(w, axis=0).sum().sum()
    soc = n.stores_t.e[stores].sum(axis=1)
    return {
        f"{carrier}_energy_TWh": energy / 1e6,
        f"{carrier}_cycles": charged / energy,
        f"{carrier}_charge_h": energy / charge_power if charge_power > 0 else float("nan"),
        f"{carrier}_discharge_h": energy / discharge_power if discharge_power > 0 else float("nan"),
        f"{carrier}_soc_min_date": soc.idxmin().strftime("%d %b"),
        f"{carrier}_soc_max_date": soc.idxmax().strftime("%d %b"),
    }


def facts(n):
    w = n.snapshot_weightings.generators
    demand = n.loads_t.p_set.mul(w, axis=0).sum().sum()
    row = {"demand_TWh": demand / 1e6}
    for carrier in STORE_LINKS:
        row.update(store_facts(n, carrier))

    # electricity delivered by ammonia CCGTs, by month
    idx = n.links.index[n.links.carrier == "CCGT NH3"]
    if len(idx):
        out = (-n.links_t.p1[idx]).clip(lower=0).sum(axis=1).mul(w)
        monthly = out.groupby(out.index.month).sum()
        row["NH3_delivered_TWh"] = out.sum() / 1e6
        row["NH3_share_Jan_Feb"] = monthly.loc[[1, 2]].sum() / out.sum() if out.sum() > 0 else float("nan")

    # hydro reservoirs (storage units with carrier hydro)
    hydro = n.storage_units.index[n.storage_units.carrier == "hydro"]
    if len(hydro):
        soc = n.storage_units_t.state_of_charge[hydro].sum(axis=1)
        row["hydro_soc_max_TWh"] = soc.max() / 1e6
        row["hydro_soc_min_TWh"] = soc.min() / 1e6
        row["hydro_soc_min_date"] = soc.idxmin().strftime("%d %b")
        row["hydro_drawdown_from_Jan_TWh"] = (soc.loc[soc.index.month == 1].max() - soc.min()) / 1e6

    # generation by carrier
    gen = n.generators_t.p.mul(w, axis=0).sum().groupby(n.generators.carrier).sum()
    gens = n.generators[n.generators.carrier != "load shedding"]
    nuc = gens[gens.carrier == "nuclear"]
    row["nuclear_GW"] = nuc.p_nom_opt.sum() / 1e3
    row["nuclear_new_GW"] = (nuc.p_nom_opt - nuc.p_nom).clip(lower=0).sum() / 1e3
    row["nuclear_cf"] = gen.get("nuclear", 0.0) / (nuc.p_nom_opt.sum() * w.sum()) if nuc.p_nom_opt.sum() > 0 else float("nan")
    row["gas_TWh"] = (gen.get("CCGT", 0.0) + gen.get("OCGT", 0.0)) / 1e6
    row["coal_lignite_TWh"] = (gen.get("coal", 0.0) + gen.get("lignite", 0.0)) / 1e6
    row["gas_share_of_demand"] = row["gas_TWh"] * 1e6 / demand
    row["existing_fossil_TW"] = gens.loc[gens.carrier.isin(FOSSIL), "p_nom"].sum() / 1e6

    # CO2 from fossil generators: output / efficiency * emission factor of the fuel
    fuel_co2 = n.carriers.co2_emissions
    p = n.generators_t.p.mul(w, axis=0).sum()
    fossil = n.generators.index[n.generators.carrier.isin(FOSSIL)]
    co2 = (p[fossil] / n.generators.loc[fossil, "efficiency"] * n.generators.loc[fossil, "carrier"].map(fuel_co2)).sum()
    row["co2_Mt"] = co2 / 1e6
    row["co2_payment_EUR_per_MWh"] = CO2_PRICE * co2 / demand
    return row


if __name__ == "__main__":
    rows = {}
    for label, opts in SCENARIOS.items():
        path = RESULTS / f"elec_s_140_ec_lcopt_{opts}.nc"
        if path.exists():
            rows[label] = facts(pypsa.Network(str(path)))
        else:
            print(f"missing: {path.name}")
    table = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(table.to_string(float_format=lambda v: f"{v:,.3f}"))
