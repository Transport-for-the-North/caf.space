# -*- coding: utf-8 -*-
"User interface for caf.space."
# Built-Ins
from functools import partial
import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from typing import Optional
import os
import sys
import logging

# Third Party
from tkinterweb import HtmlFrame, Notebook
from caf.space import inputs, zone_translation

# Local Imports
# pylint: disable=import-error,wrong-import-position
# Local imports here

# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #
SHAPE_FILEFILTER = (("Shapefiles", "*.shp"), ("All files", "*.*"))
CSV_FILEFILTER = (("CSV", "*.csv"), ("All files", "*.*"))

# # # CLASSES # # #
# pylint: disable=too-many-ancestors, too-many-instance-attributes, unused-argument


class RedirectStdOut:  # pylint: disable=too-few-public-methods
    """Class to redirect stdout to `ScolledText` widget."""

    def __init__(self, text_widget):
        self.output = text_widget.text

    def write(self, text: str):
        """Write given `text` to widget.

        Parameters
        ----------
        text : str
            Message to write to widget.
        """
        # Check what tag to add
        tag = None
        for i in ("warning", "error", "debug"):
            if f"[{i}]" in text.lower():
                tag = i
        self.output.configure(state="normal")
        self.output.insert("end", text, tag)
        self.output.configure(state="disabled")


