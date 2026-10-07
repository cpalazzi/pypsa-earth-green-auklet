#!/usr/bin/env python3
"""Build the PyPSA-Earth cost files for the technology-data runs.

Base: PyPSA-Earth's default technology-data v0.13.2 costs for 2030 (EUR2020),
as retrieved to resources/europe-year-140/costs_2030.csv.

Overrides (agreed 6 Oct 2026):
- electrolysis investment: DEA AEC 1 GW, 500 EUR/kW_e (default 1500 is a single
  IEA e-fuels / private-communication value). Efficiency 0.6217 LHV is the default.
- nuclear investment: 6504 EUR/kW (DIW DataDoc, as discussed in the paper).
- fossil fuel prices: the market-based updates in references/fuel_cost_updates.csv.

Components the ammonia extension needs, under the names add_extra_components.py
reads. Defaults are used where technology-data has the component:
- ammonia synthesis  <- Haber-Bosch (DEA investment, DECHEMA hydrogen and electricity inputs)
- ammonia storage    <- NH3 (l) storage tank incl. liquefaction (Morgan 2013)
- CCGT H2, CCGT NH3  <- CCGT (DEA), without fuel
- NH3 pipeline       <- DEA energy transport, NH3 line above 2 GW (not in technology-data)
Hydrogen pipelines use technology-data's own 'H2 pipeline' entry (Welder et al.).
The hydrogen tank is technology-data's "hydrogen storage tank type 1", which
load_costs renames; its compressor is "hydrogen storage compressor".

Writes pypsa-earth/data/costs_td2030.csv and costs_td2030_cheapbatt.csv (battery
storage investment cut tenfold, the paper's stress test).
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent / "pypsa-earth"
BASE = ROOT / "resources/europe-year-140/costs_2030.csv"
FUELS = ROOT.parent / "references/fuel_cost_updates.csv"

COLUMNS = ["technology", "parameter", "value", "unit", "source", "further description", "currency_year"]


def row(tech, parameter, value, unit, source, note="", year=2020):
    return dict(zip(COLUMNS, [tech, parameter, value, unit, source, note, year]))


def copy_rows(costs, source, target, parameters=None, note=""):
    rows = costs[costs.technology == source]
    if parameters is not None:
        rows = rows[rows.parameter.isin(parameters)]
    rows = rows.assign(technology=target)
    rows["further description"] = (f"Copy of technology-data '{source}'. {note}").strip()
    return rows


def set_value(costs, tech, parameter, value, unit, source):
    mask = (costs.technology == tech) & (costs.parameter == parameter)
    assert mask.sum() == 1, (tech, parameter)
    costs.loc[mask, ["value", "unit", "source", "further description", "currency_year"]] = [
        value, unit, source, "Override of the technology-data default", 2020]


def main():
    costs = pd.read_csv(BASE)
    assert list(costs.columns) == COLUMNS

    set_value(costs, "electrolysis", "investment", 500.0, "EUR/kW_e",
              "Danish Energy Agency, data_sheets_for_renewable_fuels.xlsx, 1.1 AEC 1 GW, 2030 specific investment")
    set_value(costs, "nuclear", "investment", 6504.0, "EUR/kW_e",
              "DIW DataDoc http://hdl.handle.net/10419/80348 [HICP 2013 to 2020]")
    fuels = pd.read_csv(FUELS)
    for _, fuel in fuels.iterrows():
        set_value(costs, fuel.fuel, "fuel", float(fuel.updated_value), "EUR/MWh_th",
                  f"{fuel.methodology}; {fuel.primary_source}")

    hb = costs[costs.technology == "Haber-Bosch"].set_index("parameter").value
    extras = [
        copy_rows(costs, "Haber-Bosch", "ammonia synthesis",
                  ["investment", "FOM", "VOM", "lifetime", "electricity-input", "hydrogen-input"],
                  "Investment per kW of ammonia output; inputs per MWh of ammonia."),
        pd.DataFrame([row("ammonia synthesis", "efficiency", 1 / hb["hydrogen-input"], "per unit",
                          "1 / Haber-Bosch hydrogen-input (DECHEMA 2017)", "Ammonia out per hydrogen in, LHV")]),
        copy_rows(costs, "NH3 (l) storage tank incl. liquefaction", "ammonia storage",
                  ["investment", "FOM", "lifetime"]),
        copy_rows(costs, "CCGT", "CCGT H2", ["investment", "FOM", "VOM", "efficiency", "lifetime"],
                  "Natural-gas CCGT data used for hydrogen firing; fuel from the H2 bus."),
        copy_rows(costs, "CCGT", "CCGT NH3", ["investment", "FOM", "VOM", "efficiency", "lifetime"],
                  "Natural-gas CCGT data used for ammonia firing; fuel from the NH3 bus."),
        pd.DataFrame([
            row("NH3 pipeline", "investment", 212.6745436, "EUR/MW/km",
                "Danish Energy Agency, energy_transport_datasheet, NH3: single line above 2000 MW (0.2127 EUR/MW/m)"),
            row("NH3 pipeline", "FOM", 0.025, "%/year",
                "Danish Energy Agency, energy_transport_datasheet, NH3: 106 EUR/km/year for a 2 GW line"),
            row("NH3 pipeline", "lifetime", 50.0, "years",
                "Danish Energy Agency, energy_transport_datasheet, NH3: technical life time"),
        ]),
    ]
    costs = pd.concat([costs, *extras], ignore_index=True)
    assert not costs.duplicated(["technology", "parameter"]).any()

    out = ROOT / "data/costs_td2030.csv"
    costs.to_csv(out, index=False)
    cheap = costs.copy()
    mask = (cheap.technology == "battery storage") & (cheap.parameter == "investment")
    cheap.loc[mask, "value"] /= 10
    cheap.loc[mask, "further description"] = "Tenfold cut of the technology-data default (stress test)"
    cheap.to_csv(ROOT / "data/costs_td2030_cheapbatt.csv", index=False)
    print(out, len(costs), "rows")


if __name__ == "__main__":
    main()
