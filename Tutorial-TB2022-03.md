# Tutorial

Based on an [ELOG entry](https://llrelog.in2p3.fr/calice/2265) (protected) for TB2022-03 at DESY.

## Semi-online monitoring

Semi-online monitoring can be started as soon as you started a run in the DAQ system (windows computer).
Alternatively, you can perform the monitoring on a run that has already finished.

### Setup

#### Setup on the monitoring PC during test beam

The `monitoring` conda environment provides the runtime (ROOT, python packages).
It should be activated by default in a new shell.

```bash
conda activate monitoring  # Only necessary if it is not already active.
cd ~/SiWECAL-TB-monitoring
```

#### Setup on your own machine/lxplus

The monitoring script needs a fairly new version of python3, ROOT compiled with
python bindings for this executable and some further python packages.
You can create such an environment locally, e.g. through conda.
A simpler approach, and the one that I am following on lxplus, is leveraging the LCG views:

```bash
git clone git@github.com:SiWECAL-TestBeam/SiWECAL-TB-monitoring.git --recurse-submodules  --shallow-submodules
# On centos7. E.g. lxplus.
source /cvmfs/sft.cern.ch/lcg/views/LCG_101/x86_64-centos7-gcc11-opt/setup.sh
# Views also exist for other platforms.
source /cvmfs/sft.cern.ch/lcg/views/LCG_101/x86_64-ubuntu2004-gcc9-opt/setup.sh
```

The CI/CD tests run on the Ubuntu view ([workflow file](https://github.com/SiWECAL-TestBeam/SiWECAL-TB-monitoring/blob/c6dff5e6666656348326a543e6742542844aa47d/.github/workflows/tests-on-dummy-data.yml#L12)).
Thus using the `LCG_101` view protects you against software incompatibility issues.

#### Starting the monitoring

- Before running, check [monitoring.cfg](./monitoring.cfg):
  - Do the calibration file paths point to the correct (existing) locations?
  - Is the layer setup correct? E.g. change `asu_versions` after moving around layers.
- With `$RUN_NAME` I refer to the name that you gave to the run when starting it in the DAQ.
- `./start_monitoring_run.py raw/$RUN_NAME`
- `./scripts/monitor_newest.py` is a wrapper that should in principle pick up the new runs automatically.
- **Never delete any files under the raw directory.**
- Monitoring writes files to data directory. Deleting run folders there can be ok.
- The monitoring should keep you informed about its progress.
  - If there is an error, you might be able to fix it? Or report it?
    [SiWECAL-TB-monitoring GitHub issues](https://github.com/SiWECAL-TestBeam/SiWECAL-TB-monitoring/issues)
  - Apart from errors, you might be most interested in lines similar to this one:
    > 🔎A new monitoring snapshot is ready: 2022-03-23-145740.root at /home/calice/SiWECAL-TB-monitoring/data/3.2GeV_W_run_050208/snapshots/2022-03-23-145740.root
- Status checks can be performed already during a run:
  - `rootbrowse /home/calice/SiWECAL-TB-monitoring/data/3.2GeV_W_run_050208/snapshots/2022-03-23-145740.root`
- After a run finished, check `data/$RUN_NAME/full_run.root`

## Interesting checks on the snapshots (`rootbrowse`)

- Event rates (from `ecal` tree)
  - `nhit_slab`: Currently we say a good event has at least 12 slabs hit.
  - Check how many cycles you monitored already
    - For a finished run (full_run.root): Maximum value of the `cycle` (confirm that minimum is close to zero).
    - For an ongoing monitoring (snapshots/YYYY-MM-DD-HHMMSS.root):
      - Depending on which parts were processed so far, reading the number of cycles from its branch might be hard.
      - Alternatively, read from `event` branch: `#non-empty cycles = #events / (2 * mean(event)  + 1)* #id_dat)`
- Hit maps, etc.: Some convenience plots, like hit maps, are part of the snapshots.
- Event displays:
  - Not really that helpful during Tungsten runs, but nice to have during MIP runs.
  - `./scripts/event_display.py data/$RUN_NAME/current_build.root`
  - Can be run on any snapshots, or `current_build.root`, `full_run.root`, ...

## Advanced usage

- Request a monitoring snapshot before the next one that is scheduled.
  - `touch data/$RUN_NAME/get_snapshot`
  - If the `ecal` tree is enough (you are not interested in hit maps etc), it is not necessary to wait for a snapshot. The most up-to-date version of the event files will always be at `data/$RUN_NAME/current_run.root`.
- Flag that a run should never be monitored.
  - `touch data/$RUN_NAME/no_monitoring`
  - This way starting the monitoring script on this run will directly inform the next shifter that this run should not be monitored.
  - Useful if you know that a run is not useful (e.g. for test purposes only, no beam, accidentally started a short run, ...)
- Stop an ongoing monitoring run.
  - `touch data/$RUN_NAME/stop_monitoring`
  - This will try to do some wrapping up before it stops, to minimize the time loss when restarting the monitoring.
  - If you are impatient, `Ctrl C` should be ok.
  - When you (or the monitoring loop) stopped a monitoring, and you want to start it again: It might be necessary to `rm data/$RUN_NAME/stop_monitoring`.
