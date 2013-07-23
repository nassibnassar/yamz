#!/usr/bin/python
#
# ice - web frontend for SeaIce, based on the Python-Flask framework. 
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

import seaice
from seaice import SeaIceFlask
from flask import Markup
from flask import render_template, render_template_string
from flask import url_for, redirect, flash
from flask import request, session, g
from flask.ext import login as l

from urllib2 import Request, urlopen, URLError
import os, sys, optparse
import json, psycopg2 as pgdb

## Parse command line options. ##

parser = optparse.OptionParser()

parser.description="""\
This program is a Python/Flask-based web frontend for the SeaIce metadictionary. 
SeaIce is a database comprised of a set of user-defined, crowd-sourced terms and 
relationss. The goal of SeaIce is to develop a succint and complete set of 
metadata terms to register just about any type of file or data set. 'ice' is 
distributed under the terms of the BSD license with the hope that it will be 
# useful, but without warranty. You should have received a copy of the BSD 
license with this program; otherwise, visit 
http://opensource.org/licenses/BSD-3-Clause.
"""

parser.add_option("--config", dest="config_file", metavar="FILE", 
                  help="User credentials for local PostgreSQL database (defaults to '$HOME/.seaice'). " + 
                       "If 'heroku' is given, then a connection to a foreign host specified by " + 
                       "DATABASE_URL is established.",
                  default=(os.environ['HOME'] + '/.seaice'))

parser.add_option("-d", "--debug", action="store_true", dest="debug", default=False,
                  help="Start flask in debug mode.")

parser.add_option("--role", dest="db_role", metavar="USER", 
                  help="Specify the database role to use for the DB connector pool. These roles " +
                       "are specified in the configuration file (see --config).",
                  default="default")

(options, args) = parser.parse_args()


## Setup flask application ##
print "ice: starting ..."

db_config = None

try:

  if options.config_file == "heroku": 
    app = SeaIceFlask(__name__)

  else: 
    db_config = seaice.get_config(options.config_file)
    app = SeaIceFlask(__name__, db_user = db_config.get(options.db_role, 'user'),
                                db_password = db_config.get(options.db_role, 'password'),
                                db_name = db_config.get(options.db_role, 'dbname'))

except pgdb.DatabaseError, e:
  print >>sys.stderr, 'error: %s' % e    
  sys.exit(1)

app.secret_key = "\x14\x16o2'\x9c\xa3\x9c\x95k\xb3}\xac\xbb=\x1a\xe1\xf2\xc8!"

  ## Session logins ##

login_manager = l.LoginManager()
login_manager.init_app(app)
login_manager.anonymous_user = seaice.AnonymousUser

  ## Prescore terms ##
  # This will be used to check for consistency errors in live scoring
  # and isn't needed until I implement O(1) scoring. 

#print "ice: checking term score consistnency (dev)" TODO
#for term in db_con.getAllTerms():
#  if not db_con.checkTermConsistency(term['id']):
#    print "warning: corrected inconsistent consensus score for term %d" % term['id']
#  db_con.commit()

print "ice: setup complete."



@login_manager.user_loader
def load_user(id):
  return app.SeaIceUsers.get(int(id))

  ## Request wrappers (may have use for these later) ##

@app.before_request
def before_request():
  pass

@app.teardown_request
def teardown_request(exception):
  pass


## HTTP request handlers ##

@app.errorhandler(404)
def pageNotFound(e):
    return render_template('basic_page.html', user_name = l.current_user.name, 
                                              title = "Oops! - 404",
                                              headline = "404",
                                              content = "The page you requested doesn't exist."), 404

@app.route("/")
def index():
  if l.current_user.id:
    g.db = app.dbPool.getScoped()
      # TODO Store these values in class User in order to prevent
      # these queries every time the homepage is accessed.  
    my = seaice.printTermsAsLinks(g.db.getTermsByUser(l.current_user.id))
    star = seaice.printTermsAsLinks(g.db.getTermsByTracking(l.current_user.id))
    notify = l.current_user.getNotificationsAsHTML(g.db)
    return render_template("index.html", user_name = l.current_user.name,
                                         my = Markup(my.decode('utf-8')) if my else None,
                                         star = Markup(star.decode('utf-8')) if star else None, 
                                         notify = Markup(notify.decode('utf-8')) if notify else None)

  return render_template("index.html", user_name = l.current_user.name)

@app.route("/about")
def about():
  return render_template("about.html", user_name = l.current_user.name)

@app.route("/contact")
def contact():
  return render_template("contact.html", user_name = l.current_user.name)


  ## Login and logout ##

@app.route("/login")
def login():
  if l.current_user.id:
      return render_template("basic_page.html", user_name = l.current_user.name,
                                                title = "Oops!", 
                                                content = "You are already logged in!")
    
  form = '''
    <p>
      In order to propose new terms or comment on others, you must first
      sign in. 
       <li>Sign in with <a href="/login/google">Google</a>.</li>
    </p>
    '''
  return render_template("basic_page.html", title = "Login page", 
                                            headline = "Login", 
                                            content = Markup(form.decode('utf-8')))

@app.route("/login/google")
def login_google():
  callback=url_for('authorized', _external=True)
  return seaice.google.authorize(callback=callback)

@app.route(seaice.REDIRECT_URI)
@seaice.google.authorized_handler
def authorized(resp):
  access_token = resp['access_token']
  session['access_token'] = access_token, ''

  headers = {'Authorization': 'OAuth '+access_token}
  req = Request('https://www.googleapis.com/oauth2/v1/userinfo', None, headers)
  try:
    res = urlopen(req)
  except URLError, e:
    if e.code == 401: # Unauthorized - bad token
      session.pop('access_token', None)
      return 'l'
  g_user = json.load(res)
  
  g.db = app.dbPool.getScoped()
  user = g.db.getUserByAuth('google', g_user['id'])
  if not user: 
    g_user['authority'] = 'google'
    g_user['auth_id'] = g_user['id']
    g_user['id'] = app.userIdPool.ConsumeId()
    g_user['last_name'] = "nil"
    g_user['first_name'] = "nil"
    g.db.insertUser(g_user)
    g.db.commit()
    user = g.db.getUserByAuth('google', g_user['auth_id'])
    app.SeaIceUsers[user['id']] = seaice.User(user['id'], user['first_name'])
    l.login_user(app.SeaIceUsers.get(user['id']))
    return render_template("settings.html", user_name = l.current_user.name,
                                            email = g_user['email'],
                                            message = """
        According to our records, this is the first time you've logged onto 
        SeaIce with this account. Please provide your first and last name as 
        you would like it to appear with your contributions. Thank you!""")
  
  l.login_user(app.SeaIceUsers.get(user['id']))
  flash("Logged in successfully")
  return redirect(url_for('index'))


@seaice.google.tokengetter
def get_access_token():
  return session.get('access_token')

@app.route('/logout')
@l.login_required
def logout():
  l.logout_user()
  return redirect(url_for('index'))

@login_manager.unauthorized_handler
def unauthorized(): 
  return redirect(url_for('login'))


  ## Users ##

@app.route("/settings", methods = ['POST', 'GET'])
@l.login_required
def settings():
  g.db = app.dbPool.dequeue()
  if request.method == "POST": 
    g.db.updateUser(l.current_user.id, 
                   request.form['first_name'],
                   request.form['last_name'])
    g.db.commit()
    app.dbPool.enqueue(g.db)
    l.current_user.name = request.form['first_name']
    return getUser(str(l.current_user.id))
  
  user = g.db.getUser(l.current_user.id)
  app.dbPool.enqueue(g.db)
  return render_template("settings.html", user_name = l.current_user.name,
                                          email = user['email'].decode('utf-8'),
                                          last_name_edit = user['last_name'].decode('utf-8'),
                                          first_name_edit = user['first_name'].decode('utf-8'),
                                          reputation = user['reputation'],
                                          message = """
                    Here you can change how your name will appear to other users. 
                    Navigating away from this page will safely discard any changes.""")

