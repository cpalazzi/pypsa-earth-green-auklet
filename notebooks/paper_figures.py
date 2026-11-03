"""PyPSA-Earth figures for the green-caribou paper: capacity map and storage state of charge.

Usage: .venv/bin/python notebooks/paper_figures.py [OPTS] [OUTDIR]
  OPTS   opts wildcard of the solved network (default Co2zero-3h-NH3-TD30)
  OUTDIR folder for the PNGs (default ../green-caribou-paper/paper/images)

The map follows notebook 01 (capacity by bus, output basis). It leaves out load-shedding
pseudo-generators, transmission links (DC, B2B, pipelines) and the internal hydrogen store links.
"""
import sys
from pathlib import Path

import cartopy.crs as ccrs
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import pypsa
from cartopy.mpl.ticker import LatitudeFormatter, LongitudeFormatter
from matplotlib.patches import Circle, FancyBboxPatch, Wedge

ROOT = Path(__file__).resolve().parents[1]
OPTS = sys.argv[1] if len(sys.argv) > 1 else "Co2zero-3h-NH3-TD30"
OUTDIR = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT.parents[1] / "green-caribou-paper/paper/images"
NAME = "co2_zero_nh3"

TECH_COLORS = {
    "solar": "#f9d71c", "onwind": "#235ebc", "offwind-ac": "#6895dd", "offwind-dc": "#74c6f2",
    "ror": "#78d4cf", "OCGT": "#e05b5b", "CCGT": "#d35050", "coal": "#545454", "lignite": "#826a4a",
    "nuclear": "#ff8c00", "oil": "#2a2a2a", "biomass": "#baa741", "geothermal": "#ba91b1",
    "H2 electrolysis": "#ff29d2", "CCGT H2": "#c251ae", "NH3 synthesis": "#46a88c", "CCGT NH3": "#1b5e4a",
    "battery charger": "#999999", "battery discharger": "#dab813",
    "H2": "#ff29d2", "NH3": "#46a88c", "battery": "#999999", "hydro": "#08306b", "hydro storage": "#08306b",
}
NOT_CAPACITY = {"DC", "B2B", "H2 pipeline", "NH3 pipeline", "H2 compressor", "H2 store discharge"}
# Legend names for readers of the paper.
DISPLAY = {"onwind": "onshore wind", "offwind-ac": "offshore wind (AC)", "offwind-dc": "offshore wind (DC)",
           "ror": "run-of-river hydro", "CCGT": "gas CCGT", "OCGT": "gas OCGT", "H2 electrolysis": "electrolysis",
           "CCGT H2": "hydrogen CCGT", "NH3 synthesis": "ammonia synthesis", "CCGT NH3": "ammonia CCGT",
           "hydro storage": "hydro reservoirs and pumped hydro"}
# Map background, and branch colours dark enough to read on it.
LAND, SEA = "#f4f3ef", "#dde9f3"
AC_COLOR, DC_COLOR = "#a8a8a8", "#5f8fc8"
# Branch widths in points per MW of capacity, and the capacities shown in the line legend. AC ratings
# (s_nom) are in MVA; the linearised power flow has no reactive power, so they act as MW limits.
WIDTH_PER_MW = 1e-4
AC_LEGEND_GW, DC_LEGEND_GW = (10, 30), (5, 10)


def capacity_by_bus(n):
    gens = n.generators[n.generators.carrier != "load shedding"]
    # Leave out plants that never run (existing fossil plants under a zero-CO2 cap).
    output = n.generators_t.p.mul(n.snapshot_weightings.generators, axis=0).sum().groupby(n.generators.carrier).sum()
    gens = gens[gens.carrier.map(output).fillna(0.0) > 1e5]
    cap = gens.groupby(["bus", "carrier"]).p_nom_opt.sum().unstack(fill_value=0.0)
    ac = set(n.buses.index[n.buses.carrier == "AC"])
    links = n.links[~n.links.carrier.isin(NOT_CAPACITY)].copy()

    def ac_bus(row):
        for col in ("bus0", "bus1"):
            if row[col] in ac:
                return row[col]
        for col in ("bus0", "bus1"):
            for suffix in (" H2", " NH3"):
                if row[col].endswith(suffix) and row[col].removesuffix(suffix) in ac:
                    return row[col].removesuffix(suffix)
        return None

    links["bus"] = links.apply(ac_bus, axis=1)
    links = links.dropna(subset=["bus"])
    links["out"] = links.p_nom_opt * links.efficiency.fillna(1.0)
    su = n.storage_units.assign(carrier="hydro storage")
    cap = pd.concat([cap, links.groupby(["bus", "carrier"]).out.sum().unstack(fill_value=0.0),
                     su.groupby(["bus", "carrier"]).p_nom_opt.sum().unstack(fill_value=0.0)])
    cap = cap.groupby(level=0).sum().fillna(0.0)
    order = [c for c in TECH_COLORS if c in cap.columns] + [c for c in cap.columns if c not in TECH_COLORS]
    return cap[order]


