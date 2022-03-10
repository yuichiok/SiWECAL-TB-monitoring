#!/usr/bin/env python3
import argparse
import logging
import os
import subprocess

logger = logging.getLogger(__file__)
plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")


def log_unexpected_error_subprocess(logger, subprocess_return, add_context=""):
    logger.error(subprocess_return)
    logger.error(
        f"💣Unexpected error{add_context}. "
        "Maybe the line above with return information "
        "from the subprocess can help to understand the issue?🙈"
    )


def add_suffix_before_extension(path, suffix, extension=".root"):
    assert path.endswith(extension), path
    return (suffix + extension).join(path.rsplit(extension, 1))


def run_hitMaps(input_file, output_file=None):
    input_file = os.path.abspath(input_file)
    if output_file is None:
        macro_output = add_suffix_before_extension(input_file, "_hitMaps", ".root")
    else:
        macro_output = output_file

    root_macro_dir = os.path.join(plugins_dir, "run")
    root_call = f'"hitMaps.C(\\"{input_file}\\", \\"{macro_output}\\")"'
    ret = subprocess.run(
        "root -b -l -q " + root_call,
        shell=True,
        capture_output=True,
        cwd=root_macro_dir,
    )
    if ret.returncode != 0 or ret.stderr != b"":
        log_unexpected_error_subprocess(logger, ret, " during run_hitMaps")
        raise Exception(ret)
    if output_file is None:
        ret = subprocess.run(
            f"rootmv {macro_output} {input_file}", shell=True, capture_output=True
        )
        if ret.returncode != 0 or ret.stderr != b"":
            log_unexpected_error_subprocess(logger, ret, " during run_hitMaps rootmv")
            raise Exception(ret)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Take a monitoring snapshot.",
    )
    parser.add_argument("input_file")
    parser.add_argument(
        "--output_file", default=None, help="If None, rootmv to input file."
    )
    run_hitMaps(**vars(parser.parse_args()))
