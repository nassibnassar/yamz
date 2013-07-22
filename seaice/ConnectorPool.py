# ConnectorPool.py - implementation of a thread-safe DB connector 
# pool for SeaIce. Also defined here is the class ScopedSeaIceConnector 
# which inherits class SeaIceConnector. This is a DB connector that is 
# acquired from SeaIceConnectorPool and is automatically released to the 
# pool when it goes out of scope. 
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

from SeaIceConnector import *
from NotifyConnector import *
from threading import Condition

##
# class ScopedSeaIceConnector
#
# Sub-class of SeaIceConnector which is released to the pool it comes
# from once it goes out of scope. This allows for a fancy short-hand. 
# See SeaIceconnectorPool.getScoped(). 
#
class ScopedSeaIceConnector (SeaIceConnector): 

  def __init__(self, pool, db_con):
    self.con = db_con.con
    self.heroku_db = db_con.heroku_db
    self.db_con = db_con
    self.pool = pool

  def __del__(self):
    self.pool.enqueue(self.db_con)

##
# class ScopedNotifyConnector
#
# Sub-class of NotifyConnector which is released to the pool it comes
# from once it goes out of scope. This allows for a fancy short-hand. 
# See NotifyconnectorPool.getScoped(). 
#
class ScopedNotifyConnector (NotifyConnector): 

  def __init__(self, pool, db_con):
    self.con = db_con.con
    self.heroku_db = db_con.heroku_db
    self.db_con = db_con
    self.pool = pool

  def __del__(self):
    self.pool.enqueue(self.db_con)

##
# class ConnectorPool
# 
# A thread-safe connection pool. 
#
class ConnectorPool:
  
  def __init__(self, Connector, count=20, user=None, password=None, db=None):
    self.pool = [ Connector(user, password, db) for _ in range(count) ]
    self.C_pool = Condition()
      
  def dequeue(self):
  #
  # Get connector 
  #
    self.C_pool.acquire()
    while len(self.pool) == 0: 
      self.C_pool.wait()
    db_con = self.pool.pop()
    self.C_pool.release()
    return db_con

  def enqueue(self, db_con): 
  #
  # Release connector
  #
    self.C_pool.acquire()
    self.pool.append(db_con)
    self.C_pool.notify()
    self.C_pool.release()


##
# class SeaIceConnectorPool
#
class SeaIceConnectorPool (ConnectorPool):
  
  def __init__(self, count=20, user=None, password=None, db=None):
    ConnectorPool.__init__(self, SeaIceConnector, count, user, password, db)

  def getScoped(self):
    return ScopedSeaIceConnector(self, self.dequeue())

##
# class NotifyConnectorPool
#
class NotifyConnectorPool (ConnectorPool):
  
  def __init__(self, count=20, user=None, password=None, db=None):
    ConnectorPool.__init__(self, NotifyConnector, count, user, password, db)

  def getScoped(self):
    return ScopedNotifyConnector(self, self.dequeue())


