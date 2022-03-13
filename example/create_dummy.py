#!/usr/bin/env python
import argparse
import itertools
import os
import random

random.seed(202203)

PrototypeDimensions = {
    "n_slab": 15,
    "n_chip": 16,
    "n_channel": 64,
    "n_sca": 15,
}

example_dir = os.path.dirname(__file__)

run_settings_header = """
== SETTINGS FILE SAVED WITH ILC SL-SOFTWARE VERSION: V4.9  == DATE OF RUN: UnixTime = 1636547290.191 date = 2021.11.10 time = 13h.28m.10s  ===
== DESY_MOVING_TABLE: NOT_CONNECTED ==
== SYSTEM_TYPE: SL_COREMODULE_INTERFACE USB_SerNum: 2.43A FPGA_Version: V2.1.13  NB_Of_Core_Daughters: 1 EXT_CLOCK: 0 ( 1 = YES, 0= NO) ==
== TriggerType: 1  ('0' = FORCE_TRIGGER, '1' = SELF_TRIGGER) ACQWindowSource: 0 ('0' = AUTO, '1'= SOFT_CMD, '2' = EXT_SIG) ACQWindow: 1 (ms) DelayBetweenCycle: 10 (ms) DelayForStartAcq: 0 (5Mhz_Clock period) ExtSigLevel: 0 ('0' = TTL, '1' = NIM, '-1' = NA) ExtSigEdge: 0 ('0' = RISING_EDGE, '1' = FALLING_EDGE, '-1' = NA) ==
=== CORE_DAUGHTER: 0 FPGA_Version: V1.3.1 Nb_Of_Connected_Slabs: {N_SLABS} ===
"""  # noqa


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


def run_settings(file_path, dims=PrototypeDimensions):
    lines = run_settings_header.format(N_SLABS=dims["n_slab"]).split("\n")[1:-1]
    for i_slab in range(dims["n_slab"]):
        lines.append(
            (
                "===== Daughter: {i_slab} SlabIdx: {i_slab} SlabAdd: 0 "
                "SL_Board_SerNum: -1 FPGA_Version: V2.4.1  "
                "Nb_Of_Connected_ASUs: 1 ====="
            ).format(i_slab=i_slab)
        )
        lines.append("# ASU: 0")
        for i_chip in range(dims["n_chip"]):
            lines.append(
                (
                    "## ChipIndex: {i_chip} ChipId: {i_chip}  "
                    "FeedbackCap: 3 ThresholdDAC: 232 HoldDelay: 138 FSPeakTime: 2 "
                    "GainSelectionThreshold: 255 "
                ).format(i_chip=i_chip)
            )
            for i_channel in range(dims["n_channel"]):
                # Add/invent some mask channels for fun.
                is_masked = bool(
                    sum(
                        [
                            i_channel in [5, 37],
                            i_channel in [2, 39, 40, 41] and i_slab in [0, 2, 3, 9],
                            random.random() < 0.03,
                        ]
                    )
                )
                lines.append(
                    "### Ch: {i_ch} TrigMask: {is_m} ChThreshold: 0 PAMask: 0 ".format(
                        i_ch=i_channel, is_m=int(is_masked)
                    )
                )
    lines.append("")
    with open(os.path.join(file_path), "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create dummy data and configuration for code testing.",
    )
    for dim, default_val in PrototypeDimensions.items():
        parser.add_argument("--" + dim, default=default_val, type=int)
    parser.add_argument("--config", action="store_true", help="Skip data creation.")
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

    if args.config:
        exit()
    else:
        dummy_run_dir = os.path.join(example_dir, "dummy_run_123456")
        if not os.path.exists(dummy_run_dir):
            os.makedirs(dummy_run_dir)
        run_settings(os.path.join(dummy_run_dir, "Run_Settings.txt"), dims)
