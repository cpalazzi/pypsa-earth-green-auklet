# PyPSA-Earth Green Auklet — Development Notes

## Purpose
This repo is a working fork of `pypsa-earth` focused on European electricity system modeling with proper version control and standardized workflows. This document is for maintainers and AI agents: decisions, conventions, testing plan, and troubleshooting. We do not preserve backward compatibility in docs or code during active development; any high-level historical notes or function descriptions should be added here.

## Repository Structure
- `pypsa-earth/` - Main PyPSA-Earth model code (submodule/fork)
- `arc/` - ARC cluster job submission scripts
- `notebooks/` - Analysis notebooks
- `results/` - Model results (gitignored, structured by scenario, kept via .gitkeep)
- `configs/scenarios/` - Model configuration files

## What we copied in
- Notebooks from the prior overlay repo into `notebooks/`.
- ARC run scripts into `arc/` (e.g., job submission wrappers, helpers).

## Naming Conventions

### Configuration Files
Format: `config.<region>-<timespan>-<nodes>.yaml`
- Region: Geographic scope (europe, africa, etc.)
- Timespan: Temporal scope (day, week, month, year)
- Nodes: Number of network nodes/clusters

Examples:
- `config.europe-day-140.yaml` - Europe, 1 day, 140 nodes
- `config.europe-week-140.yaml` - Europe, 1 week, 140 nodes
- `config.europe-year-140.yaml` - Europe, full year, 140 nodes

### Run Names
Match configuration names without the "config." prefix:
- `europe-day-140`
- `europe-week-140`
- `europe-year-140`

When reusing annual resources for shorter runs, `run.name` may intentionally differ from the config filename. Example: `config.europe-week-140.yaml` can use `run.name: europe-year-140` so week runs reuse annual `resources/europe-year-140/*` (including renewable profiles).

### Results Structure
```
results/
└── <run-name>/              # e.g., europe-day-140
    ├── networks/            # Solved networks (.nc files)
    ├── graphs/              # Visualizations
    ├── csvs/                # Exported data
    └── logs/                # Snakemake logs
```

## ARC Usage (Oxford ARC)

## ARC Access and Paths

Login host: arc-login.arc.ox.ac.uk

User: engs2523

Data root: /data/engs-df-green-ammonia/engs2523

Project root: /data/engs-df-green-ammonia/engs2523/pypsa-earth-green-auklet

Key subdirectories:
- arc/
- notebooks/
- pypsa-earth/
- envs/
- env-builds/
- slurm-*.out

### Initial Setup (One-time)
1. SSH to ARC: `ssh <user>@arc-login.arc.ox.ac.uk`
2. Run setup script: `bash arc/arc_initial_setup.sh`
3. Wait for environment build (~30-60 min)
4. Verify Gurobi license is in place

### ARC command execution pattern (for Copilot/automation)
Use single-shot non-interactive SSH commands in this form:

```bash
ssh <user>@arc-login.arc.ox.ac.uk 'cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth && <command>'
```

Example profile check:

```bash
ssh <user>@arc-login.arc.ox.ac.uk 'cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth && ../arc/arc_check_run_inputs.sh configs/scenarios/config.europe-week-140.yaml'
```

If SSH returns `Permission denied`, resolve authentication first (SSH key/password/GSSAPI) before debugging run commands.

If non-interactive SSH is not available, use interactive login and run commands directly on ARC:

```bash
ssh <user>@arc-login.arc.ox.ac.uk
cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth
```

Then run checks/submissions in that shell, for example:

```bash
../arc/arc_check_run_inputs.sh configs/scenarios/config.europe-week-140.yaml
sbatch ../arc/jobs/02_solve_only.sh \
  europe-week-140-solve \
  results/europe-year-140/networks/elec_s_140_ec_lcopt_Co2L-3h-week01.nc \
  configs/scenarios/config.europe-week-140.yaml
```

### Running Models
```bash
cd pypsa-earth
sbatch ../arc/jobs/01_build_inputs.sh europe-day-140-build networks/europe-day-140/elec_s_140_ec_lcopt_Co2L-3h.nc configs/scenarios/config.europe-day-140.yaml
```

### Monitoring Jobs
- Check status: `squeue -u <user>`
- Watch logs: `tail -f logs/snakemake-*-build-inputs.log` and `tail -f logs/snakemake-*-solve-only.log`
- Job details: `sacct -j <jobid> --format=JobID,JobName,State,Elapsed,MaxRSS`

### Week Run Readiness (reuse annual profiles)
From `pypsa-earth/` on ARC:

