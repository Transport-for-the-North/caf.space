<div align="center" style="background-color: white;">
<a href="https://www.transportforthenorth.com/">
<img src="https://www.transportforthenorth.com/wp-content/themes/tfn-theme/img/logo.svg"
  alt="Transport for the North logo">
</a>
</div>

<h1 align="center">Caf.Space</h1>

[comment]: <> (Update "{package-name}" references in below)

<p align="center">
  <a href="https://pypi.org/project/caf.space/"><img alt="Latest release" src="https://img.shields.io/github/release/transport-for-the-north/caf.space.svg?style=flat-square&maxAge=86400"></a>
  <a href="https://pypi.org/project/caf.space/"><img alt="Supported Python versions" src="https://img.shields.io/pypi/pyversions/caf.space.svg?style=flat-square"></a>
</p>
<p align="center">
  <a href="https://app.codecov.io/gh/Transport-for-the-North/caf.space"><img alt="Coverage" src="https://img.shields.io/codecov/c/github/transport-for-the-north/caf.space.svg?branch=master&style=flat-square&logo=CodeCov"></a>
  <a href="https://github.com/Transport-for-the-North/caf.space/actions?query=event%3Apush"><img alt="Testing Badge" src="https://img.shields.io/github/actions/workflow/status/transport-for-the-north/caf.space/tests.yml?style=flat-square&logo=GitHub&label=Tests"></a>
  <a href='https://cafspace.readthedocs.io/en/stable/?badge=stable'><img alt='Documentation Status' src="https://img.shields.io/readthedocs/cafspace?style=flat-square&logo=readthedocs"></a>
  <a href="https://github.com/psf/black"><img alt="code style: black" src="https://img.shields.io/badge/code%20format-black-000000.svg?style=flat-square"></a>
</p>

# CAF.space
CAF.space contains geo-processing functionality useful for transport planners. Primarily it is a tool for generating standard weighting translations in .csv format describing how to convert between different zoning systems.

The aim is to free tools up from directly having to do their own geo-processing, and instead have a single source of truth to get them from! 

## Table of Contents 
- [Overview](#overview)
  - [Who is it for?](#who-is-it-for)
  - [When should I use this tool?](#when-should-i-use-this-tool)
- [Key Inputs and Outputs](#key-inputs-and-outputs)
  - [Key Inputs](#key-inputs)
  - [Key Outputs](#key-outputs)
- [Getting Started](#getting-started)
  - [Package Dependencies](#package-dependencies)
  - [Installation](#installation)
  - [Running the Tool](#running-the-tool)
- [Documentation](#documentation)
- [What is CAF?](#what-is-caf)
  - [Related CAF Tools](#related-caf-tools)
  - [Contribution](#contribution)
- [Contact Us](#contact-us)

## Overview
### What does it do?
CAF.space is a tool used for the translation of data between different zones, supporting both spatial and non-spatial, weighted translations.

The tool has two main options for running a translation, either a purely spatial translation (where overlapping zones are split by area), or a weighted translation where overlapping zones are split by some other type of weighting data like population or employment data. For most purposes a weighted translation will be more accurate, and it is up to the user to decide the most appropriate weighting data to use. For both types of translation the tool runs from a set of parameters within a config class. If you are using the GUI then provide parameters in the first tab. If you are not using the GUI a instance of `inputs.ZoningTranslationInputs is required. This can either be loaded from a yaml file, or initialised in the code.

Consumes geospatial files to perform translations:
- **Spatial Translations**  - Where overlapping zones are split by area.
- **Weighted Translations** - Where overlapping zones are split by some other type of weighting data like population or employment data.

For most purposes a weighted translation will be more accurate, and it is up to the user to decide the most appropriate weighting data to use. 

For both types of translation the tool runs from a set of parameters within a configuration class. 

Here are the core features of the CAF.space tool:

- Spatial Translations - splitting overlapping zones only through the area without use of any weighting data.
- Weighted Translations - as above but using an additional weigting factor - e.g. population.
- Flexible configuration and running options.
- Cache path - To provide a source of run calculations and avoid duplication of results.

### Who is it for?

![CAF Analytical Process Diagram](ProcessDiagram.png)

| Target Audience                    | CAF Analytical Stage                      |
| :--------------------------------: | :---------------------------------------- |
|  Transport Modellers, Transport Planners, GIS Specialists         | Analysis       |

For more details on CAF Analytical Stages see the [description within TfN's GitHub homepage](https://github.com/Transport-for-the-North)


### When should I use this tool? 
This tool should be used in cases where you need to translate data between zoning systems. It considers the following:

- Zones may not align cleanly between two systems (Z1 and Z2), meaning many zones overlap only partially or in irregular ways.
- Population or employment are unevenly distributed within zones
- Point-like features (e.g., airports, ports, special generators) need special handling because their demand is not proportional to their geographic area

## Key Inputs and Outputs
### Key Inputs
This tool requires the following key inputs:

| Input                   | File Type       | Description                                                          |
| :----------------------: | :-------------- | :------------------------------------------------------------------: |
| Zoning System 1 Shapefile                 | .shp        | Shapefile for zoning system 1, including an ID column with zone name |
| Zoning System 2 Shapefile                 | .shp        | Shapefile for zoning system 2, including an ID column with zone name |

This tool requires the following optional inputs:

| Input                   | File Type       | Description                                                          |
| :----------------------: | :-------------- | :------------------------------------------------------------------: |
| Weighting data                 | .csv        | Weightings for zoning system based on ID column |


### Key Outputs
This tool produces the following main outputs:

| Output                   | File Type       | Description                                                          |
| :----------------------: | :-------------- | :------------------------------------------------------------------: |
| Translation between zoning system 1 and 2                 | .csv        | Zoning system 1 and 2 translation file either split by area or weighted |


## Getting Started
This section details high-level installation instructions as well as any key additional requirements that you would need to run this tool, including key package dependencies, and hardware requirements.

Further detail on specific options and tool configuration are provided in the code documentation: [https://cafspace.readthedocs.io/en/latest/](https://cafspace.readthedocs.io/en/latest/.)

### Package Dependencies
This tool has key dependencies on the following packages:
- caf.toolkit
- geopandas
- shapely

See requirements.txt for the full list of package dependencies.

### Installation
CAF.space is a python tool which can be accessed by two main methods:

Can be installed by running:

```sh
pip install caf.space
```
Or, by downloading the source code from the repository and running:

```sh
pip install ./
```
from inside the cloned repository.

### Running the Tool
CAF.space is designed to be run locally on the user's machine after being installed following the above steps.

The tool has two main methods of being operated, using either a command line interface via, for example, the windows command prompt - or - running the built-in graphical interface.

### _Command Line_
The tool can be run from command line, with the command:
```sh
python -m caf.space --mode "mode-value" --config "path/to/config.yml" --out_path "path/to/output/folder"
```

### _Graphical Interface_

The tool will create a pop-up GUI when the `--mode` argument is either omitted, or set to "GUI"
```sh
python -m caf.space --mode "GUI"
```

  <a href="https://cafspace.readthedocs.io/">
    <img src="https://cafspace.readthedocs.io/en/latest/_images/guispace.png" alt="Example GUI">
  </a>

Within this window the fields must be filled out in order to run the tool, with descriptions below for how to fill them in. There is also a ‘Console Output’ window, which will display messaged raised by the tool. This can be useful to check if a translation fails for some reason, as it will give information on which setting caused the issue, such as a path provided which does not exist.

## Documentation
The code documentation is hosted at [https://cafspace.readthedocs.io/en/latest/](https://cafspace.readthedocs.io/en/latest/.)

## What is CAF?
This tool is part of TfN's [**Common Analytical Framework (CAF)**](https://github.com/Transport-for-the-North). CAF is Transport for the North's structured suite of analytical tools designed to support transport modelling, appraisal, and strategic decision-making.

CAF provides a consistent, transparent and reusable approach to:

-   Processing transport datasets
-   Developing modelling inputs
-   Running analytical workflows
-   Supporting forecasting and appraisal
-   Generating outputs for policy and business case development

CAF improves confidence, consistency and efficiency across TfN projects and partner organisations.

### Related CAF Tools
Details on all the other CAF tools can be found on the [TfN Homepage](https://github.com/Transport-for-the-North)

### Contribution
We encourage use of, and contributions to, the repositories within this organisation, licenses are provided within our repositories and contribution guidelines are outlined [here](https://github.com/Transport-for-the-North/.github/blob/main/CONTRIBUTING.rst).

------------------------------------------------------------------------

# Contact Us

For further information about using this tool or CAF tools in your projects and work contact Transport for the North - <TfNOffer@transportforthenorth.com>

<hr>

[Go to Top](#table-of-contents)
