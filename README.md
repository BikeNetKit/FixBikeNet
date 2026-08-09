# <a href="https://docs.bikenetkit.org/FixBikeNet/"><img src="docs/source/_static/logo_fixbikenet.svg" alt="FixBikeNet" width="254.65" height="59"></a>

[![PyPI Version](https://img.shields.io/pypi/v/fixbikenet?color=10d249)](https://pypi.org/project/FixBikeNet/)
[![Docs](https://github.com/BikeNetKit/FixBikeNet/actions/workflows/docs.yml/badge.svg)](https://bikenetkit.github.io/FixBikeNet/)
[![Test](https://github.com/BikeNetKit/FixBikeNet/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/BikeNetKit/FixBikeNet/actions/workflows/test.yml)
[![Code coverage](https://codecov.io/gh/BikeNetKit/FixBikeNet/graph/badge.svg)](https://codecov.io/gh/BikeNetKit/FixBikeNet)

The Python package `fixbikenet` identifies the most important gaps to fill in a city's bicycle network. You can download street and bike network data with a single line of code, simulate different bicycle network fixing scenarios, and export and plot the resulting prioritized gaps.

FixBikeNet is a decision support tool for urban planners. It is also useful for proactive citizens to help inform their city about data-driven improvements, and it aims to foster research on bicycle networks.

## When to use
FixBikeNet works well for cities or areas that have a well developed -but not yet perfect- bicycle network. Recommended example cities to fix: Aalborg, Amsterdam, Copenhagen

For alternative approaches, or for cities with less developed bicycle networks, consider using [LinkBikeNet](https://github.com/BikeNetKit/LinkBikeNet) or extending the existing network with [GrowBikeNet](https://github.com/BikeNetKit/GrowBikeNet).

## Installation

### The easy way

The currently recommended way to install FixBikeNet is using pip:

```
pip install fixbikenet
```

<!-- > [!IMPORTANT]  
> As of 2026-05-04, the conda-forge installation is not yet working. We will remove this note once it works.

The best way to install FixBikeNet is using [`conda`](https://docs.conda.io/projects/conda/en/latest/index.html) and the `conda-forge` channel:

```
conda install -c conda-forge fixbikenet
``` -->

If this does not work, consult our [installation docs](https://docs.bikenetkit.org/FixBikeNet/installation/).

### Advanced and development installations
 See our [installation docs](https://docs.bikenetkit.org/FixBikeNet/installation/) for details.

## Usage

We provide a minimum working example in two formats:

- Python script ([examples/mwe.py](examples/mwe.py))
- Jupyter notebook ([examples/mwe.ipynb](examples/mwe.ipynb))

## Docs
Find more information in our docs: [https://docs.bikenetkit.org/FixBikeNet/](https://docs.bikenetkit.org/FixBikeNet/)

## Source
The source code builds on [the code from the research paper](https://github.com/anastassiavybornova/bikenwgaps) _Automated Detection of Missing Links in Bicycle Networks_.

**Publication**: [https://doi.org/10.1111/gean.12324](https://doi.org/10.1111/gean.12324)


## How to cite
If you use FixBikeNet in your research, please cite the paper:

> A. Vybornova, T. Cunha, A. Gühnemann, M. Szell. Automated Detection of Missing Links in Bicycle Networks. Geographical Analysis 55(2), 239-267 (2023) 
> DOI: [10.1111/gean.12324](https://doi.org/10.1111/gean.12324)

## Supported by
Development of BikeNetKit/FixBikeNet is supported by the [Innovation Fund Denmark](https://innovationsfonden.dk/en) and the EU HORIZON project [JUST STREETS](https://www.just-streets.eu).


[![Innovation Fund Denmark](https://raw.githubusercontent.com/BikeNetKit/.github/refs/heads/main/profile/_static/logo_innovationfund.png)](https://innovationsfonden.dk/en) &emsp;&emsp; [![European Union](https://raw.githubusercontent.com/BikeNetKit/.github/refs/heads/main/profile/_static/logo_eu.png)](https://commission.europa.eu/index_en) &ensp; [![JUST STREETS](https://raw.githubusercontent.com/BikeNetKit/.github/refs/heads/main/profile/_static/logo_juststreets.png)](https://www.just-streets.eu/) 
