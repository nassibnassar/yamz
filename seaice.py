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
import json, MySQLdb as mdb

## Pretty printing ##

def printAsJSObject(rows, fd = sys.stdout):
#
# Write table rows in JSON format to 'fd'. 
#
  for row in rows:
    row['Modified'] = str(row['Modified'])
    row['Created'] = str(row['Created'])
  print >>fd, json.dumps(rows, sort_keys=True, indent=2, separators=(',', ': '))

def printParagraph(text, leftMargin=8, width=60): 
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
    
def printPretty(rows):
#
# Print table rows to the terminal. 
#
  for row in rows:
    print "Term: %-26s Id No. %-7d Created: %s" % ("%s (%d)" % (row['TermString'], 
                                                                row["Score"]),
                                                   row['Id'],
                                                   row['Created']) 

    print " " * 42 + "Last Modified: %s" % row['Modified']

    print "\n    Definition:\n"    
    printParagraph(row['Definition'])
    
    print "\n    Ownership: %s" % row['ContactInfo']
    print

def printAsHTML(rows, owner="any"): 
#
# Print table rows as an HTML table. 
# 
  string = "<table colpadding=16>" 
  for row in rows:
    string += "<tr>"
    string += "  <td valign=top width=%s><i>Term:</i> <strong>%s</strong> (#%d)</td>" % (
      repr("70%"), row['TermString'], row['Id'])
    string += "  <td valign=top><i>Created</i>: %s</td>" % row['Modified']
    string += "</tr><tr>"
    string += "  <td valign=top><i>Score</i>: %s</td>" % row['Score']
    string += "  <td valign=top><i>Last Modified</i>: %s</td>" % row['Modified']
    string += "</tr><tr>"
    string += "  <td valign=top><i>Definition:</i> %s</td>" % row['Definition']
    string += "  <td valign=top><i>Ownership:</i> %s"% row['ContactInfo']
    if owner: #TODO verify 
      string += " <a href=\"/edit=%d\">[edit term]</a>" % row['Id']
    string += "</td></tr><tr height=16><td></td></tr>"
  string += "</table>"
  return string



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

class SeaIceDb: 
  
  def __init__(self, host, user, password, db):
  #
  # Establish connection to database. 
  # 
  
    self.con = mdb.connect(host, user, password, db)
    cur = self.con.cursor()
    cur.execute("SELECT VERSION(); begin")
    ver = cur.fetchone()
    #print "Database version : %s " % ver
  
  def __del__(self): 
    self.con.close()

  def createTerms(self):
  #
  # Create Terms table if it doesn't exist.
  #

    cur = self.con.cursor()
    cur.execute(
      """create table if not exists Terms
      (
        Id integer primary key auto_increment, 
        TermString text not null, 
        Definition text not null,
        ContactInfo text not null, 
        Score integer default 0 not null,
        Created timestamp default 0 not null, 
        Modified timestamp 
          default 0 on 
          update current_timestamp 
          not null 
      ); 
      alter table Terms auto_increment=1001"""
    )

  def createUsers(self):
  #
  # Create Users table if it doesn't exist.
  #
    cur = self.con.cursor()
    cur.execute(
      """create table if not exists Users
      (
        Id integer primary key auto_increment,
        Name text not null
      );
      alter table Users auto_increment=1001"""
    )
  
  def dropTable(self, table): 
  #
  # Destroy Terms table if it exists. 
  #
    cur = self.con.cursor()
    cur.execute("drop table if exists %s" % table)

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
      "Id" : "default",
      "TermString" : "<nil>", 
      "Definition" : "<nil>", 
      "ContactInfo" : "<nil>", 
      "Score" : "default", 
      "Created" : "current_timestamp", 
      "Modified" : "current_timestamp"
    }

    # Format entries for db query
    for (key, value) in term.iteritems():
      if key == "Created" or key == "Modified": 
        defTerm[key] = "'" + str(value) + "'"
      else: 
        defTerm[key] = str(value).replace("'", "\\'")
    
    try:
      return cur.execute(
        """insert into Terms( Id, 
                              TermString, 
                              Definition, 
                              ContactInfo, 
                              Score,
                              Created,
                              Modified ) 
            values(%s, '%s', '%s', '%s', %s, %s, %s) 
        """ % (defTerm['Id'], defTerm['TermString'], defTerm['Definition'], defTerm['ContactInfo'],
               defTerm['Score'], defTerm['Created'], defTerm['Modified']))
    except mdb.Error, e:
      if e.args[0] == 1062: # Duplicate primary key
        print >>sys.stderr, "warning (%d): %s (ignoring)" % (e.args[0],e.args[1])
        return 0
      else: raise e

  def remove(self, Id):
  #
  # Remove term from the database and return number of rows affected (1 or 0). 
  #
    cur = self.con.cursor()
    return cur.execute("delete from Terms where Id=%d" % Id)

  def getTerm(self, Id): 
  # 
  # Retrieve term by Id. Return dictionary structure or None. 
  # 
    cur = self.con.cursor(mdb.cursors.DictCursor)
    cur.execute("select * from Terms where Id=%d" % Id)
    return cur.fetchone()
  
  def getAllTerms(self, sortBy=None): 
  # 
  # Return a list of all terms (rows) in table. 
  # 
    cur = self.con.cursor(mdb.cursors.DictCursor)
    if sortBy:
      cur.execute("select * from Terms order by %s" % sortBy)
    else:
      cur.execute("select * from Terms")
    return cur.fetchall()

  def searchByTerm(self, TermString): 
  #
  # Search table by term string and return a list of dictionary structures
  #
    TermString = TermString.replace("'", "\\'")
    cur = self.con.cursor(mdb.cursors.DictCursor)
    cur.execute("select * from Terms where TermString='%s'" % TermString)
    return list(cur.fetchall())

  def searchByDef(self, string): 
  #
  # Search table by definition. 
  #
    pass 

  def updateTerm(self, Id, term): 
  #
  # Modify a term's definition
  # 
    cur = self.con.cursor()
    for (key, value) in term.iteritems():
      term[key] = str(value).replace("'", "\\'")
    cur.execute("update Terms set TermString='%s', ContactInfo='%s', Definition='%s' where Id=%d" % (
      term['TermString'], term['ContactInfo'], term['Definition'], Id))

  def Export(self, outf=None):
  # 
  # Export database in JSON format to "outf". If no file name 
  # provided, dump to standard out.  
  #
    if outf: 
      fd = open(outf, 'w')
    else:
      fd = sys.stdout

    cur = self.con.cursor(mdb.cursors.DictCursor)
    cur.execute("select * from Terms")
    rows = cur.fetchall()
    printAsJSObject(rows, fd)


  def Import(self, inf): 
  #
  # Import database from JSON formated "inf". 
  #
    fd = open(inf, 'r')
    for row in json.loads(fd.read()):
      self.insert(row)
