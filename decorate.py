#!/usr/bin/env python3
import argparse
import collections
import datetime
import logging
import os
import subprocess
import time


def log_unexpected_error_subprocess(logger, subprocess_return, add_context=""):
    logger.error(subprocess_return)
    if subprocess_return.stderr is not None:
        logger.error("🎄Line-by-line stderr:\n" + subprocess_return.stderr.decode())
    logger.error(
        f"🎄💣Unexpected error{add_context}. "
        "Maybe the line above with return information "
        "from the subprocess can help to understand the issue?🙈"
    )
    raise Exception(subprocess_return)


def add_suffix_before_extension(path, suffix, extension=".root"):
    assert path.endswith(extension), path
    return (suffix + extension).join(path.rsplit(extension, 1))


Timer = collections.namedtuple(
    "Timer", ["job_type", "time", "timestamp", "id", "worker", "data_path"]
)


class MonitoringPlugins:
    _plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")

    def __init__(self, input_file, logger=None, verbose=False):
        self.input_file = os.path.abspath(input_file)
        if logger is None:
            self.logger = logging.getLogger(__file__)
            if verbose:
                self.logger.setLevel(logging.DEBUG)
        else:
            self.logger = logger
        self._plugins = None
        self.times = []

    def _validate_plugins(self, new_plugins=None):
        """Currently does nothing."""
        all_valid = True
        if new_plugins is None:
            new_plugins = self._plugins
        return all_valid

    @property
    def plugins(self):
        if self._plugins is None:
            self._plugins = {}
            for plugin_level in os.listdir(self._plugins_dir):
                folder = os.path.join(self._plugins_dir, plugin_level)
                assert os.path.isdir(folder), folder
                self._plugins[plugin_level] = {}
                for file_name in os.listdir(folder):
                    file_path = os.path.join(folder, file_name)
                    assert os.path.isfile(file_path)
                    name, ext = os.path.splitext(file_name)
                    assert name not in self._plugins[plugin_level], name
                    self._plugins[plugin_level][name] = file_path
            self._validate_plugins(self._plugins)
            self._plugins = {k: v for k, v in self._plugins.items() if len(v) > 0}
        return self._plugins

    @plugins.setter
    def plugins(self, value):
        self._validate_plugins(value)
        self._plugins = value

    def shoot(self, input_file=None):
        if input_file is not None:
            self.input_file = os.path.abspath(input_file)
        for plugin_level, plugins_per_level in self.plugins.items():
            for name, plugin_path in plugins_per_level.items():
                start_time = time.time()
                self.logger.debug(
                    f"🎄Decorate {name} (per-{plugin_level}) "
                    f"on {os.path.basename(self.input_file)} "
                    f"({plugin_path} on {self.input_file})."
                )
                self.shoot_by_name(plugin_path)
                self.times.append(
                    Timer(
                        job_type=name,
                        time=time.time() - start_time,
                        timestamp=datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S"),
                        id=plugin_level,
                        worker=-1,
                        data_path=self.input_file,
                    )
                )

    def shoot_by_name(self, plugin_path, input_file=None):
        if input_file is not None:
            self.input_file = os.path.abspath(input_file)

        implementation_type = os.path.splitext(plugin_path)[-1]
        if implementation_type == ".C":
            self._shoot_root(plugin_path, input_file)
        else:
            raise NotImplementedError(implementation_type)

    def _shoot_root(self, plugin_path, output_file=None):
        if output_file is None:
            name = os.path.splitext(os.path.basename(plugin_path))[0]
            macro_output = add_suffix_before_extension(
                self.input_file, "_" + name, ".root"
            )
        else:
            macro_output = output_file
        assert not os.path.exists(macro_output), macro_output
        macro = os.path.basename(plugin_path)
        root_call = f'"{macro}(\\"{self.input_file}\\", \\"{macro_output}\\")"'
        ret = subprocess.run(
            "root -b -l -q " + root_call,
            shell=True,
            capture_output=True,
            cwd=os.path.dirname(plugin_path),
        )
        if ret.returncode != 0 or ret.stderr != b"":
            log_unexpected_error_subprocess(self.logger, ret, f" during {plugin_path}")
        if output_file is None:
            ret = subprocess.run(
                f"rootmv {macro_output} {self.input_file}",
                shell=True,
                capture_output=True,
            )
            if ret.returncode != 0 or ret.stderr != b"":
                log_unexpected_error_subprocess(
                    self.logger, ret, f" during {plugin_path} rootmv"
                )

    def write_times(self, file_name=None):
        if file_name is None:
            times_dir = os.path.join(os.path.dirname(self.input_file), ".times")
            if not os.path.isdir(times_dir):
                os.mkdir(times_dir)
            file_name = f"times_{os.path.basename(os.path.abspath(__file__))}.csv"
            file_name = os.path.join(times_dir, file_name)
        lines = [",".join(self.times[0]._fields)]
        for t in self.times:
            lines.append(
                f"{t.job_type},{t.time:.3f},{t.timestamp}"
                f",{t.id},{t.worker},{t.data_path}"
            )
        if os.path.exists(file_name):
            with open(file_name) as f:
                read_lines = f.readlines()
                if len(read_lines) and (read_lines[0] == lines[0] + "\n"):
                    lines = lines[1:]
        with open(file_name, "a") as f:
            f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Take a monitoring snapshot.",
    )
    parser.add_argument("input_file")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--times_file", default=None)
    args = parser.parse_args()
    mps = MonitoringPlugins(args.input_file, verbose=args.verbose)
    mps.shoot()
    if args.times_file is not None:
        if not os.path.isdir(os.path.dirname(args.times_file)):
            os.mkdir(os.path.dirname(args.times_file))
        mps.write_times(args.times_file)
    if args.verbose:
        print("Execution time per plugin")
        for _, t in sorted((-t.time, t) for t in mps.times):
            print(f"{t.time:6.2f}s: {t.job_type} (per {t.id})")
