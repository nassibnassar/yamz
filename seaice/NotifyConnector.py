# NotifyConnector.py - DB connector for persistent storage of 
# notificaitons. 
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
import psycopg2 as pgdb
import Pretty
import Notification as notify

class NotifyConnector:

  def __init__(self, user=None, password=None, db=None):
  
    if not user: 

      self.heroku_db = True
      urlparse.uses_netloc.append("postgres")
      url = urlparse.urlparse(os.environ["NOTIFY_DB_URL"])

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
    cur.execute("SELECT version(); BEGIN")
  
  def __del__(self):
    self.con.close()

  ##
  # Reset notification database. drop schema if exists and recreate it. 
  #
  def reset(self):
    cur = self.con.cursor()
      
    cur.execute("""
      DROP SCHEMA IF EXISTS SI_Notify CASCADE;
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
          term_string  TEXT 
        ); COMMIT
    """)


  ##
  # Get a notifications iterator
  #
  def getNotifications(self):
    cur = self.con.cursor()
    cur.execute("SELECT * FROM SI_Notify.Notify")
    for row in cur.fetchall():
      yield row

  ##
  # Insert a notification. 
  #
  def insert(self, user_id, notif):
    cur = self.con.cursor()
    if isinstance(notif, notify.Comment):
      cur.execute("""INSERT INTO SI_Notify.Notify( class, user_id, term_id, from_user_id, T ) 
                     VALUES( 'Comment', %d, %d, %d, %s ); COMMIT""" % (
                user_id, notif.term_id, notif.user_id, repr(str(notif.T_notify))))

    elif isinstance(notif, notify.TermUpdate):
      cur.execute("""INSERT INTO SI_Notify.Notify( class, user_id, term_id, from_user_id, T ) 
                     VALUES( 'TermUpdate', %d, %d, %d, %s ); COMMIT""" % (
                user_id, notif.term_id, notif.user_id, repr(str(notif.T_notify))))

    elif isinstance(notif, notify.TermRemoved):
      notif.term_string = notif.term_string.replace("'", "''")
      cur.execute("""INSERT INTO SI_Notify.Notify( class, user_id, term_string, from_user_id, T ) 
                     VALUES( 'TermRemoved', %d, '%s', %d, %s ); COMMIT""" % (
                user_id, notif.term_string, notif.user_id, repr(str(notif.T_notify)))) 

    else:
      cur.execute("""INSERT INTO SI_Notify.Notify( class, user_id, term_id, T )   
                     VALUES( 'Base', %d, %d, %s ); COMMIT""" % (
                user_id, notif.term_id, repr(str(notif.T_notify))))
  
  ##
  # Remove a notification.
  #
  def remove(self, user_id, notif):
    cur = self.con.cursor()
    print "Lonestar!"
    if isinstance(notif, notify.Comment):
      cur.execute("""DELETE FROM SI_Notify.Notify
                      WHERE class='Comment' AND user_id=%d AND term_id=%d 
                        AND from_user_id=%d AND T=%s ; COMMIT""" % (
                user_id, notif.term_id, notif.user_id, repr(str(notif.T_notify))))

    elif isinstance(notif, notify.TermUpdate):
      cur.execute("""DELETE FROM SI_Notify.Notify
                      WHERE class='TermUpdate' AND user_id=%d AND term_id=%d
                        AND from_user_id=%d AND T=%s ; COMMIT""" % (
                user_id, notif.term_id, notif.user_id, repr(str(notif.T_notify))))

    elif isinstance(notif, notify.TermRemoved):
      notif.term_string = notif.term_string.replace("'", "''")
      cur.execute("""DELETE FROM SI_Notify.Notify
                      WHERE class='TermRemoved' AND user_id=%d
                        AND term_string='%s' AND from_user_id=%d
                        AND T=%s ; COMMIT""" % (
                user_id, notif.term_string, notif.user_id, repr(str(notif.T_notify)))) 

    else:
      cur.execute("""DELETE FROM SI_Notify.Notify( class, user_id, term_id, T )   
                      WHERE class='Base' AND user_id=%d 
                        AND term_id=%d and T=%s ; COMMIT""" % (
                user_id, notif.term_id, repr(str(notif.T_notify))))
