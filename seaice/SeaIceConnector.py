# SeaIceConnector.py - implementation of class SeaIceConnector, the API for 
# the SeaIce database. This class is capable of connecting to a local 
# PostgreSQL database, or a foreign one specified by the environment variable 
# DATABASE_URI. 
#
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

import os, sys, stat, configparser, urlparse
import json, psycopg2 as pgdb
import psycopg2.extras  
import Pretty

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



## class SeaIceConnector ##

class SeaIceConnector: 
  
  def __init__(self, user=None, password=None, db=None):
  #
  # Establish connection to database. For a local database, this is
  # specified by the paramters. If the parameters are unspecified, 
  # then attempt to connect to a foreign database sepcified by the 
  # environment variable DATABASE_URL. This is to support Heroku's
  # functionality. 
  # 
  
    if not user: 

      self.heroku_db = True
      urlparse.uses_netloc.append("postgres")
      url = urlparse.urlparse(os.environ["DATABASE_URL"])

      self.con = pgdb.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
      )
      
    else: 

      self.heroku_db = False
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
  # Create a schema for the SeaIce database that includes the tables
  # Users, Terms, Relations(TODO), and Comments, and an update trigger 
  # funciton. 
  #
    
    cur = self.con.cursor()

    # Create SI schema. 
    cur.execute("""
      create schema SI; 
      """
    )
    
    # Create Users table if it doesn't exist. 
    # TODO unique constraint on (auth_id, authority)
    cur.execute("""
      create table if not exists SI.Users
        (
          id serial primary key not null,
          authority varchar(64) not null, 
          auth_id varchar(64) not null, 
          email varchar(64) not null, 
          last_name varchar(64) not null,
          first_name varchar(64) not null,
          reputation integer default 0 not null
        );
      alter sequence SI.Users_id_seq restart with 10001;"""
    )

    # Create Terms table if it doesn't exist.
    cur.execute("""
      create table if not exists SI.Terms
        (
          id serial primary key not null, 
          owner_id integer default 0 not null,
          term_string text not null, 
          definition text not null,
          tsv tsvector, 
          score integer default 0 not null,
          created timestamp default now() not null, 
          modified timestamp default now() not null, 
          foreign key (owner_id) references SI.Users(id)
        ); 
      alter sequence SI.Terms_id_seq restart with 1001;"""
    )

    # Create Comments table if it doesn't exist.
    cur.execute("""
      create table if not exists SI.Comments
        (
          id serial primary key not null, 
          owner_id integer default 0 not null, 
          term_id integer default 0 not null, 
          comment_string text not null, 
          created timestamp default now() not null,
          modified timestamp default now() not null, 
          foreign key (owner_id) references SI.Users(id),
          foreign key (term_id) references SI.Terms(id) on delete cascade
        )"""
    )

    # Create update triggers.
    cur.execute("""
      create or replace function SI.upd_timestamp() returns trigger 
        language plpgsql
        as
         $$
          begin
            new.modified = current_timestamp;
            return new;
          end;
         $$;
              
      create trigger term_update
        before update on SI.Terms
        for each row
         execute procedure SI.upd_timestamp();
      
      create trigger comment_update
        before update on SI.Comments
        for each row
         execute procedure SI.upd_timestamp();

      create trigger tsv_update 
        before insert or update on SI.Terms
        for each row execute procedure
          tsvector_update_trigger(tsv, 'pg_catalog.english', term_string, definition);"""
    )

    # Set user permissions. (Not relevant for Heroku-Postgres.)
    if not self.heroku_db:
      cur.execute("""
       grant usage on schema SI to admin, viewer, contributor;
       grant select on all tables in schema SI to viewer, contributor; 
       grant insert, delete, update on SI.Terms, SI.Terms_id_seq to contributor"""
      )
  
  def dropSchema(self): 
  #
  # Drop SeaIce schema. 
  #
  
    cur = self.con.cursor()
    cur.execute("drop schema SI cascade")


  ## Commit transactions ##

  def commit(self): 
  #
  # Commit changes to database made while the connection was open. This 
  # should be called before the class destructor is called in order to 
  # save changes. 
  #
    cur = self.con.cursor()
    cur.execute("commit")

  
  ## Term queries ##

  def insertTerm(self, term): 
  #
  # Add a term to the database and return Terms.Id (None if failed) 
  #
    cur = self.con.cursor()

    # Default values for table entries.  
    defTerm = { 
      "id" : "default",
      "term_string" : "nil", 
      "definition" : "nil", 
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
      cur.execute(
        """insert into SI.Terms( id, 
                              term_string, 
                              definition, 
                              score,
                              created,
                              modified,
                              owner_id ) 
            values(%s, '%s', '%s', %s, %s, %s, %s) 
            returning id
        """ % (defTerm['id'], defTerm['term_string'], defTerm['definition'], defTerm['score'], 
               defTerm['created'], defTerm['modified'], defTerm['owner_id']))
    
      res = cur.fetchone()
      if res: 
        return res[0]
      else:
        return None

    except pgdb.DatabaseError, e:
      if e.pgcode == '23505': # Duplicate primary key
         print >>sys.stderr, "warning: skipping duplicate primary key Id=%s" % defTerm['id']
         return None 
      raise e

  def removeTerm(self, id):
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

  def getByTerm(self, term_string): 
  #
  # Search table by term string and return a list of dictionary structures
  #
    term_string = term_string.replace("'", "\\'")
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("select i* from SI.Terms where term_string='%s'" % term_string)
    return list(cur.fetchall())

  def search(self, string): 
  #
  # Search table by definition.
  #
    string = string.replace("'", "\\'")
    string = ' & '.join(string.split(' ')) # |'s are also aloud, and pranthesis
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("""
      SELECT id, owner_id, term_string, definition, 
             score, created, modified, 
             ts_rank_cd(tsv, query, 32 /* rank(rank+1) + score */ ) AS rank
        FROM SI.Terms, to_tsquery('english', '%s') query 
        WHERE query @@ tsv 
        ORDER BY rank
     """ % string)
    return list(cur.fetchall())

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
 

  ## User queries ##

  def insertUser(self, user):
  #
  # Insert a new user into the table and return Users.Id (None if failed) 
  #

    defUser = { 
      "id" : "default",
      "email" : "nil", 
      "last_name" : "nil", 
      "first_name" : "nil", 
      "reputation" : "default", 
      "authority" : "nil",
      "auth_id" : "nil"
    }
  
    # Format entries for db query
    for (key, value) in user.iteritems():
      defUser[key] = str(value).replace("'", "\\'")

    try:
      cur = self.con.cursor()
      cur.execute("""insert into SI.Users(id, email, last_name, first_name, reputation, authority, auth_id) 
                      values (%s, '%s', '%s', '%s', %s, '%s', '%s')
                      returning id""" % (defUser['id'],
                                         defUser['email'], 
                                         defUser['last_name'], 
                                         defUser['first_name'], 
                                         defUser['reputation'], 
                                         defUser['authority'],
                                         defUser['auth_id']))
      res = cur.fetchone()
      if res: 
        return res[0]
      else:
        return None
    
    except pgdb.DatabaseError, e:
      if e.pgcode == '23505': # Duplicate primary key
         print >>sys.stderr, "warning: skipping duplicate primary key Id=%s" % defUser['id']
         return None 
      raise e

  def getUser(self, id):
  #
  # Get User by Id
  #
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("select * from SI.Users where id=%d" % id)
    return cur.fetchone()
      
  def getUserByAuth(self, authority, auth_id):
  #
  # Return Users.Id where Users.auth_id = auth_id and 
  # Users.authority = authority
  #
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("select * from SI.Users where auth_id = '%s' and authority = '%s'" % 
                 (auth_id, authority))
    res = cur.fetchone()
    return res

  def getUserNameById(self, Userid): 
  #
  # Return Users.Name where Users.id = Userid
  #
    cur = self.con.cursor()
    cur.execute("select first_name from SI.Users where id=%d" % Userid)
    res = cur.fetchone()
    if res: 
      return res[0]
    else: 
      return None
  
  def updateUser(self, id, first, last): 
  #
  # Update User name
  # 
    cur = self.con.cursor()
    cur.execute("update SI.Users set first_name='%s', last_name='%s' where id=%d" % (
      first, last, id))


  ## Comment Queries ## 

  def insertComment(self, comment): 
  #
  # Insert a new comment into the database. 
  #
    defComment = { 
      "id" : "default",
      "owner_id" : "default", 
      "term_id" : "default", 
      "comment_string" : "nil"
    }
  
    # Format entries for db query
    for (key, value) in comment.iteritems():
      defComment[key] = str(value).replace("'", "\\'")

    try:
      cur = self.con.cursor()
      cur.execute("""insert into SI.Comments (id, owner_id, term_id, comment_string) 
                      values (%s, %s, %s, '%s')
                      returning id""" % (defComment['id'],
                                         defComment['owner_id'], 
                                         defComment['term_id'], 
                                         defComment['comment_string']))
      res = cur.fetchone()
      if res: 
        return res[0]
      else:
        return None
    
    except pgdb.DatabaseError, e:
      if e.pgcode == '23505': # Duplicate primary key
         print >>sys.stderr, "warning: skipping duplicate primary key Id=%s" % defUser['id']
         return None 
      raise e

  def removeComment(self, id):
  #
  # Remove comment and return number of rows affected (1 or 0)
  # 
    cur = self.con.cursor()
    return cur.execute("delete from SI.Comments where id=%d" % id)

  def updateComment(self, id, comment):
  #
  #  Update term comment. 
  #
    cur = self.con.cursor()
    for (key, value) in comment.iteritems():
      comment[key] = str(value).replace("'", "\\'")
    cur.execute("update SI.Comments set comment_string='%s' where id=%d" % (
      comment['comment_string'], id))

  def getComment(self, id):
  #
  # Return comment.
  #
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("select * from SI.Comments where id=%d" % id)
    return cur.fetchone()

  def getCommentHistory(self, term_id):
  #
  # Return a term's comment history, ordered by creation date.
  #
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("select * from SI.Comments where term_id=%d order by created" % term_id)
    return list(cur.fetchall())


  ## Import/Export tables ##

  def Export(self, table, outf=None):
  # 
  # Export database in JSON format to "outf". If no file name 
  # provided, dump to standard out. TODO comments 
  #
    if table not in ['Users', 'Terms']:
      print >>sys.stderr, "error (export): table '%s' is not defined in the db schema" % table

    if outf: 
      fd = open(outf, 'w')
    else:
      fd = sys.stdout

    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("select * from SI.%s" % table)
    rows = cur.fetchall()
    Pretty.printAsJSObject(rows, fd)

  def Import(self, table, inf=None): 
  #
  # Import database from JSON formated "inf". TODO comments
  #
    if table not in ['Users', 'Terms']:
      print >>sys.stderr, "error (import): table '%s' is not defined in the db schema" % table

    if inf:
      fd = open(inf, 'r')
    else:
      fd = sys.stdin

    for row in json.loads(fd.read()):
      if table == "Users":
        self.insertUser(row)
      elif table == "Terms":
        self.insertTerm(row)
  

