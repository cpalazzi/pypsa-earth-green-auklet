# ARC Cluster Scripts

This directory contains scripts for running PyPSA-Earth on the Oxford ARC (Advanced Research Computing) cluster.

## Scripts

### `arc_initial_setup.sh`
Interactive setup script for first-time ARC setup.

**What it does:**
- Cleans old pypsa-earth installations
- Clones the repository
- Sets up directory structure
- Checks for Gurobi license
- Submits environment build job

**Usage:**
```bash
ssh <user>@arc-login.arc.ox.ac.uk
cd /data/<group>/<user>
# Copy this script to ARC, then:
bash arc_initial_setup.sh
```

### `arc_submit_run.sh`
Helper script to submit model runs.

**Usage:**
```bash
cd pypsa-earth
../arc/arc_submit_run.sh europe-day-140
# Or specify custom config:
../arc/arc_submit_run.sh my-scenario configs/scenarios/config.my-scenario.yaml
```

### `build-pypsa-earth-env`
SLURM job script to build the conda environment.

**What it does:**
- Loads Anaconda module
- Creates conda environment from `envs/environment.yaml`
- Installs Gurobi from conda-forge
- Logs installed packages

**Usage:**
```bash
sbatch arc/build-pypsa-earth-env
```

**Resource allocation:**
- Partition: medium
- Time: 6 hours
- CPUs: 8
- Memory: Default

### `jobs/arc_snakemake_gurobi.sh`
SLURM job script to run PyPSA-Earth with Gurobi solver.

**What it does:**
- Loads conda environment
- Sets up Gurobi license
- Runs Snakemake workflow with specified config
- Logs output

**Usage:**
```bash
cd pypsa-earth
sbatch ../arc/jobs/arc_snakemake_gurobi.sh <scenario-name> <config-file> [additional-configs...]
```

**Examples:**
```bash
sbatch ../arc/jobs/arc_snakemake_gurobi.sh europe-day-140 configs/scenarios/config.europe-day-140.yaml
```

**Resource allocation:**
- Partition: short, medium (prefers short)
- Time: 8 hours
- CPUs: 16
- Memory: 256 GB
- Mail: Sends email on BEGIN,END

**Environment variables you can set:**
- `ARC_ANACONDA_MODULE`: Anaconda module to load (default: Anaconda3/2024.06-1)
- `ARC_PYPSA_ENV`: Path to conda environment
- `PYPSA_SOLVER_NAME`: Solver name (default: gurobi)
- `LINOPY_SOLVER`: Linopy solver (default: gurobi)
- `GRB_LICENSE_FILE`: Gurobi license file path
- `ARC_WORKDIR`: Working directory (default: submission directory)
- `ARC_SNAKE_LATENCY_WAIT`: File system latency wait (default: 60s)
- `ARC_SNAKE_DRYRUN`: Set to 1 for dry run
- `ARC_SNAKE_NOLOCK`: Set to 1 to disable Snakemake locks
- `ARC_SNAKE_UNLOCK`: Set to 1 to unlock before running
- `ARC_STAGE_DATA`: Set to 1 to stage data before main run

## Directory Structure on ARC

After setup, your ARC workspace will look like:

```
/data/<group>/<user>/
├── pypsa-earth-green-auklet/          # Repository
│   ├── pypsa-earth/                   # Main model code
│   │   ├── Snakefile
│   │   ├── configs/scenarios/
│   │   └── scripts/
│   ├── arc/                           # This directory
│   ├── notebooks/
│   └── results/                       # Results by scenario
│       └── europe-day-140/
├── envs/                              # Conda environments
│   ├── pypsa-earth-env/
│   └── logs/
└── licenses/                          # Solver licenses
    └── gurobi.lic
```

## Workflow

