# IdPool.py - TODO
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

##
# class IdPool 
# 
# A thread-safe object for producing and consuming table row Ids within 
# a particluar context, i.e. Terms, Users, Comments. 
#
class IdPool:
  
  ## 
  # Query table for all Ids and sort in ascending order. 
  # Add non-contiguous regions to pool and determine the 
  # next Id to assign. 
  #
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
     
  ##
  # Assign (consume) the next Id.
  #
  def ConsumeId(self): 
    self.L_pool.acquire()
    if len(self.pool) > 0: 
      ret = self.pool.pop()
    else:
      ret = self.next
      self.next += 1
    self.L_pool.release()
    return ret

  ##
  # Get the next Id to assign without consuming it. 
  #
  def GetNextId(self): 
    self.L_pool.acquire()
    if len(self.pool) > 0: 
      ret = self.pool[-1]
    else:
      ret = self.next
    self.L_pool.release()
    return ret

  ##
  # Release Id to the pool (produce) 
  #
  def ReleaseId(self, id): 
    self.L_pool.acquire()
    if id < self.next: 
      self.pool.append(id)
    self.L_pool.release()
      