1. Submit Step A build-inputs job (prepared network target):
  ```bash
  sbatch ../arc/jobs/01_build_inputs.sh \
    europe-week-140-build \
    networks/europe-year-140/elec_s_140_ec_lcopt_Co2L-3h-week01.nc \
    configs/scenarios/config.europe-week-140.yaml
  ```
2. Verify required profile files exist for the solve config:
  ```bash
  ../arc/arc_check_run_inputs.sh configs/scenarios/config.europe-week-140.yaml
  ```
3. Recommended: after Step A completes, submit one or more Step B solve-only jobs (for different configurations/targets):
  ```bash
  sbatch ../arc/jobs/02_solve_only.sh \
    europe-week-140-solve \
    results/europe-year-140/networks/elec_s_140_ec_lcopt_Co2L-3h-week01.nc \
    configs/scenarios/config.europe-week-140.yaml
  ```
4. Optional convenience: submit Step B with dependency on Step A:
  ```bash
  BUILD_JOB=$(sbatch --parsable ../arc/jobs/01_build_inputs.sh \
    europe-week-140-build \
    networks/europe-year-140/elec_s_140_ec_lcopt_Co2L-3h-week01.nc \
    configs/scenarios/config.europe-week-140.yaml)

  sbatch --dependency=afterok:${BUILD_JOB} ../arc/jobs/02_solve_only.sh \
    europe-week-140-solve \
    results/europe-year-140/networks/elec_s_140_ec_lcopt_Co2L-3h-week01.nc \
    configs/scenarios/config.europe-week-140.yaml
  ```

### TODO: Build annual profiles only (clear recipe)

Use dedicated config: `configs/scenarios/config.europe-year-140-profiles.yaml`

Checklist (run from `pypsa-earth/` on ARC):

- [ ] Preflight expected profile outputs:
  ```bash
  ../arc/arc_check_run_inputs.sh configs/scenarios/config.europe-year-140-profiles.yaml
  ```
- [ ] Submit Step A build-inputs job for annual prepared network:
  ```bash
  sbatch ../arc/jobs/01_build_inputs.sh \
    europe-year-140-build \
    networks/europe-year-140/elec_s_140_ec_lcopt_Co2L-3h.nc \
    configs/scenarios/config.europe-year-140-profiles.yaml
  ```
- [ ] Confirm files were written:
  ```bash
  ls -lh resources/europe-year-140/renewable_profiles/profile_*.nc
  ```

Profile outputs are saved in:

- `pypsa-earth/resources/europe-year-140/renewable_profiles/profile_onwind.nc`
- `pypsa-earth/resources/europe-year-140/renewable_profiles/profile_offwind-ac.nc`
- `pypsa-earth/resources/europe-year-140/renewable_profiles/profile_offwind-dc.nc`
- `pypsa-earth/resources/europe-year-140/renewable_profiles/profile_solar.nc`
- `pypsa-earth/resources/europe-year-140/renewable_profiles/profile_hydro.nc`
- `pypsa-earth/resources/europe-year-140/renewable_profiles/profile_csp.nc`

Notes on 2013 data availability and retrieval:

- By default, this project is configured around weather year 2013 (`snapshots` and `cutout-2013-era5`).
- Without extra preparation, 2013 demand/cutout-related inputs are the ones expected to exist or be retrieved.
- PyPSA-Earth fetches these via `retrieve_databundle_light` when `enable.retrieve_databundle: true`.
- If missing databundles are prompted interactively, run non-interactive retrieval first and then resubmit Step A.

### Downloading Results
From your local machine:
```bash
rsync -av --progress <user>@arc-login.arc.ox.ac.uk:/data/<group>/<user>/pypsa-earth-green-auklet/results/europe-day-140/ results/europe-day-140/
```

## Local Development

### Environment Setup
```bash
cd pypsa-earth
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# Install dependencies from environment.yaml or requirements.txt
pip install gurobipy  # Gurobi solver
```

### Running Locally
```bash
cd pypsa-earth
snakemake --configfile configs/scenarios/config.europe-day-140.yaml --cores 4
```

### Run Timing Notes
- 2026-02-03 europe-day-140: `build_osm_network` started 16:19:28, interrupted 17:08:49 (SIGINT). Elapsed: 49m 21s.

### Jupyter Analysis
```bash
cd notebooks
jupyter lab
# Open 001_run_analysis.ipynb
```

## European Model Configuration

