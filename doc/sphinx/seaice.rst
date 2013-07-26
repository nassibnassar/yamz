.. SeaIce API documentation master file, created by
   sphinx-quickstart on Tue Jul 23 14:37:11 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

The ``seaice`` package
======================

``seaice`` is comprised of tools and datastructures on which the front ends are built. 
Distributed with *SeaIce* are two top level Python programs with very clever names: 

* ``sea`` -- Command line tool for setting up, tearing down, and other wise interacting
  with the database in various ways.  
* ``ice`` -- Web UI based on Flask for *SeaIce*. This facilitates user interactions 
  with the database by serving various *GET/POST* requests. 

See the section on top-level programs **[ref]** for more details. The *SeaIce* API 
should be imported into the application namespace with: 
  
  ``import seaice``

Included in ``seaice.*`` are user data structures for Flask-login, ``get_config()`` which 
handles local database configuration, and the various output formatters (``seaice.pretty.*``). 
The most important object, ``seaice.SeaIceFlask`` is used to build a Flask-based web interface
for *SeaIce*. 


=====================
``class SeaIceFlask``
=====================

.. automodule:: seaice

.. automodule:: seaice.SeaIceFlask
.. autoclass:: seaice.SeaIceFlask.SeaIceFlask
   :show-inheritance:

.. attribute:: SeaIceFlask.dbPool
    
    :type: :class:`seaice.ConnectorPool.SeaIceConnectorPool`

.. attribute:: SeaIceFlask.userIdPool
    
    :type: :class:`seaice.IdPool`

.. attribute:: SeaIceFlask.termIdPool
    
    :type: :class:`seaice.IdPool`

.. attribute:: SeaIceFlask.commentIdPool
    
    :type: :class:`seaice.IdPool`

.. attribute:: SeaIceFlask.SeaIceUsers
    
    :type: :class:`seaice.user.User` dict


.. autodata:: seaice.SeaIceFlask.MAX_CONNECTIONS


===================
Classes and modules
===================

In this index, you can find documentation of the various 
thingys that comprise the package. 

.. toctree::
   :maxdepth: 2
 
   SeaIceConnector.rst
   ConnectorPool.rst
   IdPool.rst
   user.rst
   notify.rst
   pretty.rst



