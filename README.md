![Transport for the North Logo](https://github.com/Transport-for-the-North/caf.toolkit/blob/main/docs/TFN_Landscape_Colour_CMYK.png)

<h1 align="center">CAF.Space</h1>

<p align="center">
<a href="https://pypi.org/project/caf.space/"><img alt="Supported Python versions" src="https://img.shields.io/pypi/pyversions/caf.space.svg?style=flat-square"></a>
<a href="https://pypi.org/project/caf.space/"><img alt="Latest release" src="https://img.shields.io/github/release/transport-for-the-north/caf.space.svg?style=flat-square&maxAge=86400"></a>
<a href="https://app.codecov.io/gh/Transport-for-the-North/caf.space"><img alt="Coverage" src="https://img.shields.io/codecov/c/github/transport-for-the-north/caf.space.svg?branch=master&style=flat-square&logo=CodeCov"></a>
<a href="https://github.com/Transport-for-the-North/caf.space/actions?query=event%3Apush"><img alt="Testing Badge" src="https://img.shields.io/github/actions/workflow/status/transport-for-the-north/caf.space/tests.yml?style=flat-square&logo=GitHub&label=Tests"></a>
<a href="https://www.gnu.org/licenses/gpl-3.0.en.html"><img alt="License: GNU GPL v3.0" src="https://img.shields.io/badge/license-GPLv3-blueviolet.svg?style=flat-square"></a>
<a href="https://github.com/psf/black"><img alt="code style: black" src="https://img.shields.io/badge/code%20format-black-000000.svg?style=flat-square"></a>
</p>

Common Analytical Framework (CAF) Space contains geo-processing functionality useful
for transport planners. Primarily it is a tool for generating standard weighting
translations in .csv format describing how to convert between different zoning systems.
The aim is to free tools up from directly having to do their own geo-processing, and    
instead have a single source of truth to get them from! For more info see https://cafspcae.readthedocs.io/en/latest/.

<u><h3> Tool info </h3></u>
The tool has two main options for running a translation, either a purely spatial translation (where overlapping zones are split by area), or a weighted translation where overlapping zones are split by some other type of weighting data like population or employment data. For most purposes a weighted translation will be more accurate, and it is up to the user to decide the most appropriate weighting data to use. For both types of translation the tool runs from a set of parameters within a config class. If you are using the GUI then provide parameters in the first tab. If you are not using the GUI a instance of inputs.ZoningTranslationInputs is required. This can either be loaded from a yaml file, or initialised in the code.

<u><h3> Command Line Tool </h3></u>
The tool can be run from command line, with the command:

<b> python -m caf.space </b>

This can be run with no arguments, which will launch the GUI, but there are also 3 arguments for running in different modes.:
* <b> mode: --mode</b> must be either "GUI" (default value), "spatial", or "weighted". "Gui" launches the GUI and the other two produce spatial or weighted zone translations respectively.
* <b> config_path: --config</b> must be provided if mode is either "spatial" or "weighted". This is a path to the config file containing parameters for that translation.
* <b> out_path: --out_path</b> must be provided if either "spatial" or "weighted". This is the directory you want your translation saved to. This directory must exist and will not be generated internally.

Running with all three arguments would look like:

<b> python -m caf.space --mode "spatial" --config "path/to/config.yml" --out_path "path/to/output/folder" </b>

<u><h4> Spatial Correspondence </h4></u>
For a spatial correspondence, the only user inputs needed are shapefiles for the two zone systems you want a translation between. The parameters required for a spatial translation are as follows:

* <b> zone_1:</b><br>
    <b>name:</b> The name of the first zone system you are providing. This should be as simple as possible, so for an MSOA shapefile, name should simply be MSOA.<br>
    <b>shapefile:</b> A file path to the shapefile you want a translation for.<br>
    <b>id_col:</b> The name of the unique ID column in your chosen shapefile. This can be any column as long as it is unique for each zone in the shapefile.<br>
    <b>point_shapefile (OPTIONAL):</b> A path to a point shapefile if you want to include true point features in a zone system.<br>
* <b> zone_2:</b> Parameters the same as for zone_1, it doesn't matter which order these are in, a two-way translation will be created.</b><br>
* <b>cache_path:</b> File path to a cache of existing translations. This defaults to a location on a network drive, and it is best to keep it there if you have access to it.<br>
* <b>sliver_tolerance:</b> This is a float less than 1, and defaults to 0.98. If filter_slivers (explained below) is chosen, tolerance controls how big or small the slithers need to be to be rounded away. For most users this can be kept as is.<br>
* <b>rounding:</b> True or False. Select whether or not zone totals will be rounded to 1 after the translation is performed. Recommended to keep as True.<br>
* <b>filter_slivers:</b> True or False. Select whether very small overlaps between zones will be filtered out. This accounts for zone boundaries not aligning perfectly when they should between shapefiles, and the tolerance for this is controlled by the tolerance parameter. With this parameter set to false translations can be a bit messy.<br>
<br>
The translation will be output as a csv to your output path location, in a folder named by the names selected for each zone system. Along with the csv will be a yml file containing the parameters the translation was run with, along with the date of the run.<br>
<br>
<u><h4> Weighted Correspondence </h4></u>
For a weighted translation more parameters must be provided. The tool creates a weighted translation by first joining weighting data to a lower zone system - this is a zone system smaller than the two primary zone systems. Overlaps are then found between the three zone systems to create a set of weighted tiles across the extent of the zones. These tiles are then used to create the translation. There is a more detailed explanation of this process in the documentation. Below are the additional parameters required for a weighted translation rather than a spatial one.<br>

* <b>lower_zoning:</b> lower_zoning is a subclass of the class used for zones 1 and 2, the first three parameters for this are the same as for zones 1 and 2. The additional parameters required for lower zoning are:<br>
    <b>weight_data</b>: File path to the weighting data for the lower zone system. This should be saved as a csv, and only needs two columns (an ID column and a column of weighting data)<br>
    <b>data_col:</b> The name of the column in the weighting data csv containing the weight data.<br>
    <b>weight_id_col:</b> The name of the columns in the weighting data containing the zone ids. This will be used to join the weighting data to the lower zoning, so the IDs must match, but the names of the ID columns may be different.<br>
    <b>weight_data_year:</b> Integer. The year the weighting data is for. This is a required parameter, if you don't know when your weight data is from you should consider whether to use it. If you are using it anyway, set this to 1.<br>
* <b>method:</b> The name of the method used for weighting (e.g. pop or emp). This can be anything, but must be included as the tool checks if this parameter exists to decide whether a weighted translation can be performed.<br>
* <b>point_handling:</b> True or False. Choose whether point and pseudo point zones will be treated specially. For an explanation of how point zones are handled see the full documentation on readthedocs.<br>
* <b>point_tolerance:</b> Int. The area below which polygon zones will be treated as point zones in a translation. This is only needed if point_handling is selected.
