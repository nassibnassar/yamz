# user.py - implementation of class User, which is used by the Flask web
# framework to store properties of active sessions. class AnonymousUser 
# inherits User. 
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

from threading import Lock

##
# class BaseUser 
#
# 
class BaseUser:
  """
    Base class for users. Users are used in Flask fo storing 
    information about active and authenticated user sessions. 
    This implements. BaseUser implements the basic routines needed 
    for the Flask login manager. See the 
    `Flask-Login <https://flask-login.readthedocs.org/en/latest/>`_
    documenttation for details. 

  :param id: User's surrogate ID in the database. 
  :type id: int 
  :param name: First name of user (for display purposes). 
  :type name: str
  """

  def __init__(self, id, name): 
    self.id = id
    self.name = name
    self.logged_in = True
  
  def is_authenticated(self):
    """ Required by `Flask-Login <https://flask-login.readthedocs.org/en/latest/>`_. """
    return self.logged_in

  def is_active(self):
    """ Required by `Flask-Login <https://flask-login.readthedocs.org/en/latest/>`_. """
    return self.logged_in

  def is_anonymous(self):
    """ Required by `Flask-Login <https://flask-login.readthedocs.org/en/latest/>`_. """
    return False

  def get_id(self):
    """ Required by `Flask-Login <https://flask-login.readthedocs.org/en/latest/>`_. 
    
    :rtype: unicode str"""
    return unicode(self.id)

class AnonymousUser(BaseUser):
  """ Handler for non-authenticated sessions. """

  def __init__(self): 
    self.id = None #: When polled, return None for ID, as prescribed by Flask-Login. 
    self.name = None 
    self.logged_in = False #: When asked if you are logged in, always respond with **no**. 
    
##
# class User
#
# 
#
    
class User(BaseUser):
  """ Handler for authenticated sessions. """

  def __init__(self, id, name): 
    BaseUser.__init__(self, id, name)
    self.notifications = [] 
    self.L_notify = Lock()

  def notify(self, notif, db_con=None):
    """ Receive notification from another user. 
      
      If *db_con* is specified, 
      insert the notifiation into the databse. The reason for having this 
      option is that not all deployments of SeaIce will need to have 
      persistent notifications. This method is thread-safe, as it's 
      possible to receive many notifications simultaneously.  

    :param notif: Notification instance. 
    :type notif: seaice.notify.BaseNotification
    :param db_con: DB connection.
    :type db_con: seaice.SeaIceConnector.SeaIceConnector
    """
    if db_con: 
      db_con.insertNotification(int(self.id), notif)
    self.L_notify.acquire()
    self.notifications.append(notif)
    self.L_notify.release()

  def remove(self, i, db_con=None):
    """ Remove notification at index *i* from the list.

      If *db_con* is specified, then remove notification from the database. 
      This method is thread-safe. **NOTE:** If the order of notifications 
      changed sometime between this point and the last time the HTML page was 
      generated, the wrong notification will be removed. 

    :param i: Index of notification. 
    :type i: int
    :param db_con: DB connection.
    :type db_con: seaice.SeaIceConnector.SeaIceConnector
    """
    if db_con: 
      db_con.removeNotification(int(self.id), self.notifications[i])
      db_con.commit()
    self.L_notify.acquire()
    self.notifications.remove(self.notifications[i])
    self.L_notify.release()
    
  def getNotificationsAsHTML(self, db_con):
    """ Get notifications as HTML. 
      
      Create a link next each one which, when clicked, calls 
      :func:`User.remove`. 
    
    :param db_con: DB connection.
    :type db_con: seaice.SeaIceConnector.SeaIceConnector
    :returns: HTML-formatted string.
    """
    self.L_notify.acquire()
    result = ''
    for i in reversed(range(len(self.notifications))):
      notify = self.notifications[i].getAsHTML(db_con)
      if notify:
        result += '''<p><a href="/user=%d/notif=%d/remove" 
                         title="Click to remove this notification">[x]</a>
                         &nbsp;&nbsp;%s</p>''' % (self.id, i, notify)
    self.L_notify.release()
    return result

  def getNotificationsAsPlaintext(self, db_con):
    """ Get notifications in plaintext form. 
      
    :param db_con: DB connection.
    :type db_con: seaice.SeaIceConnector.SeaIceConnector
    :returns: Plaintext string.
    """
    self.L_notify.acquire()
    result = ''
    for i in reversed(range(len(self.notifications))):
      notify = self.notifications[i].getAsPlaintext(db_con)
      if notify:
        result += notify + '\n\n'
    self.L_notify.release()
    return result.strip()
