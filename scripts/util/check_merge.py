#!/usr/bin/env python3
"""Check the merge.sh results.

Takes a folder. Check that the `*_merged.root` files exists for each subfolder.
Then, check that the merged file has roughly the combined size of the
`*converted_*.root files.
"""
import argparse
import os
import subprocess


class CheckMerge:
    def __init__(self, converted_folder):
        if not os.path.isdir(converted_folder):
            raise NotImplementedError(
                "converted_folder must be a folder: " + converted_folder
            )
        self.converted_parts_dirs = self.recurse_to_all_converted_dirs(converted_folder)
        assert len(self.converted_parts_dirs) > 0, converted_folder
        self.msg_lines = self.check_merged_converted(self.converted_parts_dirs)

    def __str__(self):
        if len(self.msg_lines) == 0:
            return "No missing merges detected."
        else:
            return "\n".join(self.msg_lines)

    def recurse_to_all_converted_dirs(self, path):
        converted_folders = []
        if os.path.isfile(path) and self._is_converted_file(path):
            converted_folders.append(os.path.dirname(path))
        if os.path.isdir(path):
            for item in os.listdir(path):
                f = os.path.join(path, item)
                converted_folders.extend(self.recurse_to_all_converted_dirs(f))
                if path in converted_folders:
                    break
        return converted_folders

    def check_merged_converted(self, converted_parts_dirs):
        msg_lines = []
        self._missing = []
        self._maybe_too_small = []
        self._too_small = []
        for converted_folder in converted_parts_dirs:
            merged_file = converted_folder + "_merged.root"
            if not os.path.isfile(merged_file):
                msg_lines.insert(0, "Missing merged file: " + str(merged_file))
                self._missing.insert(0, converted_folder)
                continue
            merged_size = os.path.getsize(merged_file)
            sub_dirs = (
                os.path.join(converted_folder, f) for f in os.listdir(converted_folder)
            )
            parts_size = sum(
                map(
                    self._per_part_contribution,
                    filter(self._is_converted_file, sub_dirs),
                )
            )
            if merged_size < parts_size:
                msg_lines.append(
                    "Merged file to small: {} ({:,} B, should be > {:,} B).".format(
                        merged_file, merged_size, parts_size
                    )
                )
                diff = (parts_size - merged_size) / merged_size
                if diff < 0.01:
                    _m = " Might be false alarm: Size difference < {:.3f}%.".format(
                        100 * diff
                    )
                    msg_lines[-1] = msg_lines[-1] + _m
                    self._maybe_too_small.append(converted_folder)
                else:
                    self.__too_small.append(converted_folder)
        return msg_lines

    def _is_converted_file(self, f):
        name = os.path.basename(f)
        name, ext = os.path.splitext(name)
        is_single_converted_file = os.path.isfile(f)
        is_single_converted_file &= ext == ".root"
        is_single_converted_file &= "converted_" in name
        is_single_converted_file &= not f.endswith("_merged.root")
        return is_single_converted_file

    def _per_part_contribution(self, f):
        """A few bytes are substracted for the rootfile header."""
        return os.path.getsize(f) - 30000

    def merge(self, converted_folder, merge_j=1, verbose=False):
        merged_path = converted_folder + "_merged.root"
        input_pattern = os.path.join(converted_folder, "*converted_*.root")
        if os.path.isfile(merged_path):
            os.remove(merged_path)
        subprocess.run(
            "hadd -j " + str(merge_j) + " " + merged_path + " " + input_pattern,
            shell=True,
            capture_output=not verbose,
        )
        print("(Re-)created " + merged_path + ".")


if __name__ == "__main__":
    dn = os.path.dirname
    data_dir = os.path.join(dn(dn(dn(os.path.abspath(__file__)))), "data")
    parser = argparse.ArgumentParser(
        description=(
            "Where converted files are found, "
            "check that the corresponding `_merged.root` exists."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-f",
        "--converted_folder",
        default=data_dir,
        help="Root folder below which to look for converted files.",
    )
    parser.add_argument("--merge_missing", action="store_true")
    parser.add_argument("--merge_redo", action="store_true")
    parser.add_argument("--merge_redo_strict", action="store_true")
    parser.add_argument("--merge_j", default=8, type=int, help="hadd -j")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    cm = CheckMerge(args.converted_folder)
    print(cm)
    runs_to_merge = []
    if args.merge_missing or args.merge_redo or args.merge_redo_strict:
        runs_to_merge.extend(cm._missing)
    if args.merge_redo or args.merge_redo_strict:
        runs_to_merge.extend(cm._too_small)
    if args.merge_redo_strict:
        runs_to_merge.extend(cm._maybe_too_small)
    if len(runs_to_merge) > 0:
        print("\n".join(["Runs that will be (re-)merged:"] + runs_to_merge))
    for run_converted_dir in runs_to_merge:
        cm.merge(run_converted_dir, args.merge_j, args.verbose)
