#!/usr/bin/env python3
import argparse
import collections
import concurrent.futures
import configparser
import datetime
import enum
import glob
import logging
import os
import queue
import shutil
import subprocess
import sys
import tarfile
import threading
import time

tb_analysis_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "continuous_event_building",
    "SiWECAL-TB-analysis",
)
assert os.path.isdir(tb_analysis_dir), tb_analysis_dir

file_paths = dict(
    run_settings="Run_Settings.txt",
    default_config="monitoring.cfg",
    log_file="log_monitoring.log",
    masked_channels="masked_channels.txt",
    current_build="current_build.root",
    tb_analysis_dir=tb_analysis_dir,
)
monitoring_subfolders = dict(
    tmp_dir="tmp",
    converted_dir="converted",
    build_dir="build",
    snapshot_dir="snapshots",
)
file_paths.update(**monitoring_subfolders)
my_paths = collections.namedtuple("Paths", file_paths.keys())(**file_paths)
get_root_str = (
    "source /cvmfs/sft.cern.ch/lcg/views/LCG_99/x86_64-centos7-gcc10-opt/setup.sh"
)


def as_tar(path):
    """If the file only exists in compressed form, return that compressed file."""
    tar_path = path + ".tar.gz"
    if not os.path.exists(path) and os.path.exists(tar_path):
        return tar_path
    return path


def without_tar(path):
    if path.endswith(".tar.gz"):
        path = path[: -len(".tar.gz")]
    return path


def get_now_string():
    return datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")


Timer = collections.namedtuple(
    "Timer", ["job_type", "time", "timestamp", "id", "worker", "data_path"]
)


class Priority(enum.IntEnum):
    """For job scheduling. Lowest value is executed first."""

    SNAP_SHOT = 1
    MERGE_EVENT_BUILDING = 2
    EVENT_BUILDING = 3
    CONVERSION = 4
    IDLE = 5


def priority_string(prios):
    chars = []
    for prio in prios:
        if prio is Priority.MERGE_EVENT_BUILDING:
            chars.append("🔗")
        elif prio is Priority.SNAP_SHOT:
            chars.append("🔎")
        elif prio is Priority.EVENT_BUILDING:
            chars.append("🔨")
        elif prio is Priority.CONVERSION:
            chars.append("🌱")
        elif prio is Priority.IDLE:
            chars.append("⌛")
        else:
            raise Exception(prio)
    return "".join(chars)


def create_directory_structure(run_output_dir):
    if not os.path.exists(run_output_dir):
        os.mkdir(run_output_dir)
    for subfolder in monitoring_subfolders.values():
        sub_path = os.path.join(run_output_dir, subfolder)
        if not os.path.exists(sub_path):
            os.mkdir(sub_path)


def cleanup_temporary(output_dir, logger):
    full_run_path = os.path.join(output_dir, "full_run.root")
    if os.path.exists(full_run_path):
        logger.warning(f"✅Run was already monitored. Check: {full_run_path}")
        sys.exit(0)
    no_monitoring = os.path.join(output_dir, "no_monitoring")
    if os.path.exists(no_monitoring):
        logger.warning(f"❌This run should not be monitored: {no_monitoring}")
        sys.exit(0)
    logger.warning(
        f"🧹The output directory {output_dir} already exists. "
        "This is ok and expected if you had already started (and aborted) "
        "a monitoring session for this run earlier. "
    )
    output_conf = os.path.join(
        output_dir, my_paths.log_file
    )  # my_paths.default_config)
    if not os.path.exists(output_conf):
        logger.error(
            "⛔Aborted. A previous run should have left behind "
            f"a logfile at {output_conf}. "
            "As no such file was found, it is assumed that you specified "
            "the wrong directory. "
            "To nevertheless use this output directory it suffices to"
            " create an empty file with this name."
        )
        sys.exit(1)

    # Move run-level files to a timestamped version, so they can be recreated.
    old_file_suffix = "_" + get_now_string()
    for existing_file in [
        my_paths.default_config,
        # my_paths.log,  # Comment this out for now: I prefer appending to the logfile.
        my_paths.masked_channels,
    ]:
        existing_file = os.path.join(output_dir, existing_file)
        if os.path.isfile(existing_file):
            os.rename(
                existing_file, old_file_suffix.join(os.path.splitext(existing_file))
            )

    tmp_dir = os.path.join(output_dir, my_paths.tmp_dir)
    if os.path.isdir(tmp_dir):
        for tmp_file in os.listdir(tmp_dir):
            os.remove(os.path.join(tmp_dir, tmp_file))


