# notify.py - implementations of various live notificaitons 
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

import pretty

## class BaseNotificaiton
#
#
class BaseNotification: 

  def __init__(self, term_id, T_notify): 
    self.term_id = term_id
    self.T_notify = T_notify

  def __str__(self):
    return 'Id=%d at %s' % (self.term_id, self.T_notify)

  ##
  # Return an HTML-formatted notification string. To avoid dereferencing
  # something that has been deleted (term, comment, user, etc.), return 
  # None if the database has no results. 
  #
  def getAsHTML(self, db_con): 
    term = db_con.getTerm(self.term_id)
    if not term: 
      return None

    return 'Term <a href="/term=%d">%s</a> <font color="#8B8B8B"><i>%s</i></font>' % (
                        self.term_id, term['term_string'], pretty.printPrettyDate(self.T_notify))
  

## class Comment
#
#
class Comment(BaseNotification):
 
  def __init__(self, term_id, user_id, T_notify):
    BaseNotification.__init__(self, term_id, T_notify)
    self.user_id = user_id

  def __str__(self):
    return 'UserId=%d commented on TermId=%d at %s' % (self.user_id, self.term_id, self.T_notify)

  def getAsHTML(self, db_con): 
    term = db_con.getTerm(self.term_id)
    user = db_con.getUserNameById(self.user_id, full=True)
    if not term or not user:
      return None

    return '''<font color="#4D6C82">%s</font> commented on <a href="/term=%d">%s</a>. 
              <font color="#B8B8B8"><i>%s</i></font>''' % (
            user, self.term_id, term['term_string'], pretty.printPrettyDate(self.T_notify))

## class TermUpdate
#
#
class TermUpdate(BaseNotification):
 
  def __init__(self, term_id, user_id, T_notify):
    BaseNotification.__init__(self, term_id, T_notify)
    self.user_id = user_id

  def __str__(self):
    return 'UserId=%d modified TermId=%d at %s' % (self.user_id, self.term_id, self.T_notify)

  def getAsHTML(self, db_con): 
    term = db_con.getTerm(self.term_id)
    user = db_con.getUserNameById(self.user_id, full=True)
    if not term or not user:
      return None

    return '''<font color="#4D6C82">%s</font> modified <a href="/term=%d">%s</a>. 
              <font color="#B8B8B8"><i>%s</i></font>''' % (
            user, self.term_id, term['term_string'], pretty.printPrettyDate(self.T_notify))

## class TermRemoved
#
#
class TermRemoved(BaseNotification):
 
  def __init__(self, user_id, term_string, T_notify):
    BaseNotification.__init__(self, None,  T_notify)
    self.user_id = user_id
    self.term_string = term_string

  def __str__(self):
    return 'UserId=%d has removed TermString=%d at %s' % (self.user_id, self.term_string, self.T_notify)

  def getAsHTML(self, db_con): 
    user = db_con.getUserNameById(self.user_id, full=True)
    if not user: 
      return None

    return '''<font color="#4D6C82">%s</font> has removed 
              <font color="#0088CC"><strong>%s</strong></font> from the metadictionary. 
              <font color="#B8B8B8"><i>%s</i></font>''' % (
            user, self.term_string, pretty.printPrettyDate(self.T_notify))
