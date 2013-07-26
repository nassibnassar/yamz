.. SeaIce API documentation master file, created by
   sphinx-quickstart on Tue Jul 23 14:37:11 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

``class ConnectorPool``
=======================

This class implements a thread-safe DB connector pool in the typical way. 
``ConnectorPool`` is the generic base class for ``SeaIceConnectorPool``
which is should be used in practice.  

.. toctree::
   :maxdepth: 2
 
.. automodule:: seaice

.. automodule:: seaice.ConnectorPool
.. autoclass:: seaice.ConnectorPool.ConnectorPool
   :members:
   :show-inheritance:

.. autoclass:: seaice.ConnectorPool.SeaIceConnectorPool
   :members:
   :show-inheritance:

.. inheritance-diagram:: 
      seaice.SeaIceConnector
      seaice.ScopedSeaIceConnector

.. autoclass:: seaice.ConnectorPool.ScopedSeaIceConnector
   :noindex:
   :members:
   :show-inheritance:

