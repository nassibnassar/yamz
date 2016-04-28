#! /usr/bin/env python
# 
# sea - console frontend to the SeaIce metadictionary
#
# Copyright (c) 2013, Christopher Patton, all rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * The names of contributors may be used to endorse or promote products
#     derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os, sys, optparse
import json, psycopg2 as pqdb
import seaice
import ConfigParser

# Figure out if we're in production mode.  Look in 'heroku' section only.
config = ConfigParser.ConfigParser()
config.read('.seaice_auth')
if config.has_option('heroku', 'prod_mode'):
  prod_mode = config.getboolean('heroku', 'prod_mode')
else:
  prod_mode = False             # default

## Parse command line options. ##

parser = optparse.OptionParser()

description="""This program is the command line frontend for the SeaIce metadictionary. SeaIce \
is a database comprised of a set of user-defined, crowd-sourced terms and relations. \
The goal of SeaIce is to develop a succinct and complete set of metadata terms to register \
just about any type of file or data set. 'sea' provides administrative functionality for \
SeaIce's database. It is distributed under the terms of the BSD license with the hope that it \
will be useful, but without warranty. You should have received a copy of the BSD license with \
this program; otherwise, visit http://opensource.org/licenses/BSD-3-Clause.
"""

parser.description = description

parser.add_option("-d", "--dump", action="store_true", dest="dump", default=False,
                  help="Display dictionary contents on the terminal.")

parser.add_option("--config", dest="config_file", metavar="FILE", 
                  help="User credentials for local PostgreSQL database (defaults to '$HOME/.seaice'). " + 
                       "If 'heroku' is given, then a connection to a foreign host specified by " + 
                       "DATABASE_URL is established.",
                  default='heroku')

parser.add_option("--truncate", dest="truncate_table",
                  help="Delete all rows in dictionary table; if used with --import, this option should precede it.")
                  #metavar="TABLE")

parser.add_option("--import", dest="import_table",
                  help="Import JSON-formatted FILE into the dictionary.",
                  metavar="TABLE")

parser.add_option("--rebind", action="store_true", dest="rebind", default=False,
  help="On import, also bind persistent identifier metadata.")

parser.add_option("--remint", action="store_true", dest="remint", default=False,
  help="On import, mint a new persistent identifier (implies --rebind).  Normally a new identifier is minted only when a term has none.")

parser.add_option("--export", dest="export_table",
                  help="Export dictionary as JSON-formatted FILE.",
                  metavar="TABLE")

parser.add_option("-f", "--file", dest="file_name", 
                  help="File from which to import, or file to which to export.",
                  metavar="FILE")

parser.add_option("-s", "--search", dest="search_term",
                  help="Search the metadictionary for TERM and return a list of matches.",
                  metavar="TERM")

parser.add_option("-r", "--remove", dest="remove_id",
                  help="Remove the metadictionary entry corresponding to ID.",
                  metavar="ID")

parser.add_option("--score-terms", action="store_true", dest="score", default=False,
                  help="Compute and print scores of terms. This will modify the term.")

parser.add_option("--classify-terms", action="store_true", dest="classify", default=False,
                  help="Classify stable terms in the dictionary. This will modify the term's class.")

parser.add_option("--set-reputation", dest="reputation",
                  help="Set user's reputation (to a positive integer).",
                  metavar="INT")

parser.add_option("-u", "--user", dest="user_id", 
                  help="ID of user whose reputation is to be set.",
                  metavar="ID", default=None)

parser.add_option("--drop-db", action="store_true", dest="drop_tables", default=False,
                  help="Drop all metadictionary tables from the database.")

parser.add_option("--init-db", action="store_true", dest="create_tables", default=False,
                  help="Create new tables if they don't exist.")

parser.add_option("-j", "--json", action="store_true", dest="json", default=False,
                  help="Format terminal output as a JSON structure.")

parser.add_option("-q", "--quiet", action="store_true", dest="quiet", default=False,
                  help="Don't prompt for confirmation when dropping tables.")

parser.add_option("--role", dest="db_role", metavar="USER", 
                  help="Specify the database role to use for the DB connector pool. These roles " +
                       "are specified in the configuration file (see --config).",
                  default="default")

if len(sys.argv) < 2:
  parser.print_help()
  sys.exit(0)

(options, args) = parser.parse_args()

# Note that if more than one option is given, more than one action will
# be taken.  But the order of actions is determined by the code below and
# not by the order of the options, eg, if --drop-db and --init-db are both
# given, the first action will be drop-db, followed by init-db; this
# example may be one of the few combinations that makes sense.

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
  
  ## Run specified queries. ##

  if options.remove_id:
    if not sea.removeTerm(int(options.remove_id)):
      print >>sys.stderr, "sea: no such term (Id=%s not found)" % options.remove_id

  if options.reputation:
    if not options.user_id:
      print >>sys.stderr, "sea: must specify user Id" 
    elif not sea.updateUserReputation(int(options.user_id), int(options.reputation)):
      print >>sys.stderr, "sea: no such user (Id=%s not found)" % options.user_id

  if options.truncate_table:
    sea.Truncate(options.truncate_table)

  if options.import_table:
    sea.Import(options.import_table, prod_mode, options.file_name,
      rebind=options.rebind, remint=options.remint)

  if options.export_table:
    sea.Export(options.export_table, options.file_name)
  
  if options.drop_tables:
    if not options.quiet:
      print >>sys.stderr, "warning: this will erase all terms. Are you sure? [y/n] ",
      if raw_input() in ['y', 'yes', 'Y']: 
        sea.dropSchema()
    else:
      sea.dropSchema()
        
  if options.create_tables:
    sea.createSchema()
  
  if options.dump: 
    if options.json:
      sea.Export('Terms')
    else:
      seaice.pretty.printTermsPretty(sea, sea.getAllTerms(sortBy="term_string"))

  header = True
  if options.score: 
    for term in sea.getAllTerms():
      (U, V) = sea.preScore(term['id'])
      s = sea.postScore(term['id'], U, V)
      if header: 
        print "%-8s%-20s%-8s%-8s%-8s" % ('Id', 'Term', 'Up', 'Down', 'Score')
        header = False
      print "%-8d%-20s%-8d%-8d%-8.2f" % (term['id'], 
                                   term['term_string'], 
                                   term['up'],
                                   term['down'], 
                                   (100 * s))
  
  header = True
  if options.classify:
    for (term, id) in map(lambda term: (term['term_string'], term['id']), sea.getAllTerms()):
      if header: 
        print "%-8s%-20s%-8s" % ('Id', 'Term', 'Class')
        header = False
      print "%-8s%-20s%-8s" % (id, term, sea.classifyTerm(id))
      sea.commit()
  
  if options.search_term:
    terms = sea.search(options.search_term)
    if options.json: 
      seaice.pretty.printAsJSObject(terms)
    elif len(terms) == 0: 
      print >>sys.stderr, "sea: no matches for '%s'" % options.search_term
    else: seaice.pretty.printTermsPretty(sea, terms)

  ## Commit database mutations. ##
  sea.commit()

except pqdb.DatabaseError, e:
  print 'error: %s' % e    
  sys.exit(1)

# xxx commenting these out makes for better diagnostics?
#except IOError:
#  print >>sys.stderr, "error: file not found"
#  sys.exit(1)
#
#except ValueError: 
#  print >>sys.stderr, "error: incorrect parameter type(s)"