@app.route("/user=<int:user_id>")
def getUser(user_id = None): 
 
  g.db = app.dbPool.getScoped()
  try:
    user = g.db.getUser(int(user_id))
    if user:
      result =  """<hr>
        <table cellpadding=12>
          <tr><td valign=top width="40%">First name:</td><td>{0}</td></tr>
          <tr><td valign=top>Last name:</td><td>{1}</td></tr>
          <tr><td valign=top>Email:</td><td>{2}</td></td>
          <tr><td valign=top>Reputation:</td><td>{3}</td></td>
        </table> """.format(user['first_name'], user['last_name'], user['email'], user['reputation'])
      return render_template("basic_page.html", user_name = l.current_user.name, 
                                                title = "User - %s" % user_id, 
                                                headline = "User", 
                                                content = Markup(result.decode('utf')))
  except IndexError: pass
  
  return render_template("basic_page.html", user_name = l.current_user.name, 
                                            title = "User not found",
                                            headline = "User", 
                                            content = Markup("User <strong>#%s</strong> not found!" % user_id))

@app.route("/user=<int:user_id>/notif=<int:notif_index>/remove", methods=['GET'])
@l.login_required
def remNotification(user_id, notif_index):
  try:
    assert user_id == l.current_user.id
    app.SeaIceUsers[user_id].remove(notif_index, app.dbPool.getScoped())
    return redirect("/")

  except AssertionError:
    return render_template("basic_page.html", user_name = l.current_user.name,
                                              title = "Oops!",
                                              content = 'You may only delete your own notifications.')

  except AssertionError:
    return render_template("basic_page.html", user_name = l.current_user.name,
                                              title = "Oops!",
                                              content = 'Index out of range.')
                                            


  ## Look up terms ##

@app.route("/term=<term_id>")
def getTerm(term_id = None, message = ""):
  
  g.db = app.dbPool.getScoped()
  try: 
    term = g.db.getTerm(int(term_id))
    if term:
      result = seaice.printTermAsHTML(g.db, term, l.current_user.id)
      result = message + "<hr>" + result + "<hr>"
      result += seaice.printCommentsAsHTML(g.db, g.db.getCommentHistory(term['id']),
                                                 l.current_user.id)
      if l.current_user.id:
        result += """ 
        <form action="/term={0}/comment" method="post">
          <table cellpadding=16 width=60%>
            <tr><td><textarea type="text" name="comment_string" rows=3
              style="width:100%; height:100%"
              placeholder="Add comment"></textarea></td></tr>
            <tr><td align=right><input type="submit" value="Comment"><td>
            </td>
          </table>
        </form>""".format(term['id'])
      return render_template("basic_page.html", user_name = l.current_user.name, 
                                                title = "Term - %s" % term_id, 
                                                headline = "Term", 
                                                content = Markup(result.decode('utf-8')))
  except ValueError: pass

  return render_template("basic_page.html", user_name = l.current_user.name, 
                                            title = "Term not found",
                                            headline = "Term", 
                                            content = Markup("Term <strong>#%s</strong> not found!" % term_id))

@app.route("/browse")
@app.route("/browse/<listing>")
def browse(listing = None):
  g.db = app.dbPool.getScoped()
  terms = g.db.getAllTerms(sortBy="term_string")
  letter = '~'
  result = "<h5>{0} | {1} | {2} | {3} | {4}</h5><hr>".format(
     '<a href="/browse/score">high score</a>' if listing != "score" else 'high score',
     '<a href="/browse/recent">recent</a>' if listing != "recent" else 'recent',
     '<a href="/browse/volatile">volatile</a>' if listing != "volatile" else 'volatile',
     '<a href="/browse/stable">stable</a>' if listing != "stable" else 'stable',
     '<a href="/browse/alphabetical">alphabetical</a>' if listing != "alphabetical" else 'alphabetical'
    )
 
  if listing == "recent": # Most recently added listing 
    result += seaice.printTermsAsBriefHTML(g.db, 
                                           sorted(terms, key=lambda term: term['modified'],
                                                         reverse=True),
                                           l.current_user.id)
  
  elif listing == "score": # Highest consensus
    terms = sorted(terms, key=lambda term: term['consensus'], reverse=True)
    result += seaice.printTermsAsBriefHTML(g.db, 
      sorted(terms, key=lambda term: term['up'] - term['down'], reverse=True), l.current_user.id)

  elif listing == "volatile": # Least stable (Frequent updates, commenting, and voting)
    terms = sorted(terms, key=lambda term: term['t_stable'] or term['t_last'], reverse=True)
    result += seaice.printTermsAsBriefHTML(g.db, terms, l.current_user.id)

  elif listing == "stable": # Most stable, highest consensus
    terms = sorted(terms, key=lambda term: term['t_stable'] or term['t_last'])
    result += seaice.printTermsAsBriefHTML(g.db, terms, l.current_user.id)
    
  elif listing == "alphabetical": # Alphabetical listing 
    result += "<table>"
    for term in terms: 
      if term['term_string'][0].upper() != letter:
        letter = term['term_string'][0].upper()
        result += "</td></tr><tr><td width=20% align=center valign=top><h4>{0}</h4></td><td width=80%>".format(letter)
      result += "<p><a href=\"/term=%d\">%s</a> <i>contributed by %s</i></p>" % (
        term['id'], term['term_string'], g.db.getUserNameById(term['owner_id']))
    result += "</table>"

  else:
    return redirect("/browse/recent")

  return render_template("browse.html", user_name = l.current_user.name, 
                                        title = "Browse", 
                                        headline = "Browse dictionary",
                                        content = Markup(result.decode('utf-8')))




@app.route("/search", methods = ['POST', 'GET'])
def returnQuery():
  g.db = app.dbPool.getScoped()
  if request.method == "POST": 
    terms = g.db.search(request.form['term_string'])
    if len(terms) == 0: 
      return render_template("search.html", user_name = l.current_user.name, 
                                            term_string = request.form['term_string'])
    else:
      result = seaice.printTermsAsHTML(g.db, terms, l.current_user.id)
      return render_template("search.html", user_name = l.current_user.name, 
        term_string = request.form['term_string'], result = Markup(result.decode('utf-8')))

  else: # GET
    return render_template("search.html", user_name = l.current_user.name)



  ## Propose, edit, or remove a term ##

@app.route("/contribute", methods = ['POST', 'GET'])
@l.login_required
def addTerm(): 

  if request.method == "POST": 
    g.db = app.dbPool.dequeue()
    term = { 'term_string' : request.form['term_string'],
             'definition' : request.form['definition'],
             'examples' : request.form['examples'],
             'owner_id' : l.current_user.id,
             'id' : app.termIdPool.ConsumeId() }

    id = g.db.insertTerm(term)
    g.db.commit()
    app.dbPool.enqueue(g.db)
    return getTerm(str(id), message = "Your term has been added to the metadictionary!")
  
  else: return render_template("contribute.html", user_name = l.current_user.name, 
                                                  title = "Contribute", 
                                                  headline = "Add a dictionary term")


@app.route("/term=<int:term_id>/edit", methods = ['POST', 'GET'])
@l.login_required
def editTerm(term_id = None): 

  try: 
    g.db = app.dbPool.dequeue()
    term_id = int(term_id)
    term = g.db.getTerm(term_id)
    assert l.current_user.id and term['owner_id'] == l.current_user.id
    
    if request.method == "POST":

      assert request.form.get('examples') != None
      updatedTerm = { 'term_string' : request.form['term_string'],
                      'definition' : request.form['definition'],
                      'examples' : request.form['examples'],
                      'owner_id' : l.current_user.id } 

      g.db.updateTerm(term_id, updatedTerm)

      # Notify tracking users
      notify_update = seaice.notify.TermUpdate(term_id, l.current_user.id, 
                                               term['modified'])
                                               
      for user_id in g.db.getTrackingByTerm(term_id):
        app.SeaIceUsers[user_id].notify(notify_update, g.db)        
      
      g.db.commit()
      app.dbPool.enqueue(g.db)

      return getTerm(term_id, message = "Your term has been updated in the metadictionary.")
  
    else: # GET 
      app.dbPool.enqueue(g.db)
      if term: 
        return render_template("contribute.html", user_name = l.current_user.name, 
                                                  title = "Edit - %s" % term_id,
                                                  headline = "Edit term",
                                                  edit_id = term_id,
                                                  term_string_edit = term['term_string'].decode('utf-8'),
                                                  definition_edit = term['definition'].decode('utf-8'),
                                                  examples_edit = term['examples'].decode('utf-8'))
  except ValueError:
    return render_template("basic_page.html", user_name = l.current_user.name, 
                                              title = "Term not found",
                                              headline = "Term", 
                                              content = Markup("Term <strong>#%s</strong> not found!" % term_id))

  except AssertionError:
    return render_template("basic_page.html", user_name = l.current_user.name, 
                                              title = "Term - %s" % term_id, 
                                              content = 
              """Error! You may only edit or remove terms and definitions which 
                 you've contributed. However, you may comment or vote on this term. """)


@app.route("/term=<int:term_id>/remove", methods=["POST"])
@l.login_required
def remTerm(term_id):

  try:
    g.db = app.dbPool.getScoped()
    term = g.db.getTerm(int(request.form['id']))
    assert term and term['owner_id'] == l.current_user.id
    
    tracking_users = g.db.getTrackingByTerm(term_id)

    id = g.db.removeTerm(int(request.form['id']))
    app.termIdPool.ReleaseId(id)
      
    # Notify tracking users
    notify_removed = seaice.notify.TermRemoved(l.current_user.id, 
                                               term['term_string'], 
                                               g.db.getTime())
      
    for user_id in tracking_users:
      app.SeaIceUsers[user_id].notify(notify_removed, g.db)
    
    g.db.commit()
  
    return render_template("basic_page.html", user_name = l.current_user.name, 
                                            title = "Remove term",
                                            content = Markup(
                 "Successfully removed term <b>#%s</b> from the metadictionary." % request.form['id'].decode('utf-8')))
  
  except AssertionError:
    return render_template("basic_page.html", user_name = l.current_user.name, 
                                              title = "Term - %s" % term_id, 
                                              content = 
              """Error! You may only edit or remove terms and definitions which 
                 you've contributed. However, you may comment or vote on this term. """)


  ## Comments ##

@app.route("/term=<int:term_id>/comment", methods=['POST'])
@l.login_required
def addComment(term_id):

  try:
    assert l.current_user.id
    
    term_id = int(term_id)
    g.db = app.dbPool.getScoped()
    comment = { 'comment_string' : request.form['comment_string'],
                'term_id' : term_id,
                'owner_id' : l.current_user.id,
                'id' : app.commentIdPool.ConsumeId()}
      
    comment_id = g.db.insertComment(comment) 

    # Notify owner and tracking users
    notify_comment = seaice.notify.Comment(term_id, l.current_user.id, 
                                g.db.getComment(comment_id)['created'])

    tracking_users = g.db.getTrackingByTerm(term_id)
    tracking_users.append(g.db.getTerm(term_id)['owner_id'])
    for user_id in tracking_users:
      if user_id != l.current_user.id: 
        app.SeaIceUsers[user_id].notify(notify_comment, g.db)
    
    g.db.commit()

    return redirect("term=%d" % term_id)

  except AssertionError:
    return redirect(url_for('login'))

