.. SeaIce API documentation master file, created by
   sphinx-quickstart on Tue Jul 23 14:37:11 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

``class SeaIceConnector`` -- interface for PostgreSQL DB 
========================================================

This is the interface for the *SeaIce* database. It is assumed that a PostgreSQL 
database has already been configured. The following queries are implemented: 

* Create the DB schema ``SI`` and the various table and triggers (``createSchema()``).
* Drop ``SI`` , tables, and triggers (``dropSchema()``). 
* Insert, remove, and update terms, users, and comments.
* Cast vote and track terms.
* Calculate term consensus and stability. 
* Inset and delete notifications.
* Import/export the DB. 


.. toctree::
   :maxdepth: 2
 
.. automodule:: seaice



.. automodule:: seaice.SeaIceConnector
.. autoclass:: seaice.SeaIceConnector.SeaIceConnector
   :members:
   :show-inheritance:

===============================
``class ScopedSeaIceConnector``
===============================

.. inheritance-diagram:: 
      seaice.SeaIceConnector
      seaice.ScopedSeaIceConnector

.. autoclass:: seaice.ConnectorPool.ScopedSeaIceConnector
   :members:
   :show-inheritance:
