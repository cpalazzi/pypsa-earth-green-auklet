# PyPSA-Earth Europe Testing Repository

This repository is a working fork of [PyPSA-Earth](https://github.com/pypsa-meets-earth/pypsa-earth) configured for European electricity system modeling with standardized workflows for both local development and Oxford ARC cluster execution.

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
   snakemake --configfile configs/scenarios/config.europe-day-140.yaml --cores 4
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

2. **Submit job:**
   ```bash
   cd pypsa-earth-green-auklet/pypsa-earth
   sbatch ../arc/jobs/arc_snakemake_gurobi.sh europe-day-140 configs/scenarios/config.europe-day-140.yaml
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
│   ├── arc_submit_run.sh                # Job submission helper
│   ├── build-pypsa-earth-env            # Environment builder
│   ├── jobs/arc_snakemake_gurobi.sh     # SLURM job script
│   └── README.md                         # ARC documentation
├── notebooks/                            # Analysis notebooks
│   ├── 000_arc_run_steps.ipynb          # ARC workflow example
│   └── 001_run_analysis.ipynb           # Results analysis
├── results/                              # Model results (gitignored)
│   ├── .gitignore                        # Keep structure only
│   └── README.md                         # Results documentation
├── local_setup.sh                        # Local environment setup
├── DEVELOPMENT_NOTES.md                  # Development documentation
├── TESTING_PLAN.md                       # Comprehensive testing guide
├── QUICKREF.md                           # Quick reference guide
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
- **Runtime**: ~30-60 minutes (local), ~15-30 minutes (ARC)

### Creating New Scenarios

1. Copy existing config:
   ```bash
   cp pypsa-earth/configs/scenarios/config.europe-day-140.yaml \
      pypsa-earth/configs/scenarios/config.europe-week-140.yaml
   ```

2. Update key parameters:
   ```yaml
   run:
     name: "europe-week-140"
   
   scenario:
     sopts: ["168h"]  # One week
   
   snapshots:
     start: "2013-07-08"
     end: "2013-07-15"
   ```

3. Run:
   ```bash
   snakemake --configfile configs/scenarios/config.europe-week-140.yaml --cores 4
   ```

## Naming Conventions

### Configuration Files
Format: `config.<region>-<timespan>-<nodes>.yaml`

Examples:
- `config.europe-day-140.yaml` - Europe, 1 day, 140 nodes
- `config.europe-week-140.yaml` - Europe, 1 week, 140 nodes
- `config.europe-year-140.yaml` - Europe, full year, 140 nodes

### Run Names
Match config without "config." prefix: `europe-day-140`, `europe-week-140`

### Results
Organized by run name: `results/europe-day-140/`

## Features

### Geographic Coverage
- **Major economies**: Germany, France, UK, Italy, Spain, Poland
- **Nordic countries**: Sweden, Norway, Finland, Denmark
- **Western Europe**: Netherlands, Belgium, Ireland, Luxembourg, Switzerland, Austria
- **Eastern Europe**: Poland, Czech Republic, Slovakia, Hungary, Romania, Bulgaria
- **Southern Europe**: Portugal, Spain, Italy, Greece
- **Balkans**: Serbia, Bosnia, Albania, North Macedonia, Montenegro, Croatia, Slovenia
- **Baltic states**: Lithuania, Latvia, Estonia
- **Islands**: Cyprus, Malta

### Technology Coverage
- **Renewables**: Solar PV, onshore wind, offshore wind (AC/DC)
- **Conventional**: Nuclear, coal, lignite, gas (OCGT/CCGT)
- **Storage**: Batteries (6h), hydrogen (168h)
- **Hydro**: Reservoir, run-of-river, pumped storage
- **Transmission**: AC lines, HVDC links

### Solver Configuration
- **Primary**: Gurobi (barrier method, optimized settings)
- **Fallback options**: HiGHS, CPLEX, COPT
- **Threading**: Configurable (4-64 cores)
- **Tolerance**: 1e-6 (adjustable for difficult problems)

## Testing Strategy

Progressive validation approach:

1. **Day (24h)**: Quick validation - network connectivity, data loading
2. **Week (168h)**: Storage dynamics - daily cycles, multi-day patterns
3. **Month (720h)**: Seasonal patterns - weekly variations, longer storage
4. **Year (8760h)**: Full optimization - complete seasonal cycles

See [TESTING_PLAN.md](TESTING_PLAN.md) for detailed validation procedures.

## Documentation

- **[QUICKREF.md](QUICKREF.md)**: Quick reference for common commands
- **[TESTING_PLAN.md](TESTING_PLAN.md)**: Comprehensive testing and validation guide
- **[DEVELOPMENT_NOTES.md](DEVELOPMENT_NOTES.md)**: Development notes and workflow
- **[arc/README.md](arc/README.md)**: ARC cluster usage guide
- **[results/README.md](results/README.md)**: Results organization

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

## Usage Examples

### Local Testing
```bash
cd pypsa-earth

# Dry run (check workflow)
snakemake --configfile configs/scenarios/config.europe-day-140.yaml --dry-run

# Run with 4 cores
snakemake --configfile configs/scenarios/config.europe-day-140.yaml --cores 4

# Force rebuild
snakemake --configfile configs/scenarios/config.europe-day-140.yaml --cores 4 --forceall
```

### ARC Production
```bash
cd pypsa-earth-green-auklet/pypsa-earth

# Submit job
sbatch ../arc/jobs/arc_snakemake_gurobi.sh europe-day-140 configs/scenarios/config.europe-day-140.yaml

# Monitor
squeue -u <user>
tail -f logs/snakemake-europe-day-140-*-gurobi.log

# Check results
ls -lh results/europe-day-140/
```

### Analysis
```python
import pypsa
import pandas as pd
import matplotlib.pyplot as plt

# Load network
n = pypsa.Network("results/europe-day-140/networks/elec_s_140_ec_lcopt_Co2L-3h.nc")

# Summary statistics
print(f"Buses: {len(n.buses)}")
print(f"Total load: {n.loads_t.p_set.sum().sum():.2f} MWh")
print(f"System cost: €{n.objective:,.0f}")

# Generation by carrier
gen_capacity = n.generators.groupby("carrier")["p_nom_opt"].sum()
print("\nInstalled capacity (MW):")
print(gen_capacity.sort_values(ascending=False))

# Plot network
n.plot(line_widths=0.5, title="Europe 140-node Network")
plt.show()
```

## Troubleshooting

### Common Issues

1. **Gurobi license error**
   ```bash
   export GRB_LICENSE_FILE=~/gurobi.lic
   python -c "import gurobipy; print(gurobipy.gurobi.version())"
   ```

2. **Snakemake locked**
   ```bash
   snakemake --unlock
   ```

3. **Out of memory**
   - Local: Reduce time range or clusters
   - ARC: Increase memory in job script (`#SBATCH --mem=512G`)

4. **Solver doesn't converge**
   ```yaml
   solving:
     solver:
       options: gurobi-numeric-focus
   ```

See [TESTING_PLAN.md](TESTING_PLAN.md) for more troubleshooting.

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
- [ ] Validate day scenario
- [ ] Extend to week/month/year scenarios
- [ ] Develop analysis notebooks
- [ ] Sensitivity analysis framework
- [ ] Integration with ammonia production modeling
