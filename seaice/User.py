# User.py - implementation of class User, which is used by the Flask web
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
# Store information about active user sessions. This implements
# the basic routines needed for the Flask login manager. 
# 
class BaseUser:

  def __init__(self, id, name): 
    self.id = id
    self.name = name
    self.logged_in = True
  
  def is_authenticated(self):
    return self.logged_in

  def is_active(self):
    return self.logged_in

  def is_anonymous(self):
    return False

  def get_id(self):
    return unicode(self.id)

##
# class AnonymousUser
# 
# Non logged in session. 
#
class AnonymousUser(BaseUser): 
  def __init__(self): 
    self.id = None
    self.name = None
    self.logged_in = False
    
##
# class User
#
# 
#
    
class User(BaseUser):

  def __init__(self, id, name): 
    BaseUser.__init__(self, id, name)
    self.notifications = [] 
    self.L_notify = Lock()

  ##
  # Receive notificaiton 
  # TODO squelch redundancies 
  #
  def notify(self, notif, db_con=None):
    if db_con: 
      db_con.insert(int(self.id), notif)
    self.L_notify.acquire()
    self.notifications.append(notif)
    self.L_notify.release()

  ##
  # Remove notification at index i
  # 
  def remove(self, i, db_con=None):
    if db_con: 
      db_con.remove(int(self.id), self.notifications[i])
    self.L_notify.acquire()
    self.notifications.remove(self.notifications[i])
    self.L_notify.release()
    
  ##
  # Get notifications as HTML-formatted table
  #
  def getNotificationsAsHTML(self, db_con):
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

