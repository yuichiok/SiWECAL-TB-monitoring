import logging
import os
import queue

try:
    import awkward as ak
    import matplotlib
    import matplotlib.pyplot as plt
    import numpy as np
    import uproot

    assert list(map(int, ak.__version__.split(".")))[0] >= 1, (
        "ak.__version__ < 1: " + ak.__version__
    )

    logging.getLogger("matplotlib").setLevel(level=logging.ERROR)
    matplotlib.use("agg")

    def get_quality_info(current_build_queue, monitoring, finished=False):
        w_setting = monitoring.eventbuilding_args["w_config"]
        if w_setting == 3:
            w_conf = np.full(15, 2.8)  # TODO: This should be taken from monitoring.cfg.
            w_conf[-8:] = 4.2
            s_conf = np.array(
                [
                    0.650,
                    0.650,
                    0.500,
                    0.500,
                    0.325,
                    0.325,
                    0.325,
                    0.500,
                    0.500,
                    0.500,
                    0.500,
                    0.325,
                    0.325,
                    0.325,
                    0.325,
                ]
            )
            dEdx_s = 2 * 2.33 / 1000
            dEdx_w = 2 * 19.25 / 1000
            f_layer = (s_conf * dEdx_s) / (w_conf * dEdx_w + s_conf * dEdx_s)
            f_layer = 1 / (w_conf * dEdx_w + s_conf * dEdx_s)
        else:
            f_layer = np.ones(15)

        try:
            current_build = current_build_queue.get(timeout=2)
        except queue.Empty:
            return False
        id_dat = uproot.open(current_build)["ecal/id_dat"].array()
        cycles = uproot.open(current_build)["ecal/cycle"].array()
        nhit_slab = uproot.open(current_build)["ecal/nhit_slab"].array()
        hit_slab = uproot.open(current_build)["ecal/hit_slab"].array()
        energy = uproot.open(current_build)["ecal/hit_energy"].array()
        is_hit = uproot.open(current_build)["ecal/hit_isHit"].array()
        current_build_queue.put(current_build)
        current_build_queue.task_done()

        parts = np.unique(ak.to_numpy(id_dat))
        if finished:
            n_cycles = np.max(cycles) - np.min(cycles) + 1
        else:
            # We cannot just take the unique values: There can be empty cycles.
            n_cycles = 0
            for part_id in parts:
                cycles_in_part = cycles[id_dat == part_id]
                n_cycles += np.max(cycles_in_part) - np.min(cycles_in_part) + 1
        title_text = f"{n_cycles} cycles monitored"
        if not finished:
            title_text += f" in {len(parts)} parts (ongoing)"
        title_text += f"\n{os.path.basename(monitoring.output_dir)}"

        fig, axs = plt.subplots(ncols=2, nrows=2, figsize=(12, 12))
        axs = axs.flatten()
        fig.suptitle(title_text)
        n, bins, _ = axs[0].hist(
            nhit_slab,
            bins=np.arange(ak.min(nhit_slab) - 0.5, ak.max(nhit_slab) + 1),
            cumulative=-1,
        )
        for i, counts in enumerate(n):
            axs[0].text(
                bins[i] + 0.5,
                1,
                f"{int(counts):> 10}",
                horizontalalignment="center",
                verticalalignment="bottom",
                rotation="vertical",
            )
        axs[0].set_xlabel("slab coincidence >=")
        axs[0].set_ylabel("# events")

        slabs = np.arange(ak.min(hit_slab), ak.max(hit_slab) + 1)
        axs[1].bar(slabs, [ak.sum(ak.sum(hit_slab == i, axis=1)) for i in slabs])
        axs[1].set_xlabel("slab in coincidence")
        axs[1].set_ylabel("# events")

        slab_energies = []
        slab_energies_std = []
        event_energy = np.zeros(len(energy))
        for i, i_slab in enumerate(slabs):
            e_in_slab = energy[(hit_slab == i_slab) & (is_hit > 0)]
            e_in_slab = e_in_slab[e_in_slab > 0]
            e_in_slab = e_in_slab / f_layer[i]
            event_energy = event_energy + ak.sum(e_in_slab, axis=1)
            e_flat = ak.flatten(ak.sum(e_in_slab, axis=1), axis=None)
            slab_energies.append(np.mean(e_flat))
            slab_energies_std.append(np.std(e_flat))

        axs[2].bar(slabs, slab_energies, yerr=slab_energies_std)
        axs[2].set_xlabel("slab in coincidence")
        axs[2].set_ylabel("average energy")

        axs[3].hist(event_energy, bins="auto")
        axs[3].set_xlabel("event energy")
        axs[3].set_ylabel("# events")

        fig.tight_layout()
        in_data_img_path = os.path.join(monitoring.output_dir, "data_quality.png")
        fig.savefig(in_data_img_path, dpi=300)
        monitoring_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        fig.savefig(os.path.join(monitoring_root, "data_quality.png"), dpi=300)
        monitoring.logger.info(
            "🥨" + title_text.replace("\n", ". ") + ": " + in_data_img_path
        )
        plt.close(fig)
        return True

except (ImportError, AssertionError) as e:
    no_quality_txt = "🥨No data quality info and plots will be provided. "
    no_quality_txt += str(e)
    print(no_quality_txt)

    def get_quality_info(current_build_queue, monitoring, finished=False):
        return True
