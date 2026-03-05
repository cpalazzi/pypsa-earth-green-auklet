# PyPSA-Earth Europe Testing Repository

This repository is a working fork of [PyPSA-Earth](https://github.com/pypsa-meets-earth/pypsa-earth) configured for European electricity system modeling with standardized workflows for local development and Oxford ARC cluster execution.

## Overview

PyPSA-Earth is an open-source energy system model that optimizes electricity generation, transmission, and storage. This fork focuses on European systems with:
- **35 European countries** (EU27 + UK, Norway, Switzerland, Balkans)
- **140-node network** with load-based distribution
- **Gurobi solver** optimization
- **Standardized naming** for configurations and results
- **Ready-to-run** test scenarios

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

When making changes:
1. Test locally with `europe-day-140` first
2. Document changes in commit messages
3. Update relevant documentation
4. Create new scenario configs following naming convention
5. Validate results before committing

## Resources

- **PyPSA-Earth Documentation**: https://pypsa-earth.readthedocs.io/
- **PyPSA Documentation**: https://pypsa.readthedocs.io/
- **Oxford ARC User Guide**: https://arc-user-guide.rc.ox.ac.uk/
- **Gurobi Academic Program**: https://www.gurobi.com/academia/

## License

This project inherits the license from PyPSA-Earth:
- Code: AGPL-3.0-or-later
- Data and documentation: CC-BY-4.0

## Acknowledgments

Built on [PyPSA-Earth](https://github.com/pypsa-meets-earth/pypsa-earth) by the PyPSA meets Earth initiative.

## Support

- **PyPSA-Earth Issues**: https://github.com/pypsa-meets-earth/pypsa-earth/issues
- **ARC Support**: support@arc.ox.ac.uk

## Roadmap

- [x] Repository structure and documentation
- [x] European configuration (140 nodes, 1 day)
- [x] Local and ARC setup scripts
- [x] Gurobi solver configuration
- [x] H2-power scenario (electrolysis, H2 storage, CCGT H2)
- [x] NH3 scenario (NH3 synthesis, NH3 storage, CCGT NH3, NH3 pipeline)
- [x] Submarine pipeline cost factor
- [x] DEA 2030 cost file (costs_dea2030.csv)
- [ ] Validate DEA 2030 NH3 scenario results
- [ ] Develop analysis notebooks