@app.route("/comment=<int:comment_id>/edit", methods = ['POST', 'GET'])
@l.login_required
def editComment(comment_id = None): 

  try: 
    g.db = app.dbPool.dequeue()
    comment = g.db.getComment(int(comment_id))
    assert l.current_user.id and comment['owner_id'] == l.current_user.id
    
    if request.method == "POST":
      updatedComment = { 'comment_string' : request.form['comment_string'],
                         'owner_id' : l.current_user.id } 

      g.db.updateComment(int(comment_id), updatedComment)
      g.db.commit()
      app.dbPool.enqueue(g.db)
      return getTerm(comment['term_id'], message = "Your comment has been updated.")
  
    else: # GET 
      app.dbPool.enqueue(g.db)
      if comment: 
        form = """ 
        <form action="/comment={0}/edit" method="post">
          <table cellpadding=16 width=60%>
            <tr><td><textarea type="text" name="comment_string" rows=3
              style="width:100%; height:100%"
              placeholder="Add comment">{1}</textarea></td></tr>
            <tr><td align=right><input type="submit" value="Comment"><td>
            </td>
          </table>
         </form>""".format(comment_id, comment['comment_string'])
        return render_template("basic_page.html", user_name = l.current_user.name,
                                                  title = "Edit comment", 
                                                  headline = "Edit your comment",
                                                  content = Markup(form.decode('utf-8')))


  
  except ValueError:
    return render_template("basic_page.html", user_name = l.current_user.name, 
                                              title = "Comment not found",
                                              content = Markup("Comment <strong>#%s</strong> not found!" % comment_id))

  except AssertionError:
    return render_template("basic_page.html", user_name = l.current_user.name, 
                                              title = "Term - %s" % term_id, 
                                              content = 
              """Error! You may only edit or remove terms and definitions which 
                 you've contributed. However, you may comment or vote on this term. """)


@app.route("/comment=<int:comment_id>/remove", methods=['POST'])
def remComment(comment_id):
  
  try:
    g.db = app.dbPool.getScoped()
    comment = g.db.getComment(int(request.form['id']))
    assert comment and comment['owner_id'] == l.current_user.id

    g.db.removeComment(int(request.form['id']))
    g.db.commit()
  
    return redirect('/term=%d' % comment['term_id'])
  
  except AssertionError:
    return render_template("basic_page.html", user_name = l.current_user.name, 
                                              title = "Oops!", 
                                              content = 
              """Error! You may only edit or remove your own comments.""")



  ## Voting! ##

@app.route("/term=<int:term_id>/vote", methods=['POST'])
@l.login_required
def voteOnTerm(term_id):
  g.db = app.dbPool.getScoped()
  p_vote = g.db.getVote(l.current_user.id, term_id) 
  if request.form['action'] == 'up':
    if p_vote == 1:
      g.db.castVote(l.current_user.id, term_id, 0)
    else:      
      g.db.castVote(l.current_user.id, term_id, 1)
  elif request.form['action'] == 'down':
    if p_vote == -1:
      g.db.castVote(l.current_user.id, term_id, 0)
    else: 
      g.db.castVote(l.current_user.id, term_id, -1)
  else:
    g.db.castVote(l.current_user.id, term_id, 0)
  g.db.commit()
  print "User #%d voted %s term #%d" % (l.current_user.id, request.form['action'], term_id)
  return redirect("/term=%d" % term_id)

@app.route("/term=<int:term_id>/track", methods=['POST'])
@l.login_required
def trackTerm(term_id): 
  g.db = app.dbPool.getScoped()
  if request.form['action'] == "star":
    g.db.trackTerm(l.current_user.id, term_id)
  else:
    g.db.untrackTerm(l.current_user.id, term_id)
  g.db.commit()
  print "User #%d %sed term #%d" % (l.current_user.id, request.form['action'], term_id)
  return redirect("/term=%d" % term_id)



## Start HTTP server. ##

if __name__ == '__main__':
    app.debug = True
    app.run('0.0.0.0', 5000, use_reloader=True)

