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

class BaseNotification: 
  """ Base class for notifications in the SeaIce web interface Each sub class 
      should implement __init__(), __str__(), and getAsHTML(db_con) This data
      structure only stores surrogate keys for users, terms, and comments. so 
      that a notification is never inconsistent. As a result, getAsHTML causes
      a query to the DB. 

      :param term_id: Term ID. 
      :type term_id: int
      :param T_notify: The time at which the notification was produced. 
      :type T_notify: datetime.datetime
  """

  def __init__(self, term_id, T_notify): 
    self.term_id = term_id
    self.T_notify = T_notify

  def __str__(self):
    return 'Id=%d at %s' % (self.term_id, self.T_notify)

  def getAsHTML(self, db_con): 
    """ Return an HTML-formatted notification string. To avoid dereferencing
        something that has been deleted (term, comment, user, etc.), return 
        None if the database has no results. 

        :param db_con: Connection to database. 
        :type db_con: seaice.SeaIceConnector.SeaIceConnector
        :rtype: str or None
    """
    term = db_con.getTerm(self.term_id)
    if not term: 
      return None

    return 'Term <a href="/term=%s">%s</a> <font color="#8B8B8B"><i>%s</i></font>' % (
                        term['concept_id'], term['term_string'], pretty.printPrettyDate(self.T_notify))

  def getAsPlaintext(self, db_con): 
    """ Return a notification string. To avoid dereferencing
        something that has been deleted (term, comment, user, etc.), return 
        None if the database has no results. 

        :param db_con: Connection to database. 
        :type db_con: seaice.SeaIceConnector.SeaIceConnector
        :rtype: str or None
    """
    term = db_con.getTerm(self.term_id)
    if not term: 
      return None

    return ' -- %s, term "%s".' % (
               pretty.printPrettyDate(self.T_notify), term['term_string'])
  

class Comment(BaseNotification):
  """ Notification object for comments. 

      :param term_id: Term ID. 
      :type term_id: int
      :param user_id: ID of the user has commented on a term. 
      :type user_id: int
      :param T_notify: The time at which the notification was produced. 
      :type T_notify: datetime.datetime
  """
 
  def __init__(self, term_id, user_id, comment_string, T_notify):
    BaseNotification.__init__(self, term_id, T_notify)
    self.user_id = user_id
    self.comment_string = comment_string

  def __str__(self):
    return 'UserId=%d commented on TermId=%d at %s' % (self.user_id, self.term_id, self.T_notify)

  def getAsHTML(self, db_con): 
    term = db_con.getTerm(self.term_id)
    user = db_con.getUserNameById(self.user_id, full=True)
    if not term or not user:
      return None

    return '''<font color="#4D6C82">%s</font> commented on <a href="/term=%s">%s</a>. 
              <font color="#B8B8B8"><i>%s</i></font>''' % (
            user, term['concept_id'], term['term_string'], pretty.printPrettyDate(self.T_notify))
  
  def getAsPlaintext(self, db_con): 
    term = db_con.getTerm(self.term_id)
    user = db_con.getUserNameById(self.user_id, full=True)
    if not term or not user:
      return None

    text = " -- %s, %s commented on \"%s\".\n\n" % (
             pretty.printPrettyDate(self.T_notify), user, term['term_string'])
    text += '     TERM URI: %s\n' % term['persistent_id']
    text += pretty.getPrettyParagraph(db_con, "COMMENT: " + self.comment_string, 6)
    return text


class TermUpdate(BaseNotification):
  """ Notification object for term updates. 

      :param term_id: Term ID. 
      :type term_id: int
      :param user_id: ID of the user who has updated the term. 
      :type user_id: int
      :param T_notify: The time at which the notification was produced. 
      :type T_notify: datetime.datetime
  """
 
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

    return '''<font color="#4D6C82">%s</font> modified <a href="/term=%s">%s</a>. 
              <font color="#B8B8B8"><i>%s</i></font>''' % (
            user, term['concept_id'], term['term_string'], pretty.printPrettyDate(self.T_notify))

  def getAsPlaintext(self, db_con): 
    term = db_con.getTerm(self.term_id)
    user = db_con.getUserNameById(self.user_id, full=True)
    if not term or not user:
      return None
    
    text = ' -- %s, %s modified "%s".\n' % (
              pretty.printPrettyDate(self.T_notify), user, term['term_string'])
    text += '\n' + pretty.getPrettyTerm(db_con, term) + '\n'
    return text

class TermRemoved(BaseNotification):
  """ Notification object for term removals. 

      :param user_id: ID of the user who has updated the term. 
      :type user_id: int
      :param term_string: Term string before the term was deleted. We can't use the ID 
                          since it has been removed from the database. 
      :type term_string: str
      :param T_notify: The time at which the notification was produced. 
      :type T_notify: datetime.datetime
  """
 
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

  def getAsPlaintext(self, db_con): 
    user = db_con.getUserNameById(self.user_id, full=True)
    if not user: 
      return None

    return " -- %s, %s has removed \"%s\" from the metadictionary." % (
              pretty.printPrettyDate(self.T_notify), user, self.term_string)


