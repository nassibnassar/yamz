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
from threading import Condition

class ScopedSeaIceConnector (SeaIceConnector): 
  """
    A SeaIce DB Connector which is released to the pool from whence it 
    came when it goes out of scope. This type of connector is produced by 
    :func:`seaice.ConnectorPool.SeaIceConnectorPool.getScoped`
    and should not be used directly. 

    :param pool: The pool from which this connector originates. 
                 When the destructor is called, the connection is enqueued 
                 into the pool.

    :type pool: seaice.ConnectorPool.SeaIceConnectorPool
    :param db_con: The connector. 
    :type db_con: seaice.SeaIceConnector.SeaIceConnector
  """

  def __init__(self, pool, db_con):
    self.con = db_con.con
    self.db_con = db_con
    self.pool = pool

  def __del__(self):
    self.pool.enqueue(self.db_con)


class ConnectorPool:
  """ A thread-safe connection pool. 

  TODO: Make this an actual queue, not a stack. Nomenclature is important
  sometimes. 
  """
  
  def __init__(self, Connector, count=20, user=None, password=None, db=None):
    self.pool = [ Connector(user, password, db) for _ in range(count) ]
    self.C_pool = Condition()
      
  def dequeue(self):
    """ Get connector. 
    
    :rtype: seaice.SeaIceConnector.SeaIceConnector
    """
    self.C_pool.acquire()
    while len(self.pool) == 0: 
      self.C_pool.wait()
    db_con = self.pool.pop()
    self.C_pool.release()
    return db_con

  def enqueue(self, db_con): 
    """ Release connector.

    :param db_con: The connector. 
    :type db_con: seaice.SeaIceConnector.SeaIceConnector
    """
    self.C_pool.acquire()
    self.pool.append(db_con)
    self.C_pool.notify()
    self.C_pool.release()


class SeaIceConnectorPool (ConnectorPool):
  """ 
    A thread-safe connection pool which can produce scoped SeaIce 
    connectors.

    :param count: Size of the pool.
    :type count: int
    :param user: Name of DB role (see :class:`seaice.SeaIceConnector.SeaIceConnector` for 
                 default behavior).
    :type user: str
    :param password: User's password.
    :type password: str
    :param db: Name of database. 
    :type db: str
  """
  
  def __init__(self, count=20, user=None, password=None, db=None):
    ConnectorPool.__init__(self, SeaIceConnector, count, user, password, db)

  def getScoped(self):
    """ Return a scoped connector from the pool.

    :rtype: seaice.SeaIceConnector.SeaIceConnector
    """
    return ScopedSeaIceConnector(self, self.dequeue())


