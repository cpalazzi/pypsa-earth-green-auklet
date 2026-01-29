# PyPSA-Earth Quick Reference

## Quick Start

### Local Development
```bash
# First time setup
./local_setup.sh

# Activate environment
source pypsa-earth/.venv/bin/activate

# Run test (dry-run first)
cd pypsa-earth
snakemake --configfile configs/scenarios/config.europe-day-140.yaml --cores 4 --dry-run
snakemake --configfile configs/scenarios/config.europe-day-140.yaml --cores 4
```

### ARC Cluster
```bash
# First time setup
ssh <user>@arc-login.arc.ox.ac.uk
cd /data/<group>/<user>
bash arc/arc_initial_setup.sh

# Submit job
cd pypsa-earth-green-auklet/pypsa-earth
sbatch ../arc/jobs/arc_snakemake_gurobi.sh europe-day-140 configs/scenarios/config.europe-day-140.yaml

# Monitor
squeue -u <user>
tail -f logs/snakemake-europe-day-140-*-gurobi.log

# Download results (from local machine)
rsync -av <user>@arc-login.arc.ox.ac.uk:/data/<group>/<user>/pypsa-earth-green-auklet/results/europe-day-140/ results/europe-day-140/
```

## File Structure

```
pypsa-earth-green-auklet/
├── pypsa-earth/                          # Main model
│   ├── configs/scenarios/                # Configurations
│   │   └── config.europe-day-140.yaml   # European test config
│   ├── scripts/                          # Model scripts
│   ├── envs/environment.yaml            # Dependencies
│   └── Snakefile                         # Workflow
├── arc/                                  # ARC scripts
│   ├── arc_initial_setup.sh             # Initial setup
│   ├── arc_submit_run.sh                # Submit helper
│   ├── build-pypsa-earth-env            # Build environment
│   └── jobs/arc_snakemake_gurobi.sh     # Run job
├── notebooks/                            # Analysis
├── results/                              # Results (gitignored)
├── local_setup.sh                        # Local setup
├── DEVELOPMENT_NOTES.md                  # Dev notes
├── TESTING_PLAN.md                       # Testing guide
└── README.md                             # This file (create this)
```

## Configuration Files

### Format
`config.<region>-<timespan>-<nodes>.yaml`

### Current Configurations
- `config.europe-day-140.yaml` - 35 European countries, 1 day, 140 nodes, 3h resolution

### To Create New Config
1. Copy `config.europe-day-140.yaml`
2. Rename following convention (e.g., `config.europe-week-140.yaml`)
3. Update `snapshots` section for time range
4. Update `run.name` to match filename
5. Adjust `scenario.sopts` (e.g., "168h" for week)

## Common Commands

### Snakemake
```bash
# Dry run (show what would be executed)
snakemake --dry-run --configfile <config>

# Run with 4 cores
snakemake --cores 4 --configfile <config>

# Run specific rule
snakemake <rule-name> --configfile <config>

# Unlock (if locked from previous run)
snakemake --unlock

# Clean
snakemake --delete-all-output
```

### SLURM (ARC)
```bash
# Submit job
sbatch <script>

# Check queue
squeue -u <user>

# Cancel job
scancel <jobid>

# Job info
scontrol show job <jobid>

# Job accounting
sacct -j <jobid> --format=JobID,JobName,State,Elapsed,MaxRSS

# Available resources
sinfo
```

### File Transfer
```bash
# Download from ARC
rsync -av <user>@arc-login.arc.ox.ac.uk:<remote-path> <local-path>

# Upload to ARC
rsync -av <local-path> <user>@arc-login.arc.ox.ac.uk:<remote-path>

# With progress and compression
rsync -avz --progress <source> <dest>
```

## Key Configuration Parameters

### Geographic Scope
```yaml
countries: [DE, FR, GB, IT, ES, ...]  # List of country codes
```

### Time Range
```yaml
snapshots:
  start: "2013-07-15"
  end: "2013-07-16"    # End is exclusive
  inclusive: "left"
```

### Network Size
```yaml
scenario:
  clusters: [140]      # Number of network nodes
```

### Temporal Resolution
```yaml
scenario:
  opts: [Co2L-3h]      # 3-hour timesteps
  sopts: ["24h"]       # 24-hour time slice
```

### Solver
```yaml
solving:
  solver:
    name: gurobi
    options: gurobi-default
```

## Output Files

### Network Results
```
results/<scenario>/networks/elec_s_<clusters>_ec_lcopt_Co2L-3h.nc
```

### Load with PyPSA
```python
import pypsa
n = pypsa.Network("results/europe-day-140/networks/elec_s_140_ec_lcopt_Co2L-3h.nc")

# Inspect
print(f"Buses: {len(n.buses)}")
print(f"Generators: {len(n.generators)}")
print(f"Objective: €{n.objective:,.0f}")

# Generation by carrier
n.generators.groupby("carrier")["p_nom_opt"].sum()

# Plotting
n.plot()
```

## Troubleshooting

### Issue: Module not found
```bash
# Check environment is activated
which python
# Should show .venv/bin/python

# Reinstall package
pip install <package>
```

### Issue: Gurobi license error
```bash
# Check license
echo $GRB_LICENSE_FILE
cat $GRB_LICENSE_FILE

# Set license
export GRB_LICENSE_FILE=~/gurobi.lic

# Test
python -c "import gurobipy; print(gurobipy.gurobi.version())"
```

### Issue: Snakemake locked
```bash
snakemake --unlock
```

### Issue: Out of memory
```bash
# Local: Reduce clusters or time range
# ARC: Increase memory in job script
#SBATCH --mem=512G
```

### Issue: Solver doesn't converge
```yaml
# Try numeric focus
solving:
  solver:
    options: gurobi-numeric-focus
```

## Validation Checklist

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

## Resources

- **Testing Plan**: `TESTING_PLAN.md`
- **Development Notes**: `DEVELOPMENT_NOTES.md`
- **ARC Guide**: `arc/README.md`
- **PyPSA-Earth Docs**: https://pypsa-earth.readthedocs.io/
- **PyPSA Docs**: https://pypsa.readthedocs.io/
- **ARC User Guide**: https://arc-user-guide.rc.ox.ac.uk/

## Scenarios Roadmap

- [x] europe-day-140 (1 day, 140 nodes) - Validation
- [ ] europe-week-140 (1 week, 140 nodes) - Storage dynamics
- [ ] europe-month-140 (1 month, 140 nodes) - Seasonal patterns
- [ ] europe-year-140 (1 year, 140 nodes) - Full optimization

## Support

For PyPSA-Earth issues:
- GitHub Issues: https://github.com/pypsa-meets-earth/pypsa-earth/issues
- Documentation: https://pypsa-earth.readthedocs.io/

For ARC issues:
- ARC Support: support@arc.ox.ac.uk
- User Guide: https://arc-user-guide.rc.ox.ac.uk/
