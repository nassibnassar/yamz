.. SeaIce API documentation master file, created by
   sphinx-quickstart on Tue Jul 23 14:37:11 2013.

Top level programs ``sea`` and ``ice``
======================================

Two top-level Python programs that make use of the *SeaIce* API are available 
in the root directory of the source distribution. Both share two parameters in 
comon: 

* ``--config`` -- File that specifies the postgres role for a local database, 
  typically ``$HOME/.seaice``. (Syntax of this file given below.) If ``heroku``
  is given instead of a filename, then a remote database specified by the 
  environment variable ``DATABSE_URL`` will be used. See 
  :class:`seaice.SeaIceConnector <seaice.SeaIceConnector.SeaIceConnector>`
  for details.

* ``--role`` -- Role to use for connection to a local database. The parameter
  value must appear in the DB config file. 

=======
``sea``
=======

``sea`` is the command line UI for *SeaIce* and provides administrative 
functionality. It allows you to initialize and drop the database schema, 
import and export individual tables, score and classify terms in the database, 
and seed a user's reputation. Use ``--help`` for a full list of options. 
Following are some important example usages. 

**Schedule term classification**. This process is not inherently periodic in 
nature, but is dramatically simplified by scheduling it at regular intervals. 
Currently this occurs hourly on the Heroku deployment. In ``crontab`` for 
example: 

.. code-block:: bash

  0 * * * * /usr/bin/python /directory/of/seaice/source/sea --classify-terms

**Remove a term**. A useful feature to implement for *SeaIce* would be the ability to flag 
abusive or spam terms for deletion. In the meantime, it's posible for the administrator 
to delete a term manually with ``--remove=ID``, where ``ID`` is the term's surrogate ID. 

**Reset the DB**. When modifying the DB schema, it may be necessary to reload the contents.   

.. code-block:: bash

  $ ./sea --export=Userss >users.json
  $ ./sea --export=Terms >terms.json
  $ ./sea --export=Comments >comments.json
  $ ./sea --export=Tracking >tracking.json
  $ ./sea --drop-db --init-db -q

Now add the necessary modifications directly to the ``*.json`` exports. 
When importing, it's important to do so in the correct order since the 
tables use surrogate keys to reference each other. 

.. code-block:: bash

  $ ./sea --import=Userss <users.json
  $ ./sea --import=Terms <terms.json
  $ ./sea --import=Comments <comments.json
  $ ./sea --import=Tracking <tracking.json
  
**Seed reputation**. Use ``--set-reputation=N`` with ``--user=ID``, where ``N`` is the 
new reputation value and ``ID`` is the surrogate ID of the user. Say you want to seed 
the reputation of the notorious üwe Nordberger to 400. Find his ID by exporting the table to 
standard output: 

.. code-block:: bash
 
  $ ./sea --export=Users 
  [
       ... 
    {
      "auth_id": "something secret",
      "authority": "google",
      "email": "fella@guy.de",
      "first_name": "\u00dcwe",
      "id": 1032,
      "last_name": "Nordberger",
      "reputation": 1
    }
       ... 
  ]
  $ ./sea --set-retpuation=400 --user=1032


**Score terms manually**. When a vote is cast, the new consensus score of a term is 
calculated immediately in constant time. However, using ``--score-terms`` will cause 
each term in the database to be scored once "the hard way". For each term, the reputations 
for all up voters and down voters of each term are collected and used to compute 
the score. This is quite inefficient, roughly *O(mn)* for *m* users and *n* votes. In 
addition, it causes a join on the *User* and *Tracking* tables. In spite of this, I found
it useful for verifying the more complex functions
:func:`SeaIceConnector.castVote <seaice.SeaIceConnector.SeaIceConnector.castVote>` and
:func:`SeaIceConnector.updateUserReputaiton <seaice.SeaIceConnector.SeaIceConnector.updateUserReputation>`
in development. 

=======
``ice``
=======

This program utilizes the entire *SeaIce* API functionality to implement a Flask-based 
web framework. The main object, :class:`seaice.SeaIceFlask <seaice.SeaIceFlask.SeaIceFlask>`
creates a DB connection pool (all inherit the ``--config`` configuration), surrogate ID pools for 
tables, and data structures for authenticated user sessions and notifications. The code in 
``ice`` defines the various *GET* and *POST* requests that are served. In addition, 
Flask's login manager (``Flask-login``) is imported to handle authentication of sessions and
anonymous users. Finally, Flask provides a simple way to run the framework for local testing. 
In deployment, the run code is ommitted and ``ice`` is run with a standalone web server. 
(``gunicorn ice.py`` on Heroku.) 

=====================
DB configuration file
=====================
Three parameters are specified for each view: **user**, **password**, and **dbname**. Views 
are given in squar brackets. E.g.: 

.. code-block:: text

  [default]
  dbname = seaice
  user = postgres
  password = SECRET
  [contributor]
  dbname = seaice
  user = contributor
  password = SECRET
