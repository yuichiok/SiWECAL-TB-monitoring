#!/usr/bin/env python3
import argparse
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
        self.times = {}

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
            self.times[plugin_level] = self.times.get(plugin_level, {})
            for name, plugin_path in plugins_per_level.items():
                start_time = time.time()
                self.logger.debug(
                    f"🎄Decorate {name} (per-{plugin_level}) "
                    f"on {os.path.basename(self.input_file)} "
                    f"({plugin_path} on {self.input_file})."
                )
                self.shoot_by_name(plugin_path)
                plugin_time = time.time() - start_time
                plugin_time += self.times[plugin_level].get(name, 0)
                self.times[plugin_level][name] = plugin_time

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Take a monitoring snapshot.",
    )
    parser.add_argument("input_file")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    mps = MonitoringPlugins(args.input_file, verbose=args.verbose)
    mps.shoot()
    if args.verbose:
        print("Execution time per plugin")
        for ex_time, plugin_type, name in sorted(
            (t, p, n) for p, nt in mps.times.items() for n, t in nt.items()
        ):
            print(f"{ex_time:6.2f}s: {name} (per {plugin_type})")
