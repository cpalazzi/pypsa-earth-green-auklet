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

CO2 variants (full-year, 140 nodes):
- `config.europe-year-140.yaml` - Explicit limited CO2 (default run)
- `config.europe-year-140-co2-zero.yaml` - Zero CO2 cap
- `config.europe-year-140-co2-uncapped.yaml` - Effectively uncapped CO2

H2 optionality variants (append `-h2`):
- `config.europe-year-140-h2.yaml` - Limited CO2 + H2 (CCGT H2 + pipeline)
- `config.europe-year-140-co2-zero-h2.yaml` - Zero CO2 + H2
- `config.europe-year-140-co2-uncapped-h2.yaml` - Uncapped CO2 + H2

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
sbatch ../arc/jobs/02_build_networks_and_solve_power.sh \
  europe-year-140-co2-zero-h2-power \
  configs/scenarios/config.europe-year-140-co2-zero-h2-power.yaml
```

### Running Models
```bash
cd pypsa-earth
sbatch ../arc/jobs/01_build_profiles.sh europe-year-140-profiles configs/scenarios/config.europe-year-140-profiles.yaml
sbatch ../arc/jobs/02_build_networks_and_solve_power.sh europe-year-140-co2-zero-h2-power configs/scenarios/config.europe-year-140-co2-zero-h2-power.yaml
```

Recommended power sequence:
1. `01_build_profiles.sh` (renewable profiles)
2. `02_build_networks_and_solve_power.sh` (network build + solve)

### Submitting Multiple Scenario Jobs (IMPORTANT)

**Never submit multiple solve jobs simultaneously when they share the same `run.name`.**

All our scenario configs (co2-zero, co2-limited, co2-uncapped, co2-price, etc.) share `run.name: "europe-year-140"`. This means they share:
1. **Snakemake working directory lock** — Snakemake acquires an exclusive lock on the working directory. A second job starting while the first holds the lock will fail immediately.
2. **Intermediate files** — The `_ec.nc` file (from `add_extra_components`) is rebuilt per scenario with different `extendable_carriers` (e.g., base vs H2 vs NH3). Concurrent jobs would clobber each other's intermediates.

**Use SLURM dependency chaining** to run jobs sequentially:

```bash
cd /data/engs-df-green-ammonia/engs2523/pypsa-earth-green-auklet/pypsa-earth

# Submit first job
JOB1_RAW=$(sbatch --parsable -M htc ../arc/jobs/02_build_networks_and_solve_power.sh \
  co2-price-dea30 configs/scenarios/config.europe-year-140-co2-price-dea30.yaml)
JOB1=${JOB1_RAW%%;*}   # strip ";htc" cluster suffix from --parsable output

# Chain second job after first
JOB2_RAW=$(sbatch --dependency=afterany:$JOB1 --parsable -M htc ../arc/jobs/02_build_networks_and_solve_power.sh \
  co2-price-h2-dea30 configs/scenarios/config.europe-year-140-co2-price-h2-dea30.yaml)
JOB2=${JOB2_RAW%%;*}

# Chain third job after second
sbatch --dependency=afterany:$JOB2 -M htc ../arc/jobs/02_build_networks_and_solve_power.sh \
  co2-price-nh3-dea30 configs/scenarios/config.europe-year-140-co2-price-nh3-dea30.yaml
```

Notes:
- Use `afterany` (not `afterok`) so the chain continues even if a prior job fails — each scenario is independent once intermediates are rebuilt.
- The `${JOB_RAW%%;*}` pattern strips the `;htc` cluster suffix that `--parsable` appends on multi-cluster setups.
- The job script already handles removing stale `_ec.nc` and `_ec_*.nc` intermediates before each run.

### Monitoring Jobs
- Check status across ARC clusters: `squeue --clusters=all -u <user>`
- Cluster-specific fallback: `squeue -u <user>`
- Watch logs: `tail -f logs/snakemake-*-build-profiles.log` and `tail -f logs/snakemake-*-solve-power.log`
- Job details: `sacct -j <jobid> --format=JobID,JobName,State,Elapsed,MaxRSS`

### Copilot / VS Code Terminal SSH Workflow
Copilot can run ARC commands via single-shot SSH from the VS Code terminal.
The terminal will prompt for a password — enter it when asked.

**Check a specific Slurm job:**

```bash
ssh engs2523@arc-login.arc.ox.ac.uk "sacct -j <JOBID> --format=JobID,JobName%30,State%15,Elapsed,MaxRSS,ExitCode,Start,End"
```

**List all running/pending jobs:**

```bash
ssh engs2523@arc-login.arc.ox.ac.uk "squeue --clusters=all -u engs2523"
```

**Tail Snakemake solve log:**

```bash
ssh engs2523@arc-login.arc.ox.ac.uk "tail -50 /data/engs-df-green-ammonia/engs2523/pypsa-earth-green-auklet/pypsa-earth/logs/snakemake-*-solve-power.log"
```

**Tail Slurm stdout for a job:**

```bash
ssh engs2523@arc-login.arc.ox.ac.uk "tail -50 /data/engs-df-green-ammonia/engs2523/pypsa-earth-green-auklet/pypsa-earth/slurm-<JOBID>.out"
```

**Combined status check (job + queue + recent log):**

```bash
ssh engs2523@arc-login.arc.ox.ac.uk "sacct -j <JOBID> --format=JobID,JobName%30,State%15,Elapsed,MaxRSS,ExitCode; echo '---'; squeue --clusters=all -u engs2523; echo '---'; tail -30 /data/engs-df-green-ammonia/engs2523/pypsa-earth-green-auklet/pypsa-earth/logs/snakemake-*-solve-power.log 2>/dev/null | tail -20"
```

**Push local changes to ARC (rsync):**

```bash
rsync -avz --progress pypsa-earth/scripts/prepare_network.py engs2523@arc-login.arc.ox.ac.uk:/data/engs-df-green-ammonia/engs2523/pypsa-earth-green-auklet/pypsa-earth/scripts/
```

**Resubmit a failed job after fix:**

```bash
ssh engs2523@arc-login.arc.ox.ac.uk "cd /data/engs-df-green-ammonia/engs2523/pypsa-earth-green-auklet/pypsa-earth && sbatch ../arc/jobs/02_build_networks_and_solve_power.sh europe-year-140-co2-zero-h2-power configs/scenarios/config.europe-year-140-co2-zero-h2-power.yaml"
```

### H2-Power Run Readiness (reuse annual profiles)
From `pypsa-earth/` on ARC:

1. Submit Step 1 build-profiles job (annual profiles):
  ```bash
  sbatch ../arc/jobs/01_build_profiles.sh \
    europe-year-140-profiles \
    configs/scenarios/config.europe-year-140-profiles.yaml
  ```
2. Verify required profile files exist for the solve config:
  ```bash
  ../arc/arc_check_run_inputs.sh configs/scenarios/config.europe-year-140-co2-zero-h2-power.yaml
  ```
3. After Step 1 completes, submit Step 2 power solve:
  ```bash
  sbatch ../arc/jobs/02_build_networks_and_solve_power.sh \
    europe-year-140-co2-zero-h2-power \
    configs/scenarios/config.europe-year-140-co2-zero-h2-power.yaml
  ```
4. Optional convenience: submit Step 2 with dependency on Step 1:
  ```bash
  BUILD_JOB=$(sbatch --parsable ../arc/jobs/01_build_profiles.sh \
    europe-year-140-profiles \
    configs/scenarios/config.europe-year-140-profiles.yaml)

  sbatch --dependency=afterok:${BUILD_JOB} ../arc/jobs/02_build_networks_and_solve_power.sh \
    europe-year-140-co2-zero-h2-power \
    configs/scenarios/config.europe-year-140-co2-zero-h2-power.yaml
  ```

### Annual variants

Run Step 2 with the desired config to build and solve the variant.

### Build annual profiles only

Use dedicated config: `configs/scenarios/config.europe-year-140-profiles.yaml`

Checklist (run from `pypsa-earth/` on ARC):

- [ ] Preflight expected profile outputs:
  ```bash
  ../arc/arc_check_run_inputs.sh configs/scenarios/config.europe-year-140-profiles.yaml
  ```
- [ ] Submit Step 1 build-profiles job for annual profiles:
  ```bash
  sbatch ../arc/jobs/01_build_profiles.sh \
    europe-year-140-profiles \
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
- If missing databundles are prompted interactively, run non-interactive retrieval first and then resubmit Step 1.

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

## Contributions Summary (for paper reference)

Model extensions to PyPSA-Earth v0.8.0 (non-sector electricity workflow):

### Code contributions (`scripts/add_extra_components.py`)
1. **NH3 carrier implementation** — 3 new `attach_*` functions: NH3 synthesis (Haber-Bosch with parasitic electrical draw), NH3 storage (liquid tank), CCGT NH3 (ammonia-to-power). Adds NH3 bus at each AC node, wired via Link components with configurable efficiencies.
2. **NH3 pipeline transport** — bidirectional inter-node NH3 pipelines derived from AC transmission topology, with length-proportional costs.
3. **Submarine pipeline cost factor** — `underwater_fraction`-weighted cost multiplier for H2 and NH3 pipelines (`electricity.pipeline_submarine_cost_factor` config key). Pipelines crossing water pay a configurable premium (default 2×) on the underwater segment.
4. **Orphaned bus fix** — `ac_bus_set` filter in both H2 and NH3 pipeline functions to drop stale bus references from pre-simplification `n.lines`. Without this, 40 of 114 pipeline endpoints were unconstrained.
5. **Fuel cell removal** — commented out; H2-to-power exclusively via CCGT H2 to avoid cost-dominated substitution.
6. **Nuclear made extendable** — added to `extendable_carriers.Generator` in `config.default.yaml`.

### Cost data (`data/costs_dea2030.csv`)
7. **DEA 2030 cost file** — 226 rows, 63 technologies. Primary source: Danish Energy Agency 2030 projections (4 datasheets). All values in 2020 EUR. Non-DEA rows HICP-inflated from 2013 EUR (×1.084). Key updates vs original `costs.csv`:
   - Solar utility: 600→380, onwind: 1040→930, offshore: 2040→1640
   - CCGT: 800→883 (η 0.58), OCGT: 400→468 (η 0.41)
   - Electrolysis: 669→500 (input basis, corrected from output-basis convention)
   - Battery inverter: 411 USD→149 EUR, H2 storage tank: 11.2 USD→47.76 EUR
   - H2 pipeline: 267→400 (European Hydrogen Backbone), NH3 pipeline: 267→200 (Hydrogen Council)

### Infrastructure (`Snakefile`, configs, ARC scripts)
8. **Configurable cost file** — `costs.file` config key in Snakefile (default `data/costs.csv`), enabling per-scenario cost assumptions without file renaming.
9. **Scenario configs** — 9 configs covering CO2 × H2 × NH3 × cost-set combinations.
10. **ARC job scripts** — two-step workflow (profiles → solve), preflight checker, config path fallback logic.

### Validated results (ARC HPC, europe-year-140, 2920 3h snapshots)
| Scenario | Carriers | Cost file | Status |
|----------|----------|-----------|--------|
| co2_limited | battery | original | complete |
| co2_zero | battery | original | complete |
| co2_uncapped | battery | original | complete |
| co2_zero_h2 | battery, H2 | original | complete |
| co2_zero_nh3 | battery, H2, NH3 | original | complete |
| co2_zero_nh3_dea30 | battery, H2, NH3 | DEA 2030 | submitted (job 7254231) |

### Key model results
- **NH3 energy balance**: 1:1 confirmed (98.9 TWh synthesis output)
- **Roundtrip efficiencies**: el→H2→el 37.0% (η_elec 0.74 × η_CCGT 0.50), el→H2→NH3→el 29.5% (including Haber-Bosch parasitic draw 0.141 MWh_el/MWh_H2)
- **NH3 storage 16× cheaper** than H2 per MWh (57.70 vs 927.41 EUR/MWh)
- **Submarine cost factor** produces 146 unique pipeline capital costs (length × underwater fraction)

### Fossil fuel cost updates (costs_dea2030.csv)
All IEA 2011b fuel forecasts in `costs_dea2030.csv` were replaced with recent market-based values (2020 EUR, HICP-deflated from nominal):

| Fuel | Old (IEA 2011b) | New | Source / rationale |
|------|-----------------|-----|-------------------|
| Gas | 23.4 | **40.0** | TTF 5yr avg 2021-25 excl. 2022 crisis; rounded up |
| Coal | 9.1 | **15.0** | API2 5yr avg ~$130/t ≈ 17 EUR/MWhth nom → 15 deflated |
| Lignite | 3.1 | **6.0** | EU domestic extraction; rising env/reclamation costs; mine-mouth (no shipping) but ~2× old IEA |
| Biomass | 7.6 | **25.0** | EU mixed feedstock avg (chips, pellets, forestry residues) |
| Nuclear | 3.3 | 3.3 | Unchanged — uranium spot stable |
| Oil | 54.2 | 54.2 | Unchanged — IEA WEM2017 broadly OK |

**Gas detail:** Annual TTF averages: 2021 ~47, 2022 ~131 (excluded), 2023 ~41, 2024 ~34, 2025 ~36 EUR/MWh nominal. HICP-deflated 4-year mean ~35, rounded to 40.

**Coal detail:** API2 (CIF ARA) ranged $110–160/t over 2021-25 excl. 2022. At 6.98 MWh/t and ~0.92 EUR/USD, avg ~17 EUR/MWhth nominal. HICP-deflated ≈ 15.

**Lignite detail:** Not internationally traded (mine-mouth). German/Polish production costs estimated at €5-8/MWhth with rising environmental compliance. Phase-out: Germany 2038 (some 2030), Greece 2026, Czechia 2033, Poland no date.

**Biomass detail:** EU industrial wood pellets ~€30-40/MWhth, chips ~€20-30, forestry residues ~€15-20. Weighted average for power sector mix ≈ 25.

Implied electricity fuel costs at DEA 2030 efficiencies:
- CCGT (η=0.58): 40/0.58 = **69 EUR/MWhel** (was 40)
- Coal (η=0.46): 15/0.46 = **33 EUR/MWhel** (was 20)
- Lignite (η=0.45): 6/0.45 = **13 EUR/MWhel** (was 7)
- Biomass (η=0.47): 25/0.47 = **53 EUR/MWhel** (was 16)

## Open Work
- [ ] Download and analyse DEA 2030 NH3 results (job 7254231)
- [ ] Compare original vs DEA 2030 cost sensitivity
- [ ] Add co2_limited and co2_uncapped H2/NH3 variants if needed
- [ ] Nuclear `p_min_pu` sensitivity (baseload floor at 0.3)
- [ ] Demand-side response / sector coupling
- [ ] Paper figures and tables from notebook outputs

