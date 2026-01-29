# PyPSA-Earth Europe Test Plan

## Overview
This document outlines the plan for setting up, testing, and running PyPSA-Earth models for European electricity systems.

## Repository Setup

### Directory Structure
```
pypsa-earth-green-auklet/
├── pypsa-earth/              # Main PyPSA-Earth fork
│   ├── configs/scenarios/    # Configuration files
│   │   └── config.europe-day-140.yaml
│   ├── scripts/              # Model scripts
│   ├── envs/                 # Environment files
│   └── Snakefile            # Workflow definition
├── arc/                      # ARC cluster scripts
│   ├── build-pypsa-earth-env # Environment setup script
│   └── jobs/                 # Job submission scripts
├── notebooks/                # Analysis notebooks
├── results/                  # Local results (gitignored)
└── DEVELOPMENT_NOTES.md      # Development notes
```

### Git Ignore Strategy
- Main repo `.gitignore`: Excludes `results/` from pypsa-earth subfolder
- Results folder `.gitignore`: Keeps directory structure, ignores content
- Local `.venv/` is ignored for local development

## Naming Conventions

### Configuration Files
Format: `config.<region>-<timespan>-<nodes>.yaml`

Examples:
- `config.europe-day-140.yaml` - Europe, 1 day, 140 nodes
- `config.europe-week-140.yaml` - Europe, 1 week, 140 nodes
- `config.europe-month-140.yaml` - Europe, 1 month, 140 nodes
- `config.europe-year-140.yaml` - Europe, full year, 140 nodes

### Run Names
Match configuration names: `europe-day-140`, `europe-week-140`, etc.

### Results Directory Structure
```
results/
└── <run-name>/              # e.g., europe-day-140
    ├── networks/            # Solved networks (.nc files)
    ├── graphs/              # Visualizations
    ├── csvs/                # Exported data
    └── logs/                # Snakemake logs
```

## European Configuration Details

### Geographic Scope
**35 countries covering continental Europe:**
- Major economies: DE, FR, GB, IT, ES, PL (higher node allocation)
- Nordic: SE, NO, FI, DK
- Western: NL, BE, IE, LU, CH, AT
- Eastern: PL, CZ, SK, HU, RO, BG
- Southern: PT, ES, IT, GR
- Balkans: RS, BA, AL, MK, ME, HR, SI
- Baltic: LT, LV, EE
- Islands: CY, MT

### Node Allocation Strategy (140 nodes total)
Nodes are distributed by load using `distribute_cluster: ["load"]`:
- Larger countries (Germany, France, UK, Italy, Spain): ~15-25 nodes each
- Medium countries (Poland, Netherlands, Sweden, etc.): ~5-10 nodes each
- Smaller countries (Denmark, Baltic states, etc.): ~1-3 nodes each
- Very small countries (Luxembourg, Malta, Cyprus): 1 node each

### Temporal Resolution
Progressive testing strategy:
1. **Day (24h)**: Quick validation, 3h resolution → 8 timesteps
2. **Week (168h)**: Seasonal patterns, 3h resolution → 56 timesteps
3. **Month (720h)**: Monthly variations, 3h resolution → 240 timesteps
4. **Year (8760h)**: Full annual analysis, 3h resolution → 2920 timesteps

### Technology Configuration
**Extendable carriers:**
- Solar PV
- Onshore wind
- Offshore wind AC (<30km)
- Offshore wind DC (>30km)
- OCGT (gas turbines)
- Battery storage
- Hydrogen storage

**Fixed carriers:**
- Existing nuclear, coal, lignite, CCGT
- Hydro (reservoir, run-of-river, pumped storage)

### Solver Configuration
**Gurobi** is configured as the default solver:
- Method: Barrier (method=2)
- Crossover: Disabled for speed
- Threads: 4 (adjustable via solver_options)
- Tolerance: 1e-6 (BarConvTol)

## ARC Cluster Workflow

### Initial Setup (One-time)
1. **SSH to ARC:**
   ```bash
   ssh <user>@arc-login.arc.ox.ac.uk
   ```

2. **Clean previous installations:**
   ```bash
   cd /data/engs-df-green-ammonia/<user>
   rm -rf pypsa-earth pypsa-earth-runtools-crow
   ```