def add_size_key(ax, r_scale):
    """Key at the top right, boxed like the colour legend: branch widths and pie sizes.

    Drawn in map coordinates rather than as a legend, so the circles have the pies' scale
    and the lines the plotted width.
    """
    x0, x1, y0, y1 = 17.8, 29.7, 64.4, 71.7
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=0.4",
                                facecolor="white", edgecolor="0.8", alpha=0.8, zorder=6))
    rows = [("AC lines", None, 0)] + [(f"{gw} GW", AC_COLOR, gw * 1e3) for gw in AC_LEGEND_GW]
    rows += [("DC links", None, 0)] + [(f"{gw} GW", DC_COLOR, gw * 1e3) for gw in DC_LEGEND_GW]
    for i, (label, color, mw) in enumerate(rows):
        y = y1 - 0.75 - i * 1.15
        if color is None:
            ax.text(18.2, y, label, fontsize="small", va="center", zorder=7)
        else:
            ax.plot([18.3, 19.4], [y, y], color=color, linewidth=WIDTH_PER_MW * mw, solid_capstyle="butt", zorder=7)
            ax.text(19.65, y, label, fontsize="small", va="center", zorder=7)
    y = y1 - 0.3
    for gw in (100, 50):
        r = np.sqrt(gw * 1e3) * r_scale
        y -= r
        ax.add_patch(Circle((27.6, y), r, facecolor="none", edgecolor="black", linewidth=0.8, zorder=7))
        ax.text(27.6 - r - 0.3, y, f"{gw} GW", fontsize="small", va="center", ha="right", zorder=7)
        y -= r + 0.35


def plot_map(n, path):
    cap = capacity_by_bus(n)
    cap = cap[cap.sum(axis=1) > 0]
    fig, ax = plt.subplots(figsize=(10, 8), subplot_kw={"projection": ccrs.PlateCarree()})
    n.plot(ax=ax, boundaries=(-11, 30, 34, 72), bus_sizes=0.0, color_geomap={"land": LAND, "ocean": SEA},
           line_widths=WIDTH_PER_MW * n.lines.s_nom_opt, line_colors=AC_COLOR,
           link_widths=WIDTH_PER_MW * n.links.p_nom_opt.where(n.links.carrier == "DC", 0.0), link_colors=DC_COLOR,
           branch_components={"Line", "Link"})
    r_scale = 2.0 / np.sqrt(cap.sum(axis=1).max())
    for bus, row in cap.iterrows():
        x, y = n.buses.at[bus, "x"], n.buses.at[bus, "y"]
        total, start = row.sum(), 0.0
        for carrier, value in row[row > 0].items():
            angle = 360 * value / total
            ax.add_patch(Wedge((x, y), np.sqrt(total) * r_scale, start, start + angle,
                               facecolor=TECH_COLORS.get(carrier, "#aaaaaa"), edgecolor="white", linewidth=0.3))
            start += angle
    handles = [plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=TECH_COLORS.get(c, "#aaaaaa"),
                          label=DISPLAY.get(c, c), markersize=8) for c in cap.columns if cap[c].sum() > 0]
    ax.legend(handles=handles, loc="upper left", fontsize="small", ncol=2, frameon=True)
    add_size_key(ax, r_scale)
    ax.set_axis_on()
    ax.set_xlim(-11, 30)
    ax.set_ylim(34, 72)
    ax.set_xticks(np.arange(-10, 31, 5), crs=ccrs.PlateCarree())
    ax.set_yticks(np.arange(35, 73, 5), crs=ccrs.PlateCarree())
    ax.xaxis.set_major_formatter(LongitudeFormatter())
    ax.yaxis.set_major_formatter(LatitudeFormatter())
    ax.tick_params(labelsize=8)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_soc(n, path):
    soc = n.stores_t.e.T.groupby(n.stores.carrier).sum().T
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(12, 6), sharex=True, gridspec_kw={"height_ratios": [3, 2]})
    # Seasonal stores on one axis: hydro reservoirs (storage units) and ammonia tanks.
    hydro = n.storage_units.index[n.storage_units.carrier == "hydro"]
    if len(hydro):
        top.plot(soc.index, n.storage_units_t.state_of_charge[hydro].sum(axis=1) / 1e6,
                 color=TECH_COLORS["hydro"], linewidth=1.4, label="Hydro reservoirs")
    if "NH3" in soc:
        top.plot(soc.index, soc["NH3"] / 1e6, color=TECH_COLORS["NH3"], linewidth=1.4, label="NH$_3$")
    top.set_ylabel("Seasonal stores (TWh)")
    for carrier, label in (("battery", "Battery"), ("H2", "H$_2$")):
        if carrier in soc:
            bottom.plot(soc.index, soc[carrier] / 1e3, color=TECH_COLORS[carrier], linewidth=0.8, label=label)
    bottom.set_ylabel("Battery and H$_2$ (GWh)")
    for ax, loc in ((top, "center right"), (bottom, "upper right")):
        ax.grid(alpha=0.3)
        ax.legend(loc=loc, frameon=False)
        ax.yaxis.set_major_locator(mticker.MaxNLocator(5))
    fig.autofmt_xdate()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    net = pypsa.Network(str(ROOT / f"results/europe-year-140/networks/elec_s_140_ec_lcopt_{OPTS}.nc"))
    OUTDIR.mkdir(parents=True, exist_ok=True)
    plot_map(net, OUTDIR / f"pypsa_generation_map_{NAME}.png")
    plot_soc(net, OUTDIR / f"pypsa_soc_{NAME}.png")
    print("written:", OUTDIR / f"pypsa_generation_map_{NAME}.png", OUTDIR / f"pypsa_soc_{NAME}.png")
