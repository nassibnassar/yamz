# IdPool.py
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
from threading import Lock

class IdPool:
  """ 
    A thread-safe object for producing and consuming table row IDs within 
    a particluar context, i.e. ``SI.Terms``, ``SI.Users``, and ``SI.Comments``. 
    When initialized, an instance queries the table for all assigned IDs in 
    ascending order. Continuous regions of unassigned IDs are found and added 
    to the pool. The highest assigned ID is noticed so that when the pool is 
    empty, the producer function returns the next highest avaialble.

    **TODO** This could be made more space-efficient by combining contiguous 
    free IDs into ranges.

  :param db_con: Connection to the SeaIce database.
  :type db_con: seaice.SeaIceConnector.SeaIceConnector
  :param table: Name of the table for which a pool will be created. The table
                should have a column of surrogate ID scalled "id". 
  :type table: str

  """
  
  def __init__(self, db_con, table): 
    assert table in ['Users', 'Terms', 'Comments']
    
    self.L_pool = Lock()

    cur = db_con.con.cursor()
    cur.execute("select id from SI.%s order by id" % table)
    
    self.pool = []
    prev = 1000  
    for row in map(lambda x : x[0], cur.fetchall()):
      if row > prev + 1:
        self.pool += range(prev + 1, row)
      prev = row 
   
    self.next = prev + 1

    print "Table %s pool:" % table, (self.pool, self.next)
     
  def ConsumeId(self): 
    """ Consume the next available ID. 
  
    :rtype: int
    """
    self.L_pool.acquire()
    if len(self.pool) > 0: 
      ret = self.pool.pop()
    else:
      ret = self.next
      self.next += 1
    self.L_pool.release()
    return ret

  def GetNextId(self): 
    """ Get the next ID without consuming it (look ahead). 

    :rtype: int
    """
    self.L_pool.acquire()
    if len(self.pool) > 0: 
      ret = self.pool[-1]
    else:
      ret = self.next
    self.L_pool.release()
    return ret

  def ReleaseId(self, id): 
    """ Release and ID back into the pool (produce) 

    :param id: Surrogate ID.
    :type id: int
    """
    self.L_pool.acquire()
    if id < self.next: 
      self.pool.append(id)
    self.L_pool.release()
      

