#!/usr/bin/env python
import argparse
import itertools
import os

PrototypeDimensions = {
    "n_slab": 15,
    "n_chip": 16,
    "n_channel": 64,
    "n_sca": 15,
}

example_dir = os.path.dirname(__file__)


def pedestal(file_path, dims=PrototypeDimensions):
    lines = []
    lines.append("#pedestal results (SiWECAL-TB-monitoring creat_dummy.py) : DUMMY15")
    pattern_name = (
        " ped{i} ped_error{i} noise_incoherent_ped{i} noise_coherent1_ped{i} "
        "noise_coherent2_ped{i}"
    )
    pattern_value = " 250 4 10 20 1"  # Just some dummy values.
    lines.append("#layer chip channel")
    for i in range(dims["n_sca"]):
        lines[-1] = lines[-1] + pattern_name.format(i=i)
    for i_pos in itertools.product(
        *map(range, [dims["n_slab"], dims["n_chip"], dims["n_channel"]])
    ):
        lines.append(" ".join(map(str, i_pos)) + dims["n_sca"] * pattern_value)
    with open(os.path.join(file_path), "w") as f:
        f.write("\n".join(lines))


def mip(file_path, dims=PrototypeDimensions):
    lines = []
    lines.append("#mip results DUMMY15")
    lines.append("#layer chip channel mpv empv widthmpv chi2ndf nentries")
    pattern_value = " 25 0.25 3 1.5 100"  # Just some dummy values.
    for i_pos in itertools.product(
        *map(range, [dims["n_slab"], dims["n_chip"], dims["n_channel"]])
    ):
        lines.append(" ".join(map(str, i_pos)) + pattern_value)
    with open(os.path.join(file_path), "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create dummy data and configuration for code testing.",
    )
    for dim, default_val in PrototypeDimensions.items():
        parser.add_argument("--" + dim, default=default_val, type=int)
    args = parser.parse_args()
    dims = {}
    for dim in PrototypeDimensions:
        dims[dim] = getattr(args, dim)

    dummy_calib_dir = os.path.join(example_dir, "dummy_calibration")
    if not os.path.exists(dummy_calib_dir):
        os.makedirs(dummy_calib_dir)
    pedestal(os.path.join(dummy_calib_dir, "Pedestal_dummy_highgain.txt"), dims)
    pedestal(os.path.join(dummy_calib_dir, "Pedestal_dummy_lowgain.txt"), dims)
    mip(os.path.join(dummy_calib_dir, "MIP_dummy_highgain.txt"), dims)
    mip(os.path.join(dummy_calib_dir, "MIP_dummy_lowgain.txt"), dims)
