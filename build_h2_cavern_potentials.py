"""Salt cavern potential for hydrogen at each node of the 140-node Europe network.

Usage: .venv/bin/python build_h2_cavern_potentials.py CAVERNS REGIONS_ONSHORE REGIONS_OFFSHORE
  CAVERNS           h2_salt_caverns_GWh_per_sqkm.geojson: the sites of Caglayan et al. (2020),
                    https://doi.org/10.1016/j.ijhydene.2019.12.161, as digitised for PyPSA-Eur,
                    https://zenodo.org/records/16899309/files/h2_salt_caverns_GWh_per_sqkm.geojson
  REGIONS_*         resources/europe-year-140/bus_regions/regions_{onshore,offshore}_elec_s_140.geojson

Follows PyPSA-Eur (build_salt_cavern_potentials.py, prepare_sector_network.py): each site's potential
is its energy density times its area, and the share of the site inside a node's region is credited to
that node. Onshore and nearshore sites count, offshore sites do not, a node needs at least 2 TWh and
its potential is clipped at 1000 TWh.
Writes pypsa-earth/data/h2_cavern_potentials_s_140.csv, read through electricity: h2_caverns: potentials.
"""
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parent / "pypsa-earth"
LOCATIONS = ["onshore", "nearshore"]
MIN_TWH, MAX_TWH = 2.0, 1000.0


def area_km2(gdf):
    return gdf.to_crs(epsg=3035).area / 1e6


def main(caverns_path, onshore_path, offshore_path):
    regions = pd.concat([gpd.read_file(onshore_path), gpd.read_file(offshore_path)])[["name", "geometry"]]
    regions = gpd.GeoDataFrame(regions, crs="EPSG:4326").dissolve(by="name").reset_index()
    caverns = gpd.read_file(caverns_path)
    caverns["site_area"] = area_km2(caverns)
    overlay = gpd.overlay(regions, caverns, keep_geom_type=True)
    overlay["share"] = area_km2(overlay) / overlay.site_area
    overlay["TWh"] = overlay.capacity_per_area * overlay.share * overlay.site_area / 1e3
    by_type = overlay.groupby(["name", "storage_type"]).TWh.sum().unstack("storage_type").fillna(0.0)
    potential = by_type[LOCATIONS].sum(axis=1)
    by_type["e_nom_max_MWh"] = potential.where(potential >= MIN_TWH, 0.0).clip(upper=MAX_TWH) * 1e6
    out = ROOT / "data/h2_cavern_potentials_s_140.csv"
    by_type[by_type.e_nom_max_MWh > 0].round(3).to_csv(out)
    print(out, (by_type.e_nom_max_MWh > 0).sum(), "nodes")
    return by_type


if __name__ == "__main__":
    main(*sys.argv[1:4])
