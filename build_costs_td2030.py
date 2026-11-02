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
reads. Defaults are used where technology-data has the component, except synthesis:
- ammonia synthesis  <- DEA sheet 5.4, 500 MW plant with a dedicated ASU, as in the
  green-caribou analytical model (30 Oct 2026). technology-data's Haber-Bosch takes
  DEA's 100 MW plant with the 2015-2020 price update applied twice and no ASU, and
  DECHEMA's 0.2473 MWh_el/MWh_NH3 for the compressors of a conventional plant; DEA's
  synthesis data assume hydrogen from a pressurised electrolyser (note C).
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


def ammonia_synthesis_rows():
    """DEA 5.4 Hydrogen to Ammonia, 500 MW plant with a dedicated ASU (2020 EUR, LHV).

    The values of green_caribou/analytical_inputs.py. Per unit of total input the plant
    takes 0.947 hydrogen and 0.053 electricity and yields 0.823 ammonia; the ASU uses
    0.25 MWh of electricity per tonne of nitrogen, at 0.839 t of nitrogen per tonne of
    ammonia. The investment is 0.1889 MEUR per tonne a day, converted at 5.17 MWh/t and
    raised by 1.09 for the ASU (note F). Cost depends on plant size, not year (note J).
    """
    source = "Danish Energy Agency, data_sheets_for_renewable_fuels.xlsx, 5.4 Hydrogen to Ammonia, 500 MW"
    nh3_lhv = 5.17  # MWh/t
    hydrogen = 0.947 / 0.823
    rows = [
        ("investment", 0.18888710678556964e6 / (nh3_lhv * 1000 / 24) * 1.09, "EUR/kW_NH3",
         "0.1889 MEUR per t/day, x 1.09 for a dedicated ASU (note F); per kW of ammonia at 5.17 MWh/t"),
        ("FOM", 3.0, "%/year", "3 % of investment (note G)"),
        ("VOM", 0.021268, "EUR/MWh_NH3", ""),
        ("lifetime", 30.0, "years", ""),
        ("electricity-input", 0.053 / 0.823 + 0.25 * 0.839 / nh3_lhv, "MWh_el/MWh_NH3",
         "Synthesis 0.053 / 0.823 (hydrogen at the electrolyser's 30 bar, note C) plus ASU 0.25 MWh/t_N2"),
        ("hydrogen-input", hydrogen, "MWh_H2/MWh_NH3", "0.947 / 0.823"),
        ("efficiency", 1 / hydrogen, "per unit", "Ammonia out per hydrogen in, LHV"),
    ]
    return pd.DataFrame([row("ammonia synthesis", p, v, u, source, note) for p, v, u, note in rows])


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

    extras = [
        ammonia_synthesis_rows(),
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