### 1. Initial Setup (Once)
```bash
# On local machine, copy scripts to ARC
scp -r arc <user>@arc-login.arc.ox.ac.uk:/data/<group>/<user>/

# SSH to ARC
ssh <user>@arc-login.arc.ox.ac.uk

# Run setup
cd /data/<group>/<user>
bash arc/arc_initial_setup.sh

# Wait for environment build to complete
squeue -u <user>
```

### 2. Submit Runs
```bash
cd /data/<group>/<user>/pypsa-earth-green-auklet/pypsa-earth
sbatch ../arc/jobs/arc_snakemake_gurobi.sh europe-day-140 configs/scenarios/config.europe-day-140.yaml
```

### 3. Monitor
```bash
# Check job queue
squeue -u <user>

# Watch log file
tail -f logs/snakemake-europe-day-140-*-gurobi.log

# Check job accounting
sacct -j <jobid> --format=JobID,JobName,State,Elapsed,MaxRSS,NodeList
```

### 4. Download Results
```bash
# On local machine
rsync -av --progress <user>@arc-login.arc.ox.ac.uk:/data/<group>/<user>/pypsa-earth-green-auklet/results/europe-day-140/ results/europe-day-140/
```

## Troubleshooting

### Environment Build Fails
Check the log:
```bash
cat slurm-<jobid>.out
```

Common issues:
- Network issues: Retry the build
- Package conflicts: Check environment.yaml
- Disk quota: Clean old files

### Job Fails to Start
Check SLURM logs:
```bash
cat slurm-<jobid>.out
```

Common issues:
- Wrong partition: Check available partitions with `sinfo`
- Resource limits: Reduce memory/CPU requirements
- Module not found: Check module availability with `module avail`

### Gurobi License Error
Verify license file:
```bash
cat $GRB_LICENSE_FILE
# Should show license content
```

Set environment variable:
```bash
export GRB_LICENSE_FILE=/data/<group>/<user>/licenses/gurobi.lic
```

### Snakemake Lock Error
Unlock the workflow:
```bash
cd pypsa-earth
snakemake --unlock
# Or set ARC_SNAKE_UNLOCK=1 in job script
```

### Out of Memory
Increase memory in job script:
```bash
#SBATCH --mem=512G
```

Or run on a larger node:
```bash
#SBATCH --partition=large
```

### Files Not Found
Check latency wait setting:
```bash
export ARC_SNAKE_LATENCY_WAIT=120  # Increase to 2 minutes
```

## Resource Guidelines

### Test Runs (1 day, 140 nodes)
- Time: 1-2 hours
- CPUs: 8-16
- Memory: 128-256 GB
- Partition: short

### Production Runs (1 week, 140 nodes)
- Time: 4-8 hours
- CPUs: 16-32
- Memory: 256-512 GB
- Partition: medium

### Full Year Runs (8760 hours, 140 nodes)
- Time: 12-24 hours
- CPUs: 32-64
- Memory: 512 GB - 1 TB
- Partition: long

## ARC Partitions

- **short**: Up to 4 hours
- **medium**: Up to 2 days
- **long**: Up to 7 days
- **devel**: Up to 1 hour (for testing)

Check current partition limits:
```bash
sinfo -o "%P %.5a %.10l %.6D %.6t %N"
```

## Best Practices

1. **Test first**: Always run a short test (1 day) before long runs
2. **Monitor actively**: Check logs during first hour of execution
3. **Use dryrun**: Test workflow with `ARC_SNAKE_DRYRUN=1`
4. **Save checkpoints**: Enable Snakemake's `--rerun-incomplete`
5. **Backup results**: Download important results regularly
6. **Clean workspace**: Remove old results to save disk space
7. **Document changes**: Update config comments with run details

## Contact

For ARC-specific issues:
- ARC User Guide: https://arc-user-guide.rc.ox.ac.uk/
- ARC Support: support@arc.ox.ac.uk

For PyPSA-Earth issues:
- Documentation: https://pypsa-earth.readthedocs.io/
- GitHub: https://github.com/pypsa-meets-earth/pypsa-earth