## Changes Log

### 6 Mar 2026 — Fossil Fuel Cost Audit & Update
- Audited all IEA 2011b fuel forecasts in `costs_dea2030.csv` against current market data.
- Updated gas (40), coal (15), lignite (6), biomass (25) EUR/MWhth — see fuel cost note above.
- Coal and biomass were most significantly underpriced (coal 12% of dispatch at +65% price gap).
- All three DEA30 scenarios resubmitted with fully updated cost file.

### 5 Mar 2026 — DEA 2030 Cost File and Configurable Cost Path
- Built `data/costs_dea2030.csv` (226 rows, 63 technologies, all 2020 EUR) from 4 DEA datasheets.
- Added `costs.file` config key to Snakefile (backward-compatible, defaults to `data/costs.csv`).
- Created `config.europe-year-140-co2-zero-nh3-dea30.yaml` scenario.
- Full input/output basis audit of all Link technologies passed.
- Submitted co2_zero_nh3_dea30 job (7254231) on ARC.

### 4 Mar 2026 — NH3 Implementation and Pipeline Bug Fix
- Implemented NH3 carrier: synthesis, storage, CCGT NH3, NH3 pipeline in `add_extra_components.py`.
- Fixed orphaned pipeline bus bug (`ac_bus_set` filter + `reset_index`).
- Added submarine pipeline cost factor (`electricity.pipeline_submarine_cost_factor`).
- co2_zero_nh3 solved successfully (171 MB, ~1h40m). Energy balance validated.

### 3 Mar 2026 — Nuclear Dispatch Investigation
- Nuclear at 26% CF in co2_zero run (128 GW capacity). Economically rational:
  renewables at zero marginal cost displace nuclear whenever available.
- Decision: no `p_min_pu` constraint for now (parsimonious baseline).

### 2 Mar 2026 — Batch 2 Config Overhaul
**Motivation:** Initial runs showed both co2_zero and h2_power had H2 by default,
making comparison invalid. Fuel cell dominated CCGT H2 due to lower cost + higher η.
Load shedding dominated objectives, masking real cost differences.

**Changes made:**
1. **Nuclear now extendable** — added `nuclear` to `extendable_carriers.Generator` in
   `config.default.yaml`. Existing brownfield nuclear plants can now expand capacity.
   Nuclear has zero CO2 emissions, providing a dispatchable zero-carbon backstop that
   should reduce load shedding significantly.

2. **H2 removed from default Store** — `config.default.yaml` now has `Store: [battery]`.
   H2 is only enabled in the `-h2` scenario configs. This gives a clean no-H2 baseline.

3. **Fuel cell removed** — Commented out in `add_extra_components.py`. H2-to-power
   conversion now exclusively via CCGT H2 links (when enabled). Fuel cell was cheaper
   and more efficient, making CCGT H2 irrelevant when both were present.

4. **Six scenario configs** created for systematic comparison:
   - Without H2: `co2_limited`, `co2_zero`, `co2_uncapped`
   - With H2: `co2_limited_h2`, `co2_zero_h2`, `co2_uncapped_h2`
   All H2 configs add `Store: [battery, H2]`, `Link: [CCGT H2, H2 pipeline]`,
   `max_hours.H2: 4380`.

5. **CCGT H2 capital_cost verified** — `capital_cost = investment × efficiency` correctly
   converts from per-kW-output to per-kW-input (bus0) for Link components. Same pattern
   as fuel cell (both H2→AC links). Electrolysis has no conversion because investment
   is already per-kW-input.

6. **Solar/wind land caps confirmed** — `p_nom_max` is set from resource profile datasets
   (geographical/land-availability potential). IRENA stats provide `p_nom_min` scaling.
   No changes needed.

## Findings: co2_zero vs h2_power LCOE Comparison (2 Mar 2026)

### Key Finding: Load Shedding Dominates Both Objectives
Both `co2_zero` and `h2_power` runs include H2 storage + electrolysis + fuel cell by default
(`config.default.yaml` has `Store: [battery, H2]`). The `h2_power` config only ADDS
CCGT H2 links and H2 pipelines on top.

Despite h2_power having more H2 options, its LCOE is higher (125 vs 110 EUR/MWh).
Root cause: **load shedding at 100,000 EUR/MWh** dominates the objective:
- co2_zero: 2.565 TWh shed → 256,483 MEUR penalty
- h2_power: 3.095 TWh shed → 309,539 MEUR penalty
- Difference: +53,056 MEUR ≈ entire LCOE gap

Excluding load shedding, both runs cost ~39-40 EUR/MWh — the optimizer behaves correctly.
The 0.53 TWh shedding difference (0.015% of demand) is within solver tolerance / optimality gap.

### Fuel Cell vs CCGT H2: Why Fuel Cell Dominates
The optimizer correctly prefers fuel cells over CCGT H2 on every metric:

| Parameter       | Fuel Cell    | CCGT H2      |
|-----------------|-------------|-------------- |
| Investment      | 339 EUR/kW  | 800 EUR/kW   |
| Efficiency      | 0.58        | 0.50         |
| FOM             | 3%/yr       | 2.5%/yr      |
| Lifetime        | 20 yr       | 30 yr        |
| VOM             | 0 EUR/MWh   | 4 EUR/MWh    |
| Annualized CapEx (7.1%) | ~32 EUR/kW/yr | ~65 EUR/kW/yr |
| Effective PyPSA capital_cost | investment × η | investment × η |

Both convert H2→electricity with zero fuel cost (H2 from store). Fuel cell has ~2x lower
capital cost AND higher efficiency. CCGT H2 only makes sense at very different cost assumptions.

### Nuclear Is Not Extendable
Nuclear is in `conventional_carriers` but NOT in `extendable_carriers.Generator`.
The model uses existing brownfield nuclear but cannot build new nuclear.
Under zero-CO2, the only new-build dispatchable options are H2-based (fuel cell, CCGT H2)
since OCGT/CCGT emit CO2. This limits the model's ability to displace load shedding.

Nuclear LCOE at costs.csv figures: ~77 EUR/MWh (6000 EUR/kW, 45yr, 85% CF, 7.1% WACC,
3 EUR/MWhth fuel, 8 EUR/MWhel VOM). Still far cheaper than 100,000 EUR/MWh load shedding.

### Nuclear Dispatch Findings (3 Mar 2026)
Investigation of the co2_zero run revealed that existing nuclear capacity is correctly
retained (France 66 GW, Europe total 128 GW via `p_nom_min`) but dispatch is low:
~26% capacity factor, offline 43% of the year.

**Why nuclear underperforms:** Nuclear has zero CO2 emissions in the model, so it is not
penalised under a zero-CO2 cap. The low dispatch is economically rational — massive
renewable overbuild (1,060 GW solar, 832 GW onwind) at near-zero marginal cost
displaces nuclear whenever renewables are available. The optimizer freely cycles nuclear
up and down because no `p_min_pu` or ramp constraints are imposed.

**Ramp rates are immaterial at 3h resolution:** French nuclear plants can ramp at
~5%/min in load-following mode (~1–3% p_nom/min). At 3-hour timesteps this translates
to effectively unconstrained ramping (100% in one step), so adding `ramp_limit_up/down`
would have no practical effect at our temporal resolution.

**Minimum stable load (`p_min_pu`) could matter:** Real French nuclear operates with a
minimum stable output of ~30% of nameplate (flexible mode). Setting `p_min_pu = 0.3` on
nuclear generators would prevent full shutdown and force a baseload floor, more closely
reflecting operational reality. However, we are deliberately **not** implementing this
for now — leaving nuclear unconstrained gives the optimizer maximum flexibility and
provides a parsimonious baseline. The current treatment is conservative in that it
*underestimates* nuclear's system value (by allowing the optimizer to "waste" nuclear
capacity that in practice would run at minimum load and displace some renewables).
This can be revisited if nuclear dispatch patterns become a focus of analysis.

### Implications for Next Runs
1. Load shedding signals model infeasibility at some nodes/hours — need to investigate WHERE
2. To test H2 optionality value: need a baseline WITHOUT H2 (override `Store: [battery]`,
   remove H2 from default) then compare against H2-enabled run
3. Adding nuclear to extendable_carriers would largely eliminate load shedding but is a
   policy choice, not a bug fix
4. Consider reducing solver optimality gap (MIPGap) to get tighter load-shedding bounds

## Investigation Plan: H2 and NH3 Optionality Value

### Phase 1: Clean H2 A/B Test — COMPLETE
Run A (no H2, battery only), Run B (H2 storage + electrolysis + CCGT H2 + pipeline).
Nuclear made extendable in all configs. Fuel cell removed. Six scenario configs built.
Results: co2_zero, co2_zero_h2 both solved successfully. Analysis in `notebooks/01_run_analysis.ipynb`.

### Phase 2: Ammonia Optionality — COMPLETE
NH3 synthesis, storage, CCGT NH3, and NH3 pipeline implemented in `add_extra_components.py`.
Orphaned bus bug found and fixed. co2_zero_nh3 solved with submarine pipeline cost factor.
Energy balance validated (1:1 NH3 mass balance, 98.9 TWh).

### Phase 3: DEA 2030 Cost Sensitivity — IN PROGRESS
DEA 2030-first cost file built (`data/costs_dea2030.csv`). Configurable cost file path
added to Snakefile. co2_zero_nh3_dea30 submitted (job 7254231).

## Notes on Ammonia Integration
NH3 carrier fully implemented in the non-sector electricity workflow. See
`references/tech_config_ammonia_plant_2030_dea.yaml` for the original DEA cost extraction
that informed `costs_dea2030.csv`.

### NH3 Pipeline Orphaned Bus Bug (4 Mar 2026)

**Symptom**: CCGT NH3 consumes 384× more NH3 than synthesis produces (4,159 TWh vs 10.8 TWh).
NH3 pipeline capacity is 993 GW — physically impossible. PyPSA warns about undefined buses on load.

**Root cause**: `attach_ammonia_pipelines()` (and `attach_hydrogen_pipelines()`) construct bus pairs
from `n.lines[["bus0", "bus1"]]`. After `simplify_network` / `cluster_network`, **`n.lines` retains
references to buses that were merged away** during simplification. The pipeline function appends
" NH3" to these bus names, but `attach_ammonia_stores` only creates NH3 buses for the 98 AC buses
that actually exist. Result: 40 of 114 unique pipeline bus references point to non-existent NH3
buses, creating unconstrained orphaned links.

**Diagnosis**:
- 98 NH3 buses exist (matching 98 AC buses)
- NH3 pipelines reference 114 unique buses → 40 missing
- Missing buses: DE44, DE45, DK33, DK34, etc. (pre-simplification names)
- H2 pipelines have same bug but tiny capacity (94 MW) masks the issue

**Fix applied**: Added `ac_bus_set` filter in both `attach_ammonia_pipelines()` and
`attach_hydrogen_pipelines()` to drop candidate bus pairs where either endpoint is not in
`n.buses[carrier=="AC"]`. This ensures pipelines only connect buses that actually exist.

**Impact**: co2_zero_nh3 results (job 11444046) are **invalid** — must be re-run with the fix.

**Roundtrip efficiency validation** (correctly implemented):
- el → H2 → el (CCGT H2): 37.0% (electrolysis 0.74 × CCGT 0.50)
- el → H2 → NH3 → el (CCGT NH3): 29.5% (including Haber-Bosch parasitic draw 0.141 MWh_el/MWh_H2)
- NH3 storage is 16× cheaper per MWh than H2 (57.70 vs 927.41 EUR/MWh)

## 1h Temporal Resolution Sensitivity Run

**Purpose**: Check whether battery capacity changes significantly at 1h vs 3h temporal
resolution. The hypothesis is that system LCOE will be similar, but battery sizing may
differ because 3h averaging smooths intra-day variability that drives short-duration
storage dispatch.

**Config**: `config.europe-year-140-co2-zero-nh3-dea30-1h.yaml` — identical to the 3h
zero-CO2 NH3 DEA30 config except opts changed from `Co2zero-3h-NH3-DEA30` to
`Co2zero-1h-NH3-DEA30`. Only step 02 needed; profiles are built at native hourly
resolution and reused.

**Resource requirements**: The 1h LP is ~3× larger than 3h (8760 vs 2920 snapshots) but
memory scales super-linearly (~5–8×). First attempt OOM'd at 128GB (job 7267306).
Second attempt timed out at 8h on `short` with 256GB (job 7267378, peak 213GB).
Resubmitted on `medium` partition (2-day wall time, 256GB) as job 7271075.

## Transmission Loss Modelling & Offshore Wind

**AC lines** (131 lines, total 42 833 km): type `Al/St 240/40 4-bundle 380.0`,
`s_max_pu = 0.7`, `length_factor = 1.25`. All values are PyPSA-Earth defaults
(`config.default.yaml`), not DEA parameters. Because PyPSA uses LOPF (linear optimal
power flow), AC resistive (I²R) losses are **not modelled**; `s_max_pu = 0.7` acts only
as a thermal derating limit.

**DC links** (76 links): `efficiency = 1.0` across all links — no loss modelling.
This is also a PyPSA-Earth default.

**Offshore wind**: 30 GW total capacity is present (29 923 MW offwind-dc, 0.1 MW
offwind-ac). The near-zero offwind-ac results from `max_shore_distance = 30 000 m`
leaving almost no viable AC-connected area at this spatial resolution. Capacity factor
for offwind-dc is 0.476 (125.5 TWh generation). The installed capacity aligns with
IRENA 2023 European offshore statistics (~33 GW).

## References

Fuel price data and deflator sources used in `costs_dea2030.csv` updates (see [fuel cost audit table](#fossil-fuel-cost-updates-costs_dea2030csv) above). Full data in [references/fuel_cost_updates.csv](references/fuel_cost_updates.csv).

- **TTF gas price**: ACER, *European Gas Market Reports* (quarterly), https://www.acer.europa.eu/gas/market-monitoring; Trading Economics, *EU Natural Gas — TTF Historical Data*, https://tradingeconomics.com/commodity/eu-natural-gas.
- **API2 coal price**: Trading Economics, *Coal — Historical Data*, https://tradingeconomics.com/commodity/coal; Intercontinental Exchange (ICE), API2 Rotterdam Coal Futures.
- **Lignite production cost**: Agora Energiewende, *The German Coal Commission* (2019); DIW Berlin, *Current and Prospective Costs of Electricity Generation* (DataDoc 68, 2013), http://hdl.handle.net/10419/80348.
- **Biomass fuel price**: IRENA, *Renewable Power Generation Costs in 2023* (Sep 2024); Eurostat, *Wood as a source of energy*, https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Wood_as_a_source_of_energy.
- **Oil fuel price**: IEA, *World Energy Model Documentation 2017*, http://www.iea.org/media/weowebsite/2017/WEM_Documentation_WEO2017.pdf.
- **Nuclear fuel price**: DIW Berlin DataDoc 68 (2013); World Nuclear Association, *Uranium Markets*, https://world-nuclear.org/information-library/nuclear-fuel-cycle/uranium-resources/uranium-markets.
- **HICP deflator**: Eurostat, *HICP — Annual Average Index* (2015=100), https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_aind/. Factor 2013→2020: ×1.084.
- **Coal phase-out tracker**: Beyond Fossil Fuels, *Europe's Coal Exit*, https://beyondfossilfuels.org/coal-exit-tracker/ (updated Jun 2025).

## Technology-data runs (TD30), prepared 6 October 2026

Branch `review/td-defaults-alignment`. Inputs follow PyPSA-Earth's default technology-data v0.13.2. DEA or other sources are used only where a component is missing, plus DEA electrolysis (500 EUR/kW_e) and nuclear at 6504 EUR/kW. Discount rate is the PyPSA-Earth default (7 %).

- `build_costs_td2030.py` builds `pypsa-earth/data/costs_td2030.csv` and `costs_td2030_cheapbatt.csv` (battery storage only, tenfold cut). Ammonia components map to Haber-Bosch, NH3 (l) storage tank incl. liquefaction, and CCGT. The NH3 pipeline uses DEA values. Fuel prices are the updates in `references/fuel_cost_updates.csv`.
- `add_extra_components.py`:
  - H2 tanks sit on their own "H2 store" bus behind a compressor link (technology-data hydrogen storage compressor: 0.05 MWh_el/MWh_H2) and a valve link.
  - NH3 synthesis reads hydrogen-input and electricity-input from the costs.
  - CCGT and synthesis variable O&M are multiplied by efficiency for the bus0 basis.
- Fixes versus the DEA30 runs:
  - Electrolysis efficiency is now 0.6217 LHV. It was 0.74 HHV on an LHV bus, about 19 % optimistic for H2 and NH3.
  - The ammonia tank cost follows technology-data. The old 0.52 EUR/kWh treated 3000 AUD/t as USD.
  - CCGT variable O&M was charged per MWh of fuel instead of per MWh of electricity.
- Configs: `configs/scenarios/config.europe-year-140-{co2-zero,co2-zero-h2,co2-zero-nh3,co2-price-nh3}-td30.yaml`, `...-co2-zero-nh3-td30-cheapbatt.yaml` and `...-td30-1h.yaml`.
- Smoke test: the europe-day-140 week network (168 h) with all components solves optimally with Gurobi in about 4 minutes locally. Year runs have not been started.

## TD30 runs submitted on ARC, 7 October 2026

- Synced to ARC: `build_costs_td2030.py`, `data/costs_td2030*.csv`, `scripts/add_extra_components.py` and the TD30 configs. The previous ARC copy of the script is in `_backups/2026-10-07/`.
- ARC's `data/` databundle had been re-extracted on 19 May 2026: 179 files with the same contents but new timestamps. With `--rerun-triggers mtime` that would have rebuilt the shapes, the OSM network and the renewable profiles. With Carlo's approval the timestamps were reset to 3 Feb 2026; the old values are in `_backups/2026-10-07/data_mtimes_before_reset.tsv`.
- A dry-run in a Slurm job confirmed that only `add_electricity` onwards reruns, because the cost file is new.
- Submitted as one `afterany` chain on the arc cluster (16 CPUs, 128 GB, short):
  - 13388411 co2-zero-td30
  - 13388412 co2-zero-h2-td30
  - 13388414 co2-zero-nh3-td30
  - 13388415 co2-price-nh3-td30
  - 13388416 co2-zero-nh3-td30-cheapbatt
- The 1 h check (`...-td30-1h.yaml`) is not submitted. It needs the medium partition and 256 GB.
- ARC cleanup, 7 Oct 2026, on Carlo's go-ahead. The record is in `/data/engs-df-green-ammonia/engs2523/_maintenance/2026-10-07/cleanup_manifest.tsv`.
  - Deleted the stray root copies `pypsa-earth/add_extra_components.py` and `pypsa-earth/prepare_network.py`.
  - Deleted the stray `arc/03_build_networks_and_solve_sector.sh` and `arc/config.europe-year-140-co2-zero-h2-sector.yaml`.
  - Deleted the pre-fix result archives `results/europe-year-140/networks/_archive_pre_fix_2025_03_03` and `_archive_default_costs_ccgt_ext_2025_03_05`.
  - Old `slurm-*.out` files moved to `pypsa-earth/logs/slurm/`.
  - `_resolution_sensitivity` (Appendix F of the paper) and all DEA30 results are kept.

## Isolated buses and lost load, 8 October 2026

**Finding.** Every run since February has 27-33 single-bus AC islands. Four of them (BE59 0, MT50 0, NL52 0, SI69 0) cannot meet their load. Under zero CO2 they shed 3.0 TWh a year at the 100 EUR/kWh lost-load price, 0.08 % of demand; under the CO2 price they shed 1.67 TWh. That penalty was 55-76 % of every objective.
- The September paper's "system LCOE" divided the objective by demand. It was therefore mostly lost-load penalty, and it left out the existing capacity that PyPSA reports as `objective_constant`.
- The cost differences between zero-CO2 scenarios were valid, because the penalty was identical in each. The relative savings were not: ammonia saves 7.4 % of the true system cost, not 4 %.
- Table 6's generation capacity (2.6 TW) also counted 0.64 TW of load-shedding pseudo-generators.

**History.** The 2 March notes (above) found that "load shedding dominated objectives". They attributed it to the lack of a zero-carbon dispatchable option and made nuclear extendable. The follow-up "investigate WHERE" was never done. Nuclear cannot reach islands, so the shedding stayed.

**Cause.** `cluster_options.simplify_network.s_threshold_fetch_isolated: false` in `config.default.yaml`. Isolated fragments of the OSM network then stay islands; most are mainland fragments with 1-15 % of national load.

**Fix.** The TD30 configs set `s_threshold_fetch_isolated: 0.2`. A test rebuild fetched 163 isolated OSM buses into the backbone:
- AC sub-networks fell from 33 to 8;
- only Cyprus and Malta remain single-bus islands;
- Malta still sheds under zero CO2, because its interconnector to Sicily is missing from OSM.

`notebooks/paper_metrics.py` now reports system cost as the objective plus `objective_constant` minus the lost-load penalty, and gives lost load separately. The pre-fix TD30 results are kept locally in `results/europe-year-140/networks/_archive_td30_with_islands_2026_10_07/`.

**Incident.** The test job ran `snakemake ... --forcerun simplify_network <target>`. `--forcerun` takes several values and swallowed the target, so Snakemake ran the first rule, `clean`. That rule's `--delete-all-output`, under the default config, deleted 18 downloaded inputs (33 GB):
- the ERA5 cutout, GEBCO, natura, EEZ, HydroBASINS, land cover and the SSP2 demand files;
- the default run's raw OSM files.

All 18 were restored from ARC's 10:05 hourly snapshot with `cp -a` (sizes and timestamps verified). The record is in `/data/engs-df-green-ammonia/engs2523/_maintenance/2026-10-08/`. Lesson: put the Snakemake target first.

**Storage durations are not limited (checked 8 Oct 2026).** `electricity.max_hours` (battery 6, H2 and NH3 4380) only sets StorageUnit costs in `add_electricity.costs_for_storage` and StorageUnit sizes in `attach_storageunits`. The configs add no StorageUnits (`extendable_carriers.StorageUnit` is empty). Battery, H2 and NH3 are Stores with `e_nom` independent of link power; the only extra constraint ties battery charger to discharger power (`add_battery_constraints`).
- In the September NH3 run, 16 buses hold more than 6 h of battery energy per unit of discharger power (up to 155 h). The average of 6.3 h is an economic outcome.
- In the TD30 NH3 run before the island fix, three buses hold more than 4380 h of ammonia.
- Stores are cyclic over the one-year horizon (`e_cyclic=True`), so nothing carries over between years.

**Appendix F, 1 h resolution.** It keeps the March 1 h/3 h pair (September input set, network before the island fix). Both resolutions shed the same 3.02 TWh, so the comparison is unaffected. Recomputed with `notebooks/resolution_check.py DEA30`:
- System cost per MWh: +0.24 %. The published "less than 0.1 %" used the penalty-diluted objective.
- Capacities: battery energy +6.5 %, charger +15 %, H2 storage -9 %, NH3 storage unchanged, solar -2.8 %, nuclear +1 %.

A TD30 1 h run is ready but not submitted: from `pypsa-earth/`, `bash ../arc/submit_td30_1h.sh [<jobid> <cluster>]`. It requests medium, 320 GB and 36 h; the March run took 13 h at a 232 GB peak.

## TD30 results, 9 October 2026

All five TD30 runs (jobs 13437238-44, chained `afterany` on arc) finished on 8 Oct between 14:13 and 22:51. Each took 52 min to 2 h 38 min on 16 CPUs, with peak memory of 35-108 GB against the 128 GB request. Every solve reached "Termination condition: optimal" (Gurobi barrier, no crossover). Results were fetched to `results/europe-year-140/networks/*TD30*.nc`. The table comes from `notebooks/paper_metrics.py TD30` (`results/europe-year-140/paper_metrics_TD30.csv`).

| | co2_zero | co2_zero_h2 | co2_zero_nh3 | co2_price_nh3 | low_cost_batt |
|---|---:|---:|---:|---:|---:|
| System cost (EUR/MWh) | 81.53 | 80.90 | 75.16 | 68.84 | 70.82 |
| Lost load, Malta (TWh) | 1.31 | 1.31 | 1.31 | 0.00 | 1.31 |
| Generator capacity (TW) | 2.24 | 2.20 | 2.03 | 1.71 | 2.05 |
| Nuclear (GW; 127.9 existing) | 156.0 | 135.4 | 127.9 | 127.9 | 127.9 |
| Nuclear capacity factor | 0.37 | 0.39 | 0.75 | 0.80 | 0.75 |
| Storage (TWh) | 2.09 | 6.44 | 66.80 | 1.11 | 65.21 |
| Battery: TWh delivered, cycles/yr | 291, 192 | 192, 246 | 202, 286 | 57, 305 | 347, 93 |
| NH3: TWh delivered, cycles/yr | - | - | 68.0, 1.8 | 0.3, 0.6 | 39.8, 1.2 |
| H2: TWh delivered, cycles/yr | - | 24.7, 8.1 | 1.2, 49 | 0.1, 39 | <0.1, 24 |

- Storage includes 0.51 TWh of existing hydro StorageUnits (6 h). Generator capacity includes 0.40 TW of existing coal, lignite, oil and gas plants, which are idle under the zero cap.
- Under the zero cap, ammonia takes the seasonal role. The NH3 store falls from 65 TWh in early January to almost zero on 31 March and refills from April to December. Ammonia CCGT output is 22.5, 20.3 and 7.3 TWh in January to March.
- Electrolysis (38.9 GW) and synthesis are in Greece, Britain and Ireland. NH3 CCGTs and stores are largest in Germany, Greece and Britain. Batteries are mostly in Italy and Spain.
- With ammonia, no new nuclear is built. Without hydrogen or ammonia, 28 GW is added but the fleet runs at 37 %.
- At 60 EUR/t CO2, existing CCGTs generate 249 TWh (about 7 % of demand) and ammonia is almost unused. The September DEA30 run gave 3 TWh of ammonia. Those runs differ in both inputs (DEA costs, the HHV electrolysis efficiency, the AUD tank cost) and network (four islands shedding load), so this comparison does not isolate the cause.
- Figures: `notebooks/paper_figures.py` wrote `pypsa_generation_map_co2_zero_nh3.png` and `pypsa_soc_co2_zero_nh3.png` to the paper's `images/`.
- Existing pumped hydro (50 units, 54 GW) has `max_hours = 0` in the clustered networks, so it holds no energy and never runs. Hydro reservoirs (85 GW) use the 6 h default (`hydro_max_hours` is "not active"), 0.51 TWh in total, so seasonal hydro storage is not represented. The paper states both; fixing them needs a rerun.
- `notebooks/paper_figures.py` now gives the map legend plain names and leaves out plants that never run.

## Hydro storage fix and TD30 rerun, 9 October 2026

- **Pumped hydro.** All 149 pumped hydro plants (54 GW) have no duration in `resources/europe-year-140/powerplants.csv`; the value is NaN, not 0. `add_electricity.attach_hydro` replaced only 0 with `PHS_max_hours`, so the plants kept NaN and the clustered networks carried `max_hours = 0`: pumped hydro held no energy. The fix fills NaN as well, so every plant gets the configured 6 h (0.32 TWh in total). PyPSA-Eur's version of this line already handled NaN.
- **Hydro reservoirs.** All 679 reservoirs (85.6 GW) also lack durations, so the `energy_capacity_totals_by_country` option sizes them from the `E_store[TWh]` column of `data/hydro_capacities.csv`. PyPSA-Earth's table has no European rows, so every European reservoir fell back to `hydro_max_hours_default` (6 h, 0.51 TWh in total).
  - The TD30 configs now set `renewable: hydro: hydro_capacities_extra: data/hydro_capacities_europe.csv`. That file is PyPSA-Eur's `data/hydro_capacities.csv` (master, downloaded 9 Oct 2026 with Carlo's approval; PyPSA-Eur's docs say its provenance is unclear).
  - The Snakefile passes it to `add_electricity` only, so the renewable profiles are not rebuilt.
  - Result: 206 TWh across 85.3 GW in the clustered network (NO 84.4, SE 33.6, ES 18.2, RO 12.1, FR 9.3, IT 8.4, CH 8.3 TWh). AL, ME and MK keep the 6 h default. Clustering weights `max_hours` by capacity (PyPSA 0.30), so energy is preserved.
- Check job 13447810 dry-ran first (no upstream rules), then built the co2-zero prepared network and confirmed the numbers above.
- The rerun chain on arc is 13447916-20 (`_maintenance/2026-10-09/td30_submissions.txt`). The pre-fix results are archived in `results/europe-year-140/networks/_archive_td30_before_hydro_fix_2026_10_09/`.

### TD30 results with hydro storage restored, 10 October 2026

All five reruns (13447916-20) finished optimal on 9-10 Oct (47 min to 3 h 16 min, peak 39-107 GB). Results are fetched to `results/europe-year-140/networks/*TD30*.nc` and `paper_metrics_TD30.csv`. The pre-fix runs are in `_archive_td30_before_hydro_fix_2026_10_09/`.

| | Base | Hydrogen | Ammonia | Carbon price | Cheap batteries |
|---|---:|---:|---:|---:|---:|
| System LCOE (EUR/MWh) | 73.12 | 72.57 | 69.36 | 66.01 | 65.94 |
| Stores built (TWh; hydro adds 206.47) | 1.42 | 3.75 | 29.10 | 0.22 | 25.56 |
| Battery: TWh delivered, cycles/yr | 207, 152 | 128, 258 | 161, 327 | 38, 340 | 347, 125 |
| NH3: TWh delivered, cycles/yr | - | - | 24.6, 1.6 | 0.08, 0.8 | 14.4, 1.1 |
| H2: TWh delivered, cycles/yr | - | 15.8, 8.2 | 0.15, 68 | 0.02, 35 | 0.01, 25 |
| Nuclear capacity factor (127.9 GW, none new) | 0.63 | 0.68 | 0.85 | 0.84 | 0.92 |

- Hydro reservoirs (206 TWh) fall by 52-55 TWh from 1 January to mid-April under the zero cap.
- In the Ammonia scenario, the NH3 store (28.5 TWh) empties from 6 January to 2 March. CCGT NH3 delivers 11.5 TWh in January and 7.4 TWh in February. Store ratios: battery about 6 h; NH3 charges over about 4600 h (tau_C) and discharges over about 260 h (tau_R).
- Carbon price: gas CCGTs generate 96 TWh and emit 35 Mt of CO2; payments are 0.58 EUR/MWh of demand.
- Effect of the fix: system LCOE falls by 8-10 %, no new nuclear is built even in Base, and ammonia delivers 24.6 TWh instead of 68 (it lowers system LCOE by 4.4 % instead of 7.1 %).
- `notebooks/paper_figures.py` now plots hydro reservoirs next to ammonia (state of charge) and shows hydro storage capacity on the map.

### Only the hydro-storage runs kept; upstream reports, 10 October 2026

- Carlo: only runs with pumped hydro and reservoir storage stay. On the Mac, the DEA30 networks, `paper_metrics_DEA30.csv`, `_resolution_sensitivity`, the five `_archive_*` folders, `results/europe-day-140` and `_verify_nuclear_cost.py` went to the macOS Trash. On arc, 11 items (1.9 GB: the nine DEA30 networks, `_resolution_sensitivity` and `results/europe-year-140-co2-zero-h2-sector`) were moved to `/data/engs-df-green-ammonia/engs2523/_to_delete_2026-10-10/`, listed in `/data/engs-df-green-ammonia/engs2523/_maintenance/2026-10-10/cleanup_manifest.tsv`. Carlo deletes that folder.
- `notebooks/resolution_check.py` and `02_resolution_analysis.ipynb` read the removed 1 h/3 h DEA30 pair. They stay for a 1 h check with hydro storage (`arc/submit_td30_1h.sh`), which is not submitted.
- Upstream PyPSA-Earth `main` (4f6bae8e, 10 Oct 2026) still has both hydro problems: `attach_hydro` fills only zero PHS `max_hours`, and `data/hydro_capacities.csv` has only African rows. The fork clone `~/programming/pypsa_models/pypsa-earth` (origin `cpalazzi/pypsa-earth`, remote `upstream`) has branch `fix/phs-max-hours-nan` (commit `db3a3226`, not pushed) with PyPSA-Eur's one-line fix. Two issue drafts and a PR description wait for Carlo's approval. The local patches here stay until auklet takes a PyPSA-Earth version that includes them.
- The fork's earlier fixes, checked 10 Oct 2026:
  - Gzipped Geofabrik MD5 files: fixed in earth-osm 3.0.2 (earth-osm issue 75, October 2025). The arc environment has earth-osm 3.0.2 and PyPSA-Earth now requires it, so `pypsa-earth/sitecustomize.py` duplicates installed code and can go.
  - `extra_functionality` chaining: a feature, unused here.
  - `retrieve_cost_data` local path: no failure reproduced with upstream's Snakemake 7 pin.
- Later on 10 Oct: the fork's main was reset to upstream main (4f6bae8e), and its two old branches were deleted on GitHub. The old commits stay in the clone's local branches `archive/old-main`, `add-gzip-detection-to-verify-pbf` and `fix/retrieve-cost-data-local-path`. A scheduled task (`pypsa-earth-issues-reminder`, 13 Oct 2026 at 09:00) reminds Carlo about the reports and holds the drafts.
- TD30 1 h run with hydro storage (`Co2zero-1h-NH3-TD30`, the Ammonia scenario at 1 h), submitted at Carlo's request on 10 Oct 2026:
  - Job 13450571 on arc (medium, 16 CPUs, 320 GB, 36 h), running on arc-c229 since 16:18.
  - A dry-run job (13450568) first confirmed that only `prepare_network` and `solve_network` run.
  - The submission is logged in `/data/engs-df-green-ammonia/engs2523/_maintenance/2026-10-10/td30_1h_submission.txt`.
  - When it ends:
    1. Check `sacct -M arc -j 13450571 --format=JobID,State,Elapsed,MaxRSS`.
    2. Fetch `results/europe-year-140/networks/elec_s_140_ec_lcopt_Co2zero-1h-NH3-TD30.nc`.
    3. Compare it with `Co2zero-3h-NH3-TD30`, adapting `notebooks/resolution_check.py`.
    4. Put the resolution check back into the paper.

### Duplicated OSM branches and merged HVDC ratings fixed; TD30 rerun, 12 October 2026

- Problem (read-only investigation on the Mac, 12 Oct): existing cross-border capacity in the TD30 networks was overstated.
  - OSM ways near a border are in two Geofabrik extracts and reached `base.nc` once per extract (earth-osm appends the extracts; `set_unique_id` in `clean_osm_data` renames the repeats instead of dropping them). 1,203 line and 548 cable ways are affected; about 300 of the 709 GVA of cross-border AC `s_nom` in the TD30 networks were copies. NorNed was in `base.nc` three times.
  - `simplify_links` gave a merged HVDC chain the sum of `p_nom` over all its links instead of the minimum over its segments. Cross-border HVDC was 109.5 GW after simplification against 34.8 GW in `base.nc` (NL-NO 6.2 GW; NorNed is 0.7 GW).
  - The networks were the same in all five scenarios, so the scenario comparisons were not driven by this, but the extra interconnection probably understated the value of storage.
- Fix, commit `e2d4614` in `pypsa-earth/scripts/simplify_network.py` (Carlo's go-ahead, 12 Oct):
  - `drop_duplicate_branches`, before simplification: branches with the same parameters between the same buses whose geometries match up to floating-point noise but are not byte-identical (copies from different extracts differ in the last digits; circuits split from one OSM way are identical and are kept). On the local networks it drops 477 of the 494 copied lines (529 of 539 GVA) and all 40 copied HVDC links, with one wrong hit (Klobuck-Rebielice, 110 kV, 123 MVA). Clustering is unchanged.
  - Merged HVDC chains: parallel sum within each segment, minimum over segments, as PyPSA-Eur does.
  - Expected after the fix: cross-border AC about 410 GVA, cross-border HVDC 14.7 GW. Individual links come out at 0.4-1.1 times their real ratings, because PyPSA-Earth rates every HVDC way at `v_nom` x 1.638 kA, and North Sea Link, BritNed and Nemo are missing from the network.
  - The "0.0" frequency tag on some DC cables changes `num_parallel` only: `base_network` sets HVDC `p_nom` from voltage and current. No capacity effect.
- Upstream: the proper fixes are on local branches of the fork clone `~/programming/pypsa_models/pypsa-earth`, based on upstream main `54784b7e`: `fix/drop-duplicate-osm-elements` (`c35bd4ce`, drops repeats by OSM type and id in `clean_osm_data`) and `fix/simplify-links-dc-capacity` (`bcdaef28`). `fix/phs-max-hours-nan` is rebased onto `54784b7e` (`b08b9bc0`). Four issues and three PRs are drafted; nothing is posted until Carlo approves the texts. No issue or PR exists upstream; PR #1694 proposed the HVDC fix but was closed the same day with unrelated changes.
- Malta correction: the Malta-Sicily cable is in OSM and in every run (line `IT0 5`-`MT0 0`). OSM lacks the 132 kV link from Maghtab into the rest of Malta, so `MT35 0` (89 % of Malta's demand) is an island and sheds 1.31 TWh under the zero cap. Carlo decided to leave it (effect on system LCOE about 0.02-0.03 EUR/MWh).
- ARC (record in `/data/engs-df-green-ammonia/engs2523/_maintenance/2026-10-12/`):
  - The old `simplify_network.py` and the stale intermediates (`elec_s.nc`, `elec_s_140.nc`, `elec_s_140_ec.nc`, the prepared 1 h network) were moved to `_backups/2026-10-12/`. Moving only `elec_s.nc` is not enough: Snakemake does not rebuild a missing intermediate while its downstream outputs exist (dry-run 13468190 showed only prepare and solve). Dry-run 13468219 then showed simplify, cluster, add_extra_components, prepare and solve.
  - The six uncorrected TD30 results, including the 1 h run (job 13450571, finished 11 Oct after 14 h 57 min, not fetched), were moved to `results/europe-year-140/networks/_archive_td30_before_line_fix_2026_10_12/`.
  - Submitted as an `afterany` chain on arc: 13468229 co2-zero-td30, 13468230 co2-zero-h2-td30, 13468231 co2-zero-nh3-td30, 13468232 co2-price-nh3-td30, 13468233 co2-zero-nh3-td30-cheapbatt, then 13468234 co2-zero-nh3-td30-1h (medium, 320 GB, 36 h).
- When the chain ends: move the local TD30 results to `results/europe-year-140/networks/_archive_td30_before_line_fix_2026_10_12/`, fetch the new ones, run `notebooks/paper_metrics.py TD30` and `notebooks/paper_facts.py`, regenerate the figures with `notebooks/paper_figures.py`, and update the paper.

### Corrected TD30 results, 14 October 2026

- All six jobs completed (12-13 Oct): the 3 h runs in 1-2.7 h each, all optimal; the 1 h run in 10 h 28 min at about 270 GB peak, ending "suboptimal" with primal and dual objectives 0.07 % apart. `simplify_network` dropped 477 lines (529.7 GVA) and 40 HVDC links (23.2 GW), as in the local test.
- Fetching the networks ran at about 50 KB/s, so the analysis ran on ARC in `/data/engs-df-green-ammonia/engs2523/pypsa-earth-green-auklet/_analysis/2026-10-14/` (scripts copied there, `results` linked to the run's results). Outputs copied to `results/europe-year-140/`: `paper_metrics_TD30.csv`, `td30_extra_checks.csv` (old and new, 3 h and 1 h) and `td30_interconnection.csv`. The networks themselves stay on ARC.

| | Base | Hydrogen | Ammonia | Carbon price | Cheap batteries |
|---|---|---|---|---|---|
| System LCOE (EUR/MWh) | 71.81 | 71.34 | 68.03 | 64.56 | 64.40 |
| Stores built excl. hydro (TWh) | 1.43 | 3.45 | 30.52 | 0.19 | 26.28 |
| Battery: TWh delivered, cycles/yr | 223, 163 | 155, 250 | 187, 326 | 40, 335 | 389, 124 |
| NH3: TWh delivered, cycles/yr | - | - | 24.7, 1.5 | 0.05, 0.9 | 14.7, 1.1 |
| H2: TWh delivered, cycles/yr | - | 13.2, 8.0 | 0.22, 65 | 0.01, 36 | 0.01, 26 |

- Cross-border capacity: existing 399 GVA AC and 14.7 GW HVDC (was 709 and 109.5); optimised in the Ammonia scenario 632 GVA and 82 GW (was 847 and 126).
- Carbon price: gas 118 TWh, 42 Mt CO2, payments 0.70 EUR/MWh. Hydro reservoirs fall by 52-56 TWh to mid-April under the zero cap. No new nuclear.
- 1 h against 3 h (Ammonia scenario): system LCOE +0.46 %, battery energy +4.67 %, NH3 store +1.64 %, electricity from ammonia +3.73 %; same carriers and roles.
- The paper uses these results (green-caribou-paper commit `a39385b`).

### Upstream issues posted, 14 October 2026

- Posted [pypsa-meets-earth/pypsa-earth#2072](https://github.com/pypsa-meets-earth/pypsa-earth/issues/2072) (cross-border lines, cables and HVDC links counted once per country extract) and [#2073](https://github.com/pypsa-meets-earth/pypsa-earth/issues/2073) (merged HVDC links get the summed capacity of their sections). The fixes are open as [#2076](https://github.com/pypsa-meets-earth/pypsa-earth/pull/2076) (from `fix/drop-duplicate-osm-elements`, closes #2072) and [#2077](https://github.com/pypsa-meets-earth/pypsa-earth/pull/2077) (from `fix/simplify-links-dc-capacity`, closes #2073), pushed to the fork `cpalazzi/pypsa-earth`.
- Also posted [#2074](https://github.com/pypsa-meets-earth/pypsa-earth/issues/2074) (pumped hydro with NaN `max_hours` gets no storage) and [#2075](https://github.com/pypsa-meets-earth/pypsa-earth/issues/2075) (`hydro_capacities.csv` only covers African countries). Both point to the open PR #1707 (davide-f, since January 2026, awaiting review), which already makes both changes as part of a revision of hydro inflows, with PyPSA-Eur's rows for 30 European countries. The PR from `fix/phs-max-hours-nan` waits for the developers' answer on #2074.

### technology-data Haber-Bosch cost, 29 October 2026

- technology-data v0.13.2 gives `Haber-Bosch` 1460.0 EUR/kW_NH3 (`currency_year` 2015), the investment `build_costs_td2030.py` copies to `ammonia synthesis`. It is DEA sheet 5.4's 2030 value for the 100 MW plant, 1379.7 EUR/kW, which is already in 2020 EUR (DEA's August 2023 update), inflated again by HICP 2015-2020 (x1.0582); the VOM shows the same (0.0225 = 0.02127 x 1.0582). PyPSA-Earth's `load_costs` takes every row as EUR2020 and converts only currencies. The other rows the ammonia extension uses are converted correctly: CCGT 878 = DEA's 2015 value 830 x 1.0582; the NH3 pipeline from DEA (0.2127 EUR/MW/m, one update); the H2 tank and compressor from Stoeckl (2020); the DEA electrolysis override (2020).
- Effect (ARC job 13570574, `_analysis/2026-10-29/haber_bosch_check.py`): synthesis is 6.2 GW of ammonia output in the zero-cap ammonia run and costs 1.00 bn EUR a year; the correct value would save 0.055 bn EUR a year at fixed design, 0.015 EUR/MWh or 0.02 % of system LCOE. No rerun; a technology-data issue could be drafted for Carlo's approval.