### Geographic Scope (35 countries)
Major economies: DE, FR, GB, IT, ES, PL
Nordic: SE, NO, FI, DK  
Western: NL, BE, IE, LU, CH, AT
Eastern: PL, CZ, SK, HU, RO, BG
Southern: PT, ES, IT, GR
Balkans: RS, BA, AL, MK, ME, HR, SI
Baltic: LT, LV, EE
Islands: CY, MT

### Node Distribution (140 nodes total)
Nodes distributed by load (`distribute_cluster: ["load"]`):
- Large countries (DE, FR, GB, IT, ES): ~15-25 nodes
- Medium countries: ~5-10 nodes
- Small countries (DK, Baltic): ~1-3 nodes
- Very small (LU, MT, CY): 1 node

### Testing Strategy
1. **Day test (24h)**: Quick validation, ~30 min runtime
2. **Week test (168h)**: Storage dynamics, ~2 hours
3. **Month test (720h)**: Seasonal patterns, ~6 hours
4. **Year test (8760h)**: Full optimization, ~12-24 hours

### Solver Configuration
- Default: Gurobi with barrier method
- Configured for both local and ARC environments
- License set via `GRB_LICENSE_FILE` environment variable
- Fallback options available (HiGHS, CPLEX, COPT)

## Files and Directories

### Version Controlled
- Configuration files (`configs/scenarios/*.yaml`)
- Scripts and notebooks
- Documentation (this file, TESTING_PLAN.md)
- ARC job scripts

### Gitignored
- Results (`results/`)
- Virtual environments (`.venv/`, `venv/`)
- Data files (automatically downloaded via databundle)
- Cutouts (weather data)
- Network intermediate files
- Logs

## Testing Plan and Validation

Progressive validation approach:

1. **Day (24h)**: Quick validation, data loading, network connectivity
2. **Week (168h)**: Storage dynamics and daily cycles
3. **Month (720h)**: Seasonal patterns and longer storage behavior
4. **Year (8760h)**: Full optimization with seasonal cycles

### Validation Checklist

- [ ] Network loads successfully
- [ ] Correct number of buses/nodes
- [ ] All countries represented
- [ ] Renewables have non-zero potential
- [ ] Network is fully connected
- [ ] Solver converges to optimal
- [ ] No load shedding (unless CO2 constrained)
- [ ] Energy balance: generation ≈ load
- [ ] Capacity factors are reasonable
- [ ] System costs are reasonable

### Useful Snippets

```python
import pypsa
n = pypsa.Network("results/europe-day-140/networks/elec_s_140_ec_lcopt_Co2L-3h.nc")

print(f"Buses: {len(n.buses)}")
print(f"Generators: {len(n.generators)}")
print(f"Snapshots: {len(n.snapshots)}")
print(f"Total load: {n.loads_t.p_set.sum().sum():.2f} MWh")
print(f"Total generation: {n.generators_t.p.sum().sum():.2f} MWh")
print(f"Total system cost: €{n.objective:,.0f}")
```

### Troubleshooting

**Gurobi license error**
```bash
export GRB_LICENSE_FILE=~/gurobi.lic
python -c "import gurobipy; print(gurobipy.gurobi.version())"
```

**Snakemake locked**
```bash
snakemake --unlock
```

**Out of memory**
- Local: Reduce time range or clusters
- ARC: Increase memory in job script (`#SBATCH --mem=512G`)

**Solver doesn't converge**
```yaml
solving:
  solver:
    options: gurobi-numeric-focus
```

### Gurobi License
Ensure `GRB_LICENSE_FILE` environment variable points to license file:
- Local: Set in your shell profile
- ARC: Set in job script (already configured)

### Memory Issues
Increase SLURM memory allocation:
```bash
#SBATCH --mem=512G  # In job script
```

### Solver Convergence
Try numeric focus for difficult problems:
```yaml
solving:
  solver:
    options: gurobi-numeric-focus
```

## Documentation

- **PyPSA-Earth Docs**: https://pypsa-earth.readthedocs.io/
- **PyPSA Docs**: https://pypsa.readthedocs.io/
- **ARC Guide**: https://arc-user-guide.rc.ox.ac.uk/

## Next Steps
- [x] Set up repository structure
- [x] Create European configuration (140 nodes)
- [x] Configure Gurobi solver
- [x] Create ARC setup scripts
- [x] Write testing plan
- [ ] Run day test validation
- [ ] Expand to week/month/year tests
- [ ] Develop analysis notebooks
- [ ] Create visualization scripts

## Notes on Ammonia Integration
We intentionally did **not** migrate ammonia scripts/configs from the prior overlay repo. 
These should be rebuilt with full context later after validating the base electricity model.
