.. SeaIce API documentation master file, created by
   sphinx-quickstart on Tue Jul 23 14:37:11 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

The ``notify`` module
=====================

Notifications are generated when important changes to the *SeaIce* dictionary 
are made and relevant users neeed to be informed. For example, when the owner
of a term modifies the definition, users who have voted on the term must be
notified so that they can recast their vote if necessary. Another useful 
application of notifications is when users comment on your term. ``BaseNotification``
comprises the basis and requires at a minimum the time when the event occured
and the surrogate ID of the term it pertains to. A few basic notifications are 
implemented here; undoubtedly more will prove to be useful.

Notifications are handled by the function :func:`seaice.user.User.notify`. 
There is a table and schema (``SI_Notify.Notfiy``) in the *SeaIce* database 
for persistent storage of notifications. 
:func:`insertNotifciation() <seaice.SeaIceConnector.SeaIceConnector.insertNotification>`
and :func:`removeNotification() <seaice.SeaIceConnector.SeaIceConnector.removeNotification>` are called in 
:func:`seaice.user.User.notify` for handling insertion and deletion respectively. Note that
this is meant to be optional, however; omitting the *db_con* parameter will skip this. 


.. toctree::
   :maxdepth: 2

.. inheritance-diagram::
   seaice.notify.BaseNotification
   seaice.notify.Comment
   seaice.notify.TermUpdate
   seaice.notify.TermRemoved

.. automodule:: seaice.notify

.. autoclass:: seaice.notify.BaseNotification
   :members: 
   :show-inheritance:

.. autoclass:: seaice.notify.Comment
   :members: 
   :show-inheritance:

.. autoclass:: seaice.notify.TermUpdate
   :members: 
   :show-inheritance:

.. autoclass:: seaice.notify.TermRemoved
   :members: 
   :show-inheritance:

