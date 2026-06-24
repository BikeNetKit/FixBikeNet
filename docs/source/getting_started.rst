Getting started
===============

Get Started in 4 Steps
----------------------

1. Install FixBikeNet by following the :doc:`installation` guide.

2. Read the :ref:`introducing-fixbikenet` section below.

3. To check that the installation worked, run ``python examples/mwe.py`` or the Jupyter :doc:`mwe`.

4. Consult the :doc:`reference_user` for complete details on using the package.

Finally, if you're not already familiar with `NetworkX`_ and `GeoPandas`_, make sure you read their user guides as FixBikeNet uses their data structures.

.. _introducing-fixbikenet:

Introducing FixBikeNet
-----------------------

FixBikeNet is built on top of `OSMnx`_/`NetworkX`_ and `GeoPandas`_. It takes one mandatory parameter, the city name, which it passes via `Nominatim`_ to `OSMnx`_, to download a city's street network. FixBikeNet then runs the following operations:

* TBA


To try it out, run the:

.. toctree::
   :maxdepth: 1

   Minimum working example <mwe>


.. _GeoPandas: https://geopandas.org
.. _NetworkX: https://networkx.org
.. _OSMnx: https://osmnx.readthedocs.io
.. _Nominatim: https://nominatim.openstreetmap.org