3. **Clone repository:**
   ```bash
   git clone https://github.com/<your-fork>/pypsa-earth-green-auklet.git
   cd pypsa-earth-green-auklet
   ```

4. **Build environment:**
   ```bash
   sbatch arc/build-pypsa-earth-env
   # Wait for job to complete (~30-60 min)
   squeue -u <user>
   ```

### Running Models on ARC

**Submit a job:**
```bash
cd /data/engs-df-green-ammonia/<user>/pypsa-earth-green-auklet/pypsa-earth
sbatch ../arc/jobs/arc_snakemake_gurobi.sh europe-day-140 configs/scenarios/config.europe-day-140.yaml
```

**Monitor progress:**
```bash
# Check job status
squeue -u <user>

# Watch log file
tail -f logs/snakemake-europe-day-140-*-gurobi.log

# Check specific job details
sacct -j <jobid> --format=JobID,JobName,State,Elapsed,MaxRSS
```

**Download results:**
```bash
# On local machine
rsync -av --progress <user>@arc-login.arc.ox.ac.uk:/data/engs-df-green-ammonia/<user>/pypsa-earth-green-auklet/results/europe-day-140/ results/europe-day-140/
```

## Local Development Workflow

### Environment Setup
1. **Create virtual environment:**
   ```bash
   cd pypsa-earth
   python3.11 -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   # .venv\Scripts\activate  # On Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt  # If exists
   # OR use conda environment
   conda env create -f envs/environment.yaml
   conda activate pypsa-earth
   
   # Install Gurobi
   pip install gurobipy
   # Configure Gurobi license (if not already done)
   ```

### Running Locally
```bash
cd pypsa-earth
snakemake --configfile configs/scenarios/config.europe-day-140.yaml --cores 4
```

### Jupyter Notebook Analysis
```bash
cd notebooks
jupyter lab
# Open 001_run_analysis.ipynb
```

## Testing Strategy

### Phase 1: Single Day Validation (europe-day-140)
**Goal:** Validate model setup and data loading

**Checks:**
- [ ] All 35 countries load successfully
- [ ] 140 nodes are created
- [ ] Node distribution matches load patterns
- [ ] All renewable potentials are calculated
- [ ] Network topology is connected
- [ ] Model solves without errors
- [ ] Results are physically reasonable

**Expected runtime:**
- Local: ~30-60 minutes
- ARC: ~15-30 minutes (with more CPUs)

**Success criteria:**
- Solver converges to optimal solution
- Load is fully served (no load shedding unless CO2 constrained)
- Generation mix includes renewables + storage + conventional
- Cross-border flows are reasonable

### Phase 2: Week Test (europe-week-140)
**Goal:** Validate temporal dynamics and storage

**New checks:**
- [ ] Storage charging/discharging cycles
- [ ] Day/night solar patterns
- [ ] Weekly demand variations
- [ ] Inter-day energy arbitrage

**Expected runtime:**
- Local: ~2-4 hours
- ARC: ~1-2 hours

### Phase 3: Month Test (europe-month-140)
**Goal:** Validate seasonal patterns

**New checks:**
- [ ] Multi-week storage cycles
- [ ] Weather correlation effects
- [ ] Longer-term storage (H2) utilization
- [ ] Cross-border seasonal flows

**Expected runtime:**
- Local: ~6-12 hours
- ARC: ~3-6 hours

### Phase 4: Full Year (europe-year-140)
**Goal:** Complete annual optimization

**New checks:**
- [ ] Annual energy balance
- [ ] Full seasonal storage cycles
- [ ] Capacity factor validation
- [ ] Cost optimization across full year

**Expected runtime:**
- Local: Not recommended (too slow)
- ARC: ~8-24 hours (depends on solver performance)

## Validation Checks

