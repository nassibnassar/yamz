#!/usr/bin/python
# Fix concept id's on terms.  

import os, sys, optparse,re
import json, psycopg2 as pqdb
import seaice

## Parse command line options. ##

parser = optparse.OptionParser()

parser.add_option("--config", dest="config_file", metavar="FILE", 
                  help="User credentials for local PostgreSQL database (defaults to '$HOME/.seaice'). " + 
                       "If 'heroku' is given, then a connection to a foreign host specified by " + 
                       "DATABASE_URL is established.",
                  default='heroku')

parser.add_option("--role", dest="db_role", metavar="USER", 
                  help="Specify the database role to use for the DB connector pool. These roles " +
                       "are specified in the configuration file (see --config).",
                  default="default")

(options, args) = parser.parse_args()


## Establish connection to PostgreSQL db ##

try:

  if options.config_file == "heroku": 
    
    sea = seaice.SeaIceConnector()

  else: 
    try: 
      config = seaice.auth.get_config(options.config_file)
    except OSError: 
      print >>sys.stderr, "error: config file '%s' not found" % options.config_file
      sys.exit(1)

    sea = seaice.SeaIceConnector(config.get(options.db_role, 'user'),       
                                 config.get(options.db_role, 'password'),
                                 config.get(options.db_role, 'dbname'))
  
  cur = sea.con.cursor()
  cur.execute('SELECT NOW();') 

  (t,) = cur.fetchone()
  print '%s %s %s' % (t.day, seaice.pretty.monthOf[t.month - 1], t.year)
    
  ## Commit database mutations. ##
  sea.commit()

except pqdb.DatabaseError, e:
  print 'error: %s' % e    
  sys.exit(1)

except IOError:
  print >>sys.stderr, "error: file not found"
  sys.exit(1)

except ValueError: 
  print >>sys.stderr, "error: incorrect paramater type(s)"
