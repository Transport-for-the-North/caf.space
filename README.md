<div align="center" style="background-color: white;">
<a href="https://www.transportforthenorth.com/">
<img src="https://www.transportforthenorth.com/wp-content/themes/tfn-theme/img/logo.svg"
  alt="Transport for the North logo">
</a>
</div>

<h1 align="center">CAF.Space</h1>

<p align="center">
<a href="https://transport-for-the-north.github.io/CAF-Handbook/python_tools/framework.html">
  <img alt="CAF Status - Release" src="https://img.shields.io/badge/CAF%20Status-Release-green">
</a>
</p>
<p align="center">
<a href="https://pypi.org/project/caf.space/">
  <img alt="Supported Python versions" src="https://img.shields.io/pypi/pyversions/caf.space.svg?style=flat-square">
</a>
<a href="https://pypi.org/project/caf.space/">
  <img alt="Latest release" src="https://img.shields.io/github/release/Transport-for-the-North/caf.space.svg?style=flat-square&maxAge=86400">
</a>
<a href="https://anaconda.org/conda-forge/caf.space">
  <img alt="Conda" src="https://img.shields.io/conda/v/conda-forge/caf.space?style=flat-square&logo=condaforge">
</a>
</p>
<p align="center">
<a href="https://github.com/Transport-for-the-North/caf.space/actions?query=event%3Apush">
  <img alt="Testing Badge" src="https://img.shields.io/github/actions/workflow/status/Transport-for-the-North/caf.space/tests.yml?style=flat-square&logo=GitHub&label=Tests">
</a>
<a href="https://app.codecov.io/gh/Transport-for-the-North/caf.space">
  <img alt="Coverage" src="https://img.shields.io/codecov/c/github/Transport-for-the-North/caf.space.svg?branch=main&style=flat-square&logo=CodeCov">
</a>
<a href='https://cafspace.readthedocs.io/en/stable/'>
  <img alt='Documentation Status' src="https://img.shields.io/readthedocs/cafspace?style=flat-square&logo=readthedocs">
</a>
<a href="https://github.com/psf/black">
  <img alt="code style: black" src="https://img.shields.io/badge/code%20format-black-000000.svg">
</a>
</p>

CAF.space contains geo-processing functionality useful for transport planners. Primarily it is a tool
for generating standard weighting translations describing how to convert between different zoning systems.

The aim is to free tools up from directly having to do their own geo-processing, and instead have
a single source of truth to get them from!

> [!TIP]
> For more detailed information including a user guide, tutorials and API reference see the full
> [caf.space documentation](https://cafspace.readthedocs.io/en/stable/)

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Overview](#overview)
  - [What does it do?](#what-does-it-do)
  - [Main Features](#main-features)
    - [Work-in-Progress](#work-in-progress)
  - [Who is it for?](#who-is-it-for)
- [Where to get it](#where-to-get-it)
  - [Installation from GitHub](#installation-from-github)
- [Usage](#usage)
  - [Command Line](#command-line)
  - [Graphical Interface](#graphical-interface)
- [Documentation](#documentation)
- [What is CAF?](#what-is-caf)
- [Contribution](#contribution)
- [Contact Us](#contact-us)

## Overview

### What does it do?

CAF.space is primarily a tool used for the translation of data between different zoning systems, supporting
both spatial and weighted translations. The tools also includes functionality for producing correspondences
between other GIS data types and more general GIS functionality.

### Main Features

- **Zone correspondence** - Produce a correspondence file between two transport zone systems (GIS Polygons) to translate datasets.
  - **Spatial correspondence** - A basic correspondence using the overlap of the polygons in the two zone systems, handles
    correspondences with many to many relationships by providing translation factors.
  - **Weighted correspondence** - Apply weightings to the spatial correspondence to consider the contents of a zone, e.g. zone population or employment.
    This method generally performs better than the simpler spatial correspondence, so should be used when possible.
  - **Handles point-like features** - Airports, ports and special generators need special handling because their demand is not proportional to their geographic area.
- **General GIS functionality** - Reading and writing GIS files ([caf.space.inputs](https://cafspace.readthedocs.io/en/stable/_autosummary/caf.space.inputs.html#module-caf.space.inputs))
  and handling GIS data within Python.

#### Work-in-Progress

- **Line to line correspondence** - Two sets of GIS lines datasets e.g. representing transport networks.
- **Line to polygon correspondence** - Correspondence between lines and zones (GIS polygons) datasets.

> [!WARNING]
> These features are work-in-progress and are not available in a released version of caf.space, to
> access these features a specific branch of caf.space should be installed, see [Installation from GitHub](#installation-from-github).

### Who is it for?

- **Target audience:** Transport Modellers, Transport Planners, GIS Specialists
- **CAF Analytical Stage:** Analysis

![CAF Analytical Process Diagram](https://github.com/Transport-for-the-North/.github/blob/21a428e81880639839e221940881572cdee24d5a/profile/ProcessDiagram.png?raw=true)

For more details on CAF Analytical Stages see the [description within TfN's GitHub homepage](https://github.com/Transport-for-the-North)

## Where to get it

The latest released version are available at the [Python
Package Index (PyPI)](https://pypi.org/project/caf.space) and on [Conda](https://anaconda.org/conda-forge/caf.space).

```sh
conda install -c conda-forge caf.space
```

```sh
pip install caf.space
```

> [!TIP]
>
> - See the [Quick Start Guide](https://cafspace.readthedocs.io/en/stable/start.html#quick-start) for more detailed instructions.
> - See the [requirements.txt](requirements.txt) for the full list of package dependencies.

### Installation from GitHub

> [!WARNING]
> Unreleased GitHub versions should **not** be considered stable.

The latest, unreleased, version can be installed directly from GitHub using:

```sh
pip install "git+https://github.com/Transport-for-the-North/caf.space"
```

> [!TIP]
> `pip install` can install a specific tag, or branch, using `@{tag-name}`
> after the git URL.

## Usage

CAF.space provides and Command-line (CLI) and graphical interface (GUI) to use many of it's
features without the need to write any Python code, see the [Tool Usage section](https://cafspace.readthedocs.io/en/stable/usage/index.html)
of the user guide for more details.

### Command Line

The tool can be run from command line, with the command:

```sh
caf.space --mode "mode-value" --config "path/to/config.yml" --out_path "path/to/output/folder"
```

See [Command-Line Interface (User Guide)](https://cafspace.readthedocs.io/en/stable/usage/cli.html)
for full explanations of the parameters.

### Graphical Interface

Running caf.space without any arguments will open the GUI to provide parameters and run
the tool, see [Graphical User Interface (User Guide)](https://cafspace.readthedocs.io/en/stable/usage/gui.html#graphical-user-interface)
for more details.

```sh
caf.space
```

![Example GUI](https://cafspace.readthedocs.io/en/latest/_images/guispace.png)

## Documentation

The code documentation is hosted at <https://cafspace.readthedocs.io/en/latest/>.

## What is CAF?

This tool is part of TfN's [Common Analytical Framework (CAF)](https://github.com/Transport-for-the-North).
CAF is Transport for the North's structured suite of analytical tools designed to support transport
modelling, appraisal, and strategic decision-making.

More information on CAF and details on other CAF tools can be found on [TfN's GitHub Homepage](https://github.com/Transport-for-the-North).

## Contribution

We encourage use of, and contributions to, the repositories within this organisation, licenses are provided within
the repositories and the [organisation contribution guide](https://github.com/Transport-for-the-North/.github/blob/main/CONTRIBUTING.rst)
provides details for contributions.

---

## Contact Us

For further information about using this tool or CAF tools in your projects and work contact Transport for the North - <TfNOffer@transportforthenorth.com>

---

[Go to Top](#table-of-contents)
