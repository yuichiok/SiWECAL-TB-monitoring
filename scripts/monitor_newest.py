#!/usr/bin/env python3
import os
import subprocess
import time

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_sorter(run_name):
    return run_name.split("run_")[-1]


def main(raw_parent, output_parent):
    all_raw_runs = []
    for run_name in os.listdir(raw_parent):
        run_path = os.path.join(raw_parent, run_name)
        if os.path.isdir(run_path):
            all_raw_runs.append(run_path)
    assert len(all_raw_runs) > 0, raw_parent
    for run_path in sorted(all_raw_runs, key=run_sorter)[::-1]:
        try:
            int(run_path.split("run_")[-1])
        except ValueError:
            print(f"Not a valid run name. Skipping folder: {run_path}")
            continue
        output_dir = os.path.join(output_parent, os.path.basename(run_path))
        output_log = os.path.join(output_dir, "log_monitoring.log")
        is_finished = os.path.exists(os.path.join(output_dir, "full_run.root"))
        if not is_finished and os.path.exists(output_log):
            time_since_last_change = int(time.time() - os.path.getmtime(output_log))
            if time_since_last_change < 180:
                print(
                    f"❓Unfinished run detected: {output_dir} . "
                    f"But the last logging was only {time_since_last_change}s ago. "
                    "Maybe someone else is already working on it? "
                    "Skipping it, to be save."
                )
                continue
        subprocess.call(
            f"./start_monitoring_run.py {run_path}",
            cwd=repo_root,
            shell=True,
        )


if __name__ == "__main__":
    output_parent = os.path.join(repo_root, "data")
    raw_parent = os.path.join(repo_root, "raw")
    main(raw_parent, output_parent)
