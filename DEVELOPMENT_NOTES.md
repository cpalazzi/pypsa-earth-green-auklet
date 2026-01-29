# PyPSA-Earth Green Auklet — Development Notes

## Purpose
This repo is a working fork of `pypsa-earth` focused on European electricity system modeling with proper version control and standardized workflows.

## Repository Structure
- `pypsa-earth/` - Main PyPSA-Earth model code (submodule/fork)
- `arc/` - ARC cluster job submission scripts
- `notebooks/` - Analysis notebooks
- `results/` - Model results (gitignored, structured by scenario)
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

### Initial Setup (One-time)
1. SSH to ARC: `ssh <user>@arc-login.arc.ox.ac.uk`
2. Run setup script: `bash arc/arc_initial_setup.sh`
3. Wait for environment build (~30-60 min)
4. Verify Gurobi license is in place

### Running Models
```bash
cd pypsa-earth
sbatch ../arc/jobs/arc_snakemake_gurobi.sh europe-day-140 configs/scenarios/config.europe-day-140.yaml
```

Or use the helper script:
```bash
cd pypsa-earth
../arc/arc_submit_run.sh europe-day-140
```

### Monitoring Jobs
- Check status: `squeue -u <user>`
- Watch log: `tail -f logs/snakemake-europe-day-140-*-gurobi.log`
- Job details: `sacct -j <jobid> --format=JobID,JobName,State,Elapsed,MaxRSS`

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

## Common Issues and Solutions

See `TESTING_PLAN.md` for detailed troubleshooting guide.

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

- **Testing Plan**: `TESTING_PLAN.md` - Comprehensive testing and validation guide
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
