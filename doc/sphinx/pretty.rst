.. SeaIce API documentation master file, created by
   sphinx-quickstart on Tue Jul 23 14:37:11 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

The ``pretty`` module
=====================

This module implements various output-formatters that have been found
useful for creating web pages and console output.

.. toctree::
   :maxdepth: 2

.. automodule:: seaice.pretty

.. autofunction:: seaice.pretty.printPrettyDate
.. autofunction:: seaice.pretty.processTags

==========
Plain text
==========

.. autofunction:: seaice.pretty.printAsJSObject
.. autofunction:: seaice.pretty.printParagraph
.. autofunction:: seaice.pretty.printTermsPretty

====
HTML
====

.. autofunction:: seaice.pretty.printTermAsHTML
.. autofunction:: seaice.pretty.printTermsAsHTML
.. autofunction:: seaice.pretty.printTermsAsBriefHTML
.. autofunction:: seaice.pretty.printTermsAsLinks
.. autofunction:: seaice.pretty.printCommentsAsHTML


