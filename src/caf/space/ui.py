# -*- coding: utf-8 -*-
"""
User interface for caf.space
"""
# Built-Ins
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
# Third Party
from caf.space import inputs, zone_translation

# Local Imports
# pylint: disable=import-error,wrong-import-position
# Local imports here
# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #


# # # CLASSES # # #
class FileWidget(ttk.Frame):
    """Tkinter widget for an entry box to select a file."""

    LABEL_WIDTH = 20

    def __init__(self, parent, label="", labelentry=False, browse="open"):
        """
        Parameters
        ----------
        parent: tkinter container widget
            Parent container for storing the widget.
        label: str, optional
            Text to use for labelling the widget, if empty
            string (default) does not add a label.
        userLabel: bool, optional
            Whether the label should be user editable. If false
            (default) uses label widget otherwise uses entry widget
            with `label` as default text.
        browse: str, optional
            Type of browse to use, either 'open' or 'save' for files
            or 'directory' to select a directory.
        """
        super().__init__(parent)
        self.labelEntry = bool(labelentry)
        self.browseType = str(browse).lower()

        # Create label if needed as either entry or label widget
        if self.labelEntry:
            self.label = ttk.Entry(self, width=self.LABEL_WIDTH)
            self.label.insert(0, label)
        elif label != "":
            self.label = ttk.Label(self, text=label, width=self.LABEL_WIDTH)

        # Create entry box and browse button
        self.path = ttk.Entry(self, width=30)
        self.button = ttk.Button(self, text="...", width=3, command=self.browse)

        # Attempt to place label if it exists
        try:
            self.label.pack(side="left", fill="x", padx=5)
        except AttributeError:
            pass
        # Place widgets
        self.path.pack(side="left", fill="x", expand=True)
        self.button.pack(side="right", fill="x", padx=5)

        return

    def browse(self):
        """Method to open filedialog for selecting a file."""
        if self.browseType == "open":
            path = filedialog.askopenfilename()
        elif self.browseType == "save":
            path = filedialog.asksaveasfilename()
        elif self.browseType == "directory":
            path = filedialog.askdirectory()
        else:
            raise ValueError("Invalid browse type")
        self.set(path)
        return path

    def get(self):
        """Method to access the entry boxes, path and label (if labelEntry)."""
        if self.labelEntry:
            return (self.label.get(), self.path.get())
        return self.path.get()

    def set(self, value, label=None):
        """Set the entry box to given value.

        Parameters
        ----------
        value: str
            Value to set the path entry box to.
        label: str, optional
            Value to set the label entry box to.
        """
        self.path.delete(0, len(self.path.get()))
        self.path.insert(0, value)
        if self.labelEntry and not label is None:
            self.label.delete(0, len(self.label.get()))
            self.label.insert(0, label)
        return

    def disable(self):
        self.button.config(state="disabled")
        self.path.config(state="disabled")
        if self.labelEntry:
            self.label.config(state="disabled")

    def enable(self):
        self.button.config(state="normal")
        self.path.config(state="normal")
        if self.labelEntry:
            self.label.config(state="normal")


class LabelledTextEntry(ttk.Frame):
    def __init__(self, parent, label: str, label_width: int = 20, variable: tk.StringVar = None):
        """
        Simple text input box with a label
        Parameters
        ----------
        parent: tkinter container widget
            Parent container for storing the widget.
        label (str): Text used for labelling widget.
        """
        super().__init__(parent)
        self.label = ttk.Label(self, text=label, width=label_width)
        if variable:
            self.text = ttk.Entry(self, width=20, textvariable=variable)
        else:
            self.text = ttk.Entry(self, width=20)
        self.label.pack(side="left", fill="x", padx=5)
        self.text.pack(side="left", fill="x", expand=True)

        return

    def get(self):
        return self.text.get()

    def set(self, value):
        self.text.delete(0, len(self.text.get()))
        self.text.insert(0, value)
        return

    def disable(self):
        self.text.config(state="disabled")

    def enable(self):
        self.text.config(state="normal")


