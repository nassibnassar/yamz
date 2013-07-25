.. SeaIce API documentation master file, created by
   sphinx-quickstart on Tue Jul 23 14:37:11 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

seaice API
==========

Contents:

.. toctree::
   :maxdepth: 2
 
   SeaIceConnector.rst
   ConnectorPool.rst
   IdPool.rst
   user.rst
   notify.rst
   pretty.rst



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



* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