def configure_logging(logger, log_file=None):
    """TODO: Nicer formatting. Maybe different for console and file."""
    logger.setLevel(logging.DEBUG)
    # FORMAT = "%(asctime)s[%(levelname)-5.5s:%(name)s %(threadName)s] %(message)s"
    FORMAT = "[%(levelname)-5.5s%(threadName)s🕙%(asctime)s] %(message)s"
    fmt = logging.Formatter(FORMAT, datefmt="%H:%M:%S")
    threading.current_thread().name = "🧠  "

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt=fmt)
    logger.addHandler(console_handler)

    if log_file is not None:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(fmt=fmt)
        logger.addHandler(file_handler)

    time_now = get_now_string()
    logger.info(f"🛫Logging to file {log_file} started at {time_now}.")


def log_unexpected_error_subprocess(logger, subprocess_return, add_context=""):
    logger.error(subprocess_return)
    logger.error(
        f"💣Unexpected error{add_context}. "
        "Maybe the line above with return information "
        "from the subprocess can help to understand the issue?🙈"
    )


def guess_id_run(name, output_parent):
    """Ideally takes the number following `run_`. Else constructs a id_run."""
    # Best-case scenario: Find a number after the string `run_`.
    pos_run_prefix = name.lower().find("run_")
    if pos_run_prefix != -1:
        idx_start_number = pos_run_prefix + len("run_")
        if len(name) >= idx_start_number and name[idx_start_number].isdigit():
            for idx_end_number in range(idx_start_number, len(name)):
                if not name[idx_end_number].isdigit():
                    break
            else:
                idx_end_number += 1
            return int(name[idx_start_number:idx_end_number])

    # Next try: find the longest (then largest) number-string of at least length 3.
    numbers = [""]
    for s in name:
        if s.isdigit():
            numbers[-1] = numbers[-1] + s
        elif numbers[-1] != "":
            numbers.append("")
    longest_number = max(map(len, numbers))
    if longest_number >= 3:
        longest_numbers = (n for n in numbers if len(n) == longest_number)
        return max(map(int, longest_numbers))

    # Last resort: Use the number of monitored runs as id_run.
    return sum(
        os.path.isdir(os.path.join(output_parent, d)) for d in os.listdir(output_parent)
    )


