.. FixBikeNet documentation master file, created by
   sphinx-quickstart on Thu Feb 12 15:01:19 2026.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

FixBikeNet |version| documentation
===================================

The Python package ``fixbikenet`` identifies the most important gaps to fill in a city's bicycle network. It is hosted on `Github <https://github.com/BikeNetKit/FixBikeNet>`__, part of `BikeNetKit <https://bikenetkit.org>`__.

The software downloads and pre-processes data from OpenStreetMap, identifies the gaps, saves the results, creates plots and videos. The source code builds on `the code from the
research paper <https://github.com/anastassiavybornova/bikenwgaps>`__ *Automated Detection of Missing Links in Bicycle Networks*.


Setup and use
-------------

To set up FixBikeNet, see the :doc:`installation` page.
To use FixBikeNet, the :doc:`getting_started` page
is a good place to start, which also explains how the package works in detail. For technical documentation, consult the :doc:`reference_user`.

.. Statement of need
.. =================

.. TBA

How to cite
-----------

If you use FixBikeNet in your research, please cite `the paper <https://doi.org/10.1111/gean.12324>`__:

   A. Vybornova, T. Cunha, A. Gühnemann, M. Szell. Automated Detection of Missing Links in Bicycle Networks. Geographical Analysis 55(2), 239-267 (2023)

Contributing
------------

If you want to contribute to the development of FixBikeNet, please read the
`CONTRIBUTING.md <https://github.com/BikeNetKit/FixBikeNet?tab=contributing-ov-file#contributing-to-bikenetkit>`__
file.

Supported by
------------

Development of BikeNetKit/FixBikeNet was supported by the Innovation Fund Denmark
and the EU HORIZON grant JUST STREETS.

|Innovation Fund Denmark|    |European Union|   |JUST STREETS|

.. |Innovation Fund Denmark| image:: _static/logo_innovationfund.png
   :target: https://innovationsfonden.dk/en
.. |European Union| image:: _static/logo_eu.png
   :target: https://commission.europa.eu/index_en
.. |JUST STREETS| image:: _static/logo_juststreets.png
   :target: https://www.just-streets.eu/


Documentation contents
----------------------

.. toctree::
   :maxdepth: 1

   Home <self>
   installation
   getting_started
   reference_user
   reference_developer
   references