class NumberScroller(ttk.Frame):
    def __init__(self, parent, scroll_range, label, default_value):
        super().__init__(parent)
        self.link_var = tk.IntVar(value=default_value)
        self.label = ttk.Label(self, text=label, width=20)
        self.scroller = ttk.Spinbox(
            self, from_=scroll_range[0], to=scroll_range[-1], width=20, textvariable=self.link_var
        )
        self.label.pack(side="left", fill="x", padx=5)
        self.scroller.pack(side="right", fill="x", padx=5)
        return

    def get(self):
        return self.link_var.get()

    def set(self, value):
        self.scroller.set(value)

    def disable(self):
        self.scroller.config(state="disabled")

    def enable(self):
        self.scroller.config(state="normal")


class ZoneFrame(ttk.LabelFrame):
    def __init__(self, parent, label):
        super().__init__(parent, text=label)
        self.shapefile = FileWidget(self, label="Shapefile", browse="open")
        self.name = LabelledTextEntry(self, label="Zone system name")
        self.id_col = LabelledTextEntry(self, label="ID column name")
        self.point_shapefile = FileWidget(
            self, label="Optional point shapefile", browse="open"
        )

        self.shapefile.grid(column=0, row=0, columnspan=3, sticky="ew", pady=5)
        self.name.grid(column=0, row=1, columnspan=3, sticky="ew", pady=5)
        self.id_col.grid(column=0, row=2, columnspan=3, sticky="ew", pady=5)
        self.point_shapefile.grid(column=0, row=3, columnspan=3, sticky="ew", pady=5)

    def disable(self):
        self.shapefile.disable()
        self.name.disable()
        self.id_col.disable()
        self.point_shapefile.disable()

    def enable(self):
        self.shapefile.enable()
        self.name.enable()
        self.id_col.enable()
        self.point_shapefile.enable()

    def get(self):
        zone = inputs.TransZoneSystemInfo(
            shapefile=self.shapefile.get(),
            name=self.name.get(),
            id_col=self.id_col.get(),
            point_shapefile=self.point_shapefile.get(),
        )
        return zone


class LowerZoneFrame(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Lower Zone")
        self.shapefile = FileWidget(self, label="Shapefile", browse="open")
        self.name = LabelledTextEntry(self, label="Zone system name")
        self.id_col = LabelledTextEntry(self, label="ID column name")
        self.weight_data = FileWidget(self, label="Path to weight data", browse="open")
        self.data_col = LabelledTextEntry(self, label="Weight data column name")
        self.weight_id_col = LabelledTextEntry(self, label="Weight id col name")
        self.weight_data_year = LabelledTextEntry(self, label="Year of weight data")

        self.shapefile.grid(column=0, row=0, columnspan=3, sticky="ew", pady=5)
        self.name.grid(column=0, row=1, columnspan=3, sticky="ew", pady=5)
        self.id_col.grid(column=0, row=2, columnspan=3, sticky="ew", pady=5)
        self.weight_data.grid(column=3, row=0, columnspan=3, sticky="ew", pady=5)
        self.data_col.grid(column=3, row=1, columnspan=3, sticky="ew", pady=5)
        self.weight_id_col.grid(column=3, row=2, columnspan=3, sticky="ew", pady=5)
        self.weight_data_year.grid(column=3, row=3, columnspan=3, sticky="ew", pady=5)

    def disable(self):
        self.shapefile.disable()
        self.name.disable()
        self.id_col.disable()
        self.weight_data.disable()
        self.data_col.disable()
        self.weight_id_col.disable()
        self.weight_data_year.disable()

    def enable(self):
        self.shapefile.enable()
        self.name.enable()
        self.id_col.enable()
        self.weight_data.enable()
        self.data_col.enable()
        self.weight_id_col.enable()
        self.weight_data_year.enable()

    def get(self):
        lower_zone = inputs.LowerZoneSystemInfo(
            shapefile=self.shapefile.get(),
            name=self.name.get(),
            id_col=self.id_col.get(),
            weight_data=self.weight_data.get(),
            data_col=self.data_col.get(),
            weight_id_col=self.weight_id_col.get(),
            weight_data_year=int(self.weight_data_year.get()),
        )
        return lower_zone


class ParametersFrame(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Parameters")
        self.method_var = tk.StringVar()
        self.handling_var = tk.BooleanVar()
        self.rounding_var = tk.BooleanVar(value=True)
        self.slivers_var = tk.BooleanVar(value=True)
        self.cache_folder = FileWidget(self, label="Output Folder", browse="directory")
        self.cache_folder.set(inputs.CACHE_PATH)
        self.method = LabelledTextEntry(self, label="Method name", variable=self.method_var)
        self.method_var.trace_add("write", self.activateLower)
        self.lower = LowerZoneFrame(self)
        self.lower.disable()

        self.slither_tolerance = NumberScroller(
            self, scroll_range=(1, 100), label="Percentage sliver tolerance", default_value=98
        )
        self.point_tolerance = NumberScroller(
            self, scroll_range=(1, 1e06), label="Area threshold for point zones", default_value=1
        )
        self.rounding = ttk.Checkbutton(
            self,
            text="Round total factors to 1?",
            variable=self.rounding_var,
        )

        self.point_handling = ttk.Checkbutton(
            self,
            text="Do you want point zones handled?",
            variable=self.handling_var,
            command=self.activateHandling
        )

        self.filter_slithers = ttk.Checkbutton(
            self,
            text="Filter out slivers?",
            variable=self.slivers_var,
            command=self.activateSlivers
        )


        self.cache_folder.grid(column=0, row=0, columnspan=4, sticky="ew", pady=5)
        self.filter_slithers.grid(column=0, row=1, sticky="s", pady=10)
        self.rounding.grid(column=1, row=1, sticky="es", pady=10)
        self.point_handling.grid(column=2, row=1, sticky="s", pady=10)
        self.slither_tolerance.grid(column=0, row=2, columnspan=3, sticky="s", pady=10)
        self.point_tolerance.grid(column=3, row=2, columnspan=3, sticky="s", pady=10)
        self.method.grid(column=4, row=0, columnspan=2, sticky="ew", pady=5)
        self.lower.grid(column=0, row=3, columnspan=6, sticky="s", pady=10)

    def activateHandling(self):
        if self.handling_var.get():
            self.point_tolerance.enable()
        else:
            self.point_tolerance.disable()

    def activateSlivers(self):
        if self.slivers_var.get():
            self.slither_tolerance.enable()
        else:
            self.slither_tolerance.disable()

    def activateLower(self, *args):
        if len(self.method_var.get()) > 0:
            self.lower.enable()
        else:
            self.lower.disable()
    def get(self):
        params = {
            "cache_path": Path(self.cache_folder.get()),
            "filter_slivers": self.slivers_var.get(),
            "rounding": self.rounding_var.get(),
            "point_handling": self.handling_var.get(),
            "sliver_tolerance": self.slither_tolerance.get() / 100,
            "point_tolerance": self.point_tolerance.get(),
            "method": self.method_var.get(),
            "lower": self.lower.get()
        }
        return params

class Main(tk.Tk):
    def __init__(self):
        super().__init__()
        self.main_params = ParametersFrame(self)
        self.zone_1 = ZoneFrame(self, "zone 1")
        self.zone_2 = ZoneFrame(self, "zone 2")
        self.run_button = ttk.Button(self, text="Weighted translation", command=self.run_weighted)

        self.main_params.grid(column=0, row=0, rowspan=3, sticky="ew", pady=5)
        self.zone_1.grid(column=1, row=0, sticky="ew", pady=5)
        self.zone_2.grid(column=1, row=1, sticky="ew", pady=5)
        self.run_button.grid(column=0, columnspan=2, row=3, sticky="ew", pady=5)



    def run_weighted(self):
        main_params = self.main_params.get()
        zone_1 = self.zone_1.get()
        zone_2 = self.zone_2.get()
        if main_params["method"]:
            lower = self.lower_zone.get()
        else:
            lower = None
        config=inputs.ZoningTranslationInputs(
            zone_1=zone_1,
            zone_2=zone_2,
            cache_path=main_params["cache_path"],
            filter_slivers=main_params["filter_slivers"],
            rounding=main_params["rounding"],
            point_handling=main_params["point_handling"],
            sliver_tolerance=main_params["sliver_tolerance"],
            point_tolerance=main_params["point_tolerance"],
            lower_zoning=lower
        )
        zt = zone_translation.ZoneTranslation(config)
        zt.weighted_translation()
        return

    # def run_


if __name__ == "__main__":
    app = Main()
    app.mainloop()



# # # FUNCTIONS # # #
