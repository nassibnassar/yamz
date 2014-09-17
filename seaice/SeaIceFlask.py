# SeaIceFlask.py - subclass of Flask. 
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

from flask import Flask
from ConnectorPool import * 
from IdPool import *
import notify
import user

#: The number of DB connections that will be instantiated. 
MAX_CONNECTIONS = 18

class SeaIceFlask (Flask): 
  """ 
    A subclass of the main Flask interface. This includes various live data structures
    used in the web interface, as well as a pool of database connectors.
    All features in the SeaIce API that the top-level progams make use of
    are available as attributes of this class. 

  :param user: Name of DB role (see :class:`seaice.SeaIceConnector.SeaIceConnector` for 
               default behavior).
  :type user: str
  :param password: User's password.
  :type password: str
  :param db: Name of database. 
  :type db: str
  """
  
  def __init__(self, import_name, static_path=None, static_url_path=None,
                     static_folder='html/static', template_folder='html/templates',
                     instance_path=None, instance_relative_config=False,
                     db_user=None, db_password=None, db_name=None):

    Flask.__init__(self, import_name, static_path, static_url_path, 
                         static_folder, template_folder,
                         instance_path, instance_relative_config)

    #: DB connector pool.
    self.dbPool = SeaIceConnectorPool(MAX_CONNECTIONS, db_user, db_password, db_name)

    # Id pools.
    db_con = self.dbPool.getScoped()
    
    self.userIdPool = IdPool(db_con, "Users") #: Pool for user surrogate IDs. 
    self.termIdPool = IdPool(db_con, "Terms") #: Pool for term surrogate IDs. 
    self.commentIdPool = IdPool(db_con, "Comments") #: Pool for comment surrogate IDs.
     
    #: Live User data structures. This includes storage of notifications. 
    self.SeaIceUsers = {}
    for row in db_con.getAllUsers():
      self.SeaIceUsers[row['id']] = user.User(row['id'], 
                                    row['first_name'].decode('utf-8'))

    # Load notifcations 
    for (user_id, notif_class, T_notify, 
         term_id, from_user_id, term_string,
         enotified) in db_con.getAllNotifications():

      if notif_class == 'Base': 
        notif = notify.BaseNotification(term_id, T_notify)
      elif notif_class == 'Comment': 
        notif = notify.Comment(term_id, from_user_id, term_string, T_notify)
      elif notif_class == 'TermUpdate': 
        notif = notify.TermUpdate(term_id, from_user_id, T_notify)
      elif notif_class == 'TermRemoved': 
        notif = notify.TermRemoved(from_user_id, term_string, T_notify) 
        
      self.SeaIceUsers[user_id].notify(notif)
      
    

    


