# -*- coding: utf-8 -*-
"""
User interface for caf.space
"""
# Built-Ins
from tkinterweb import HtmlFrame
from tkhtmlview import HTMLScrolledText, RenderHTML
import markdown
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import sys

# Third Party
from caf.space import inputs, zone_translation

# Local Imports
# pylint: disable=import-error,wrong-import-position
# Local imports here
# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #
SHAPE_FILEFILTER = (("Shapefiles", "*.shp"), ("All files", "*.*"))
CSV_FILEFILTER = (("CSV", "*.csv"), ("All files", "*.*"))


# # # CLASSES # # #
class FileWidget(ttk.Frame):
    """Tkinter widget for an entry box to select a file."""

    def __init__(
        self,
        parent,
        label="",
        browse="open",
        path_width=20,
        label_width=20,
        file_filter=(("All files", "*.*")),
    ):
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
        self.browseType = str(browse).lower()

        # Create label if needed as either entry or label widget
        self.label = ttk.Label(self, text=label, width=label_width)
        self.file_filter = file_filter
        # Create entry box and browse button
        self.path = ttk.Entry(self, width=path_width)
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
            path = filedialog.askopenfilename(filetypes=self.file_filter)
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
        return

    def disable(self):
        self.button.config(state="disabled")
        self.path.config(state="disabled")

    def enable(self):
        self.button.config(state="normal")
        self.path.config(state="normal")


class LabelledTextEntry(ttk.Frame):
    def __init__(
        self,
        parent,
        label: str,
        label_width: int = 20,
        text_width=20,
        variable: tk.StringVar = None,
    ):
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
            self.text = ttk.Entry(self, width=text_width, textvariable=variable)
        else:
            self.text = ttk.Entry(self, width=text_width)
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
    def __init__(self, parent, scroll_range, label, default_value, label_width=20):
        super().__init__(parent)
        self.link_var = tk.IntVar(value=default_value)
        self.label = ttk.Label(self, text=label, width=label_width)
        self.scroller = ttk.Spinbox(
            self,
            from_=scroll_range[0],
            to=scroll_range[-1],
            width=10,
            textvariable=self.link_var,
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
        self.shapefile = FileWidget(
            self,
            label="Shapefile",
            browse="open",
            label_width=15,
            path_width=30,
            file_filter=SHAPE_FILEFILTER,
        )
        self.name = LabelledTextEntry(self, label="Zone system name", text_width=10)
        self.id_col = LabelledTextEntry(self, label="ID column name", text_width=10)
        self.point_shapefile = FileWidget(
            self,
            label="Point shapefile",
            browse="open",
            label_width=15,
            path_width=30,
            file_filter=SHAPE_FILEFILTER,
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
        self.shapefile = FileWidget(
            self,
            label="Shapefile",
            browse="open",
            label_width=15,
            path_width=30,
            file_filter=SHAPE_FILEFILTER,
        )
        self.name = LabelledTextEntry(self, label="Zone system name")
        self.id_col = LabelledTextEntry(self, label="ID column name")
        self.weight_data = FileWidget(
            self,
            label="Weight data",
            browse="open",
            label_width=15,
            path_width=30,
            file_filter=CSV_FILEFILTER,
        )
        self.data_col = LabelledTextEntry(
            self, label="Weight data column", label_width=30, text_width=10
        )
        self.weight_id_col = LabelledTextEntry(
            self, label="Weight id col", label_width=30, text_width=10
        )
        self.weight_data_year = LabelledTextEntry(
            self, label="Year of weight data", label_width=30, text_width=10
        )

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
        self.cache_folder = FileWidget(
            self, label="Cache Path", browse="directory", label_width=15
        )
        self.cache_folder.set(inputs.CACHE_PATH)
        self.output_folder = FileWidget(
            self, label="Output Folder", browse="directory", label_width=15
        )
        self.method = LabelledTextEntry(
            self, label="Method name", variable=self.method_var, label_width=15, text_width=10
        )
        self.method_var.trace_add("write", self.activateLower)
        self.lower = LowerZoneFrame(self)
        self.lower.disable()
        self.zone_1 = ZoneFrame(self, "zone 1")
        self.zone_2 = ZoneFrame(self, "zone 2")

        self.slither_tolerance = NumberScroller(
            self,
            scroll_range=(1, 100),
            label="Percentage sliver tolerance",
            default_value=98,
            label_width=30,
        )
        self.point_tolerance = NumberScroller(
            self,
            scroll_range=(1, 1e06),
            label="Area threshold for point zones",
            default_value=1,
            label_width=30,
        )
        self.point_tolerance.disable()
        self.rounding = ttk.Checkbutton(
            self,
            text="Round total factors to 1?",
            variable=self.rounding_var,
        )

        self.point_handling = ttk.Checkbutton(
            self,
            text="Do you want point zones handled?",
            variable=self.handling_var,
            command=self.activateHandling,
        )

        self.filter_slithers = ttk.Checkbutton(
            self,
            text="Filter out slivers?",
            variable=self.slivers_var,
            command=self.activateSlivers,
        )

        self.cache_folder.grid(column=0, row=0, columnspan=3, sticky="ew", pady=5)
        self.output_folder.grid(column=3, row=0, columnspan=3, sticky="ew", pady=5)
        self.filter_slithers.grid(column=0, columnspan=2, row=1, sticky="s", pady=10)
        self.rounding.grid(column=2, columnspan=2, row=1, sticky="es", pady=10)
        self.point_handling.grid(column=4, columnspan=2, row=1, sticky="s", pady=10)
        self.slither_tolerance.grid(column=0, row=2, columnspan=2, sticky="s", pady=5)
        self.point_tolerance.grid(column=2, row=2, columnspan=2, sticky="s", pady=5)
        self.method.grid(column=4, row=2, columnspan=2, sticky="ew", pady=5)
        self.zone_1.grid(column=0, row=4, columnspan=3, sticky="nsew", pady=5)
        self.zone_2.grid(column=3, row=4, columnspan=3, sticky="nsew", pady=5)
        self.lower.grid(column=0, row=5, columnspan=6, sticky="s", pady=5)

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
        if len(self.method_var.get()) > 0:
            lower = self.lower.get()
        else:
            lower = None
        params = {
            "output_path": Path(self.output_folder.get()),
            "cache_path": Path(self.cache_folder.get()),
            "filter_slivers": self.slivers_var.get(),
            "rounding": self.rounding_var.get(),
            "point_handling": self.handling_var.get(),
            "sliver_tolerance": self.slither_tolerance.get() / 100,
            "point_tolerance": self.point_tolerance.get(),
            "method": self.method_var.get(),
            "lower": lower,
        }
        return params


class UiTab(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.main_params = ParametersFrame(self)
        # self.zone_1 = ZoneFrame(self, "zone 1")
        # self.zone_2 = ZoneFrame(self, "zone 2")
        self.weighted_button = ttk.Button(
            self, text="Weighted translation", command=self.run_weighted
        )
        self.spatial_button = ttk.Button(
            self, text="Spatial translation", command=self.run_spatial
        )

        self.main_params.grid(column=0, row=0, rowspan=3, columnspan=2, sticky="ew", pady=5)
        # self.zone_1.grid(column=1, row=0, sticky="ew", pady=5)
        # self.zone_2.grid(column=1, row=1, sticky="ew", pady=5)
        self.weighted_button.grid(column=0, columnspan=1, row=3, sticky="ew", pady=5)
        self.spatial_button.grid(column=1, columnspan=1, row=3, sticky="ew", pady=5)

    def run_weighted(self):
        main_params = self.main_params.get()
        zone_1 = self.zone_1.get()
        zone_2 = self.zone_2.get()
        lower = main_params["lower"]
        config = inputs.ZoningTranslationInputs(
            zone_1=zone_1,
            zone_2=zone_2,
            cache_path=main_params["cache_path"],
            filter_slivers=main_params["filter_slivers"],
            rounding=main_params["rounding"],
            point_handling=main_params["point_handling"],
            sliver_tolerance=main_params["sliver_tolerance"],
            point_tolerance=main_params["point_tolerance"],
            method=main_params["method"],
            lower_zoning=lower,
        )
        zt = zone_translation.ZoneTranslation(config)
        zt.weighted_translation().to_csv(
            main_params["output_path"]
            / f"{config.zone_1.name}_{config.zone_2.name}_{config.method}.csv"
        )
        return

    def run_spatial(self):
        main_params = self.main_params.get()
        zone_1 = self.zone_1.get()
        zone_2 = self.zone_2.get()
        config = inputs.ZoningTranslationInputs(
            zone_1=zone_1,
            zone_2=zone_2,
            cache_path=main_params["cache_path"],
            filter_slivers=main_params["filter_slivers"],
            rounding=main_params["rounding"],
            point_handling=main_params["point_handling"],
            sliver_tolerance=main_params["sliver_tolerance"],
            point_tolerance=main_params["point_tolerance"],
        )
        zt = zone_translation.ZoneTranslation(config)
        zt.spatial_translation().to_csv(
            main_params["output_path"]
            / f"{config.zone_1.name}_{config.zone_2.name}_spatial.csv"
        )
        return


class ReadmeTab(ttk.Frame):
    def __init__(self, master=None, readme_path="readme.md", **kwargs):
        super().__init__(master, **kwargs)

        # create a text widget to display the readme contents

        # read the contents of the readme file
        with open(readme_path, "r") as f:
            readme_contents = f.read()

        # convert the Markdown text to HTML
        html_text = markdown.markdown(readme_contents)
        self.readme_text = HTMLScrolledText(
            self, wrap="word", state="disabled", html=html_text
        )
        self.readme_text.pack(fill="both", expand=True)
        print("debugging")


class ConsoleFrame(ttk.Frame):
    """Frame containing the console."""

    class StdoutRedirector(object):
        def __init__(self, text_widget):
            self.text_space = text_widget
            self.text_space.tag_configure("n", font=("Calibri", 12))

        def write(self, string):
            self.text_space.config(state="normal")
            self.text_space.insert("end", string, "n")
            self.text_space.see("end")
            self.text_space.config(state="disabled")

        def flush(self):
            return

    def __init__(self, parent):
        super().__init__(parent)

        # Configure text widget
        self.text = tk.Text(self)
        yscroll = ttk.Scrollbar(self, command=self.text.yview)
        xscroll = ttk.Scrollbar(self, command=self.text.xview, orient="horizontal")
        self.text.config(
            state="disabled",
            yscrollcommand=yscroll.set,
            xscrollcommand=xscroll.set,
            wrap="none",
        )

        # Change stdout
        sys.stdout = self.StdoutRedirector(self.text)
        sys.stderr = self.StdoutRedirector(self.text)

        # Pack widgets
        yscroll.pack(side="right", fill="y")
        xscroll.pack(side="bottom", fill="x")
        self.text.pack(side="left", fill="both", expand=True)
        return


class NotebookApp:
    def __init__(self):
        self.root = tk.Tk()
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        # Add MyUI instance as a tab
        my_ui_tab = ttk.Frame(self.notebook)
        my_ui = UiTab(master=my_ui_tab)
        my_ui.pack(fill="both", expand=True)
        self.notebook.add(my_ui_tab, text="My UI")

        # Add readme as a tab
        readme_tab = ttk.Frame(self.notebook)
        readme = ReadmeTab(
            master=readme_tab,
            readme_path=r"C:\Users\IsaacScott\Projects\caf\caf.space\README.md",
        )
        readme.pack(fill="both", expand=True)
        self.notebook.add(readme_tab, text="Readme")

        console_tab = ttk.Frame(self.notebook)
        console_text = ConsoleFrame(console_tab)
        console_text.pack(fill="both", expand=True)
        self.notebook.add(console_tab, text="Console Output")

        self.root.mainloop()


def test_func():
    root = tk.Tk()  # create the tkinter window
    frame = HtmlFrame(root)  # create HTML browser
    frame.load_website("https://cafspcae.readthedocs.io/en/latest/")
    frame.pack(fill="both", expand=True)
    root.mainloop()

if __name__ == "__main__":
    # NotebookApp()
    test_func()

# # # FUNCTIONS # # #