### Data Validation
```python
import pypsa
n = pypsa.Network("results/europe-day-140/networks/elec_s_140_ec_lcopt_Co2L-3h.nc")

# Check network size
print(f"Buses: {len(n.buses)}")
print(f"Lines: {len(n.lines)}")
print(f"Generators: {len(n.generators)}")
print(f"Snapshots: {len(n.snapshots)}")

# Check load
total_load = n.loads_t.p_set.sum().sum()
print(f"Total load: {total_load:.2f} MWh")

# Check generation
total_gen = n.generators_t.p.sum().sum()
print(f"Total generation: {total_gen:.2f} MWh")

# Check by carrier
gen_by_carrier = n.generators.groupby("carrier")["p_nom_opt"].sum()
print("\nInstalled capacity by carrier (MW):")
print(gen_by_carrier.sort_values(ascending=False))

# Check objective
print(f"\nTotal system cost: €{n.objective:,.0f}")
```

### Physical Reasonableness
- Total load should match historical European electricity demand (~3500 TWh/year)
- Solar capacity factors: 10-15% (annual), higher in summer
- Onshore wind capacity factors: 20-30%
- Offshore wind capacity factors: 40-50%
- No negative prices (unless surplus renewable generation)
- Cross-border flows should match interconnector capacities

### Network Connectivity
```python
import networkx as nx
G = n.graph()
print(f"Connected components: {nx.number_connected_components(G)}")
# Should be 1 (all nodes connected)
```

## Common Issues and Fixes

### Issue 1: Gurobi License
**Problem:** License not found on ARC
**Fix:** Ensure `GRB_LICENSE_FILE` is set in job script
```bash
export GRB_LICENSE_FILE=/data/engs-df-green-ammonia/<user>/licenses/gurobi.lic
```

### Issue 2: Memory Issues
**Problem:** Job killed due to OOM
**Fix:** Increase memory in SLURM script
```bash
#SBATCH --mem=512G  # Instead of 256G
```

### Issue 3: Cutout Missing
**Problem:** Cutout file not found
**Fix:** Enable retrieve_databundle or build_cutout
```yaml
enable:
  retrieve_databundle: true
  build_cutout: false  # Use databundle instead
```

### Issue 4: Solver Timeout
**Problem:** Solver doesn't converge
**Fix:** Try numeric focus options
```yaml
solving:
  solver:
    name: gurobi
    options: gurobi-numeric-focus  # More stable but slower
```

### Issue 5: Isolated Nodes
**Problem:** Some countries are disconnected
**Fix:** Lower threshold for dropping isolated networks
```yaml
cluster_options:
  simplify_network:
    p_threshold_drop_isolated: 10  # Lower from 20 MW
```

## Next Steps After Validation

1. **Expand temporal scope:**
   - Create `config.europe-week-140.yaml`
   - Create `config.europe-month-140.yaml`
   - Create `config.europe-year-140.yaml`

2. **Sensitivity analysis:**
   - Vary CO2 limits: Co2L-1h, Co2L-2h, Co2L-3h
   - Vary cluster count: 70, 140, 200 nodes
   - Vary weather years: 2012, 2013, 2014

3. **Policy scenarios:**
   - No offshore wind
   - No nuclear
   - High H2 storage
   - Limited interconnectors

4. **Integration with notebooks:**
   - Update `001_run_analysis.ipynb` for European analysis
   - Create visualization scripts
   - Export summary statistics

## Resource Requirements

### Local Development
- **CPU:** 4-8 cores recommended
- **RAM:** 16-32 GB for day/week, 64+ GB for month/year
- **Disk:** ~50 GB for cutouts, ~10 GB per result set
- **Solver:** Gurobi (free academic license)

### ARC Cluster
- **Partition:** short (day), medium (week/month), long (year)
- **CPUs:** 16-32 cores
- **Memory:** 256-512 GB
- **Time:** 2h (day), 8h (week/month), 24h (year)
- **Solver:** Gurobi (site license via environment variable)

## Contacts and Resources

- **PyPSA-Earth Documentation:** https://pypsa-earth.readthedocs.io/
- **PyPSA Documentation:** https://pypsa.readthedocs.io/
- **ARC Documentation:** https://arc-user-guide.rc.ox.ac.uk/
- **Gurobi Documentation:** https://www.gurobi.com/documentation/

## Version Control

- Keep `DEVELOPMENT_NOTES.md` updated with progress
- Create git tags for validated configurations
- Document any bugfixes in commit messages
- Keep ARC scripts synced with local changes
