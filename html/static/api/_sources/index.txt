.. SeaIce API documentation master file, created by
   sphinx-quickstart on Tue Jul 23 14:37:11 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to the *YAMZ* documentation!
======================================

*YAMZ* is an online, crowd-sourced dictionary for metadata terms, and
*SeaIce* (frozen sea water) is an open-source implementation of it using
Python, PostgreSQL, and Flask.

Users log in to *YAMZ* and contribute terms, vote on others', and leave
comments. A reputation-based heuristic is used to estimate community
consensus on these terms as a percentage. This **consensus score** is
used in combination with a **term stability** metric to classify terms as
being **vernacular**, **canonical**, or **deprecated**. The hope is that
*YAMZ* will facilitate the evolution of a set of stable, canonical
metadata terms, verified in social a ecosystem. We're calling the service
a *metadictionary*. Check out the prototype at `yamz.net <http://yamz.net>`_. 

Here you can find the complete documentation of the *SeaIce* API.

.. toctree::
   :maxdepth: 4 

   seaice.rst 
   scoring.rst
   top.rst

This version of *SeaIce* is meant as a proof-of-concept and is missing
some desirable features. Currently, reputation of users is seeded in the
database and there is no way to gain reputation by contributing to the
metadictionary. Other missing features include:

* Contextual IDs for terms. The ability to reference terms on *SeaIce* elswehere. 
* Flag irrelevant/abusive terms and comments. This is standard on other crowd-sourced
  services.
* More notifications. 

The prototype is deployed on `Heroku <http://www.heroku.com>`_. The
source code for the project is distributed under the terms of the BSD
license and is published on `github
<http://www.github.com/nassar/yamz>`_. 

*SeaIce* was originally developed by `Christopher Patton
<http://cjpatton.sdf.org>`_ as an internship for `DataONE
<http://www.dataone.org>`_. CSS and JavaScript templates
were contributed by Karthik Ram. 



Indices and tables
==================
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

