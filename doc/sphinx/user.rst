.. SeaIce API documentation master file, created by
   sphinx-quickstart on Tue Jul 23 14:37:11 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

the ``user`` module
===================

This module implements the live data structures needed for Flask as well as
notifications. See related topic: 

.. toctree::
   :maxdepth: 2

   auth.rst

.. automodule:: seaice.user

.. inheritance-diagram::
      seaice.user.BaseUser
      seaice.user.AnonymousUser
      seaice.user.User

.. autoclass:: seaice.user.BaseUser
   :members:
   :show-inheritance:

.. autoclass:: seaice.user.User
   :members:
   :show-inheritance:

.. autoclass:: seaice.user.AnonymousUser 
   :members:
   :show-inheritance:


