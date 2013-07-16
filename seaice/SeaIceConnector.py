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

##
# Verify permissions of configuration file. 
#
def accessible_by_group_or_world(file):
  st = os.stat(file)
  return bool( st.st_mode & (stat.S_IRWXG | stat.S_IRWXO) )

## 
# Get Local db configuration from $HOME/.seaice 
# or file specified. 
#
def get_config(config_file = os.environ['HOME'] + '/.seaice'):
  if accessible_by_group_or_world(config_file):
    print ('error: config file ' + config_file +
      ' has group or world ' +
      'access; permissions should be set to u=rw')
    sys.exit(1)
  config = configparser.RawConfigParser()
  config.read(config_file)
  return config



## 
# class SeaIceConnector 
# 
# Connection to the PostgreSQL database. Create or drop schema, 
# tables, and triggers, encapsulation of all the queries we need. 
#
class SeaIceConnector: 
  
  ##
  # Establish connection to database. For a local database, this is
  # specified by the paramters. If the parameters are unspecified, 
  # then attempt to connect to a foreign database sepcified by the 
  # environment variable DATABASE_URL. This is to support Heroku's
  # functionality. 
  # 
  def __init__(self, user=None, password=None, db=None):
  
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


  ## Alter Schema 
  # Create a schema for the SeaIce database that includes the tables
  # Users, Terms, Relations(TODO), and Comments, and an update trigger 
  # funciton. 
  #
  def createSchema(self):
    
    cur = self.con.cursor()

    # Create SI schema. 
    cur.execute("""
      create schema SI; 
      """
    )
    
    # Create Users table if it doesn't exist. 
    # TODO unique constraint on enail
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
      alter sequence SI.Users_id_seq restart with 1001;"""
    )

    # Create Terms table if it doesn't exist.
    cur.execute("""
      create type SI.Class as enum ('vernacular', 'canonical', 'deprecated');
      create table if not exists SI.Terms
        (
          id serial primary key not null, 
          owner_id integer default 0 not null,
          term_string text not null, 
          definition text not null,
          examples text not null, 
          tsv tsvector, 
          score integer default 0 not null,
          consensus float default 0 not null,
          class SI.Class default 'vernacular' not null,
          created timestamp default now() not null, 
          modified timestamp default now() not null, 
          
          R integer default 0 not null,
          U_sum integer default 0 not null,
          D_sum integer default 0 not null,
          u integer default 0 not null,
          d integer default 0 not null,
          T_last   timestamp default now() not null, 
          T_stable timestamp default now() not null, 
          
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
        );
      alter sequence SI.Comments_id_seq restart with 1001;"""
    )

    # Create Tracking table if it doesn't exist. This table keeps 
    # track of the terms users have starred as well as their vote
    # (+1 or -1). If they haven't voted, then vote = 0. This
    # implies a rule: if a user untracks a term, then his or her 
    # vote is removed. 
    cur.execute("""
      create table if not exists SI.Tracking
      (
        user_id integer not null, 
        term_id integer not null,
        vote integer default 0 not null, 
        star boolean default true not null,
        UNIQUE (user_id, term_id),
        foreign key (user_id) references SI.Users(id) on delete cascade, 
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
        before update of term_string, definition, examples on SI.Terms
        for each row
         execute procedure SI.upd_timestamp();
      
      create trigger comment_update
        before update on SI.Comments
        for each row
         execute procedure SI.upd_timestamp();

      create trigger tsv_update 
        before insert or update on SI.Terms
        for each row execute procedure
          tsvector_update_trigger(tsv, 'pg_catalog.english', term_string, definition, examples);"""
    )

    # Set user permissions. (Not relevant for Heroku-Postgres.)
    if not self.heroku_db:
      cur.execute("""
       grant usage on schema SI to admin, viewer, contributor;
       grant select on all tables in schema SI to viewer, contributor; 
       grant insert, delete, update on SI.Terms, SI.Terms_id_seq to contributor"""
      )
  
  ##
  # Drop SeaIce schema. 
  #
  def dropSchema(self): 
    cur = self.con.cursor()
    cur.execute("drop schema SI cascade")

  ##
  # Commit changes to database made while the connection was open. This 
  # should be called before the class destructor is called in order to 
  # save changes. 
  #
  def commit(self): 
    self.con.commit()

  ##
  # Add a term to the database and return Terms.Id (None if failed) 
  #
  def insertTerm(self, term): 
    cur = self.con.cursor()

    # Default values for table entries.  
    defTerm = { 
      "id" : "default",
      "term_string" : "nil", 
      "definition" : "nil", 
      "examples" : "nil", 
      "score" : "default", 
      "created" : "current_timestamp", 
      "modified" : "current_timestamp",
      "owner_id" : "default"
    }

    # Format entries for db query
    for (key, value) in term.iteritems():
      if key in ["created", "modified", "t_stable", "t_last"]:
        defTerm[key] = "'" + str(value) + "'"
      else: 
        defTerm[key] = unicode(value).replace("'", "''")

    try:
      cur.execute(
        """insert into SI.Terms( id, 
                              term_string, 
                              definition, 
                              examples, 
                              score,
                              created,
                              modified,
                              owner_id ) 
            values(%s, '%s', '%s', '%s', %s, %s, %s, %s) 
            returning id
        """ % (defTerm['id'], defTerm['term_string'], defTerm['definition'], defTerm['examples'], 
               defTerm['score'], defTerm['created'], defTerm['modified'], defTerm['owner_id']))
    
      res = cur.fetchone()
      if res: 
        return res[0]
      else:
        return None

    except pgdb.DatabaseError, e:
      if e.pgcode == '23505': # Duplicate primary key
         print >>sys.stderr, "warning: skipping duplicate primary key Id=%s" % defTerm['id']
         cur.execute("rollback;")
         return None 
      raise e

  ##
  # Remove term from the database and return id of deleted
  #
  def removeTerm(self, id):
    cur = self.con.cursor()
    cur.execute("delete from SI.Terms where id=%d returning id" % id)
    res = cur.fetchone()
    if res: return res[0]
    else:   return None


  ## 
  # Retrieve term by id. Return dictionary structure or None. 
  # 
  def getTerm(self, id): 
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("select * from SI.Terms where id=%d" % id)
    return cur.fetchone()
  
  ## 
  # Return a list of all terms (rows) in table. 
  # 
  def getAllTerms(self, sortBy=None): 
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    if sortBy:
      cur.execute("select * from SI.Terms order by %s" % sortBy)
    else:
      cur.execute("select * from SI.Terms")
    return cur.fetchall()

  ##
  # Search table by term string and return a list of dictionary structures
  #
  def getByTerm(self, term_string): 
    term_string = term_string.replace("'", "''")
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("select * from SI.Terms where term_string='%s'" % term_string)
    return list(cur.fetchall())

  ##
  # Return a list of terms owned by User
  #
  def getTermsByUser(self, user_id):
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("select * from SI.Terms where owner_id=%d" % user_id) 
    return list(cur.fetchall())

  ##
  # Return a list of terms starred by user
  #
  def getTermsByTracking(self, user_id):
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("""select *from SI.Terms as term, SI.Tracking as track
                   where track.user_id={0} 
                     and track.term_id=term.id 
                     and term.owner_id!={0}
                     and track.star=true""".format(user_id))
    return list(cur.fetchall())

  ##
  # Search table by definition.
  #
  def search(self, string): 
    string = string.replace("'", "''")
    string = ' & '.join(string.split(' ')) # |'s are also aloud, and paranthesis TODO
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("""
      SELECT id, owner_id, term_string, definition, examples,  
             score, created, modified, consensus, class,
             ts_rank_cd(tsv, query, 32 /* rank(rank+1) */ ) AS rank
        FROM SI.Terms, to_tsquery('english', '%s') query 
        WHERE query @@ tsv 
        ORDER BY rank DESC
     """ % string)

    return list(cur.fetchall())

  ##
  # Modify a term's definition and/or term_string. 
  # Note: term ownership authenticated upstream! 
  # 
  def updateTerm(self, id, term): 
    cur = self.con.cursor()
    for (key, value) in term.iteritems():
      term[key] = unicode(value).replace("'", "''")
    cur.execute("update SI.Terms set term_string='%s', definition='%s', examples='%s' where id=%d" % (
      term['term_string'], term['definition'], term['examples'], id))
 

  ##
  # Insert a new user into the table and return Users.Id (None if failed) 
  #
  def insertUser(self, user):
    
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
      defUser[key] = unicode(value).replace("'", "''")

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
         cur.execute("rollback;")
         return None 
      raise e

  ##
  # Get User by Id
  #
  def getUser(self, id):
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("select * from SI.Users where id=%d" % id)
    return cur.fetchone()
      
  ##
  # Return Users.Id where Users.auth_id = auth_id and 
  # Users.authority = authority
  #
  def getUserByAuth(self, authority, auth_id):
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("select * from SI.Users where auth_id = '%s' and authority = '%s'" % 
                 (auth_id, authority))
    res = cur.fetchone()
    return res

  ##
  # Return Users.Name where Users.id = Userid
  #
  def getUserNameById(self, Userid, full=False): 
    cur = self.con.cursor()
    cur.execute("select first_name, last_name from SI.Users where id=%d" % Userid)
    res = cur.fetchone()
    if res and full: 
      return res[0] + " " + res[1]
    elif res and not full: 
      return res[0]
    else: 
      return None
  
  ##
  # Update User name
  # 
  def updateUser(self, id, first, last): 
    cur = self.con.cursor()
    cur.execute("update SI.Users set first_name='%s', last_name='%s' where id=%d" % (
      first, last, id))
  ##
  # Set reputation of user
  # TODO update consensus for terms user has voted on.
  #
  def updateUserReputation(self, user_id, rep): 
    cur = self.con.cursor()
    cur.execute("update SI.Users set reputation=%d where id=%d" % (rep, user_id))

  ##
  # Insert a new comment into the database. 
  #
  def insertComment(self, comment): 
    defComment = { 
      "id" : "default",
      "owner_id" : "default", 
      "term_id" : "default", 
      "comment_string" : "nil"
    }
  
    # Format entries for db query
    for (key, value) in comment.iteritems():
      if key in ["created", "modified"]:
        defTerm[key] = "'" + str(value) + "'"
      else: defComment[key] = unicode(value).replace("'", "''")

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
         print >>sys.stderr, "warning: skipping duplicate primary key Id=%s" % defComment['id']
         cur.execute("rollback;")
         return None 
      raise e

  ##
  # Remove comment and return id of removed
  # 
  def removeComment(self, id):
    cur = self.con.cursor()
    cur.execute("delete from SI.Comments where id=%d returning id" % id)
    res = cur.fetchone()
    if res: return res[0]
    else: return None

  ##
  #  Update term comment. 
  #
  def updateComment(self, id, comment):
    cur = self.con.cursor()
    for (key, value) in comment.iteritems():
      comment[key] = unicode(value).replace("'", "''")
    cur.execute("update SI.Comments set comment_string='%s' where id=%d" % (
      comment['comment_string'], id))

  ##
  # Return comment.
  #
  def getComment(self, id):
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("select * from SI.Comments where id=%d" % id)
    return cur.fetchone()

  ##
  # Return a term's comment history, ordered by creation date.
  #
  def getCommentHistory(self, term_id):
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("select * from SI.Comments where term_id=%d order by created" % term_id)
    return list(cur.fetchall())
  
  ##
  # Insert a tracking row, skipping if (term_id, user_id) pair exists
  #
  def insertTracking(self, tracking): 
    defTracking = { 
      "vote" : "default" 
    }
    
    for (key, value) in tracking.iteritems():
      defTracking[key] = unicode(value)
  
    try:
      cur = self.con.cursor()
      cur.execute("""insert into SI.Tracking (user_id, term_id, vote) 
                      values (%s, %s, %s)
                      returning user_id, term_id""" % (defTracking['user_id'], 
                                                       defTracking['term_id'], 
                                                       defTracking['vote']))
      return cur.fetchone()
    
    except pgdb.DatabaseError, e:
      if e.pgcode == '23505': # Duplicate primary key
         print >>sys.stderr, "warning: skipping duplicate (TermId=%s, UserId=%s)" % (
          defTracking['term_id'], defTracking['user_id'])
         cur.execute("rollback;")
         return None 
      raise e

  ##
  # Cast or change a user's vote on a term. Return the change in term's score. 
  #
  def castVote(self, user_id, term_id, vote): 
    cur = self.con.cursor()
    cur.execute("""SELECT vote FROM SI.Tracking WHERE
                   user_id={0} AND term_id={1}""".format(user_id, term_id))
    p_vote = cur.fetchone()

    res = 0

    if not p_vote:
      cur.execute("""INSERT INTO SI.Tracking (user_id, term_id, vote)
                     VALUES ({0}, {1}, {2})""".format(user_id, term_id, vote))
      cur.execute("UPDATE SI.Terms SET score=(score+({1})) WHERE id={0}".format(term_id, vote))
      res = vote
      
    elif p_vote[0] != vote:
      cur.execute("""UPDATE SI.Tracking SET vote={2}
                     WHERE user_id={0} AND term_id={1}""".format(user_id, term_id, vote))
      cur.execute("UPDATE SI.Terms SET score=(score+({1})) WHERE id={0}".format(term_id, vote - p_vote[0]))
      res = vote - p_vote[0]
    
    (U, V) = self.preScore(term_id) # TODO implement O(1) 
    S = self.postScore(U, V)
      
    cur.execute("""UPDATE SI.Terms SET consensus={1}
                   WHERE id={0}""".format(term_id, S))

    return res

  ##
  # Get user's vote for a term
  #
  def getVote(self, user_id, term_id): 
    cur = self.con.cursor()
    cur.execute("""SELECT vote FROM SI.Tracking WHERE
                   user_id={0} AND term_id={1}""".format(user_id, term_id))
    res = cur.fetchone()
    if res: 
      return res[0]
    return None 

  ##
  # User is tracking term. Return 1 if a row was inserted into the Tracking 
  # table, 0 if not. 
  #
  def trackTerm(self, user_id, term_id): 
    cur = self.con.cursor()
    cur.execute("""SELECT vote FROM SI.Tracking 
                   WHERE user_id={0} AND term_id={1}""".format(user_id, term_id))
    if not cur.fetchone(): 
      cur.execute("""INSERT INTO SI.Tracking (user_id, term_id, vote) 
                     VALUES ({0}, {1}, 0)""".format(user_id, term_id))
      return 1
    else: 
      cur.execute("""UPDATE SI.Tracking SET star=True
                     WHERE user_id={0} AND term_id={1}""".format(user_id, term_id))
      return 0

  ##
  # Untrack term. 
  #
  def untrackTerm(self, user_id, term_id):
    cur = self.con.cursor()
    cur.execute("""UPDATE SI.Tracking SET star=False
                   WHERE user_id={0} AND term_id={1} 
                   RETURNING vote""".format(user_id, term_id))
    vote = cur.fetchone()
    if vote: 
      return 1
    else: return 0

  ##
  # Check tracking
  #
  def checkTracking(self, user_id, term_id):
    cur = self.con.cursor()
    cur.execute("""SELECT star FROM SI.Tracking 
                   WHERE user_id={0} AND term_id={1}""".format(user_id, term_id))
    star = cur.fetchone()
    if star:
      return star[0]
    else: return False
  
  
  
  ##
  # Prescore term. Returns a tuple of pair of dictionaries 
  # (User.Id -> User.Reputation) of up voters and down voters
  # (U, D). 
  # 
  def preScore(self, term_id):
    cur = self.con.cursor()
    cur.execute("""SELECT v.user_id, v.vote, u.reputation
                   FROM SI.Users as u, SI.Tracking as v
                   WHERE v.term_id = %d AND v.user_id = u.id""" % term_id)
    U = {}; D = {}
    for (user_id, vote, rep) in cur.fetchall():
      if vote == 1: 
        U[user_id] = rep
      elif vote == -1:
        D[user_id] = rep

    return (U, D) 

  ##
  # Postscore term. Input the reputations of upvoters and downvoters 
  # and compute the consensus score. 
  #
  def postScore(self, U, D):
    cur = self.con.cursor()
    cur.execute("SELECT COUNT(*) FROM SI.Users")
    t = cur.fetchone()[0] # total users
    u = len(U) 
    d = len(D)
    v = u + d             # total voters

    R = reduce(lambda Ri,Rj: Ri+Rj, [0] + U.values() + D.values()) # total reputation
                                                                   # of voters
    
    if R: 
      R = float(R) 
      U_sum = reduce(lambda ri,rj: ri+rj, 
                      [0] + map(lambda Ri: Ri/R, U.values()))
      D_sum = reduce(lambda ri,rj: ri+rj, 
                      [0] + map(lambda Ri: Ri/R, D.values()))
    else:
      U_sum = D_sum = 0.0

    return (u + U_sum * (t - v)) / (u + d + (U_sum + D_sum) * (t - v)) if v else 0

  ##
  # Check that Terms.Consensus is consistent. Update if it wasn't 
  #
  def checkTermConsensus(self, term_id):
    cur = self.con.cursor()
    cur.execute("SELECT consensus FROM SI.Terms where id=%d" % term_id)
    p_S = cur.fetchone()[0]
    (U, V) = self.preScore(term_id)
    S = self.postScore(U, V)
    if int(p_S) != int(S):
      cur.execute("UPDATE SI.Terms SET consensus=%d WHERE id=%d" % (S, term_id))
      return False
    return True
      


  ## 
  # Export database in JSON format to "outf". If no file name 
  # provided, dump to standard out. 
  #
  def Export(self, table, outf=None):
    if table not in ['Users', 'Terms', 'Comments', 'Tracking']:
      print >>sys.stderr, "error (export): table '%s' is not defined in the db schema" % table
      return

    if outf: 
      fd = open(outf, 'w')
    else:
      fd = sys.stdout

    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("select * from SI.%s" % table)
    rows = cur.fetchall()
    Pretty.printAsJSObject(rows, fd)

  ##
  # Import database from JSON formated "inf".
  #
  def Import(self, table, inf=None): 
    if table not in ['Users', 'Terms', 'Comments', 'Tracking']:
      print >>sys.stderr, "error (import): table '%s' is not defined in the db schema" % table
      return 

    if inf:
      fd = open(inf, 'r')
    else:
      fd = sys.stdin

    for row in json.loads(fd.read()):
      if table == "Users":
        self.insertUser(row)
      elif table == "Terms":
        self.insertTerm(row)
      elif table == "Comments":
        self.insertComment(row)
      elif table == "Tracking":
        self.insertTracking(row)
  

