#!/usr/bin/python
# Copyright (c) 2013, Christopher Patton
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

import sys, json, MySQLdb as mdb

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
  
  def __del__(self): 
    self.con.close()

  def createTable(self):
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
  
  def destroyTable(self): 
  #
  # Destroy Terms table if it exists. 
  #
    cur = self.con.cursor()
    cur.execute("drop table if exists Terms")

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
  # Add a term to the database. Expects a dictionary type.
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
        defTerm[key] = str(value)
    
    cur.execute(
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

  def remove(self, Id):
  #
  # Remove term from the database. 
  #
    cur = self.con.cursor()
    cur.execute("delete from Terms where Id=%d" % Id)

  def getTerm(self, Id): 
  # 
  # Retrieve term by Id. Return dictionary structure or None. 
  # 
    cur = self.con.cursor(mdb.cursors.DictCursor)
    cur.execute("select * from Terms where Id=%d" % Id)
    return cur.fetchone()

  def searchByTerm(self, TermString): 
  #
  # Search table by term string and return a list of dictionary structures
  #
    cur = self.con.cursor(mdb.cursors.DictCursor)
    cur.execute("select * from Terms where TermString='%s'" % TermString)
    return list(cur.fetchall())

  def searchByDef(self, string): 
  #
  # Search table by definition. 
  #
    pass 

  def updateDef(self, Id, Definition): 
  #
  # Modify a term's definition
  # 
    cur = self.con.cursor()
    cur.execute("update Terms set Definition='%s' where Id=%d" % (Definition, Id))

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
      row['Modified'] = str(row['Modified'])
      row['Created'] = str(row['Created'])
    print >>fd, json.dumps(rows, sort_keys=True, indent=2, separators=(',', ': '))
      

  def Import(self, inf): 
  #
  # Import database from JSON formated "inf". 
  #
    fd = open(inf, 'r')
    for row in json.loads(fd.read()):
      self.insert(row)
