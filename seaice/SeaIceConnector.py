# SeaIceConnector.py - implementation of class SeaIceConnector, the API for 
# the SeaIce database. This class is capable of connecting to a local 
# PostgreSQL database, or a foreign one specified by the environment variable 
# DATABASE_URI. 
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

import os, sys, configparser, urlparse
import json, psycopg2 as pgdb
import psycopg2.extras  
import pretty
import auth
import notify

"""
  Some constants for stability calculation. 
"""

#: The maximum varation in consensus allowed 
#: for score to be considered stable (S/hour).
stabilityError = 0.10  

stabilityFactor = 3600 #: Convert seconds (datetime.timedelta.seconds) to hours. 

#: Interval (in hours) for which a term must
#: be stable in order to be classified. 
stabilityInterval = 1 
        
stabilityConsensusIntervalHigh = 0.75 #: Classify stable term as canonical.
stabilityConsensusIntervalLow =  0.25 #: Classify stable term as deprecated.


def calculateConsensus(u, d, t, U_sum, D_sum):
  """ Calcluate consensus score. This is a heuristic for the percentage 
      of the community who finds a term useful. Based on the observation
      that not every user will vote on a given term, user reptuation is 
      used to estimate consensus. As the number of voters approaches 
      the number of users, the votes become more equitable. (See 
      doc/Scoring.pdf for details.) 
   
      :param u: Number of up voters.
      :param d: Number of donw voters.
      :param t: Number of total users.
      :param U_sum: Sum of up-voter reputation.
      :param D_sum: Sum of down-voter reputation.
  """
  v = u + d
  R = U_sum + D_sum
  return (u + (float(U_sum)/R if R > 0 else 0.0) * (t-v)) / t if v else 0


def calculateStability(S, p_S, T_now, T_last, T_stable):
  """Calculate term stability, returning the time point when the term 
     become stable (as a datetime.datetime) or None if it's not stable. 
     This is based on the rate of change of the consensus score: 
     
        ``delta_S = (S - P_s) / (T_now - T_last)``
    
     :param T_now: Current time.
     :type T_now: datetime.datetime
     :param T_last: Time of last consensus score calculation. 
     :type T_last: datetime.datetime
     :param T_stable: Time since term stabilized.
     :type T_last: datetime.datetime or None
     :param S: Consensus score at T_now.
     :type S: float
     :param p_S: Consensus score at T_last.
     :type p_S: float
  """ 
  try: 
    delta_S = abs((S - p_S) * stabilityFactor / (T_now - T_last).seconds) 
  except ZeroDivisionError: 
    delta_S = float('+inf')

  if delta_S < stabilityError and T_stable == None: # Score becomes stable
    T_stable = T_now

  elif delta_S > stabilityError: # Score has become unstable, reset T_stable
    T_stable = None

  else: # Score is stable and below threshold, do nothing
    pass

  return T_stable


orderOfClass = { 'deprecated' : 2, 'vernacular' : 1, 'canonical' : 0 }

