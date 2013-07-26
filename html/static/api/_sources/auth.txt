.. SeaIce API documentation master file, created by
   sphinx-quickstart on Tue Jul 23 14:37:11 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

The ``auth`` module
===================

This module contains the various data structures used for authenticating
sessions. *SeaIce* doesn't handle user accounts directly; instead, it 
utilizes third-party authentication services to make it easy for users 
log on with existing accounts. So far, only Google account authentication
is implemented. To add other authenticator services -- Facebook, OpenID, 
and StackOverflow to name a few -- it will be necessary to restructure 
this code a bit (noted below). In addition, this will require changing
``ice`` a fair amount. 

.. automodule:: seaice.auth

.. autofunction:: seaice.auth.accessible_by_group_or_world
.. autofunction:: seaice.auth.get_config


.. autodata:: seaice.auth.REDIRECT_URI
.. autodata:: seaice.auth.GOOGLE_CLIENT_ID
.. autodata:: seaice.auth.GOOGLE_CLIENT_SECRET
.. autodata:: seaice.auth.google

