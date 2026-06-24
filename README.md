# Bike Net Kit / Fix Bike Net

[![Docs](https://github.com/BikeNetKit/FixBikeNet/actions/workflows/docs.yml/badge.svg)](https://bikenetkit.github.io/FixBikeNet/)
[![Test](https://github.com/BikeNetKit/FixBikeNet/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/BikeNetKit/FixBikeNet/actions/workflows/test.yml)
[![PyPI - Version](https://img.shields.io/pypi/v/fixbikenet)](https://pypi.org/project/FixBikeNet/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![Human created](https://raw.githubusercontent.com/BikeNetKit/.github/refs/heads/main/profile/_static/badge_humancreated.svg)

The Python package `fixbikenet` identifies the most important gaps to fill in a city's bicycle network. 

The software downloads and pre-processes data from OpenStreetMap, identifies the gaps, saves the results, creates plots and videos. The source code builds on [the code from the research paper](https://github.com/anastassiavybornova/bikenwgaps) _Automated Detection of Missing Links in Bicycle Networks_.


**Publication**: [https://doi.org/10.1111/gean.12324](https://doi.org/10.1111/gean.12324)


## Installation

### The easy way

The currently default way to install FixBikeNet is using pip:

```
pip install fixbikenet
```

<!-- > [!IMPORTANT]  
> As of 2026-05-04, the conda-forge installation is not yet working. We will remove this note once it works.

The best way to install FixBikeNet is using [`conda`](https://docs.conda.io/projects/conda/en/latest/index.html) and the `conda-forge` channel:

```
conda install -c conda-forge fixbikenet
``` -->

If this does not work, consult our [installation docs](https://bikenetkit.github.io/FixBikeNet/installation/).

### Advanced and development installations
 See our [installation docs](https://bikenetkit.github.io/FixBikeNet/installation/) for details.

## Usage

We provide a minimum working example in two formats:

- Python script ([examples/mwe.py](examples/mwe.py))
- Jupyter notebook ([examples/mwe.ipynb](examples/mwe.ipynb))

## Docs
Find more information in our docs: [https://bikenetkit.github.io/FixBikeNet/](https://bikenetkit.github.io/FixBikeNet/)


## Supported by
Development of BikeNetKit/FixBikeNet was supported by the [Innovation Fund Denmark](https://innovationsfonden.dk/en) and the EU HORIZON project [JUST STREETS](https://www.just-streets.eu).


[![Innovation Fund Denmark](https://raw.githubusercontent.com/BikeNetKit/.github/refs/heads/main/profile/_static/logo_innovationfund.png)](https://innovationsfonden.dk/en) &emsp;&emsp; [![European Union](https://raw.githubusercontent.com/BikeNetKit/.github/refs/heads/main/profile/_static/logo_eu.png)](https://commission.europa.eu/index_en) &ensp; [![JUST STREETS](https://raw.githubusercontent.com/BikeNetKit/.github/refs/heads/main/profile/_static/logo_juststreets.png)](https://www.just-streets.eu/) 
