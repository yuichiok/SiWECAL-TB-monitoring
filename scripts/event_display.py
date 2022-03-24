#!/usr/bin/env python3
import argparse
import logging
import os

import awkward as ak
import numpy as np
import plotly.graph_objects as go
import uproot

default_img_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
default_img_folder = os.path.join(default_img_folder, "data", "displays")


class EventDisplay:
    # Dimensions of the prototype. Lengths in mm.
    _n_layers = 15
    _layer_distance = 15
    _pos_xy = np.arange(3.8, 87, 5.5)
    _pos_x_fev13 = np.arange(3.8, 87 + 60, 5.5)
    _w_xy = 2.23  # 1/2 length per side of the drawn square.

    _z_1D = np.arange(0, _n_layers * _layer_distance + 2)
    _x_1D = np.concatenate([-_pos_x_fev13[::-1], _pos_xy])
    _y_1D = np.concatenate([-_pos_xy[::-1], _pos_xy])

    _xaxis = dict(
        title="Z (0=upper module) [mm]",
        range=[_z_1D[0], _z_1D[-1] + 5],
    )
    _yaxis = dict(
        title="X [mm]",
        range=[_x_1D[0] - 3, _x_1D[-1] + 3],
    )
    _zaxis = dict(
        title="Y [mm]",
        range=[_y_1D[0] - 3, _y_1D[-1] + 3],
    )

    def __init__(self, args):
        logging.basicConfig(format="%(message)s")
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

        self._args = args
        if not os.path.exists(os.path.dirname(args.img_folder)):
            os.mkdir(os.path.dirname(args.img_folder))
        if not os.path.exists(args.img_folder):
            os.mkdir(args.img_folder)
        file_name = args.build_file
        assert os.path.isfile(file_name)
        ecal = uproot.open(file_name)["ecal"].arrays()
        mask = self.event_selection(ecal, args)
        self.ecal = ecal[mask]

        if "(" in args.hover_var:
            self._hover_var, hover_lim = args.hover_var.strip().split("(")
        else:
            self._hover_var = args.hover_var
            hover_lim = ""
        assert self._hover_var in ak.fields(
            self.ecal
        ), f"{self._hover_var}, {ak.fields(self.ecal)}"
        if len(hover_lim):
            assert hover_lim.endswith(")"), hover_lim
            self._hover_lim = list(map(int, hover_lim[:-1].split(",")))
            assert len(self._hover_lim) == 2
        else:
            x = getattr(self.ecal, self._hover_var)
            self._hover_lim = (ak.min(x), ak.max(x))

    def get_figure(self, energies, xs, ys, zs, title="title"):
        txt = self._hover_var + ": %{customdata[0]:d}"
        txt += "<br>layer %{customdata[1]:d} (%{y:.1f},%{z:.1f})<extra></extra>"
        fig = go.Figure()
        for i, (energy, x, y, z) in enumerate(zip(energies, xs, ys, zs)):
            fig.add_surface(
                x=np.full(2, z),
                y=[x - self._w_xy, x + self._w_xy],
                z=[[y - self._w_xy, y + self._w_xy], [y - self._w_xy, y + self._w_xy]],
                opacity=0.8,
                surfacecolor=np.full((2, 2), energy),
                cmin=self._hover_lim[0],
                cmax=self._hover_lim[1],
                colorscale="Viridis",
                colorbar=dict(title=self._hover_var),
                showscale=i == 0,
                hovertemplate=txt,
                customdata=np.stack(
                    (
                        np.full((2, 2), energy),
                        np.full((2, 2), z / self._layer_distance),
                    ),
                    axis=-1,
                ),
            )
        fig.update_layout(
            title=title,
            scene={ax: getattr(self, "_" + ax) for ax in ["xaxis", "yaxis", "zaxis"]},
        )
        return fig

    def event_selection(self, ecal, args):
        self.logger.debug(f"Total number of events: {len(ecal)}")
        mask = ecal.nhit_slab >= args.coincidences
        self.logger.debug(f" - >= {args.coincidences} coincidences: {ak.sum(mask)}")

        for layer_required in map(int, filter(None, args.layers_required.split(","))):
            if layer_required == "":
                continue
            mask = mask & ak.sum(ecal.hit_slab == int(layer_required), axis=1) > 0
            self.logger.debug(f" - With hits in layer {layer_required}: {ak.sum(mask)}")
        if args.max_hits > 0:
            mask = mask & (ak.sum(ecal.hit_isHit, axis=1) <= args.max_hits)
            self.logger.debug(f" - With at most {args.max_hits} hits: {ak.sum(mask)}")
        return mask

    def write_event_display(self, i_event=0, save_to=None):
        args = self._args
        if save_to is None:
            save_name = f"{args.file_tag}_Display_{i_event}.html"
            save_to = os.path.join(args.img_folder, save_name)
        if i_event >= len(self.ecal):
            self.logger.warning(
                f"Requested event id too high: {i_event} >= {len(self.ecal)}."
            )
            return False
        ev = self.ecal[i_event]
        x = getattr(ev, self._hover_var)
        m = ev.hit_isHit == 1
        title = (
            f"Event display {args.file_tag}_{i_event} "
            f"#Hits={len(x)} "
            f"#Coincidences={len(np.unique(np.array(ev.hit_slab[m])))}"
        )
        fig = self.get_figure(x[m], ev.hit_x[m], ev.hit_y[m], ev.hit_z[m], title)
        fig.write_html(save_to)
        self.logger.debug(f"New event: {i_event} at file://" + save_to)
        return save_to

    def interactive_event_display(self):
        args = self._args
        html_path = os.path.join(str(args.img_folder), "new_event.html")
        i_event = 0
        self.logger.info(
            "ENTER to create a new event (i_event + 1). "
            f"If you type a number (<{len(self.ecal)}) first, "
            "that event will be displayed."
        )
        while True:
            inp = input()
            try:
                i_event = int(inp)
            except ValueError:
                pass
            if self.write_event_display(save_to=html_path, i_event=i_event):
                i_event += 1
            else:
                self.logger.warning("All events were shown. We restart from 0.")
                i_event = 0


def get_parser_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("build_file")
    parser.add_argument(
        "-c",
        "--coincidences",
        type=int,
        default=13,
        help="Minimum number of slabs hit in coincidence.",
    )
    parser.add_argument(
        "-l",
        "--layers_required",
        default="",
        help="Comma seperated list of layer numbers that must be in event.",
    )
    parser.add_argument(
        "-m",
        "--max_hits",
        type=int,
        default=-1,
        help="If > 0: Maximum number of hits allowed in the event.",
    )
    parser.add_argument("-t", "--file_tag", type=str, default="Run_name")
    parser.add_argument(
        "-v",
        "--hover_var",
        type=str,
        default="hit_hg(0,1000)",
        help=(
            "Variable used for coloring the cells. "
            "If followed by a tuple with two numbers, these are interpreted "
            "as the color scale range."
        ),
    )
    parser.add_argument("--img_folder", default=default_img_folder, help="Save to.")
    parser.add_argument(
        "-i",
        "--event_id_string",
        type=str,
        default="-1",
        help=(
            "Comma seperated list of event ids (after applying the mask. "
            "For interactive usage (recommended), put `-1,`."
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = get_parser_args()
    ed = EventDisplay(args)
    write_events = list(map(int, filter(None, args.event_id_string.split(","))))
    if len(write_events) >= 1 and write_events[0] != -1:
        for i_event in write_events:
            ed.write_event_display(i_event)
    else:
        ed.interactive_event_display()
