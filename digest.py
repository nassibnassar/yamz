#!/usr/bin/python
# 
# notify - Send email notifications to users.  
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

import os, sys, optparse
import json, psycopg2 as pqdb
import seaice

import smtplib
from email.mime.text import MIMEText

## Parse command line options. ##

parser = optparse.OptionParser()

description="""
This program is distributed under the terms of the BSD license with the hope that it \
will be useful, but without warranty. You should have received a copy of the BSD license with \
this program; otherwise, visit http://opensource.org/licenses/BSD-3-Clause.
"""

parser.description = description

parser.add_option("--config", dest="config_file", metavar="FILE", 
                  help="User credentials for local PostgreSQL database (defaults to '$HOME/.seaice'). " + 
                       "If 'heroku' is given, then a connection to a foreign host specified by " + 
                       "DATABASE_URL is established.",
                  default='heroku')

parser.add_option("--role", dest="db_role", metavar="USER", 
                  help="Specify the database role to use for the DB connector pool. These roles " +
                       "are specified in the configuration file (see --config).",
                  default="default")

(options, args) = parser.parse_args()


try:

  if options.config_file == "heroku": 
    
    sea = seaice.SeaIceConnector()

  else: 
    try: 
      config = seaice.auth.get_config(options.config_file)
    except OSError: 
      print >>sys.stderr, "error: config file '%s' not found" % options.config_file
      sys.exit(1)

    sea = seaice.SeaIceConnector(config.get(options.db_role, 'user'),       
                                 config.get(options.db_role, 'password'),
                                 config.get(options.db_role, 'dbname'))

  # Set up SMTP server. 
  s = smtplib.SMTP('smtp.mailgun.org', 587)
  s.login(os.environ['MAILGUN_SMTP_LOGIN'], os.environ['MAILGUN_SMTP_PASSWORD'])
  
  # Sender address
  from_addr = 'yamz-noreply@yamz.net'

  # Message subject
  cur = sea.con.cursor()
  cur.execute('SELECT NOW();') 
  (t,) = cur.fetchone()
  msg_subject = 'YAMZ digest (%s %s %s)' % (
              t.day, seaice.pretty.monthOf[t.month - 1], t.year)

  for (id, name, notify, to_addr) in map(lambda(u) : (u['id'], 
                             u['first_name'] + ' ' + u['last_name'], 
                             u['enotify'], u['email']), sea.getAllUsers()):
    user = seaice.user.User(id, name)
    
    if notify: 
      
      for (user_id, notif_class, T_notify, 
           term_id, from_user_id, term_string, notified) in sea.getUserNotifications(id):
       
        if not notified: 
        
          if notif_class == 'Base': 
            notif = seaice.notify.BaseNotification(term_id, T_notify)
          elif notif_class == 'Comment': 
            notif = seaice.notify.Comment(term_id, from_user_id, term_string, T_notify)
          elif notif_class == 'TermUpdate': 
            notif = seaice.notify.TermUpdate(term_id, from_user_id, T_notify)
          elif notif_class == 'TermRemoved': 
            notif = seaice.notify.TermRemoved(from_user_id, term_string, T_notify) 

          user.notify(notif)
    
      
      text = user.getNotificationsAsPlaintext(sea)
  
      if len(text) == 0: 
      
        print "No notifications for `%s`." % to_addr
       

      else: 
        
        # Message 
        msg =  "%s,\n\n" % name
        msg += "These are your YAMZ updates.\n\n\n"
        msg += text
        msg += "\n\n\nYou are receiving this email because you have elected to receive notifications "
        msg += "from YAMZ. You can turn this off by changing your account settings at "
        msg += "http://yamz.net/account."
        msg += "\n\n - YAMZ development team\n\n"
        
        print "Sending the following message to `%s`:" % to_addr
        print "-----------------------------------------------------------"
        print msg
        print "-----------------------------------------------------------\n"

        # Send message
        msg = MIMEText(msg)
        msg['Subject'] = msg_subject
        msg['From']    = from_addr
        msg['To']      = to_addr

        s.sendmail(msg['From'], msg['To'], msg.as_string())

        cur.execute('''UPDATE SI_Notify.Notify 
                          SET enotified=True 
                        WHERE user_id=%s''', (user_id,))

  s.quit()
  sea.commit()

except pqdb.DatabaseError, e:
  print 'error: %s' % e    
  sys.exit(1)

except IOError:
  print >>sys.stderr, "error: file not found"
  sys.exit(1)
