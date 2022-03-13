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

dat_header = """
=== DATA FILE SAVED WITH ILC SL-SOFTWARE VERSION: V4.9  == DATE OF RUN: UnixTime = 1636547317.233 date = 2021.11.10 time = 13h.28m.37s.233ms  ===
=== SL_COREMODULE_INTERFACE SerNum 2.43A FPGA Version V2.1.13 == NB OF CORE DAUGHTERS: 1 ===
====== CORE DAUGHTER 0 == FPGA Version V1.3.1 == NB OF CONNECTED SLABs 15 ======
{DAT_SLAB_LINES}
=== DATA STRUCTURE INFO : DECODED FRAMES ===
====== SkirocEventNumber (# int) NbOfSingleSkirocEvents('Size' int) ChipID (unsigned char) CoreDaughterIndex (signed char) SlabIndex (signed char) SlabAdd (signed char) AsuIndex(unsigned char) SkirocIndex (unsigned char) TransmitID (unsigned int) CycleID (unsigned int) StartAcqTimeStamp (unsigned int) rawTSD (unsigned int) rawAVDD0 (unsigned int) rawAVDD1 (unsigned int) tsdValue (Temperature in �C float) avDD0 ('AVDD at Start Acq in Volts' float) aVDD1 ('AVDD at End Acq in Volts' float) ======
========== SingleSkirocEventNumber (## int) SkirocID ('ChipID' unsigned char) BunchCrossingID ('BCID' unsigned short) SCAColumnIndex ('SCA' unsigned char) NbOfHitsInEvent ('#Hits' int) ==========
============ Channel (unsigned char) LowValue (unsigned short) LowHitFlag (unsigned char) LowGainFlag (unsigned char) HighValue (unsigned short) HighHitFlag (unsigned char) HighGainFlag (unsigned char) ============
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


def _channel_lines(channels=[3], dims=PrototypeDimensions):
    lines = []
    lines.extend([f"Ch {i} LG 250 0 0 HG 250 0 0" for i in range(dims["n_channel"])])
    for ch in channels:
        sig = random.gauss(200, 40)
        lines[ch] = lines[ch].replace(
            "LG 250 0", "LG " + str(int(250 + sig / 10)) + " 1"
        )
        lines[ch] = lines[ch].replace("HG 250 0", "HG " + str(int(250 + sig)) + " 1")
    return lines


def _next_bcid(bcid):
    return bcid + int(random.random() * 8 * (1 + 100 * (random.random() < 0.95)))


def _chip_lines(signals={2587: 3}, n_sca=1, bcid=0, dims=PrototypeDimensions):
    lines = []
    bcid_chan = {}
    for i in range(n_sca):
        new_bcid = _next_bcid(bcid)
        rand_chan = random.randint(0, dims["n_channel"] - 1)
        channels = bcid_chan.get(new_bcid, [])
        channels.append(rand_chan)
        bcid_chan[new_bcid] = channels
    for sig_bcid, sig_channel in signals.items():
        channels = bcid_chan.get(sig_bcid, [])
        channels.append(sig_channel)
        bcid_chan[sig_bcid] = channels
    if len(bcid_chan) > dims["n_sca"]:
        for overflow in sorted(bcid_chan)[::-1]:
            bcid_chan.pop(overflow)
    for i, bcid in enumerate(sorted(bcid_chan)):
        sca = len(bcid_chan) - i - 1
        channels = bcid_chan[bcid]
        lines.append(f"##{i} BCID {bcid % 4096} SCA {sca} #Hits 1")
        lines.extend(_channel_lines(channels, dims))
    return lines, len(bcid_chan)


def _random_nsca_filled():
    """I do not claim that this is accurate/close to true rates.

    I found that this distribution createdsrather interesting buildfiles.
    Note: The mean is 4 (0.5 * 8). This is _much_ higher than what we obtain in reality.
    - ~5% of chips will have > 15 SCA fill attempts.
    - 38% <0 2 -> the chip readouts recorded a single filled SCA.
    >>> import scipy.stats as stats
    >>> stats.gamma.cdf([2, 16], a=0.5, scale=8)
    """
    return max(1, int(random.gammavariate(0.5, 8)))


def dat(
    file_path, i_shift=0, dims=PrototypeDimensions, n_dat_entries=10000, cycle_id=0
):
    chip_header = (
        "#{i} Size {size} ChipID {chip} coreIdx 0 slabIdx {slab} slabAdd {slab} "
        "Asu 0 SkirocIndex {chip} transmitID 0 cycleID {cycle_id} "
        "StartTime 54578 rawTSD 3692 rawAVDD0 2039 rawAVDD1 2039 tsdValue 33.02 "
        "avDD0 1.993 aVDD1 1.993"
    )
    dat_slab_lines = "\n".join(
        map(
            (
                "========= DAUGHTER 0 == SLAB {0} == SL BOARD ADD {0} "
                "== FPGA Version V2.4.1 == NB OF CONNECTED ASUs 1 ========="
            ).format,
            range(dims["n_slab"]),
        )
    )
    lines = dat_header.format(DAT_SLAB_LINES=dat_slab_lines).split("\n")[1:-1]
    bcid = 0
    mip_signal_channel = 22
    kw = {}
    kw["cycle_id"] = cycle_id + 1
    kw["i"] = i_shift * n_dat_entries
    i_end = (i_shift + 1) * n_dat_entries
    chips_to_write = {}
    while kw["i"] < i_end:
        bcid = _next_bcid(bcid)
        is_mip_signal = random.random() < 0.005
        if is_mip_signal:
            kw["chip"] = 0
            signals = {bcid: mip_signal_channel}
            for slab in range(dims["n_slab"]):
                n_sca = _random_nsca_filled()
                n_sca += len(signals)
                kw["slab"] = slab
                chip_lines, n_sca_filled = _chip_lines(signals, n_sca, bcid, dims)
                kw["size"] = n_sca_filled
                chip_id = (kw["slab"], kw["chip"])
                chips_to_write[chip_id] = [chip_header.format(**kw)] + chip_lines
                kw["i"] = kw["i"] + 1
            kw["cycle_id"] = kw["cycle_id"] + 1
            for chip_lines in chips_to_write.values():
                lines.extend(chip_lines)
            chips_to_write = {}
        else:
            n_sca = _random_nsca_filled()
            kw["chip"] = random.randint(0, dims["n_chip"] - 1)
            kw["slab"] = random.randint(0, dims["n_slab"] - 1)
            chip_id = (kw["slab"], kw["chip"])
            if chip_id not in chips_to_write:
                chip_lines, n_sca_filled = _chip_lines({}, n_sca, bcid, dims)
                kw["size"] = n_sca_filled
                chips_to_write[chip_id] = [chip_header.format(**kw)] + chip_lines
                kw["i"] = kw["i"] + 1
            if random.random() < 0.15:
                kw["cycle_id"] = kw["cycle_id"] + 1
                for chip_lines in chips_to_write.values():
                    lines.extend(chip_lines)
                chips_to_write = {}
    lines.append("")
    with open(os.path.join(file_path), "w") as f:
        f.write("\n".join(lines))
    return kw["cycle_id"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create dummy data and configuration for code testing.",
    )
    for dim, default_val in PrototypeDimensions.items():
        parser.add_argument("--" + dim, default=default_val, type=int)
    parser.add_argument("--config", action="store_true", help="Skip data creation.")
    parser.add_argument("--n_dat", default=40, type=int)
    help = "A real .dat_XXXX file has 10000 entries. "
    help += "Less entries but more files is better for testing the monitoring."
    parser.add_argument("--n_dat_entries", default=1000, type=int, help=help)
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
        cycle_id = 0
        for i_dat in range(args.n_dat):
            name = f"dummy_run_123456.dat_{i_dat:04}"
            cycle_id = dat(
                os.path.join(dummy_run_dir, name),
                i_dat,
                dims,
                args.n_dat_entries,
                cycle_id,
            )
