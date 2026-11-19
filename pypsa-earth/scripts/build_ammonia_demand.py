# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Build a constant ammonia demand at each clustered node, for the ``NH3dem`` and ``NH3demG`` opts.

Each country's production is the USGS figure (Table 12 of the nitrogen tables; kt of nitrogen
times 17/14), averaged over ``ammonia_demand: years``. Production is split among the country's
plants in ``data/ammonia_plants_europe.csv`` in proportion to their ammonia capacity: a plant
without a capacity gets no share when another plant of its country has one, and an equal share
when none has. Each plant goes to the node whose onshore region contains it, or else to the
nearest onshore region of its country. Countries with production but no plant are logged and
left out.

The USGS table is read as in upstream's ``build_ammonia_production.py``. Output: one row per node
with a demand, giving ``p_set`` (MW of ammonia at its lower heating value, constant over the
year), the annual energy and mass, and the plants.
"""

import country_converter as coco
import geopandas as gpd
import pandas as pd
from _helpers import configure_logging, create_logger

logger = create_logger(__name__)


def country_production(usgs, years):
    """Mean ammonia production of each country over ``years``, in kt of NH3 a year."""
    table = pd.read_excel(
        usgs,
        sheet_name="T12",
        skiprows=5,
        header=0,
        index_col=0,
        skipfooter=7,
        na_values=["--"],
    )
    table.index = coco.CountryConverter().convert(
        table.index.astype(str).str.strip(), to="iso2", not_found=None
    )
    table = table.rename(columns=str)[[str(y) for y in years]]
    table = table.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    return table.groupby(level=0).sum().mean(axis=1) * 17 / 14


def plant_production(plants, production):
    """Production of each plant, in kt of NH3 a year, from its country's total."""
    plants = plants.copy()
    plants["share"] = 0.0
    for country, group in plants.groupby("country"):
        capacity = group.capacity
        if capacity.notna().any():
            share = capacity.fillna(0.0) / capacity.sum()
        else:
            share = pd.Series(1.0 / len(group), index=group.index)
        plants.loc[group.index, "share"] = share
    plants["kt"] = plants.share * plants.country.map(production).fillna(0.0)
    return plants


def assign_nodes(plants, regions):
    """Node of each plant: its region if one of its country contains it, else the nearest one."""
    regions = regions.to_crs(3035)
    points = gpd.GeoSeries(
        gpd.points_from_xy(plants.x, plants.y), index=plants.index, crs=4326
    ).to_crs(3035)
    nodes = {}
    for i, country in plants.country.items():
        own = regions[regions.country == country]
        if own.empty:
            logger.warning(
                f"No onshore region in {country} for plant {plants.at[i, 'plant']}"
            )
            continue
        inside = own[own.contains(points[i])]
        if len(inside):
            nodes[i] = inside["name"].iloc[0]
        else:
            nearest = own.distance(points[i]).idxmin()
            nodes[i] = own.at[nearest, "name"]
            logger.info(
                f"Plant {plants.at[i, 'plant']} lies outside the onshore regions of {country}; "
                f"assigned to the nearest, {nodes[i]}"
            )
    return pd.Series(nodes, dtype=object)


if __name__ == "__main__":
    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake("build_ammonia_demand", simpl="", clusters="140")

    configure_logging(snakemake)
    options = snakemake.params.ammonia_demand
    countries = snakemake.params.countries
    mwh_per_t = options["lhv_GJ_per_t"] / 3.6

    production = country_production(snakemake.input.usgs, options["years"])
    production = production[production.index.isin(countries) & (production > 0)]

    plants = pd.read_csv(snakemake.input.plants)
    plants = plants.rename(
        columns={
            "Plant": "plant",
            "Ammonia [kt/a]": "capacity",
            "Longitude": "x",
            "Latitude": "y",
        }
    )
    plants["country"] = coco.CountryConverter().convert(
        plants.Country.str.strip(), to="iso2", not_found=None
    )
    plants = plants[plants.country.isin(production.index)]
    missing = production.index.difference(plants.country)
    if len(missing):
        logger.warning(
            f"Ammonia production without a plant, left out: "
            f"{production[missing].round(0).to_dict()} kt a year"
        )

    plants = plant_production(plants, production)
    regions = gpd.read_file(snakemake.input.regions)
    plants["node"] = assign_nodes(plants, regions)
    plants = plants.dropna(subset=["node"])

    demand = plants.groupby("node").agg(
        kt_per_year=("kt", "sum"),
        plants=("plant", lambda p: "; ".join(p)),
    )
    demand["TWh_per_year"] = demand.kt_per_year * mwh_per_t / 1e3
    demand["p_set"] = demand.kt_per_year * 1e3 * mwh_per_t / 8760.0
    demand = demand[demand.p_set > 0][
        ["p_set", "TWh_per_year", "kt_per_year", "plants"]
    ]
    demand.index.name = "node"
    logger.info(
        f"Ammonia demand: {demand.TWh_per_year.sum():.1f} TWh a year at {len(demand)} nodes, "
        f"of {production.sum() * mwh_per_t / 1e3:.1f} TWh produced in the model's countries"
    )
    demand.to_csv(snakemake.output[0])
