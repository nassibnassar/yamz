#!/usr/bin/python
# Copyright (c) 2013, Christopher Patton
# All rights reserved.
# 
# TODO
# Created/Modified timestamps
# Import/Export/delete
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

import sys
import json, MySQLdb as mdb

class SeaIceDb: 
  
  def __init__(self, host, user, password, db):
  #
  # Establish connection to database. 
  # 
  
    self.con = mdb.connect(host, user, password, db)
    cur = self.con.cursor()
    cur.execute("SELECT VERSION(); begin")
    ver = cur.fetchone()
    print "Database version : %s " % ver

  def createTable(self):
  #
  # Create Terms table if it doesn't exist.
  # TODO relations.
  #

    cur = self.con.cursor()
    cur.execute(
      """create table if not exists Terms
      (
        Id integer primary key auto_increment, 
        TermString text not null, 
        Definition text not null,
        ContactInfo text not null, 
        Score integer not null,
        Created timestamp not null, 
        Modified timestamp not null 
      );"""
    )
  
  def __del__(self): 
    self.con.close()

  def destroyTable(self): 
  #
  # Destroy Terms table if it exists. 
  #
    cur = self.con.cursor()
    cur.execute("drop table if exists Terms")

  def commit(self): 
  #
  # Commit changes to database made while the connection was open. 
  #
    cur = self.con.cursor()
    cur.execute("commit")
    
  def add(self, term): 
  #
  # Add a term to the database. Expects a dictionary type.
  # TODO probably want to be able to specify Id and Score. 
  #
    cur = self.con.cursor()
    
    cur.execute(
      """insert into Terms( TermString, 
                            Definition, 
                            ContactInfo, 
                            Score,
                            Created,
                            Modified ) 
          values('%s', '%s', '%s', 0, current_timestamp, current_timestamp) 
      """ % (term['TermString'], term['Definition'], term['ContactInfo']))

  def dump(self): 
  #
  # Dump all terms in the table in JSON format (TODO).
  #
    cur = self.con.cursor(mdb.cursors.DictCursor)
    cur.execute("select * from Terms")
    rows = cur.fetchall()
    for row in rows:
      print row

  def delete(self, Id):
  #
  # Remove term from the database. 
  #
    pass

  def getTerm(self, Id): 
  # 
  # Retrieve term by Id. 
  # 
    pass

  def searchByTerm(self, TermString): 
  #
  # Search table by term string. 
  #
    pass

  def searchByDef(self, string): 
  #
  # Search table by definition. 
  #
    pass 

  def updateDef(self, Id, Definition): 
  #
  # Modify a term's definition
  # 
    pass



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
    for row in rows:
      print row
      for (key, value) in row.iteritems():
        row[key] = str(value)
    print >>fd, json.dumps(rows, sort_keys=True, indent=2, separators=(',', ': '))
      

  def Import(self, inf): 
  #
  # Import database from JSON formated "inf". 
  # TODO handle dates!
  #
    fd = open(inf, 'r')
    for row in json.loads(fd.read()):
      self.add(row) 
