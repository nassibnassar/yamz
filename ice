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

from flask import Flask
from flask import Markup
from flask import render_template, render_template_string
from flask import url_for, redirect, flash
from flask import request, session, g
from flask.ext import login as l

from urllib2 import Request, urlopen, URLError
import os, sys, optparse
import json, psycopg2 as pgdb
import seaice

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

(options, args) = parser.parse_args()




## Connect to PostgreSQL databse ## 

db_config = None

try:

  if options.config_file == "heroku": 
    dbPool = seaice.SeaIceConnectorPool(20)

  else: 
    db_config = seaice.get_config(options.config_file)
    dbPool = seaice.SeaIceConnectorPool(20, db_config.get('default', 'user'),
                                            db_config.get('default', 'password'),
                                            db_config.get('default', 'dbname'))

except pgdb.DatabaseError, e:
  print 'error: %s' % e    
  sys.exit(1)



## Setup flask application ##

app = Flask(__name__)
app.secret_key = "\x14\x16o2'\x9c\xa3\x9c\x95k\xb3}\xac\xbb=\x1a\xe1\xf2\xc8!"

  ## Session logins ##

login_manager = l.LoginManager()
login_manager.init_app(app)
login_manager.anonymous_user = seaice.AnonymousUser

@login_manager.user_loader
def load_user(id):
  db = dbPool.getScoped()
  name = db.getUserNameById(int(id))
  if name:
    return seaice.User(int(id), name)
  return None

  ## Request wrappers (may have use for these later) ##

@app.before_request
def before_request():
  pass

@app.teardown_request
def teardown_request(exception):
  pass


## HTTP request handlers ##

@app.route("/")
def index():
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
                                            content = Markup(form))

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
  
  g.db = dbPool.getScoped()
  user = g.db.getUserByAuth('google', g_user['id'])
  if not user: 
    g_user['authority'] = 'google'
    g_user['auth_id'] = g_user['id']
    g_user['id'] = 'default'
    g_user['last_name'] = "nil"
    g_user['first_name'] = "nil"
    g.db.insertUser(g_user)
    g.db.commit()
    user = g.db.getUserByAuth('google', g_user['auth_id'])
    l.login_user(seaice.User(user['id'], user['first_name']))
    return render_template("settings.html", user_name = l.current_user.name,
                                            email = g_user['email'],
                                            message = """
        According to our records, this is the first time you've logged onto 
        SeaIce with this account. Please provide your first and last name as 
        you would like it to appear with your contributions. Thank you!""")
  
  l.login_user(seaice.User(user['id'], user['first_name']))
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
  g.db = dbPool.dequeue()
  if request.method == "POST": 
    g.db.updateUser(l.current_user.id, 
                   request.form['first_name'],
                   request.form['last_name'])
    g.db.commit()
    dbPool.enqueue(g.db)
    l.current_user.name = request.form['first_name']
    return getUser(str(l.current_user.id))
  
  user = g.db.getUser(l.current_user.id)
  dbPool.enqueue(g.db)
  return render_template("settings.html", user_name = l.current_user.name,
                                          email = user['email'],
                                          last_name_edit = user['last_name'],
                                          first_name_edit = user['first_name'],
                                          message = """
                    Here you can change how your name will appear""")

@app.route("/user=<user_id>")
def getUser(user_id = None): 
 
  g.db = dbPool.getScoped()
  try:
    user = g.db.getUser(int(user_id))
    if user:
      result =  """<hr>
        <table cellpadding=12>
          <tr><td valign=top width="40%">First name:</td><td>{0}</td></tr>
          <tr><td valign=top>Last name:</td><td>{1}</td></tr>
          <tr><td valign=top>Email:</td><td>{2}</td></td>
        </table> """.format(user['first_name'], user['last_name'], user['email'])
      return render_template("basic_page.html", user_name = l.current_user.name, 
                                                title = "User - %s" % user_id, 
                                                headline = "User", 
                                                content = Markup(result))
  except IndexError: pass
  
  return render_template("basic_page.html", user_name = l.current_user.name, 
                                            title = "User not found",
                                            headline = "User", 
                                            content = Markup("User <strong>#%s</strong> not found!" % user_id))

  ## Look up terms ##

@app.route("/term=<term_id>")
def getTerm(term_id = None, message = ""):
  
  g.db = dbPool.getScoped()
  try: 
    term = g.db.getTerm(int(term_id))
    if term:
      result = seaice.printTermsAsHTML(g.db, [term], l.current_user.id)
      result = message + "<hr>" + result + "<hr>"
      result += seaice.printCommentsAsHTML(g.db, g.db.getCommentHistory(term['id']),
                                                 l.current_user.id)
      result += """ 
      <form action="term={0}/comment" method="post">
        <table cellpadding=16>
          <tr><td><textarea cols=50 rows=4 type="text" name="comment_string"></textarea></td></tr>
          <tr><td with=70%></td><td align=right><input type="submit" value="Comment"><td>
          </td>
        </table>
      </form>""".format(term['id'])
      return render_template("basic_page.html", user_name = l.current_user.name, 
                                                title = "Term - %s" % term_id, 
                                                headline = "Term", 
                                                content = Markup(result))
  except ValueError: pass

  return render_template("basic_page.html", user_name = l.current_user.name, 
                                            title = "Term not found",
                                            headline = "Term", 
                                            content = Markup("Term <strong>#%s</strong> not found!" % term_id))

@app.route("/browse")
def browse():
  g.db = dbPool.getScoped()
  terms = g.db.getAllTerms(sortBy="term_string")
  result = "<hr>"

  for term in terms: 
    result += "<p><a href=\"/term=%d\">%s</a> <i>contributed by %s</i></p>" % (
      term['id'], term['term_string'], g.db.getUserNameById(term['owner_id']))

  return render_template("browse.html", user_name = l.current_user.name, 
                                        title = "Browse", 
                                        headline = "Browse dictionary",
                                        content = Markup(result))


@app.route("/search", methods = ['POST', 'GET'])
def returnQuery():
  g.db = dbPool.getScoped()
  if request.method == "POST": 
    terms = g.db.search(request.form['term_string'])
    if len(terms) == 0: 
      return render_template("search.html", user_name = l.current_user.name, 
                                            term_string = request.form['term_string'])
    else:
      result = seaice.printTermsAsHTML(g.db, terms, l.current_user.id)
      return render_template("search.html", user_name = l.current_user.name, 
        term_string = request.form['term_string'], result = Markup(result))

  else: # GET
    return render_template("search.html", user_name = l.current_user.name)



  ## Propose, edit, or remove a term ##

@app.route("/contribute", methods = ['POST', 'GET'])
@l.login_required
def addTerm(): 

  if request.method == "POST": 
    g.db = dbPool.dequeue()
    term = { 'term_string' : request.form['term_string'],
             'definition' : request.form['definition'],
             'owner_id' : l.current_user.id }

    id = g.db.insertTerm(term)
    g.db.commit()
    dbPool.enqueue(g.db)
    return getTerm(str(id), message = "Your term has been added to the metadictionary!")
  
  else: return render_template("contribute.html", user_name = l.current_user.name, 
                                                  title = "Contribute", 
                                                  headline = "Add a dictionary term")


@app.route("/term=<int:term_id>/edit", methods = ['POST', 'GET'])
@l.login_required
def editTerm(term_id = None): 

  try: 
    g.db = dbPool.dequeue()
    term = g.db.getTerm(int(term_id))
    assert l.current_user.id and term['owner_id'] == l.current_user.id
    
    if request.method == "POST":
      updatedTerm = { 'term_string' : request.form['term_string'],
                      'definition' : request.form['definition'],
                      'owner_id' : l.current_user.id } 

      g.db.updateTerm(int(term_id), updatedTerm)
      g.db.commit()
      dbPool.enqueue(g.db)
      return getTerm(term_id, message = "Your term has been updated in the metadictionary.")
  
    else: # GET 
      dbPool.enqueue(g.db)
      if term: 
        return render_template("contribute.html", user_name = l.current_user.name, 
                                                  title = "Edit - %s" % term_id,
                                                  headline = "Edit term",
                                                  edit_id = term_id,
                                                  term_string_edit = term['term_string'],
                                                  definition_edit = term['definition'])
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
    g.db = dbPool.getScoped()
    term = g.db.getTerm(int(request.form['id']))
    assert term and term['owner_id'] == l.current_user.id

    g.db.removeTerm(int(request.form['id']))
    g.db.commit()
  
    return render_template("basic_page.html", user_name = l.current_user.name, 
                                            title = "Remove term",
                                            content = Markup(
                 "Successfully removed term <b>#%s</b> from the metadictionary." % request.form['id']))
  
  except AssertionError:
    return render_template("basic_page.html", user_name = l.current_user.name, 
                                              title = "Term - %s" % term_id, 
                                              content = 
              """Error! You may only edit or remove terms and definitions which 
                 you've contributed. However, you may comment or vote on this term. """)


  ## Comments ##

@app.route("/term=<int:term_id>/comment", methods=['POST'])
def addComment(term_id):

  try:
    assert l.current_user.id

    g.db = dbPool.getScoped()
    comment = { 'comment_string' : request.form['comment_string'],
                'term_id' : int(term_id),
                'owner_id' : l.current_user.id }
      
    g.db.insertComment(comment) 
    g.db.commit()

    return redirect("term=%d" % int(term_id))

  except AssertionError:
    return redirect(url_for('login'))

@app.route("/comment=<int:comment_id>/remove", methods=['POST'])
def remComment(comment_id):
  
  try:
    g.db = dbPool.getScoped()
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


## Start HTTP server. ##

if __name__ == '__main__':
    app.debug = True
    app.run('0.0.0.0', 5000)

