#!/usr/bin/env python3
import argparse
import os

import numpy as np

_string_length = "S100"


class TimingInfo:
    timer_fields = [
        ("job_type", _string_length),
        ("time", float),
        ("timestamp", _string_length),
        ("id", _string_length),
        ("worker", float),
        ("data_path", _string_length),
    ]

    def __init__(self, timing_file_or_folder=None):
        if timing_file_or_folder is None:
            timing_file_or_folder = self.get_default_timing_folder()
        self._timing_file_or_folder = timing_file_or_folder
        self.timing_files = self.get_timing_files(timing_file_or_folder)

    def get_default_timing_folder(self):
        dirname = os.path.dirname
        repo_root = dirname(dirname(dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(repo_root, "data")
        assert os.path.isdir(data_dir), data_dir
        all_runs_below_data = [os.path.join(data_dir, d) for d in os.listdir(data_dir)]
        assert len(all_runs_below_data)
        newest_run = max((os.path.getmtime(d), d) for d in all_runs_below_data)[1]
        return newest_run

    def get_timing_files(self, timing_file_or_folder):
        assert os.path.exists(timing_file_or_folder), timing_file_or_folder
        print(os.path.basename(timing_file_or_folder))
        if timing_file_or_folder.endswith(os.path.sep):
            timing_file_or_folder = timing_file_or_folder[:-1]
        if os.path.isfile(timing_file_or_folder):
            name = os.path.basename(timing_file_or_folder)
            if name.startswith("times_") and name.endswith(".csv"):
                return [timing_file_or_folder]
            else:
                return []
        elif os.path.basename(timing_file_or_folder) == ".times":
            timing_files = []
            for f in os.listdir(timing_file_or_folder):
                full_path_f = os.path.join(timing_file_or_folder, f)
                timing_files.extend(self.get_timing_files(full_path_f))
            return timing_files
        elif ".times" in os.listdir(timing_file_or_folder):
            return self.get_timing_files(os.path.join(timing_file_or_folder, ".times"))
        else:
            raise Exception(timing_file_or_folder)

    def file_info_string(self, file_path):
        lines = [f"- {os.path.basename(file_path)}: "]
        with open(file_path) as f:
            fields = f.readline()[:-1].split(",")
            timer_field_names = [fs[0] for fs in self.timer_fields]
            assert fields == timer_field_names, f"{fields} != {timer_field_names}"
            timers = np.loadtxt(f, delimiter=",", dtype=self.timer_fields)
        lines.append(
            "Jobs done in time window "
            f"{min(timers['timestamp']).decode('utf8')} - "
            f"{max(timers['timestamp']).decode('utf8')}."
        )
        for data_path in np.unique(timers["data_path"]):
            lines.append(f"Data from {data_path.decode('utf8')}.")
        lines.append(
            "job type            count     total    mean     std      max      "
            "min    parallel"
        )
        job_types = np.unique(timers["job_type"])
        table_lines = []
        for job_type in [b"all"] + list(job_types):
            if job_type == b"all":
                job_timers = np.copy(timers)
            else:
                job_timers = timers[timers["job_type"] == job_type]
            workers = job_timers["worker"]
            if np.all(workers >= 0):
                parallel = "YES"
            elif np.all(workers < 0):
                parallel = "NO"
            else:
                parallel = "MIX"
            if len(np.unique(job_timers["id"])) == 1:
                if job_timers["id"][0] != b"-1":
                    job_type += b" (" + job_timers["id"][0] + b")"

            t = job_timers["time"]
            table_lines.append(
                (
                    t.sum(),
                    f"{job_type.decode('utf8')[:20]:<20}{len(t):>5}  "
                    f"{t.sum():>8.2f}s{t.mean():>8.2f}s{t.std():>8.2f}s"
                    f"{t.max():>8.2f}s{t.min():>8.2f}s"
                    f"{parallel:>7}",
                )
            )
        lines.extend([line_string[1] for line_string in sorted(table_lines)[::-1]])
        return "\n".join(map(lambda x: 4 * " " + x, lines))[4:]

    def __str__(self):
        lines = [f"Timing info for {self._timing_file_or_folder}."]
        lines.append("\n\n".join(map(self.file_info_string, self.timing_files)))
        return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Read some monitoring timing information from times**.csv files.",
    )
    parser.add_argument(
        "-f",
        "--timing_file_or_folder",
        default=None,
        help=(
            "Timing file/folder that should be summarized. "
            "Defaults to using the last modified run folder under data/. "
        ),
    )
    args = parser.parse_args()
    print(TimingInfo(**vars(args)))