class EcalMonitoring:
    def __init__(self, raw_run_folder, config_file):
        setup_time = time.time()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.raw_run_folder = self._validate_raw_run_folder(raw_run_folder)
        self._validate_computing_environment()
        self._read_config(config_file)
        masking_time = time.time()
        self.times = {
            -1: [
                Timer(
                    job_type="SETUP",
                    time=masking_time - setup_time,
                    timestamp=get_now_string(),
                    id=-1,
                    worker=-1,
                    data_path=self.output_dir,
                )
            ]
        }
        self.masked_channels = self.create_masking()
        self.times[-1].append(
            Timer(
                job_type="MASKING",
                time=time.time() - masking_time,
                timestamp=get_now_string(),
                id=-1,
                worker=-1,
                data_path=self.output_dir,
            )
        )

    def _validate_raw_run_folder(self, raw_run_folder):
        # Removes potential trailing backslash.
        # Otherwise, os.path.basename == "" later on.
        raw_run_folder = os.path.realpath(raw_run_folder)
        assert os.path.isdir(raw_run_folder), raw_run_folder
        run_settings = as_tar(os.path.join(raw_run_folder, my_paths.run_settings))
        assert os.path.exists(run_settings), (
            run_settings + " must exist in the raw_run_folder."
        )
        return raw_run_folder

    def _validate_computing_environment(self):
        try:
            subprocess.run(["root", "--version"], capture_output=True)
        except FileNotFoundError:
            self.logger.error(
                "⛔Aborted. CERN root not available. "
                "💡Hint: try the environment at\n" + get_root_str
            )
            sys.exit(1)
        env_py_v = ""
        try:
            # This is not necessarily the python that runs this script, but
            # the one that will run the eventbuilding (and is linked with ROOT).
            ret = subprocess.run(["python", "--version"], capture_output=True)
            # Python2 writes version info to sys.stderr, Python3 to sys.stderr.
            env_py_v = ret.stdout + ret.stderr
            assert env_py_v.startswith(b"Python ") and env_py_v.endswith(
                b"\n"
            ), env_py_v
            py_v_list = list(map(int, env_py_v[len("Python ") : -1].split(b".")))
        except Exception as e:
            self.logger.error(f"env_py_v={env_py_v}")
            self.logger.exception(e)
            py_v_list = [2, 0, 0]
        if py_v_list[0] != 3:
            self.logger.warning(
                "🐌Using pyROOT with python2 for eventbuilding is not technically "
                f"forbidden, but discouraged for performance reasons: {env_py_v}. "
                "💡Hint: try the environment at\n" + get_root_str
            )

    def _read_config(self, config_file):
        if not os.path.isabs(config_file):
            folder = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(folder, config_file)
        assert os.path.isfile(config_file), config_file
        config = configparser.ConfigParser()

        def get_with_fallback(section, key, default):
            config.set(section, key, config[section].get(key, default))
            return config[section][key]

        config.read(config_file)
        output_parent = get_with_fallback("monitoring", "output_parent", "data")
        if not os.path.exists(output_parent):
            os.mkdir(output_parent)
        output_name = os.path.basename(self.raw_run_folder)
        output_name = get_with_fallback("monitoring", "output_name", output_name)
        self.output_dir = os.path.abspath(os.path.join(output_parent, output_name))
        if os.path.exists(self.output_dir) and len(os.listdir(self.output_dir)) > 0:
            cleanup_temporary(self.output_dir, self.logger)
        create_directory_structure(self.output_dir)
        configure_logging(self.logger, os.path.join(self.output_dir, my_paths.log_file))
        self.max_workers = int(get_with_fallback("monitoring", "max_workers", "10"))
        assert self.max_workers >= 1, self.max_workers
        self._skip_dirty_dat = config["monitoring"].getboolean("skip_dirty_dat", False)
        self._binary_split_M = config["monitoring"].getint("binary_split_M", -1)

        ev_building = config["eventbuilding"]

        def ensure_calibration_exists(calib):
            file = os.path.abspath(ev_building.get(calib))
            assert os.path.exists(file), file
            ev_building[calib] = file
            return file

        self.eventbuilding_args = dict()
        for calib in [
            "pedestals_file",
            "mip_calibration_file",
            "pedestals_lg_file",
            "mip_calibration_lg_file",
        ]:
            self.eventbuilding_args[calib] = ensure_calibration_exists(calib)
        self.eventbuilding_args["w_config"] = ev_building.getint("w_config")
        self.eventbuilding_args["min_slabs_hit"] = ev_building.getint("min_slabs_hit")
        if ev_building.getboolean("no_zero_suppress"):
            self.eventbuilding_args["no_zero_suppress"] = ""
        self.eventbuilding_args["asu_version"] = ev_building["asu_version"]
        if "id_run" not in ev_building:
            ev_building["id_run"] = str(guess_id_run(output_name, output_parent))
        self.eventbuilding_args["id_run"] = ev_building.getint("id_run")

        _s_after = config["snapshot"].get("after", "")
        try:
            self._snapshot_after = list(int(_s_after))
        except ValueError:
            self._snapshot_after = list(map(int, filter(len, _s_after.split(","))))
        if "every" in config["snapshot"]:
            self._snapshot_every = config["snapshot"].getint("every")
        else:
            self._snapshot_every = 10000
        self._delete_previous_snaphots = config["snapshot"].getboolean(
            "delete_previous", False
        )

        with open(os.path.join(self.output_dir, my_paths.default_config), "w") as f:
            config.write(f)
        return config

    def create_masking(self):
        tmp_run_settings = os.path.join(self.output_dir, my_paths.run_settings)
        run_settings = as_tar(os.path.join(self.raw_run_folder, my_paths.run_settings))
        if run_settings.endswith(".tar.gz"):
            with tarfile.open(run_settings) as tar:
                tar.extractall(path=self.output_dir)
            assert os.path.exists(tmp_run_settings)
        else:
            shutil.copy(
                os.path.join(self.raw_run_folder, my_paths.run_settings),
                tmp_run_settings,
            )
        tmp_rs_name = os.path.splitext(tmp_run_settings)[0]
        root_macro_dir = os.path.join(my_paths.tb_analysis_dir, "SLBcommissioning")
        root_call = f'"test_read_masked_channels_summary.C(\\"{tmp_rs_name}\\")"'
        ret = subprocess.run(
            "root -b -l -q " + root_call,
            shell=True,
            capture_output=True,
            cwd=root_macro_dir,
        )
        output_lines = ret.stdout.split(b"\n")
        # Reading error as indicated by the root macro's output.
        root_macro_issue_stdout = b" dameyo - damedame"
        settings_file_not_read = output_lines[2] == root_macro_issue_stdout
        if ret.returncode != 0 or settings_file_not_read:
            log_unexpected_error_subprocess(self.logger, ret, " during create_masking")
            sys.exit(1)
        assert not any(
            [line == root_macro_issue_stdout for line in output_lines]
        ), "This condition should be unreachable."
        masked_channels = os.path.join(self.output_dir, my_paths.masked_channels)
        os.rename(
            os.path.join(self.output_dir, tmp_rs_name + "_masked.txt"),
            masked_channels,
        )
        os.remove(tmp_run_settings)
        self.logger.debug(f"👏Channel masks written to {masked_channels}.")
        self.eventbuilding_args["masked_file"] = masked_channels
        return masked_channels

    def start_loop(self):
        start_loop_time = time.time()
        self._largest_raw_dat = 0
        self._last_n_monitored = 0
        self._snapshot_needs_current_build = False
        self._run_finished = False
        self._time_last_raw_check = 0
        self._time_last_snapshot = time.time()
        self._time_last_job = time.time()
        self._current_jobs = [Priority.IDLE for _ in range(self.max_workers)]
        queues = {}
        queues["job"] = queue.PriorityQueue()
        current_build = os.path.join(self.output_dir, my_paths.current_build)
        queues["current_build"] = queue.Queue(maxsize=1)
        queues["current_build"].put(current_build)
        queues["merge"] = queue.LifoQueue()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for i in range(self.max_workers):
                job_args = [queues, i]
                futures.append(executor.submit(self.find_and_do_job, *job_args))
                time.sleep(1)  # Head start for the startup bookkeeping.
            self._debug_future_returns(futures, queues)
        wrap_up_time = time.time()
        self.times[-1].append(
            Timer(
                job_type="LOOP",
                time=wrap_up_time - start_loop_time,
                timestamp=get_now_string(),
                id=-1,
                worker=-1,
                data_path=self.output_dir,
            )
        )
        self._wrap_up(queues)
        self.logger.info(
            "🛬The run has finished. The monitoring has treated all files. "
        )
        self.times[-1].append(
            Timer(
                job_type="WRAP_UP",
                time=time.time() - wrap_up_time,
                timestamp=get_now_string(),
                id=-1,
                worker=-1,
                data_path=self.output_dir,
            )
        )

    def _debug_future_returns(self, futures, queues):
        """Check the futures for issues. Added for debugging; should be fast."""
        done, not_done = concurrent.futures.wait(
            futures,
            return_when=concurrent.futures.FIRST_EXCEPTION,
        )
        self.logger.info(
            "💡If this script does not finish soon, there is an unexpected error. "
        )
        if len(not_done) != 0:
            self.logger.warning(
                f"🔥🚒 A worker threw an exception. "
                f"{len(not_done)}/{len(futures)} jobs were still ongoing. "
                "They are shut down now so that you can investigate the problem."
            )
            open(os.path.join(self.output_dir, "stop_monitoring"), "w").close()
            done, not_done = concurrent.futures.wait(
                futures,
                return_when=concurrent.futures.ALL_COMPLETED,
            )
        had_exception = False
        for p in done:
            if p.exception() is not None:
                had_exception = True
                self.logger.error(
                    f"At least one worker raised an exception: {p.exception()}."
                )
                try:
                    p.result()
                except Exception as e:
                    self.logger.exception(e)
                    sys.exit(1)
            else:
                if p.result() is not None:
                    self.logger.error(f"p.result()={p.result()}")
                    raise NotImplementedError
        if not had_exception and not hasattr(self, "_stopped_gracefully"):
            queues["job"].join()
        assert queues["current_build"].qsize() == 1, queues["current_build"].queue
        dir_converted = os.path.join(self.output_dir, my_paths.converted_dir)
        dir_build = os.path.join(self.output_dir, my_paths.build_dir)
        n_converted = len(os.listdir(dir_converted))
        n_build = len(os.listdir(dir_build))
        assert n_converted == n_build, f"{n_converted} != {n_build}"

    def find_and_do_job(self, queues, i_worker=0):
        self.times[i_worker] = []
        threading.current_thread().name = f"👷{i_worker:02}"
        job_queue = queues["job"]
        total_time_look_for_jobs = 0
        total_time_idle = 0
        while True:
            time_look_for_jobs = time.time()
            self._look_for_snapshot_request(job_queue)
            # The try is not technically thread safe, but good enough here.
            try:
                assert job_queue.queue[0][0] < Priority.CONVERSION
            except (IndexError, AssertionError):
                self._look_for_new_raw(job_queue)

            all_done = self._run_finished and job_queue.empty()
            file_stop_gracefully = os.path.join(self.output_dir, "stop_monitoring")
            if all_done or os.path.exists(file_stop_gracefully):
                if not all_done:
                    if not hasattr(self, "_stopped_gracefully"):
                        self._stopped_gracefully = True
                        self.logger.info(
                            "🤝Graceful stopping granted before end of monitoring. "
                            f"This was requested by {file_stop_gracefully}."
                        )
                self.times[i_worker].append(
                    Timer(
                        job_type="LOOK_FOR_JOB",
                        time=total_time_look_for_jobs,
                        timestamp=get_now_string(),
                        id=-1,
                        worker=i_worker,
                        data_path=self.output_dir,
                    )
                )
                self.times[i_worker].append(
                    Timer(
                        job_type=Priority.IDLE.name,
                        time=total_time_idle,
                        timestamp=get_now_string(),
                        id=-1,
                        worker=i_worker,
                        data_path=self.output_dir,
                    )
                )
                return
            try:
                priority, neg_id_dat, in_file = job_queue.get(timeout=2)
            except queue.Empty:
                self._current_jobs[i_worker] = Priority.IDLE
                continue
            time_do_job = time.time()
            total_time_look_for_jobs += time_do_job - time_look_for_jobs

            self._current_jobs[i_worker] = priority
            print(priority_string(self._current_jobs), end="\r")
            if priority == Priority.CONVERSION:
                res_file = self.convert_to_root(in_file, job_queue)
                if res_file:
                    job_queue.put((Priority.EVENT_BUILDING, neg_id_dat, res_file))
            elif priority == Priority.EVENT_BUILDING:
                res_file = self.run_eventbuilding(in_file, -neg_id_dat)
                if res_file:
                    job_queue.put((Priority.MERGE_EVENT_BUILDING, 0, "not used"))
                    queues["merge"].put(res_file)
            elif priority == Priority.MERGE_EVENT_BUILDING:
                try:
                    self.merge_eventbuilding(queues)
                    self._look_for_snapshot_request(job_queue, check_scheduled=True)
                    res_file = True
                except queue.Empty:
                    # Purpose of this loop: Have only one worker at a time
                    # waiting for the chance to merge build files.
                    for i in range(len(self._current_jobs)):
                        if i == i_worker:
                            continue
                        elif self._current_jobs[i] == Priority.MERGE_EVENT_BUILDING:
                            break
                    else:
                        job_queue.put((Priority.MERGE_EVENT_BUILDING, 0, "not used"))
                    res_file = False
            elif priority == Priority.SNAP_SHOT:
                res_file = self.get_snapshot(queues["current_build"])
            else:
                raise NotImplementedError(priority)
            job_queue.task_done()
            self._time_last_job = time.time()
            if res_file:
                self.times[i_worker].append(
                    Timer(
                        job_type=priority.name,
                        time=self._time_last_job - time_do_job,
                        timestamp=get_now_string(),
                        id=-neg_id_dat,
                        worker=i_worker,
                        data_path=self.output_dir,
                    )
                )
            else:
                total_time_idle += self._time_last_job - time_do_job

    def _look_for_new_raw(self, job_queue):
        if self._run_finished:
            return
        delta_t_daq_output_checks = 2  # in seconds.
        if time.time() - self._time_last_raw_check < delta_t_daq_output_checks:
            if job_queue.empty():
                time.sleep(delta_t_daq_output_checks)
            return
        self._time_last_raw_check = time.time()
        dat_pattern = os.path.join(self.raw_run_folder, "*.dat_[0-9][0-9][0-9][0-9]")
        dat_files = sorted(glob.glob(dat_pattern))
        if len(dat_files) == 0:
            dat_from_tar = glob.glob(dat_pattern + ".tar.gz")
            dat_files.extend(sorted(map(without_tar, dat_from_tar)))
        if len(dat_files) != 0:
            path_start = dat_files[-1][:-4]
            new_largest_dat = int(dat_files[-1][-4:])
            for i in range(self._largest_raw_dat, new_largest_dat):
                path = path_start + f"{i:04}"
                if os.path.exists(as_tar(path)):
                    job_queue.put((Priority.CONVERSION, -i, path))
            self._largest_raw_dat = new_largest_dat
            self._special_case_0000(job_queue, ".dat")
        file_run_finished = as_tar(
            os.path.join(self.raw_run_folder, "hitsHistogram.txt")
        )
        self._run_finished = os.path.exists(file_run_finished)
        self._check_for_binary(dat_files, job_queue)
        if self._run_finished:
            if len(dat_files) > 0:
                job_queue.put((Priority.CONVERSION, -new_largest_dat, dat_files[-1]))
            else:
                self._special_case_0000(job_queue, ".dat")
                self._special_case_0000(job_queue, "_raw.bin")
            self.logger.info(
                "🏃The run has finished. " "Monitoring will try to catch up now."
            )
        self._alert_is_idle(file_run_finished)

    def _check_for_binary(self, dat_files, job_queue):
        bin_ext = "_raw.bin"
        bin_pattern = "*" + bin_ext + "*_[0-9][0-9][0-9][0-9]"
        bin_pattern = os.path.join(self.raw_run_folder, bin_pattern)
        binary_parts = sorted(glob.glob(bin_pattern))
        if len(binary_parts) == 0:
            binary_from_tar = glob.glob(bin_pattern + ".tar.gz")
            binary_parts.extend(sorted(map(without_tar, binary_from_tar)))
        if len(dat_files) > 0 and len(binary_parts) > 0:
            self.logger.error(
                "⛔ Cannnot have both ascii data and raw_bin data in same run! "
                f"{dat_files} {binary_parts}"
            )
        if len(binary_parts) > 0:
            path_start = binary_parts[-1][:-4]
            new_largest_dat = int(binary_parts[-1][-4:])
            for i in range(self._largest_raw_dat, new_largest_dat):
                path = path_start + f"{i:04}"
                if os.path.exists(as_tar(path)):
                    job_queue.put((Priority.CONVERSION, -i, path))
            self._largest_raw_dat = new_largest_dat
            self._special_case_0000(job_queue, bin_ext)

    def _special_case_0000(self, job_queue, pattern=".dat"):
        if hasattr(self, "_already_done_0000"):
            return False
        first_dat_pattern = os.path.join(self.raw_run_folder, "*" + pattern)
        first_dat_glob = list(glob.glob(first_dat_pattern))
        if len(first_dat_glob) == 0:
            return False
        elif len(first_dat_glob) == 1:
            raw_file_path = first_dat_glob[0]
            raw_file_name = os.path.basename(raw_file_path)
            converted_name = "converted_" + raw_file_name + "_0000.root"
            converted_dir = os.path.join(self.output_dir, my_paths.converted_dir)
            tmp_dir = os.path.join(self.output_dir, my_paths.tmp_dir)
            if os.path.exists(os.path.join(converted_dir, converted_name)):
                return False
            if os.path.exists(os.path.join(tmp_dir, converted_name)):
                return False
            elif os.path.exists(as_tar(raw_file_path)):
                self._already_done_0000 = True
                job_queue.put((Priority.CONVERSION, 0, raw_file_path))
                return True
        else:
            raise NotImplementedError(first_dat_glob)
        return False

    def _look_for_snapshot_request(self, job_queue, check_scheduled=False):
        schedule_snapshot = False
        file_get_snapshot = os.path.join(self.output_dir, "get_snapshot")
        if os.path.exists(file_get_snapshot):
            os.remove(file_get_snapshot)
            schedule_snapshot = True
        if check_scheduled:
            n_build_parts = len(
                os.listdir(os.path.join(self.output_dir, my_paths.build_dir))
            )
            for ss_after in self._snapshot_after:
                if self._last_n_monitored < ss_after <= n_build_parts:
                    schedule_snapshot = True
                    break
            next_it_every = n_build_parts // self._snapshot_every
            if self._last_n_monitored < next_it_every * self._snapshot_every:
                schedule_snapshot = True
        if schedule_snapshot:
            job_queue.put((Priority.SNAP_SHOT, 0, "not used"))

    def _alert_is_idle(self, file_run_finished, seconds_before_alert=60):
        time_without_jobs = time.time() - self._time_last_job
        n_idle_infos = getattr(self, "_n_idle_infos", 1)
        if time_without_jobs < seconds_before_alert * n_idle_infos:
            return
        self._n_idle_infos = n_idle_infos + 1

        file_suppress_idle_info = os.path.join(self.output_dir, "suppress_idle_info")
        if os.path.exists(file_suppress_idle_info):
            return

        self.logger.info(
            "💤🤷Already waiting for new jobs since "
            f"{int(time_without_jobs)} seconds. "
            "By now we would have expected to find the file that "
            f"indicates the end of the run: {file_run_finished}. "
        )
        self.logger.info(
            "💡Hint: To exit this infinite loop gracefully, and perform "
            "the end-of run computations, create a dummy version of that file. "
            f"To suppress this info, create the file {file_suppress_idle_info}. "
        )

    def convert_to_root(self, raw_file_path, job_queue):
        raw_file_name = os.path.basename(raw_file_path)
        raw_file_path = as_tar(raw_file_path)
        if self._skip_dirty_dat:
            if os.path.getsize(raw_file_path) < 1024:
                self.logger.debug("🦘Skip empty dat file: " + raw_file_path)
                return False
        if raw_file_name.endswith(".dat") or raw_file_name.endswith("raw.bin"):
            converted_name = "converted_" + raw_file_name + "_0000.root"
        else:
            converted_name = "converted_" + raw_file_name + ".root"
        out_path = os.path.join(self.output_dir, my_paths.converted_dir, converted_name)
        if os.path.exists(out_path):
            return out_path
        tmp_dir = os.path.join(self.output_dir, my_paths.tmp_dir)
        tmp_path = os.path.join(tmp_dir, converted_name)
        if raw_file_path.endswith(".tar.gz"):
            with tarfile.open(raw_file_path) as tar:
                tar.extractall(path=tmp_dir)
            in_path = os.path.join(tmp_dir, raw_file_name)
            assert os.path.exists(in_path)
        else:
            in_path = raw_file_path

        root_macro_dir = os.path.join(my_paths.tb_analysis_dir, "converter_SLB")
        if "_raw.bin" in raw_file_name:
            root_call = (
                f'"RawConvertDataSL.cc(\\"{in_path}\\", false, \\"{tmp_path}\\")"'
            )
            if self._split_binary_too_large(in_path, job_queue):
                return False
        elif ".dat" in raw_file_name:
            root_call = f'"ConvertDataSL.cc(\\"{in_path}\\", false, \\"{tmp_path}\\")"'
        else:
            raise NotImplementedError(raw_file_name)
        ret = subprocess.run(
            "root -b -l -q " + root_call,
            shell=True,
            capture_output=True,
            cwd=root_macro_dir,
        )
        if ret.returncode != 0 or ret.stderr != b"":
            log_unexpected_error_subprocess(self.logger, ret, " during convert_to_root")
            sys.exit(1)
        os.rename(tmp_path, out_path)
        if raw_file_path.endswith(".tar.gz"):
            os.remove(in_path)
        elif "_monitoring_split_" in os.path.basename(in_path):
            os.remove(in_path)
        self.logger.debug(
            f"🌱New converted file {os.path.basename(out_path)} at {out_path}."
        )
        return out_path

    def _split_binary_too_large(self, binary_path, job_queue):
        try:
            binary_id = int(binary_path[-4:]) + 1
        except ValueError:
            binary_id = 1
        if self._binary_split_M <= 0:
            return False
        if os.path.getsize(binary_path) > 1024**2 * self._binary_split_M:
            tmp_dir = os.path.join(self.output_dir, my_paths.tmp_dir)
            part_prefix_name = os.path.basename(binary_path) + "_monitoring_split_"
            part_prefix = os.path.join(tmp_dir, part_prefix_name)
            cmd = f"split {binary_path} {part_prefix} "
            cmd += f"-b {self._binary_split_M}M "
            cmd += "--suffix-length 5 --numeric "
            ret = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
            )
            if ret.returncode != 0 or ret.stderr != b"":
                log_unexpected_error_subprocess(
                    self.logger, ret, " during _split_binary_too_large"
                )
                sys.exit(1)
            for i, binary_part in enumerate(sorted(glob.glob(part_prefix + "*"))):
                binary_part_path = os.path.join(tmp_dir, binary_part)
                id_job = 10000 * binary_id + i
                job_queue.put((Priority.CONVERSION, -id_job, binary_part_path))
            return True
        return False

    def run_eventbuilding(self, converted_path, id_dat):
        if self._skip_dirty_dat:
            if os.path.getsize(converted_path) < 1024**2 * 3:
                self.logger.debug("🦘Skip converted file too small: " + converted_path)
                return False
        converted_name = os.path.basename(converted_path)
        build_name = converted_name.replace("converted_", "build_")
        out_path = os.path.join(self.output_dir, my_paths.build_dir, build_name)
        if os.path.exists(out_path):
            return out_path
        tmp_path = os.path.join(self.output_dir, my_paths.tmp_dir, build_name)
        in_path = os.path.join(self.output_dir, my_paths.converted_dir, converted_name)

        builder_dir = os.path.join(my_paths.tb_analysis_dir, "eventbuilding")
        args = f" {in_path} --out_file_name {tmp_path}"
        self.eventbuilding_args["id_dat"] = int(id_dat)
        for k, v in self.eventbuilding_args.items():
            args += f" --{k} {v}"
        args += " --no_progress_info"
        ret = subprocess.run(
            "./build_events.py" + args,
            shell=True,
            capture_output=True,
            cwd=builder_dir,
        )
        if ret.returncode != 0 or ret.stderr != b"":
            log_unexpected_error_subprocess(
                self.logger, ret, " during run_eventbuilding"
            )
            sys.exit(1)
        return tmp_path

    def merge_eventbuilding(self, queues):
        while self._snapshot_needs_current_build:
            time.sleep(1)
        current_build = queues["current_build"].get(timeout=2)
        files_to_merge = []
        while queues["merge"].qsize():
            files_to_merge.append(queues["merge"].get(timeout=0.1))
        for tmp_path in files_to_merge:
            self._single_merge_eventbuilding(tmp_path, current_build)
            queues["merge"].task_done()
        queues["current_build"].put(current_build)
        queues["current_build"].task_done()

    def _single_merge_eventbuilding(self, tmp_path, current_build):
        build_name = os.path.basename(tmp_path)
        part_path = os.path.join(self.output_dir, my_paths.build_dir, build_name)
        if os.path.exists(part_path):
            return part_path
        if not os.path.exists(current_build):
            # The first build.root part that was finished.
            shutil.copy(tmp_path, current_build)
        else:
            root_macro_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "continuous_event_building"
            )
            args = '\\"' + '\\", \\"'.join((current_build, tmp_path, "ecal")) + '\\"'
            root_call = f'"mergeSelective.C({args})"'
            ret = subprocess.run(
                "root -b -l -q " + root_call,
                shell=True,
                capture_output=True,
                cwd=root_macro_dir,
            )
            if ret.returncode != 0 or ret.stderr != b"":
                log_unexpected_error_subprocess(
                    self.logger, ret, " during merge_eventbuilding"
                )
                sys.exit(1)
        os.rename(tmp_path, part_path)
        self.logger.debug(
            f"🔨New event file " f"{os.path.basename(part_path)} at {part_path}."
        )

    def get_snapshot(
        self,
        current_build_queue=None,
        build_file=None,
        snap_path=None,
        force_snapshot=False,
    ):
        now = time.time()
        if now - self._time_last_snapshot < 30 and not force_snapshot:
            return False
        else:
            self._time_last_snapshot = now
        if snap_path is None:
            snap_name = get_now_string() + ".root"
            snap_path = os.path.join(self.output_dir, my_paths.snapshot_dir, snap_name)
        else:
            snap_name = os.path.basename(snap_path)
        tmp_snap_path = os.path.join(
            self.output_dir, my_paths.tmp_dir, os.path.basename(snap_path)
        )
        n_build_parts = len(
            os.listdir(os.path.join(self.output_dir, my_paths.build_dir))
        )
        if self._last_n_monitored < n_build_parts:
            self._last_n_monitored = n_build_parts
        elif not force_snapshot:
            return False
        if build_file is None:
            self._snapshot_needs_current_build = True
            build_file = current_build_queue.get()
            shutil.copy(
                build_file,
                tmp_snap_path,
            )
            self._snapshot_needs_current_build = False
            current_build_queue.put(build_file)
            current_build_queue.task_done()
        else:
            shutil.copy(
                build_file,
                tmp_snap_path,
            )
        deco_times_file = "times_decorate.py.csv"
        deco_times_file = os.path.join(self.output_dir, ".times", deco_times_file)
        ret = subprocess.run(
            f"./decorate.py {tmp_snap_path} --times_file {deco_times_file}",
            shell=True,
            capture_output=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        if ret.returncode != 0 or ret.stderr != b"":
            log_unexpected_error_subprocess(self.logger, ret, " during get_snapshot")
            sys.exit(1)
        os.rename(tmp_snap_path, snap_path)
        if self._delete_previous_snaphots:
            snap_dir = os.path.join(self.output_dir, my_paths.snapshot_dir)
            for f in os.listdir(snap_dir):
                if f == snap_name:
                    continue
                f_path = os.path.join(snap_dir, f)
                if f.startswith("202") and os.path.isfile(f_path):
                    os.remove(f_path)
        self.logger.debug(
            f"🔎A new monitoring snapshot is ready: {snap_name} at {snap_path}."
        )
        return snap_path

    def _wrap_up(self, queues):
        current_build_queue = queues["current_build"]
        if current_build_queue.empty():
            self.logger.warning(
                "🤷The wrap-up has to be skipped. "
                "No access to the final buildfile was granted."
            )
        else:
            if hasattr(self, "_stopped_gracefully") and self._stopped_gracefully:
                snapshot_name = "stopped_run.root"
            else:
                snapshot_name = "full_run.root"
            build_file = current_build_queue.get()
            self.get_snapshot(
                current_build_queue=None,
                build_file=build_file,
                snap_path=os.path.join(self.output_dir, snapshot_name),
                force_snapshot=True,
            )
            current_build_queue.put(build_file)
            current_build_queue.task_done()

    def write_times(self, file_name=None):
        if file_name is None:
            times_dir = os.path.join(self.output_dir, ".times")
            if not os.path.isdir(times_dir):
                os.mkdir(times_dir)
            file_name = f"times_{os.path.basename(os.path.abspath(__file__))}.csv"
            file_name = os.path.join(times_dir, file_name)
        lines = [",".join(self.times[-1][0]._fields)]
        for t in [v for per_worker in self.times.values() for v in per_worker]:
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
        description="Run the event-based monitoring loop from SiW-ECAL DAQ files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("raw_run_folder", help="Folder of the run to be monitored.")
    parser.add_argument(
        "-c",
        "--config_file",
        default=my_paths.default_config,
        help=f"If relative path, then relative to {__file__}",
    )
    monitoring = EcalMonitoring(**vars(parser.parse_args()))
    monitoring.start_loop()
    monitoring.write_times()
