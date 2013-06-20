#!/usr/bin/python
# Copyright (c) 2013, Christopher Patton, Nassib Nassar
# All rights reserved.
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

import os, sys, stat, configparser
import json, psycopg2 as pgdb
import psycopg2.extras  

## Local db configuration $HOME/.seaice ## 

def accessible_by_group_or_world(file):
  st = os.stat(file)
  return bool( st.st_mode & (stat.S_IRWXG | stat.S_IRWXO) )

def get_config(config_file = os.environ['HOME'] + '/.seaice'):
  if accessible_by_group_or_world(config_file):
    print ('error: config file ' + config_file +
      ' has group or world ' +
      'access; permissions should be set to u=rw')
    sys.exit(1)
  config = configparser.RawConfigParser()
  config.read(config_file)
  return config



## Interface to database ##

class SeaIceConnector: 
  
  def __init__(self, user, password, db):
  #
  # Establish connection to database. 
  # 
  
    self.con = pgdb.connect(database=db, user=user, password=password)
    cur = self.con.cursor()
    cur.execute("SELECT VERSION(); begin")
    #ver = cur.fetchone()
    #print "Database version : %s " % ver
  
  def __del__(self): 
    self.con.close()

  ## Alter Schema ##

  def createSchema(self):
  #
  # TODO
  #
    
    cur = self.con.cursor()

    # Create SI schema. 
    cur.execute("""
      create schema SI; 
      """
    )
    
    # Create Users table if it doesn't exist. 
    cur.execute("""
      create table if not exists SI.Users
        (
          id serial primary key,
          Name text not null
        );
      alter sequence SI.Users_id_seq start with 1001"""
    )

    # Create Terms table if it doesn't exist.
    cur.execute("""
      create table if not exists SI.Terms
        (
          id serial primary key not null, 
          owner_id integer default 0 not null,
          term_string text not null, 
          definition text not null,
          score integer default 0 not null,
          created timestamp default now() not null, 
          modified timestamp default now() not null, 
          foreign key (owner_id) references SI.Users(id)
        ); 
      alter sequence SI.Terms_id_seq start with 1001"""
    )

    # Create update triggers.
    cur.execute("""
      CREATE OR REPLACE FUNCTION SI.upd_timestamp() RETURNS TRIGGER 
        LANGUAGE plpgsql
        AS
         $$
          BEGIN
            NEW.modified = CURRENT_TIMESTAMP;
            RETURN NEW;
          END;
         $$;
              
      CREATE TRIGGER t_name
        BEFORE UPDATE
         ON SI.Terms
        FOR EACH ROW
         EXECUTE PROCEDURE SI.upd_timestamp();"""
    )

    # Set user permissions.
    cur.execute("""
      grant usage on schema SI to admin, viewer, contributor;
      grant select on all tables in schema SI to viewer, contributor; 
      grant insert, delete, update on SI.Terms, SI.Terms_id_seq to contributor"""
    )

  
  def dropSchema(self): 
  #
  # TODO
  #
  
    # Destroy Terms table if it exists. 
    cur = self.con.cursor()
    cur.execute("drop schema SI cascade")

  ## Queries ##

  def commit(self): 
  #
  # Commit changes to database made while the connection was open. This 
# should be called before the class destructor is called in order to 
  # save changes. 
  #
    cur = self.con.cursor()
    cur.execute("commit")

  def insert(self, term): 
  #
  # Add a term to the database and return number of rows affected (1 or 0. 
  # Expects a dictionary type.
  #
    cur = self.con.cursor()

    # Default values for table entries.  
    defTerm = { 
      "id" : "default",
      "term_string" : "<nil>", 
      "definition" : "<nil>", 
      "score" : "default", 
      "created" : "current_timestamp", 
      "modified" : "current_timestamp",
      "owner_id" : "default"
    }

    # Format entries for db query
    for (key, value) in term.iteritems():
      if key == "created" or key == "modified": 
        defTerm[key] = "'" + str(value) + "'"
      else: 
        defTerm[key] = str(value).replace("'", "\\'")
    
    try:
      return cur.execute(
        """insert into SI.Terms( id, 
                              term_string, 
                              definition, 
                              score,
                              created,
                              modified,
                              owner_id ) 
            values(%s, '%s', '%s', %s, %s, %s, %s) 
        """ % (defTerm['id'], defTerm['term_string'], defTerm['definition'], defTerm['score'], 
               defTerm['created'], defTerm['modified'], defTerm['owner_id']))

    except pgdb.DatabaseError, e:
      #print 'Error %s' % e    
      #sys.exit(1)
      # TODO if duplicate key, output warning. Otherwise raise e
      # This how it looked before migration to postgres:
      # if e.args[0] == 1062: # Duplicate primary key
      #   print >>sys.stderr, "warning (%d): %s (ignoring)" % (e.args[0],e.args[1])
      #   return 0
      raise e

  def remove(self, id):
  #
  # Remove term from the database and return number of rows affected (1 or 0). 
  #
    cur = self.con.cursor()
    return cur.execute("delete from SI.Terms where id=%d" % id)

  def getTerm(self, id): 
  # 
  # Retrieve term by id. Return dictionary structure or None. 
  # 
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("select * from SI.Terms where id=%d" % id)
    return cur.fetchone()
  
  def getAllTerms(self, sortBy=None): 
  # 
  # Return a list of all terms (rows) in table. 
  # 
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    if sortBy:
      cur.execute("select * from SI.Terms order by %s" % sortBy)
    else:
      cur.execute("select * from SI.Terms")
    return cur.fetchall()

  def searchByTerm(self, term_string): 
  #
  # Search table by term string and return a list of dictionary structures
  #
    term_string = term_string.replace("'", "\\'")
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("select * from SI.Terms where term_string='%s'" % term_string)
    return list(cur.fetchall())

  def searchByDef(self, string): 
  #
  # Search table by definition. TODO
  #
    pass 

  def updateTerm(self, id, term): 
  #
  # Modify a term's definition and/or term_string. 
  # Note: term ownership authenticated upstream! 
  # 
    cur = self.con.cursor()
    for (key, value) in term.iteritems():
      term[key] = str(value).replace("'", "\\'")
    cur.execute("update SI.Terms set term_string='%s', definition='%s' where id=%d" % (
      term['term_string'], term['definition'], id))
  
  def getUserNameByid(self, Userid): 
  #
  # Return Users.Name where Users.id = Userid
  #
    cur = self.con.cursor()
    cur.execute("select Name from SI.Users where id=%d" % Userid)
    res = cur.fetchone()
    if res: 
      return res[0]
    else: 
      return None


  ## Import/Export tables ##

  def Export(self, outf=None):
  # 
  # Export database in JSON format to "outf". If no file name 
  # provided, dump to standard out.  
  #
    if outf: 
      fd = open(outf, 'w')
    else:
      fd = sys.stdout

    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("select * from SI.Terms")
    rows = cur.fetchall()
    printAsJSObject(rows, fd)

  def Import(self, inf): 
  #
  # Import database from JSON formated "inf". 
  #
    fd = open(inf, 'r')
    for row in json.loads(fd.read()):
      self.insert(row)
  

  ## Pretty prints ##
  
  def printAsJSObject(self, rows, fd = sys.stdout):
  #
  # Write table rows in JSON format to 'fd'. 
  #
    for row in rows:
      row['modified'] = str(row['modified'])
      row['created'] = str(row['created'])
    print >>fd, json.dumps(rows, sort_keys=True, indent=2, separators=(',', ': '))

  def printParagraph(self, text, leftMargin=8, width=60): 
  #
  # Print a nice paragraph. 
  #
    lineLength = 0
    print " " * (leftMargin-1), 
    for word in text.split(" "):
      if lineLength < width:
        print word, 
        lineLength += len(word) + 1
      else:
        print "\n" + (" " * (leftMargin-1)),
        lineLength = 0
    print
      
  def printPretty(self, rows):
  #
  # Print table rows to the terminal. 
  #
    for row in rows:
      print "Term: %-26s id No. %-7d created: %s" % ("%s (%d)" % (row['term_string'], 
                                                                  row["score"]),
                                                     row['id'],
                                                     row['created']) 

      print " " * 42 + "Last modified: %s" % row['modified']

      print "\n    definition:\n"    
      self.printParagraph(row['definition'])
      
      print "\n    Ownership: %s" % self.getUserNameByid(row['owner_id'])
      print

  def printAsHTML(self, rows, owner_id=0): 
  #
  # Print table rows as an HTML table (to string) 
  # 
    string = "<table colpadding=16>" 
    for row in rows:
      string += "<tr>"
      string += "  <td valign=top width=%s><i>Term:</i> <strong>%s</strong> (#%d)</td>" % (
        repr("70%"), row['term_string'], row['id'])
      string += "  <td valign=top><i>created</i>: %s</td>" % row['created']
      string += "</tr><tr>"
      string += "  <td valign=top><i>score</i>: %s</td>" % row['score']
      string += "  <td valign=top><i>Last modified</i>: %s</td>" % row['modified']
      string += "</tr><tr>"
      string += "  <td valign=top><i>definition:</i> %s</td>" % row['definition']
      string += "  <td valign=top><i>Ownership:</i> %s"% self.getUserNameByid(row['owner_id'])
      if owner_id == row['owner_id']:
        string += " <a href=\"/edit=%d\">[edit term]</a>" % row['id']
      string += "</td></tr><tr height=16><td></td></tr>"
    string += "</table>"
    return string
    

  ## For testing purposes ##

  def addUser(self): # TEMP!!!
    cur = self.con.cursor()
    cur.execute("insert into SI.Users (id, Name) values (999, 'Chris')")
    cur.execute("insert into SI.Users (id, Name) values (1000, 'Julie')")
    cur.execute("commit")