class FileWidget(ttk.Frame):
    """Tkinter widget for an entry box to select a file."""

    def __init__(
        self,
        parent,
        variable: Optional[tk.StringVar] = None,
        label="",
        browse="open",
        widths=(20, 20),
        file_filter=(("All files", "*.*")),
    ):
        """
        Initialise class.

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
        self.browse_type = str(browse).lower()

        # Create label if needed as either entry or label widget
        self.label = ttk.Label(self, text=label, width=widths[1])
        self.file_filter = file_filter
        # Create entry box and browse button
        if variable:
            self.path = ttk.Entry(self, width=widths[0], textvariable=variable)
        else:
            self.path = ttk.Entry(self, width=widths[0])
        self.button = ttk.Button(self, text="...", width=3, command=self.browse)

        # Attempt to place label if it exists
        try:
            self.label.pack(side="left", fill="x", padx=5)
        except AttributeError:
            pass
        # Place widgets
        self.path.pack(side="left", fill="x", expand=True)
        self.button.pack(side="right", fill="x", padx=5)

    def browse(self):
        """Open filedialog for selecting a file."""
        if self.browse_type == "open":
            path = filedialog.askopenfilename(filetypes=self.file_filter)
        elif self.browse_type == "save":
            path = filedialog.asksaveasfilename()
        elif self.browse_type == "directory":
            path = filedialog.askdirectory()
        else:
            raise ValueError("Invalid browse type")
        self.set(path)
        return path

    def get(self):
        """Method to access the entry boxes, path and label (if labelEntry)."""
        return self.path.get()

    def set(self, value):
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

    def disable(self):
        """
        Disable method for class.
        """
        self.button.config(state="disabled")
        self.path.config(state="disabled")

    def enable(self):
        """
        Enable method for class.
        """
        self.button.config(state="normal")
        self.path.config(state="normal")


class LabelledTextEntry(ttk.Frame):
    """
    Simple text input box with a label.
    """

    def __init__(
        self,
        parent,
        label: str,
        variable: Optional[tk.StringVar] = None,
        label_width: int = 20,
        text_width=20,
    ):
        """
        Parameters
        ----------
        parent: tkinter container widget
            Parent container for storing the widget.
        label (str): Text used for labelling widget.
        label_width (int): Width of label.
        text_width (int): Width of text.
        variable (tk.StringVar): The variable linked to this input, if any.
        """
        super().__init__(parent)
        self.label = ttk.Label(self, text=label, width=label_width)
        if variable:
            self.text = ttk.Entry(self, width=text_width, textvariable=variable)
        else:
            self.text = ttk.Entry(self, width=text_width)
        self.label.pack(side="left", fill="x", padx=5)
        self.text.pack(side="left", fill="x", expand=True)

    def get(self):
        """
        Get method for class.
        """
        return self.text.get()

    def set(self, value):
        """
        Set method for class. Sets to value.
        """
        self.text.delete(0, len(self.text.get()))
        self.text.insert(0, value)

    def disable(self):
        """
        Disable method for class.
        """
        self.text.config(state="disabled")

    def enable(self):
        """
        Enable method for class.
        """
        self.text.config(state="normal")


class NumberScroller(ttk.Frame):
    """
    Number scroller class to add a number scroller.

    Parameters
    ----------
    parent: tkinter container widget
            Parent container for storing the widget.
    scroll_range: The range of numbers the scroller will scroll between.
    label (str): Label text.
    default_value (int): The value the scroller will start on.
    label_width (int): The width of the label.
    """

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

    def get(self):
        """
        Get method.
        Returns
        -------
        Int stored in link_var.
        """
        return self.link_var.get()

    def set(self, value):
        """
        Setter for class.
        Parameters
        ----------
        value: Value to set to.
        """
        self.scroller.set(value)

    def disable(self):
        """
        Disable mtehod for class.
        """
        self.scroller.config(state="disabled")

    def enable(self):
        """
        Enable method for class.
        """
        self.scroller.config(state="normal")


class ZoneFrame(ttk.LabelFrame):
    """
    Class for creating frames for TransZoneSystemInfo from the config class.

    This is currently not very customisable when called, but parameters passed
    to sub frames and widgets could be exposed.

    Parameters
    ----------
    parent: The parent frame this frame sits within.
    label: Passed to the 'text' parameter of LabelFrame.
    """

    def __init__(self, parent, label):
        super().__init__(parent, text=label)
        self.shape_var = tk.StringVar(value="")
        self.name_var = tk.StringVar(value="zone_name")
        self.id_col_var = tk.StringVar(value="shape_id_col")
        self.shapefile = FileWidget(
            self,
            label="Shapefile",
            browse="open",
            widths=(30, 15),
            file_filter=SHAPE_FILEFILTER,
            variable=self.shape_var,
        )
        self.name = LabelledTextEntry(
            self, label="Zone system name", text_width=10, variable=self.name_var
        )
        self.id_col = LabelledTextEntry(
            self, label="ID column name", text_width=10, variable=self.id_col_var
        )
        self.point_shapefile = FileWidget(
            self,
            label="Point shapefile",
            browse="open",
            widths=(30, 15),
            file_filter=SHAPE_FILEFILTER,
        )

        self.shapefile.grid(column=0, row=0, columnspan=3, sticky="ew", pady=5)
        self.name.grid(column=0, row=1, columnspan=3, sticky="ew", pady=5)
        self.id_col.grid(column=0, row=2, columnspan=3, sticky="ew", pady=5)
        self.point_shapefile.grid(column=0, row=3, columnspan=3, sticky="ew", pady=5)

    def disable(self):
        """
        Disable method for class.
        """
        self.shapefile.disable()
        self.name.disable()
        self.id_col.disable()
        self.point_shapefile.disable()

    def enable(self):
        """
        Enable method for class.
        """
        self.shapefile.enable()
        self.name.enable()
        self.id_col.enable()
        self.point_shapefile.enable()

    def get(self):
        """
        Get method for class.

        Returns
        -------
        Instance of TransZoneSystemInfo class with parameters read from UI.
        """
        if self.point_shapefile.get() == "":
            zone = inputs.TransZoneSystemInfo(
                shapefile=self.shape_var.get(),
                name=self.name_var.get(),
                id_col=self.id_col_var.get(),
            )
        else:
            zone = inputs.TransZoneSystemInfo(
                shapefile=self.shape_var.get(),
                name=self.name_var.get(),
                id_col=self.id_col_var.get(),
                point_shapefile=self.point_shapefile.get(),
            )
        return zone

    def validate(self):
        """
        Confirm that this frame is sufficiently provided.
        """
        return self.shape_var.get().endswith(".shp")


class LowerZoneFrame(ttk.LabelFrame):
    """
    Class for creating frames corresponding to the LowerZoneSystem class in inputs.

    This is currently not very customisable when called, but parameters passed
    to sub frames and widgets could be exposed.

    Parameters
    ----------
    parent: The parent frame this frame sits within.
    label: Passed to the 'text' parameter of LabelFrame.
    """

    def __init__(self, parent):
        super().__init__(parent, text="Lower Zone")
        self.shape_var = tk.StringVar(value="PATH/TO/LOWER/SHAPEFILE")
        self.weight_var = tk.StringVar(value="PATH/TO/WEIGHT/DATA")
        self.shapefile = FileWidget(
            self,
            label="Shapefile",
            browse="open",
            widths=(30, 15),
            file_filter=SHAPE_FILEFILTER,
            variable=self.shape_var,
        )
        self.name = LabelledTextEntry(self, label="Zone system name")
        self.id_col = LabelledTextEntry(self, label="ID column name")
        self.weight_data = FileWidget(
            self,
            label="Weight data",
            browse="open",
            widths=(30, 15),
            file_filter=CSV_FILEFILTER,
            variable=self.weight_var,
        )
        self.data_col = LabelledTextEntry(
            self,
            label="Weight data column",
            label_width=30,
            text_width=10,
        )
        self.weight_id_col = LabelledTextEntry(
            self, label="Weight id col", label_width=30, text_width=10
        )
        self.weight_data_year = LabelledTextEntry(
            self,
            label="Year of weight data",
            label_width=30,
            text_width=10,
        )

        self.shapefile.grid(column=0, row=0, columnspan=3, sticky="ew", pady=5)
        self.name.grid(column=0, row=1, columnspan=3, sticky="ew", pady=5)
        self.id_col.grid(column=0, row=2, columnspan=3, sticky="ew", pady=5)
        self.weight_data.grid(column=3, row=0, columnspan=3, sticky="ew", pady=5)
        self.data_col.grid(column=3, row=1, columnspan=3, sticky="ew", pady=5)
        self.weight_id_col.grid(column=3, row=2, columnspan=3, sticky="ew", pady=5)
        self.weight_data_year.grid(column=3, row=3, columnspan=3, sticky="ew", pady=5)

    def disable(self):
        """
        Disable method for class.
        """
        self.shapefile.disable()
        self.name.disable()
        self.id_col.disable()
        self.weight_data.disable()
        self.data_col.disable()
        self.weight_id_col.disable()
        self.weight_data_year.disable()

    def enable(self):
        """
        Enable method for class.
        """
        self.shapefile.enable()
        self.name.enable()
        self.id_col.enable()
        self.weight_data.enable()
        self.data_col.enable()
        self.weight_id_col.enable()
        self.weight_data_year.enable()

    def get(self):
        """
        Get method for class.
        Returns
        -------
        Instance of LowerZoneSystemInfo class with parameters read from UI.
        """
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

    def validate(self):
        """
        Validate that paths used for lower zoning are provided.

        This is a very weak validation, as all parameters are more rigorously
        validated by the config class they are passed to from the UI.

        Returns
        -------
        Bool
        """
        return self.shape_var.get().endswith(".shp") and self.weight_var.get().endswith(".csv")


class ParametersFrame(ttk.LabelFrame):
    """
    Frame for main parameters for ZoneTranslationInputs class.

    This frame contains all parameters which aren't stores within either
    zone system info class

    Parameters
    ----------
    parent: Parent frame
    """

    def __init__(self, parent):
        super().__init__(parent, text="Parameters")
        self.method_var = tk.StringVar()
        self.handling_var = tk.BooleanVar()
        self.rounding_var = tk.BooleanVar(value=True)
        self.slivers_var = tk.BooleanVar(value=True)
        self.cache_var = tk.StringVar(value=inputs.CACHE_PATH)
        self.output_var = tk.StringVar(value="path/to/output/folder")
        self.cache_folder = FileWidget(
            self,
            label="Cache Path",
            browse="directory",
            widths=(20, 15),
            variable=self.cache_var,
        )
        self.output_folder = FileWidget(
            self,
            label="Output Folder",
            browse="directory",
            widths=(20, 15),
            variable=self.output_var,
        )
        self.method = LabelledTextEntry(
            self,
            label="Method name",
            variable=self.method_var,
            label_width=15,
            text_width=10,
        )
        self.method_var.trace_add("write", self.activate_lower)
        self.lower = LowerZoneFrame(self)
        self.lower.disable()
        self.zone_1 = ZoneFrame(self, "zone 1")
        self.zone_2 = ZoneFrame(self, "zone 2")

        self.sliver_tolerance = NumberScroller(
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
            command=partial(
                self.activator, var=self.handling_var, widget=self.point_tolerance
            ),
        )

        self.filter_slithers = ttk.Checkbutton(
            self,
            text="Filter out slivers?",
            variable=self.slivers_var,
            command=partial(
                self.activator, var=self.slivers_var, widget=self.sliver_tolerance
            ),
        )

        self.cache_folder.grid(column=0, row=0, columnspan=3, sticky="ew", pady=5)
        self.output_folder.grid(column=3, row=0, columnspan=3, sticky="ew", pady=5)
        self.filter_slithers.grid(column=0, columnspan=2, row=1, sticky="sw", pady=10)
        self.rounding.grid(column=2, columnspan=2, row=1, sticky="sw", pady=10)
        self.point_handling.grid(column=4, columnspan=2, row=1, sticky="sw", pady=10)
        self.sliver_tolerance.grid(column=0, row=2, columnspan=2, sticky="s", pady=5)
        self.point_tolerance.grid(column=2, row=2, columnspan=2, sticky="s", pady=5)
        self.method.grid(column=4, row=2, columnspan=2, sticky="ew", pady=5)
        self.zone_1.grid(column=0, row=4, columnspan=3, sticky="nsew", pady=5)
        self.zone_2.grid(column=3, row=4, columnspan=3, sticky="nsew", pady=5)
        self.lower.grid(column=0, row=5, columnspan=6, sticky="s", pady=5)

    def activator(self, var, widget):
        """
        Method used as a command argument within ttk.Checkbox objects,
        Parameters
        ----------
        var: The variable connected to the checkbox.
        widget: The widget being toggled by the checkbox.

        Returns
        -------

        """
        if var.get():
            widget.enable()
        else:
            widget.disable()

    def activate_lower(self, *args):
        """
        Toggles the lower frame based on whether there is any text in method.
        """
        if len(self.method_var.get()) > 0:
            self.lower.enable()
        else:
            self.lower.disable()

    def get(self):
        """
        Get method for parameters.

        Returns
        -------
        A dictionary of parameters from the ui in the correct format to be
        passed to ZoningTranslationInputs.
        """
        if len(self.method_var.get()) > 0:
            lower = self.lower.get()
        else:
            lower = None
        zone_1 = self.zone_1.get()
        zone_2 = self.zone_2.get()
        conf = inputs.ZoningTranslationInputs(
            zone_1=zone_1,
            zone_2=zone_2,
            lower_zoning=lower,
            cache_path=Path(self.cache_var.get()),
            filter_slivers=self.slivers_var.get(),
            point_handling=self.handling_var.get(),
            method=self.method_var.get(),
            sliver_tolerance=self.sliver_tolerance.get() / 100,
            point_tolerance=self.point_tolerance.get(),
            rounding=self.rounding_var.get(),
        )

        return conf, Path(self.output_var.get())


class UiTab(ttk.Frame):
    """
    The tab containing the inputs for zone translations.
    """

    def __init__(self, master=None):
        super().__init__(master)
        self.main_params = ParametersFrame(self)
        self.main_params.zone_1.shape_var.trace_add("write", self.activate_spatial)
        self.main_params.zone_1.shape_var.trace_add("write", self.activate_weighted)
        self.main_params.zone_2.shape_var.trace_add("write", self.activate_spatial)
        self.main_params.zone_2.shape_var.trace_add("write", self.activate_weighted)
        self.main_params.lower.shape_var.trace_add("write", self.activate_weighted)
        self.main_params.lower.weight_var.trace_add("write", self.activate_weighted)
        self.weighted_button = ttk.Button(
            self, text="Weighted translation", command=self.run_weighted
        )
        self.weighted_button.config(state="disabled")
        self.spatial_button = ttk.Button(
            self, text="Spatial translation", command=self.run_spatial
        )
        self.spatial_button.config(state="disabled")

        self.main_params.grid(
            column=0,
            row=0,
            rowspan=3,
            columnspan=2,
            sticky="ew",
            pady=5,
        )
        self.weighted_button.grid(column=0, columnspan=1, row=3, sticky="ew", pady=1, padx=1)
        self.spatial_button.grid(column=1, columnspan=1, row=3, sticky="ew", pady=1, padx=1)

    def activate_spatial(self, *args):
        """
        Toggles the run spatial button depending on provided parameters.
        """
        if self.main_params.zone_2.validate() and self.main_params.zone_1.validate():
            self.spatial_button.config(state="normal")
        else:
            self.spatial_button.config(state="disabled")

    def activate_weighted(self, *args):
        """
        Toggles the run weighted button depending on provided parameters.
        """
        if (
            self.main_params.zone_1.validate()
            and self.main_params.zone_2.validate()
            and self.main_params.lower.validate()
        ):
            self.weighted_button.config(state="normal")
        else:
            self.weighted_button.config(state="disabled")

    def run_weighted(self):
        """
        Function controlled by run weighted button.

        Gets parameters from UI inputs, passes them to a config class, and uses
        them to generate a weighted translation, which is saved to the output
        path.
        """
        params, output_path = self.main_params.get()
        trans = zone_translation.ZoneTranslation(params)
        trans.weighted_translation().to_csv(
            output_path / f"{params.zone_1.name}_{params.zone_2.name}_{params.method}.csv"
        )

    def run_spatial(self):
        """
        Function controlled by run spatial button.

        Gets parameters from UI inputs, passes them to a config class, and uses
        them to generate a spatial translation, which is saved to the output
        path.
        """
        params, output_path = self.main_params.get()
        trans = zone_translation.ZoneTranslation(params)
        trans.spatial_translation().to_csv(
            output_path / f"{params.zone_1.name}_{params.zone_2.name}_spatial.csv"
        )


class ConsoleFrame(ttk.Frame):
    """Frame containing the console."""

    class StdoutRedirector:
        """
        Class for redirecting.
        """

        def __init__(self, text_widget):
            self.text_space = text_widget
            self.text_space.tag_configure("n", font=("Calibri", 12))

        def write(self, string):
            """
            Turns on write, writes output then disables.
            """
            self.text_space.config(state="normal")
            self.text_space.insert("end", string, "n")
            self.text_space.see("end")
            self.text_space.config(state="disabled")

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
        self.text.tag_configure("warning", foreground="orange")
        self.text.tag_configure("error", foreground="red")
        self.text.tag_configure("debug", foreground="gray")
        self.text.pack(side="left", fill="both", expand=True)


class NotebookApp(tk.Tk):
    """
    Main notebook, containing three pages.

    One for the UI, one for the documentation, one for the console.
    """

    def __init__(self):
        super().__init__()
        # self.logger = logging.getLogger("SPACE")
        self.notebook = Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        # Add MyUI instance as a tab
        my_ui_tab = ttk.Frame(self.notebook)
        my_ui = UiTab(master=my_ui_tab)
        my_ui.pack(fill="both", expand=True)
        self.notebook.add(my_ui_tab, text="Zone translation parameters")
        readme_tab = HtmlFrame(self.notebook, messages_enabled=False)
        readme_tab.load_website("https://cafspcae.readthedocs.io/en/latest/")
        self.notebook.add(readme_tab, text="Documentation")
        console_tab = ttk.Frame(self.notebook)
        self.console_text = ConsoleFrame(console_tab)
        self._redirect_logging()
        self.console_text.pack(fill="both", expand=True)
        self.notebook.add(console_tab, text="Console Output")
        self.mainloop()

    def _redirect_logging(self):
        """Add new handler to root logger which outputs to `self.terminal`."""
        self._logger = logging.getLogger("SPACE")
        self.console_handler = logging.StreamHandler(stream=RedirectStdOut(self.console_text))
        fmt = logging.Formatter("[{levelname}] {message}", style="{")
        self.console_handler.setFormatter(fmt)
        self.console_handler.setLevel(logging.INFO)
        self._logger.addHandler(self.console_handler)
        self._logger.info("Log file saved here: %s", (Path(os.getcwd()) / SpaceUI._LOG_NAME))


class SpaceUI:
    """
    Main class to launch UI.
    """

    _LOG_NAME = "SPACE.log"

    def __init__(self):
        self.log_file = Path(os.getcwd()) / self._LOG_NAME
        # Remove log file if present
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

        # Initiate logger object
        self.logger = logging.getLogger("SPACE")
        self.logger.setLevel(logging.DEBUG)

        # Create file handler which logs everything
        f_h = logging.FileHandler(self.log_file)
        f_h.setLevel(logging.DEBUG)

        # Create formatter and add to handlers
        fmt = logging.Formatter(
            "%(asctime)s [%(name)-20.20s] [%(levelname)-8.8s]  %(message)s"
        )
        f_h.setFormatter(fmt)
        self.logger.addHandler(f_h)
        # Start it with initial line
        self.logger.info("Initialised log file.")
        self._gui = NotebookApp()


# pylint: enable=too-many-ancestors, too-many-instance-attributes, unused-argument