class SeaIceConnector: 
  """ Connection to the PostgreSQL database. 
      
    This object is capable of either connecting to a local database
    (specified by the parameters) or a remote database specified by
    the environment variable ``DATABASE_URL`` if no paramters are 
    given. This is to support Heroku functionality. For local testing 
    with your Heroku-Postgres based database, do 

    ``export DATABAE_URL=$(heroku config:get DATABASE_URL) && ./ice --config=heroku``

  :param user: Name of DB role.
  :type user: str
  :param password: User's password.
  :type password: str
  :param db: Name of database. 
  :type db: str
  """

  def __init__(self, user=None, password=None, db=None):
  
    if not user: 

      urlparse.uses_netloc.append("postgres")
      url = urlparse.urlparse(os.environ["DATABASE_URL"])

      #: The PostgreSQL database connector provided 
      #: by the psycopg2 package. 
      self.con = pgdb.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
      )
      
    else: 
        
      self.con = pgdb.connect(database=db, user=user, password=password)

    cur = self.con.cursor()
    cur.execute("SELECT version(); BEGIN")
  
  def __del__(self):
    self.con.close()


  def createSchema(self):
    """ 
      Create the ``SI`` schema for SeaIce with the tables ``SI.Users``, 
      ``SI.Terms``, ``SI.Comments``, ``SI.Tracking`` (vote and star), 
      and various triggers; create ``SI_Notify`` with ``SI_Notify.Notify``.
    """
    
    cur = self.con.cursor()

    #: Create SI schema. 
    cur.execute("""
      CREATE SCHEMA SI; 
      """
    )
    
    #: Create Users table if it doesn't exist. 
    cur.execute("""
      CREATE TABLE IF NOT EXISTS SI.Users
        (
          id           SERIAL PRIMARY KEY NOT NULL,
          authority    VARCHAR(64) NOT NULL, 
          auth_id      VARCHAR(64) NOT NULL, 
          email        VARCHAR(64) NOT NULL, 
          last_name    VARCHAR(64) NOT NULL,
          first_name   VARCHAR(64) NOT NULL,
          reputation   INTEGER default 1 NOT NULL,
          UNIQUE (email)
        );
      ALTER SEQUENCE SI.Users_id_seq RESTART WITH 1001;"""
    )

    #: Create Terms table if it doesn't exist.
    cur.execute("""
      CREATE TYPE SI.Class AS ENUM ('vernacular', 'canonical', 'deprecated');
      CREATE TABLE IF NOT EXISTS SI.Terms
        (
          id          SERIAL PRIMARY KEY NOT NULL, 
          owner_id    INTEGER DEFAULT 0 NOT NULL,
          created     TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
          modified    TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
          term_string TEXT NOT NULL, 
          definition  TEXT NOT NULL,
          examples    TEXT NOT NULL, 
         
          up         INTEGER DEFAULT 0 NOT NULL,
          down       INTEGER DEFAULT 0 NOT NULL,
          consensus  FLOAT DEFAULT 0 NOT NULL,
          class SI.Class DEFAULT 'vernacular' NOT NULL,
          
          U_sum     INTEGER DEFAULT 0 NOT NULL,
          D_sum     INTEGER DEFAULT 0 NOT NULL,
          T_last    TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
          T_stable  TIMESTAMP WITH TIME ZONE DEFAULT now(), 
          
          tsv tsvector, 
          
          FOREIGN KEY (owner_id) REFERENCES SI.Users(id)
        ); 
      ALTER SEQUENCE SI.Terms_id_seq RESTART WITH 1001;"""
    )

    #: Create Comments table if it doesn't exist.
    cur.execute("""
      CREATE TABLE IF NOT EXISTS SI.Comments
        (
          id        SERIAL PRIMARY KEY NOT NULL, 
          owner_id  INTEGER DEFAULT 0 NOT NULL, 
          term_id   INTEGER DEFAULT 0 NOT NULL, 
          created   TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
          modified  TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
          comment_string TEXT NOT NULL,

          FOREIGN kEY (owner_id) REFERENCES SI.Users(id),
          FOREIGN KEY (term_id) REFERENCES SI.Terms(id) ON DELETE CASCADE
        );
      ALTER SEQUENCE SI.Comments_id_seq RESTART WITH 1001;"""
    )

    #: Create Tracking table if it doesn't exist. This table keeps 
    #: track of the terms users have starred as well as their vote
    #: (+1 or -1). If they haven't voted, then vote = 0. This
    #: implies a rule: if a user untracks a term, then his or her 
    #: vote is removed. 
    cur.execute("""
      CREATE TABLE IF NOT EXISTS SI.Tracking
      (
        user_id        INTEGER NOT NULL, 
        term_id        INTEGER NOT NULL,
        vote INTEGER   DEFAULT 0 NOT NULL, 
        star BOOLEAN   DEFAULT true NOT NULL,

        UNIQUE (user_id, term_id),
        FOREIGN KEY (user_id) REFERENCES SI.Users(id) ON DELETE CASCADE, 
        FOREIGN KEY (term_id) REFERENCES SI.Terms(id) ON DELETE CASCADE
      )"""
    )
    
    #: Create schema and table for notifications.  
    cur.execute("""
      CREATE SCHEMA SI_Notify; 
      CREATE TYPE SI_Notify.Class AS ENUM ('Base', 
                                           'Comment',
                                           'TermUpdate',
                                           'TermRemoved');
                                                                                    
      CREATE TABLE SI_Notify.Notify
        (
          user_id      INTEGER not null, 
          class        SI_notify.class not null, 
          T            TIMESTAMP WITH TIME ZONE not null, 
          term_id      INTEGER, 
          from_user_id INTEGER, 
          term_string  TEXT, 
          FOREIGN KEY (user_id) REFERENCES SI.Users(id) on DELETE CASCADE, 
          FOREIGN KEY (from_user_id) REFERENCES SI.Users(id) on DELETE CASCADE, 
          FOREIGN KEY (term_id) REFERENCES SI.Terms(id) on DELETE CASCADE
        );
    """)
  
    #: Create update triggers.
    cur.execute("""
      CREATE OR REPLACE FUNCTION SI.upd_timestamp() RETURNS TRIGGER 
        language plpgsql
        as
         $$
          begin
            new.modified = current_timestamp;
            return new;
          end;
         $$;
              
      CREATE TRIGGER term_update
        before update of term_string, definition, examples on SI.Terms
        for each row
         execute procedure SI.upd_timestamp();
      
      CREATE TRIGGER comment_update
        before update on SI.Comments
        for each row
         execute procedure SI.upd_timestamp();

      CREATE TRIGGER tsv_update 
        before insert or update on SI.Terms
        for each row execute procedure
          tsvector_update_trigger(tsv, 'pg_catalog.english', term_string, definition, examples);"""
    )

  def dropSchema(self): 
    """ Drop ``SI`` and ``SI_Notify`` schemas. """
    cur = self.con.cursor()
    cur.execute("DROP SCHEMA SI CASCADE")
    cur.execute("DROP SCHEMA IF EXISTS SI_Notify CASCADE")

  
  def commit(self): 
    """ Commit changes to database made while the connection was open. This 
        should be called before the class destructor is called in order to 
        save changes. It should be called freuqently in a mult-threaded 
        environment. 
    """
    return self.con.commit()

  def getTime(self):
    """ Get *T_now* timestamp according to database. This is important when
        the SeaIce database is deployed to some anonymous server farm.

    :rtype: datetime.datetime
    """
    cur = self.con.cursor()
    cur.execute("SELECT now()")
    return cur.fetchone()[0]
    
    ## Term queries ##

  def insertTerm(self, term): 
    """ Add a term to the database and return the term's ID. 

    :param term: Term row to be inserted. Default values will be used for 
                 omitted columns.
    :type term:  dict
    :returns: ID of inserted row. If term['id'] isn't assigned, the next
              available ID in the sequence is given. 
    :rtype:   int or None
    """
    cur = self.con.cursor()

    #: Default values for table entries.  
    defTerm = { 
      "id" : "default",
      "term_string" : "nil", 
      "definition" : "nil", 
      "examples" : "nil", 
      "down" : "default", 
      "up" : "default", 
      "created" : "now()", 
      "modified" : "now()",
      "T_stable" : "NULL", 
      "T_last" : "now()", 
      "owner_id" : "default"
    }

    #: Format entries for db query
    for (key, value) in term.iteritems():
      if key.lower() in ["created", "modified", "t_stable", "t_last"]:
        defTerm[key] = "'" + str(value) + "'"
      else: 
        defTerm[key] = unicode(value).replace("'", "''")

    try:
      cur.execute(
        """INSERT INTO SI.Terms( id, 
                              term_string, 
                              definition, 
                              examples, 
                              up,
                              down,
                              created,
                              modified,
                              owner_id ) 
            VALUES(%s, '%s', '%s', '%s', %s, %s, %s, %s, %s) 
            RETURNING id
        """ % (defTerm['id'], defTerm['term_string'], defTerm['definition'], defTerm['examples'], 
               defTerm['up'], defTerm['down'], defTerm['created'], defTerm['modified'], defTerm['owner_id']))
    
      res = cur.fetchone()
      if res: 
        return res[0]
      else:
        return None

    except pgdb.DatabaseError, e:
      if e.pgcode == '23505': #: Duplicate primary key
         print >>sys.stderr, "warning: skipping duplicate primary key Id=%s" % defTerm['id']
         cur.execute("ROLLBACK;")
         return None 
      raise e

  def removeTerm(self, id):
    """ Remove term row from the database.

    :param id: Term Id.
    :type id: int
    :returns: ID of removed term. 
    :rtype: int or None
    """
    cur = self.con.cursor()
    cur.execute("DELETE FROM SI.Terms WHERE id=%d RETURNING id" % id)
    res = cur.fetchone()
    if res: return res[0]
    else:   return None


  def getTerm(self, id): 
    """ Get term by ID. 

    :param id: Term ID.
    :type id: int
    :rtype: dict or None
    """ 
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM SI.Terms WHERE id=%d" % id)
    return cur.fetchone()
  
  def getTermString(self, id): 
    """ Get term string by ID.

    :param id: Term ID.
    :type id: int
    :rtype: str or None
    """
    cur = self.con.cursor()
    cur.execute("SELECT term_string FROM SI.Terms WHERE id=%d" % id)
    res = cur.fetchone()
    if res: return res[0]
    else:   return None
  
  def getAllTerms(self, sortBy=None): 
    """ Return an iterator over ``SI.Terms``. 

    :param sortBy: Column by which sort the results in ascending order.
    :type sortBy: str
    :rtype: dict iterator
    """ 
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    if sortBy:
      cur.execute("""SELECT id, owner_id, term_string, definition, examples, 
                            modified, created, up, down, consensus, class,
                            T_stable, T_last
                       FROM SI.Terms 
                      ORDER BY %s""" % sortBy)
    else:
      cur.execute("""SELECT id, owner_id, term_string, definition, examples, 
                            modified, created, up, down, consensus, class,
                            T_stable, T_last
                       FROM SI.Terms""")
    for row in cur.fetchall():
      yield row

  def getTermStats(self):
    """ Return the various parameters used to calculate consensus 
        and stability for each term.  

    :rtype: dict iterator
    """
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("""SELECT id, owner_id, term_string, modified, created, 
                          up, down, U_sum, D_sum, T_last, T_stable
                     FROM SI.Terms""")
    for row in cur.fetchall():
      yield row

  def getByTerm(self, term_string): 
    """ Search table by term string and return an iterator over the matches.

    :param term_string: The exact term string (case sensitive). 
    :type term_string: str
    :rtype: dict or None
    """
    term_string = term_string.replace("'", "''")
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM SI.Terms WHERE term_string='%s'" % term_string)
    for row in cur.fetchall():
      yield row

  def getTermsByUser(self, user_id):
    """ Return an iterator over terms owned by a user. 
    
    :param user_id: ID of the user. 
    :type user_id: int
    :rtype: dict iterator
    """
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM SI.Terms WHERE owner_id=%d" % user_id) 
    for row in cur.fetchall():
      yield row

  def getTermsByTracking(self, user_id):
    """ Return an iterator over terms tracked by a user (terms that the 
        user has starred). 

    :param user_id: ID of the user. 
    :type user_id: int
    :rtype: dict iterator
    """
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("""SELECT * FROM SI.Terms AS term, 
                                 SI.Tracking AS track
                    WHERE track.user_id={0} 
                      AND track.term_id=term.id 
                      AND term.owner_id!={0}
                      AND track.star=true""".format(user_id))
    for row in cur.fetchall():
      yield row

  def getTrackingByTerm(self, term_id):
    """ Return an iterator over users tracking a term.

    :param term_id: ID of term. 
    :type user_id: int
    :returns: User rows. 
    :rtype: dict iterator
    """ 
    cur = self.con.cursor()
    cur.execute("""SELECT user_id FROM SI.Tracking 
                    WHERE term_id={0} """.format(term_id))
    for row in cur.fetchall():
      yield row[0]

  def search(self, string): 
    """ Search table by term_string, definition and examples. Rank 
        results by relevance to query, consensus, and classificaiton.

    :param string: Search query.
    :type string: str
    :rtype: dict list
    """
    string = string.replace("'", "''")
    string = ' & '.join(string.split(' ')) # |'s are also aloud, and paranthesis TODO
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("""
      SELECT id, owner_id, term_string, definition, examples,  
             up, down, created, modified, consensus, class,
             ts_rank_cd(tsv, query, 32 /* rank(rank+1) */ ) AS rank
        FROM SI.Terms, to_tsquery('english', '%s') query 
        WHERE query @@ tsv 
        ORDER BY rank DESC
     """ % string)

    rows = sorted(cur.fetchall(), key=lambda row: orderOfClass[row['class']])
    rows = sorted(rows, key=lambda row: row['consensus'], reverse=True)
    return list(rows)

  def updateTerm(self, id, term): 
    """ Modify a term's term string, deifnition and examples. 
        Note: term ownership authenticated upstream! 

    :param id: Term ID. 
    :type id: int
    :param term: Dictionary containing atleast the keys 'term_string', 'definition', 
                 and 'examples' with string values.
    :type term: dict 
    """ 
    cur = self.con.cursor()
    for (key, value) in term.iteritems():
      term[key] = unicode(value).replace("'", "''")
    cur.execute("UPDATE SI.Terms SET term_string='%s', definition='%s', examples='%s' WHERE id=%d" % (
      term['term_string'], term['definition'], term['examples'], id))
 

    ## User queries ##

  def insertUser(self, user):
    """ Insert a new user into the table and return the new ID. 

    :param user: Default values are used for any omitted columns.
    :type user: dict 
    :rtype: int or None
    """
    
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
      cur.execute("""INSERT INTO SI.Users(id, email, last_name, first_name, reputation, authority, auth_id) 
                     VALUES (%s, '%s', '%s', '%s', %s, '%s', '%s')
                     RETURNING id""" % (defUser['id'],
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
         cur.execute("ROLLBACK;")
         return None 
      raise e

  def getUser(self, id):
    """ Get User by ID.

    :param id: User ID. 
    :type id: int
    :rtype: dict or None
    """
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM SI.Users WHERE id=%d" % id)
    return cur.fetchone()
  
  def getAllUsers(self): 
    """ Return an iterator over ``SI.Users``. 

    :rtype: dict iterator
    """ 
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM SI.Users")
    for row in cur.fetchall():
      yield row
      
  def getUserByAuth(self, authority, auth_id):
    """ Get user identified by an authentication ID. It's assumed that this ID 
        is unique in the context of a particular authority, such as Google. 

    **TODO:** originally I planned to use (authority, auth_id) as the unique 
    constraint on the SI.Users table. My guess is that most, if not all 
    services have an associated email address. The unique constraint is 
    actually the user's email. This method should be replaced.  

    :param authority: Organization providing authentication. 
    :type authority: str
    :param auth_id: Authentication ID.
    :type auth_id: str
    :returns: Internal surrogate ID of user. 
    :rtype: int or None
    """
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM SI.Users WHERE auth_id = '%s' AND authority = '%s'" % 
                 (auth_id, authority))
    res = cur.fetchone()
    return res

  def getUserNameById(self, id, full=False): 
    """ Get username by ID. 

    :param id: User ID. 
    :type id: int
    :param full: Get full name
    :type full: bool
    :returns: If *full* is set, then return the first and last name of the user. 
              Otherwise, just return the first name. 
    :rtype: str or None
    """
    cur = self.con.cursor()
    cur.execute("SELECT first_name, last_name FROM SI.Users WHERE id=%d" % id)
    res = cur.fetchone()
    if res and full: 
      return res[0] + " " + res[1]
    elif res and not full: 
      return res[0]
    else: 
      return None
  
  def updateUser(self, id, first, last): 
    """ Update user's name. 

    :param id: User ID.  
    :type id: int
    :param first: First name. 
    :type first: str
    :param last: Last name. 
    :type last: str
    """ 
    cur = self.con.cursor()
    cur.execute("UPDATE SI.Users SET first_name='%s', last_name='%s' WHERE id=%d" % (
      first, last, id))

  def updateUserReputation(self, id, rep): 
    """ Set reputation of user. This triggers an update of the consensus score
        and term stability. Commit updates immediately. 

    :param id: User ID. 
    :type id: int
    :param rep: New reputation score. 
    :type rep: int
    """
    cur = self.con.cursor()
    cur.execute("SELECT now(), count(*) FROM SI.Users")
    (T_now, t) = cur.fetchone() 
    cur.execute("SELECT reputation FROM SI.Users WHERE id=%d" % id) 
    p_rep = cur.fetchone()
    if not p_rep:
      return None
    p_rep = p_rep[0]

    cur.execute("""SELECT v.vote, t.id, t.up, t.down, t.U_sum, t.D_sum, 
                          t.T_last, t.T_stable, t.consensus
                   FROM SI.Tracking as v, 
                        SI.Terms as t
                   WHERE v.user_id = %d 
                     AND v.term_id = t.id
                     AND v.vote != 0""" % id)
    
    for (vote, term_id, u, d, U_sum, D_sum, T_last, T_stable, p_S) in cur.fetchall():
      
      #: Compute new consensus score
      if vote == 1:      U_sum += rep - p_rep
      elif vote == -1:   D_sum += rep - p_rep 
      S = calculateConsensus(u, d, t, float(U_sum), float(D_sum))

      #: See if stability has changed  
      T_stable = calculateStability(S, p_S, T_now, T_last, T_stable)
      
      cur.execute("""UPDATE SI.Terms SET consensus={1}, T_last='{2}', T_stable={3},
                     U_sum={4}, D_sum={5} WHERE id={0}; COMMIT""".format(
        term_id, S, str(T_now), repr(str(T_stable)) if T_stable else "NULL", U_sum, D_sum))

    cur.execute("UPDATE SI.Users SET reputation=%d WHERE id=%d RETURNING id; COMMIT" % (rep, id))
    return id


    ## Comment queries ##
    
  def insertComment(self, comment): 
    """ Insert a new comment into the database and return ID.

    :param comment: New comment as dictionary. Default values will be used for ommitted 
                    columns. 
    :type comment: dict 
    :rtype: int
    """
    defComment = { 
      "id" : "default",
      "owner_id" : "default", 
      "term_id" : "default", 
      "comment_string" : "nil"
    }
  
    #: Format entries for db query
    for (key, value) in comment.iteritems():
      if key in ["created", "modified"]:
        defComment[key] = "'" + str(value) + "'"
      else: defComment[key] = unicode(value).replace("'", "''")

    try:
      cur = self.con.cursor()
      cur.execute("""INSERT INTO SI.Comments (id, owner_id, term_id, comment_string) 
                     VALUES (%s, %s, %s, '%s')
                     RETURNING id""" % (defComment['id'],
                                        defComment['owner_id'], 
                                        defComment['term_id'], 
                                        defComment['comment_string']))
      res = cur.fetchone()
      if res: return res[0]
      else:   return None
    
    except pgdb.DatabaseError, e:
      if e.pgcode == '23505': #: Duplicate primary key
         print >>sys.stderr, "warning: skipping duplicate primary key Id=%s" % defComment['id']
         cur.execute("ROLLBACK;")
         return None 
      raise e

  def removeComment(self, id):
    """ Remove comment and return ID. 
    
    :param id: Comment ID. 
    :type id: int
    :rtype: int or None
    """ 
    cur = self.con.cursor()
    cur.execute("DELETE FROM SI.Comments WHERE id=%d RETURNING id" % id)
    res = cur.fetchone()
    if res: return res[0]
    else:   return None

  def updateComment(self, id, comment):
    """ Update term comment. Note that user authentication is handled up stream!

    :param id: Comment ID.
    :type id: int 
    :param comment: Expects at least the key 'comment_string' with string value. 
    :type id: dict 
    """
    cur = self.con.cursor()
    for (key, value) in comment.iteritems():
      comment[key] = unicode(value).replace("'", "''")
    cur.execute("UPDATE SI.Comments SET comment_string='%s' WHERE id=%d" % (
      comment['comment_string'], id))

  def getComment(self, id):
    """  Get comment by ID.

    :param id: Comment ID. 
    :type id: int
    :rtype: dict or None
    """
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM SI.Comments WHERE id=%d" % id)
    return cur.fetchone()

  def getCommentHistory(self, term_id):
    """ Return a term's comment history, ordered by creation date.

    :param term_id: Term ID. 
    :type term_id: int
    :rtype: dict iterator
    """
    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM SI.Comments WHERE term_id=%d ORDER BY created" % term_id)
    for row in cur.fetchall():
      yield row

    ## Tracking (Voting) queries ##

  def insertTracking(self, tracking): 
    """ Insert a tracking row, skipping if (term_id, user_id) pair exists. 

    :param tracking: Expect dictionary with keys 'user_id', 'term_id', and 'vote'. 
    :type tracking: dictionary
    :returns: (term_id, user_id)
    :rtype: (int, int) or None
    """
    defTracking = { 
      "vote" : "default" 
    }
    
    for (key, value) in tracking.iteritems():
      defTracking[key] = unicode(value)
  
    try:
      cur = self.con.cursor()
      cur.execute("""INSERT INTO SI.Tracking (user_id, term_id, vote) 
                     VALUES (%s, %s, %s)
                     RETURNING user_id, term_id""" % (defTracking['user_id'], 
                                                      defTracking['term_id'], 
                                                      defTracking['vote']))
      return cur.fetchone()
    
    except pgdb.DatabaseError, e:
      if e.pgcode == '23505': #: Duplicate primary key
         print >>sys.stderr, "warning: skipping duplicate (TermId=%s, UserId=%s)" % (
          defTracking['term_id'], defTracking['user_id'])
         cur.execute("ROLLBACK;")
         return None 
      raise e

  def getVote(self, user_id, term_id): 
    """ Get user's vote for a term.

    :param user_id: User ID. 
    :type user_id: int
    :param term_id: Term ID. 
    :type term_id: int
    :returns: +1, 0, or -1. 
    :rtype: int or None
    """
    cur = self.con.cursor()
    cur.execute("""SELECT vote FROM SI.Tracking WHERE
                   user_id={0} AND term_id={1}""".format(user_id, term_id))
    res = cur.fetchone()
    if res: return res[0]
    else:   return None 

  def trackTerm(self, user_id, term_id): 
    """ User has starred a term. Return True if a row was 
        inserted into the Tracking table, False if not. 
    
    :rtype: bool
    """
    cur = self.con.cursor()
    cur.execute("""SELECT vote FROM SI.Tracking 
                   WHERE user_id={0} AND term_id={1}""".format(user_id, term_id))
    if not cur.fetchone(): 
      cur.execute("""INSERT INTO SI.Tracking (user_id, term_id, vote) 
                     VALUES ({0}, {1}, 0)""".format(user_id, term_id))
      return True
    else: 
      cur.execute("""UPDATE SI.Tracking SET star=True
                     WHERE user_id={0} AND term_id={1}""".format(user_id, term_id))
      return False

  def untrackTerm(self, user_id, term_id):
    """ Untrack term. """
    cur = self.con.cursor()
    cur.execute("""UPDATE SI.Tracking SET star=False
                   WHERE user_id={0} AND term_id={1} 
                   RETURNING vote""".format(user_id, term_id))
    vote = cur.fetchone()
    if vote: 
      return 1
    else: return 0

  def checkTracking(self, user_id, term_id):
    """ Check tracking.

    :rtype: bool
    """
    cur = self.con.cursor()
    cur.execute("""SELECT star FROM SI.Tracking 
                   WHERE user_id={0} AND term_id={1}""".format(user_id, term_id))
    star = cur.fetchone()
    if star:
      return star[0]
    else: return False

  def preScore(self, term_id):
    """ Prescore term. Returns a tuple of dictionaries (User.Id -> User.Reputation) 
        of up voters and down voters (*U, D*).

    :param term_id: Term ID. 
    :type term_id: int
    :returns: (*U, D*)
    :rtype: ((*int --> int*), (*int --> int*)) 
    """ 
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

  def postScore(self, term_id, U, D):
    """ Postscore term. Input the reputations of up voters and down voters and 
        compute the consensus score. Update the term row as a side-affect. 

    :param U: Up voters. 
    :type U: int --> int 
    :param D: Down voters. 
    :type D: int --> int
    """
    cur = self.con.cursor()
    cur.execute("SELECT COUNT(*) FROM SI.Users")
    t = cur.fetchone()[0] # total users
    u = len(U) 
    d = len(D)

    U_sum = reduce(lambda ri,rj: ri+rj, 
                    [0] + map(lambda Ri: Ri, U.values()))
    D_sum = reduce(lambda ri,rj: ri+rj, 
                    [0] + map(lambda Ri: Ri, D.values()))

    S = calculateConsensus(u, d, t, float(U_sum), float(D_sum)) 

    cur.execute("""UPDATE SI.Terms SET up={1}, down={2}, U_sum={3}, D_sum={4}, consensus={5}
                   WHERE id={0}""".format(term_id, u, d, U_sum, D_sum, S))
    return S


  def castVote(self, user_id, term_id, vote): 
    """ Cast or change a user's vote on a term. Return the term's new consensus score.

    :param user_id: User ID. 
    :type user_id: int
    :param term_id: Term Id.
    :type term_id: int
    :param vote: +1, 0, or -1. 
    :type vote: int
    :rtype: float
    """
    cur = self.con.cursor()
    
    cur.execute("SELECT now(), count(*) FROM SI.Users")
    (T_now, t) = cur.fetchone() 
    cur.execute("SELECT reputation FROM SI.Users WHERE id=%d" % user_id) 
    rep = cur.fetchone()[0]
  
    #: Get current state
    cur.execute("""SELECT vote FROM SI.Tracking WHERE
                   user_id={0} AND term_id={1}""".format(user_id, term_id))
    p_vote = cur.fetchone()

    cur.execute("""SELECT up, down, U_sum, D_sum, t_last, t_stable, consensus FROM SI.Terms
                   WHERE id={0}""".format(term_id))
    (u, d, U_sum, D_sum, T_last, T_stable, p_S) = cur.fetchone()

    #: Cast vote
    if not p_vote:
      cur.execute("""INSERT INTO SI.Tracking (user_id, term_id, vote)
                     VALUES ({0}, {1}, {2})""".format(user_id, term_id, vote))
      p_vote = 0
      
    elif p_vote[0] != vote:
      cur.execute("""UPDATE SI.Tracking SET vote={2}
                     WHERE user_id={0} AND term_id={1}""".format(user_id, term_id, vote))
      p_vote = p_vote[0]

    #: Calculate new consensus score
    if p_vote == 1:    u -= 1; U_sum -= rep 
    elif p_vote == -1: d -= 1; D_sum -= rep
    if vote == 1:      u += 1; U_sum += rep
    elif vote == -1:   d += 1; D_sum += rep
    S = calculateConsensus(u, d, t, float(U_sum), float(D_sum))

    #: Calculate stability
    T_stable = calculateStability(S, p_S, T_now, T_last, T_stable)

    #: Update term
    cur.execute("""UPDATE SI.Terms SET consensus={1}, T_last='{2}', t_stable={3},
                   up={4}, down={5}, U_sum={6}, D_sum={7} WHERE id={0}""".format(
      term_id, S, str(T_now), repr(str(T_stable)) if T_stable else "NULL", u, d, U_sum, D_sum))

    return S


  def classifyTerm(self, term_id):
    """ Check if term is stable. If so, classify it as being *canonical*, *vernacular*, 
        or *deprecated*. Update term and return class as string.

    :returns: 'canonical', 'vernacular', or 'deprecated'.
    :rtype: class
    """ 
    cur = self.con.cursor()  

    cur.execute("SELECT now()")
    T_now = cur.fetchone()[0]

    cur.execute("SELECT consensus, T_stable, T_last, modified, class FROM SI.Terms where id=%d" % term_id)
    (S, T_stable, T_last, T_modified, term_class) = cur.fetchone()

    if ((T_stable and ((T_now - T_stable).seconds / stabilityFactor) > stabilityInterval) \
        or ((T_now - T_last).seconds / stabilityFactor) > stabilityInterval) \
        and ((T_now - T_modified).seconds / stabilityFactor) > stabilityInterval: 
      
      if S > stabilityConsensusIntervalHigh:
        term_class = "canonical"
      
      elif S < stabilityConsensusIntervalLow: 
        term_class = "deprecated"

      else: term_class = "vernacular"

    cur.execute("UPDATE SI.Terms SET class={0} WHERE id={1}".format(repr(term_class), term_id))
    return term_class 

  def checkTermConsistency(self, term_id):
    """ Check that a term's consensus score is consistent by scoring it the hard way.
        Update if it wasn't. 

    :rtype: bool
    """
    cur = self.con.cursor()
    cur.execute("SELECT consensus FROM SI.Terms where id=%d" % term_id)
    p_S = cur.fetchone()[0]
    (U, V) = self.preScore(term_id)
    S = self.postScore(term_id, U, V) 
    if int(p_S) != int(S):
      return False
    return True

    ## Notification queries ##

  def getAllNotifications(self):
    """ Return an iterator over ``SI_Notify.Notify``. 

    :rtype: dict iterator
    """
    cur = self.con.cursor()
    cur.execute("SELECT * FROM SI_Notify.Notify")
    for row in cur.fetchall():
      yield row
  
  def insertNotification(self, user_id, notif):
    """ Insert a notification. 

    :param notif: Notification. 
    :type notif: seaice.notify.BaseNotification
    """
    cur = self.con.cursor()
    if isinstance(notif, notify.Comment):
      cur.execute("""INSERT INTO SI_Notify.Notify( class, user_id, term_id, from_user_id, T ) 
                     VALUES( 'Comment', %d, %d, %d, %s ); """ % (
                user_id, notif.term_id, notif.user_id, repr(str(notif.T_notify))))

    elif isinstance(notif, notify.TermUpdate):
      cur.execute("""INSERT INTO SI_Notify.Notify( class, user_id, term_id, from_user_id, T ) 
                     VALUES( 'TermUpdate', %d, %d, %d, %s ); """ % (
                user_id, notif.term_id, notif.user_id, repr(str(notif.T_notify))))

    elif isinstance(notif, notify.TermRemoved):
      notif.term_string = notif.term_string.replace("'", "''")
      cur.execute("""INSERT INTO SI_Notify.Notify( class, user_id, term_string, from_user_id, T ) 
                     VALUES( 'TermRemoved', %d, '%s', %d, %s ); """ % (
                user_id, notif.term_string, notif.user_id, repr(str(notif.T_notify)))) 

    else:
      cur.execute("""INSERT INTO SI_Notify.Notify( class, user_id, term_id, T )   
                     VALUES( 'Base', %d, %d, %s ); """ % (
                user_id, notif.term_id, repr(str(notif.T_notify))))
  
  def removeNotification(self, user_id, notif):
    """ Remove a notification.

    :param notif: Notification. 
    :type notif: seaice.notify.BaseNotification
    """
    cur = self.con.cursor()
    print "Lonestar!"
    if isinstance(notif, notify.Comment):
      cur.execute("""DELETE FROM SI_Notify.Notify
                      WHERE class='Comment' AND user_id=%d AND term_id=%d 
                        AND from_user_id=%d AND T=%s ; """ % (
                user_id, notif.term_id, notif.user_id, repr(str(notif.T_notify))))

    elif isinstance(notif, notify.TermUpdate):
      cur.execute("""DELETE FROM SI_Notify.Notify
                      WHERE class='TermUpdate' AND user_id=%d AND term_id=%d
                        AND from_user_id=%d AND T=%s ; """ % (
                user_id, notif.term_id, notif.user_id, repr(str(notif.T_notify))))

    elif isinstance(notif, notify.TermRemoved):
      notif.term_string = notif.term_string.replace("'", "''")
      cur.execute("""DELETE FROM SI_Notify.Notify
                      WHERE class='TermRemoved' AND user_id=%d
                        AND term_string='%s' AND from_user_id=%d
                        AND T=%s ; """ % (
                user_id, notif.term_string, notif.user_id, repr(str(notif.T_notify)))) 

    else:
      cur.execute("""DELETE FROM SI_Notify.Notify( class, user_id, term_id, T )   
                      WHERE class='Base' AND user_id=%d 
                        AND term_id=%d and T=%s ; """ % (
                user_id, notif.term_id, repr(str(notif.T_notify))))
  


  def Export(self, table, outf=None):
    """ Export database in JSON format to *outf*. If no file name 
        provided, dump to standard out. 

    :param table: Name of table.
    :type table: str
    :param outf: Filename to output table to.
    :type outf: str
    """
    if table not in ['Users', 'Terms', 'Comments', 'Tracking']:
      print >>sys.stderr, "error (export): table '%s' is not defined in the db schema" % table
      return

    if outf: 
      fd = open(outf, 'w')
    else:
      fd = sys.stdout

    cur = self.con.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM SI.%s" % table)
    rows = cur.fetchall()
    pretty.printAsJSObject(rows, fd)

  def Import(self, table, inf=None): 
    """ Import database from JSON formated *inf*.

    :param table: Name of table. 
    :type table: str
    :param inf: File name from which to import.
    :type inf: str
    """
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
  

