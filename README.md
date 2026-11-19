# pypsa-earth-green-auklet

A research fork of [PyPSA-Earth](https://github.com/pypsa-meets-earth/pypsa-earth) v0.8.0 that extends its electricity-only workflow. It holds the PyPSA-Earth runs of two studies:

- "An analytical cost model for green energy carriers" (green-caribou), which compares its analytical model with these runs. The runs use the code and configs at commit `2d5ac52`.
- A follow-up study (tartan-tortoise) that runs the same model at a range of carbon prices.

The model covers 35 European countries (the EU27 plus the UK, Norway, Switzerland, Serbia, Bosnia and Herzegovina, Albania, North Macedonia and Montenegro) in 140 nodes. It optimises one year at 3-hour resolution, with weather year 2013 and 2030 demand, and is solved with Gurobi.

The fork is kept so that the papers' runs can be reproduced; it is not maintained as a general model. For general use of PyPSA-Earth, and for issues and contributions, go to the main project, [pypsa-meets-earth/pypsa-earth](https://github.com/pypsa-meets-earth/pypsa-earth).

## Changes to PyPSA-Earth v0.8.0

- Ammonia: synthesis (Haber-Bosch, with its electricity use), liquid ammonia tanks, ammonia CCGTs (combined-cycle gas turbines that burn ammonia) and ammonia pipelines between nodes, in `pypsa-earth/scripts/add_extra_components.py`.
- Hydrogen: hydrogen-to-power through hydrogen CCGTs in place of fuel cells, hydrogen pipelines with a cost factor for submarine sections, and salt caverns at nodes with salt (`build_h2_cavern_potentials.py`).
- Nuclear capacity can be extended.
- The cost file is set per scenario (`costs.file`). The 2030 cost sets come from the Danish Energy Agency's technology catalogues (`pypsa-earth/data/costs_dea2030.csv`) and from technology-data (`build_costs_td.py`).
- Fixes for pumped-hydro storage durations, hydro capacities, duplicated OpenStreetMap lines and links, and the ratings of merged HVDC (high-voltage direct current) links, reported upstream in issues #2072 to #2075.

[DEVELOPMENT_NOTES.md](DEVELOPMENT_NOTES.md) records every change and the green-caribou runs. The scenario configs are in `pypsa-earth/configs/scenarios/`. The green-caribou runs use the configs whose names contain `td30`, except the three `co2-price-sweep` configs, which hold the follow-up study's carbon-price runs.

## Quick Start

### Local Development

1. **Setup environment:**
   ```bash
   ./local_setup.sh
   source pypsa-earth/.venv/bin/activate
   ```

2. **Run test scenario:**
   ```bash
   cd pypsa-earth
   snakemake --cores 4 \
     results/europe-day-140/networks/elec_s_140_ec_lcopt_Co2L-3h.nc \
     --configfile configs/scenarios/config.europe-day-140.yaml
   ```

3. **Analyze results:**
   ```python
   import pypsa
   n = pypsa.Network("results/europe-day-140/networks/elec_s_140_ec_lcopt_Co2L-3h.nc")
   print(f"Total cost: €{n.objective:,.0f}")
   ```

### ARC Cluster

1. **Initial setup (one-time):**
   ```bash
   ssh <user>@arc-login.arc.ox.ac.uk
   bash arc/arc_initial_setup.sh
   ```

2. **Submit jobs:**
   ```bash
   cd pypsa-earth-green-auklet/pypsa-earth
   sbatch ../arc/jobs/01_build_profiles.sh europe-year-140-profiles configs/scenarios/config.europe-year-140-profiles.yaml
   sbatch ../arc/jobs/02_build_networks_and_solve_power.sh europe-year-140-co2-zero-h2-power configs/scenarios/config.europe-year-140-co2-zero-h2-power.yaml
   ```

3. **Download results:**
   ```bash
   rsync -av <user>@arc-login.arc.ox.ac.uk:/data/<group>/<user>/pypsa-earth-green-auklet/results/europe-day-140/ results/europe-day-140/
   ```

## Repository Structure

```
pypsa-earth-green-auklet/
├── pypsa-earth/                          # Main PyPSA-Earth model
│   ├── configs/scenarios/                # Scenario configurations
│   │   └── config.europe-day-140.yaml   # European 1-day test
│   ├── scripts/                          # Model scripts
│   ├── envs/environment.yaml            # Python dependencies
│   └── Snakefile                         # Snakemake workflow
├── arc/                                  # ARC cluster scripts
│   ├── arc_initial_setup.sh             # Interactive setup wizard
│   ├── build-pypsa-earth-env            # Environment builder
│   ├── jobs/01_build_profiles.sh        # Step 1: build renewable profiles
│   ├── jobs/02_build_networks_and_solve_power.sh  # Step 2: power build + solve
│   └── README.md                         # ARC documentation
├── notebooks/                            # Analysis notebooks
│   ├── 000_arc_run_steps.ipynb          # ARC workflow example
│   └── 001_run_analysis.ipynb           # Results analysis
├── results/                              # Model results (gitignored, keep via .gitkeep)
├── local_setup.sh                        # Local environment setup
├── DEVELOPMENT_NOTES.md                  # Development notes + test plan
└── README.md                             # This file
```

## Configuration

### Current Scenarios

#### europe-day-140
- **Geographic scope**: 35 European countries
- **Time range**: 1 day (2013-07-15)
- **Resolution**: 3-hour timesteps (8 snapshots)
- **Network**: 140 nodes, load-weighted distribution
- **Purpose**: Quick validation and testing
- **Runtime**: Scenario- and environment-dependent; use Snakemake benchmark files and `sacct` (ARC) for measured timings.

#### europe-year-140 (default limited CO2)
- **Geographic scope**: 35 European countries
- **Time range**: 2013 full year
- **Resolution**: 3-hour timesteps
- **Network**: 140 nodes, load-weighted distribution
- **CO2 cap**: Explicitly limited (default European cap)
- **Purpose**: Baseline annual run used for comparisons

#### europe-year-140 CO2 variants
- `config.europe-year-140-co2-zero.yaml`: zero CO2 cap
- `config.europe-year-140-co2-uncapped.yaml`: effectively uncapped CO2
- `config.europe-year-140-co2-zero-nh3.yaml`: zero CO2 with H2 + NH3 optionality (base costs)
- `config.europe-year-140-co2-zero-nh3-dea30.yaml`: zero CO2 with H2 + NH3, DEA 2030 costs

### Creating New Scenarios

1. Copy existing config:
   ```bash
   cp pypsa-earth/configs/scenarios/config.europe-day-140.yaml \
      pypsa-earth/configs/scenarios/config.europe-week-140.yaml
   ```

2. Update key parameters:
   ```yaml
   run:
     name: "europe-year-140"  # keep base-year run name to reuse existing profiles
   
   scenario:
     opts: [Co2L-3h-week01]  # unique output label for this variant
     sopts: ["168h"]  # One week
   
   snapshots:
     start: "2013-07-08"
     end: "2013-07-15"
   ```

3. Dry-run first:
   ```bash
   cd pypsa-earth
    bash scripts/run_from_base_profiles.sh \
       configs/scenarios/config.europe-week-140.yaml \
       results/europe-year-140/networks/elec_s_140_ec_lcopt_Co2L-3h-week01.nc \
       4
   ```

4. The script runs a dry-run first, then the real workflow with a restricted rule set.

## Cost Data

### Cost Files

Two cost files are available in `pypsa-earth/data/`:

| File | Basis | Currency | Description |
|------|-------|----------|-------------|
| `costs.csv` | DIW 2010 / budischak2013 | Mixed (2013 EUR + some USD) | Original PyPSA-Earth defaults |
| `costs_dea2030.csv` | DEA 2030 first, HICP-inflated fallback | 2020 EUR throughout | Updated cost assumptions for 2030 studies |

### Key Differences (costs_dea2030.csv vs costs.csv)

| Technology | Old value | New value | Source |
|------------|-----------|-----------|--------|
| Solar utility | 600 EUR/kW | 380 EUR/kW | DEA 2030 sheet 22 |
| Onshore wind | 1040 EUR/kW | 930 EUR/kW | DEA 2030 sheet 20 |
| Offshore wind | 2040 EUR/kW | 1640 EUR/kW | DEA 2030 sheet 21 |
| CCGT | 800 EUR/kW | 883 EUR/kW (η 0.58) | DEA 2030 sheet 05 |
| OCGT | 400 EUR/kW | 468 EUR/kW (η 0.41) | DEA 2030 sheet 05 |
| Electrolysis | 669 EUR/kW | 500 EUR/kW (input basis) | DEA 2030 sheet 86 |
| Battery inverter | 411 USD/kW | 149 EUR/kW | DEA 2030 sheet 180 |
| H2 pipeline | 267 EUR/MW/km | 400 EUR/MW/km | European Hydrogen Backbone |
| NH3 pipeline | 267 EUR/MW/km | 200 EUR/MW/km | Hydrogen Council 2021 |
| H2 storage tank | 11.2 USD/kWh | 47.76 EUR/kWh | DEA 2030 sheet 151 |

Technologies not available from DEA were HICP-inflated from 2013 EUR to 2020 EUR (× 1.084).

### Using the DEA 2030 Costs

The Snakefile reads the cost file path from `costs.file` in config (defaulting to `data/costs.csv`). To use DEA 2030 costs, add to your scenario config:

```yaml
costs:
  file: "data/costs_dea2030.csv"
```

This key is only used when `enable.retrieve_cost_data: false`. An example scenario config using DEA 2030 costs:

```
configs/scenarios/config.europe-year-140-co2-zero-nh3-dea30.yaml
```

### Input/Output Basis Conventions

Cost values in the CSV follow the basis expected by the code that applies them:

- **Electrolysis**: input basis (EUR/kW_input_e) — code uses `capital_cost` directly, `p_nom` = MW input
- **CCGT H2/NH3, NH3 synthesis**: output basis (EUR/kW_output) — code multiplies `capital_cost × efficiency`
- **Battery inverter**: bidirectional, no conversion needed
- **Pipelines**: EUR/MW/km, multiplied by line length and submarine cost factor

## Naming Conventions

### Configuration Files
Format: `config.<region>-<timespan>-<nodes>.yaml`

Examples:
- `config.europe-day-140.yaml` - Europe, 1 day, 140 nodes
- `config.europe-week-140.yaml` - Europe, 1 week, 140 nodes
- `config.europe-year-140.yaml` - Europe, full year, 140 nodes
- `config.europe-year-140-co2-zero.yaml` - Europe, full year, zero CO2 cap
- `config.europe-year-140-co2-uncapped.yaml` - Europe, full year, uncapped CO2

### Run Names
`run.name` controls `resources/`, `networks/`, and `results/` paths.

For profile reuse workflows, keep `run.name` fixed to the base-year profile directory (for example `europe-year-140`) and vary `scenario.opts` to create distinct output filenames.

### Results
Organized by run name: `results/europe-day-140/`

## Solver Configuration

- **Primary**: Gurobi (barrier method, optimized settings)
- **Fallback options**: HiGHS, CPLEX, COPT
- **Threading**: Standardized to 48 threads on ARC submission scripts/configs
- **Tolerance**: 1e-6 (adjustable for difficult problems)

## Results

Results are organized by scenario name:

```
results/
├── <scenario-name>/
│   ├── networks/        # Solved network files (.nc)
│   ├── graphs/          # Network visualizations
│   ├── csvs/            # Exported CSV data
│   └── logs/            # Run logs
```

Scenarios follow the pattern: `<region>-<time>-<nodes>` (e.g., `europe-day-140`).

## Safe Profile Reuse (No Atlite Rebuilds)

To run week/variant scenarios while reusing existing base-year renewable profiles:

Recommended ARC sequence:

1. Run Step 1 once to build renewable profiles.
2. Run Step 2 one or more times for different solve configurations/targets.

Detailed commands are in [arc/README.md](arc/README.md).

1. Keep `run.name` set to the base profile namespace (for example `europe-year-140`).
2. Keep `enable.build_cutout: false`.
3. Use a unique `scenario.opts` suffix (for example `Co2L-3h-week01`) so outputs do not overwrite previous solved networks.

Preflight check before launching (reads the config to determine required carriers):

```bash
cd pypsa-earth
python - <<'PY'
import os
import sys
import yaml

def load(path):
   if not os.path.exists(path):
      return {}
   with open(path, "r", encoding="utf-8") as f:
      return yaml.safe_load(f) or {}

def deep_merge(base, override):
   for key, value in override.items():
      if isinstance(value, dict) and isinstance(base.get(key), dict):
         deep_merge(base[key], value)
      else:
         base[key] = value
   return base

config_file = "configs/scenarios/config.europe-week-140.yaml"
cfg = {}
for path in ("config.default.yaml", "config.yaml", config_file):
   cfg = deep_merge(cfg, load(path))

renewable = cfg.get("renewable", {}) or {}
carriers = set(cfg.get("electricity", {}).get("renewable_carriers", []) or [])
techs = sorted([tech for tech in renewable.keys() if tech in carriers])
run_name = (cfg.get("run", {}) or {}).get("name", "")
rdir = f"{run_name}/" if run_name else ""

missing = []
for tech in techs:
   path = f"resources/{rdir}renewable_profiles/profile_{tech}.nc"
   if not os.path.exists(path):
      missing.append(path)

if missing:
   print("Missing renewable profiles:")
   for path in missing:
      print(f"  {path}")
   sys.exit(1)

print("All renewable profiles present.")
PY
```

If any file is missing, the safe run script exits before Snakemake can build profiles.

## H2-Power Scenario (Non-Sector Workflow)

Use `configs/scenarios/config.europe-year-140-co2-zero-h2-power.yaml` to run the non-sector workflow with:
- H2 electrolysis + H2 fuel-cell links (via `Store: [H2]`)
- H2 storage tanks
- Extendable `CCGT H2` links (`Link: [CCGT H2]`)

Example ARC submission:

```bash
cd pypsa-earth
sbatch ../arc/jobs/01_build_profiles.sh \
  europe-year-140-profiles \
  configs/scenarios/config.europe-year-140-profiles.yaml

sbatch ../arc/jobs/02_build_networks_and_solve_power.sh \
  europe-year-140-co2-zero-h2-power \
  configs/scenarios/config.europe-year-140-co2-zero-h2-power.yaml
```

Important: do not run bare `snakemake` in this repository. The first rule in the Snakefile is `clean`, so always pass an explicit target.

Safe run script (dry-run first, then real run):

```bash
cd pypsa-earth
bash scripts/run_from_base_profiles.sh \
   configs/scenarios/config.europe-week-140.yaml \
   results/europe-year-140/networks/elec_s_140_ec_lcopt_Co2L-3h-week01.nc \
   4
```

Download ARC results:

```bash
rsync -av <user>@arc-login.arc.ox.ac.uk:/data/<group>/<user>/pypsa-earth-green-auklet/results/<scenario>/ results/<scenario>/
```

## Documentation

- **[DEVELOPMENT_NOTES.md](DEVELOPMENT_NOTES.md)**: Development notes, testing plan, and validation checklist
- **[arc/README.md](arc/README.md)**: ARC cluster usage guide

## Requirements

### Local Development
- Python 3.10 or 3.11
- 16-32 GB RAM (day/week), 64+ GB (month/year)
- 4-8 CPU cores
- ~50 GB disk space
- Gurobi license (free for academics)

### ARC Cluster
- Oxford ARC account
- Gurobi license file
- ~50 GB disk quota

## Installation

### Local

```bash
# Clone repository
git clone <your-fork-url> pypsa-earth-green-auklet
cd pypsa-earth-green-auklet

# Run setup
./local_setup.sh

# Activate environment
source pypsa-earth/.venv/bin/activate

# Configure Gurobi (if not done)
grbgetkey <your-license-key>
```

### ARC

```bash
# SSH to ARC
ssh <user>@arc-login.arc.ox.ac.uk

# Run interactive setup
cd /data/<group>/<user>
# Copy arc scripts first, then:
bash arc/arc_initial_setup.sh

# Wait for environment build
squeue -u <user>
```

## Troubleshooting

See [DEVELOPMENT_NOTES.md](DEVELOPMENT_NOTES.md) for the validation checklist and troubleshooting steps.

## Contributing

This fork does not take contributions. Report problems with PyPSA-Earth, and propose changes, at [pypsa-meets-earth/pypsa-earth](https://github.com/pypsa-meets-earth/pypsa-earth), where the fixes made here are also proposed.

## Resources

- **PyPSA-Earth Documentation**: https://pypsa-earth.readthedocs.io/
- **PyPSA Documentation**: https://pypsa.readthedocs.io/
- **Oxford ARC User Guide**: https://arc-user-guide.rc.ox.ac.uk/
- **Gurobi Academic Program**: https://www.gurobi.com/academia/

## Licence

- PyPSA-Earth's files keep their licences: AGPL-3.0-or-later (the GNU Affero General Public License) for the code, CC-BY-4.0 for data and documentation, and CC0-1.0 for the configuration files, as set out in `pypsa-earth/REUSE.toml` and `pypsa-earth/LICENSES/`.
- The files this fork adds outside `pypsa-earth/`, such as `arc/`, `notebooks/` and `build_costs_td.py`, are released under AGPL-3.0-or-later; see [LICENSE](LICENSE).
- The Danish Energy Agency data sheets in `references/dea_data_sheets/` keep the agency's terms.

## Acknowledgments

Built on [PyPSA-Earth](https://github.com/pypsa-meets-earth/pypsa-earth) by the PyPSA meets Earth initiative.

## Support

- **PyPSA-Earth Issues**: https://github.com/pypsa-meets-earth/pypsa-earth/issues
- **ARC Support**: support@arc.ox.ac.uk
