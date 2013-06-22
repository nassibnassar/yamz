#!/usr/bin/python
# Copyright (c) 2013, Christopher Patton
# All rights reserved.
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
from flask_oauth import OAuth
from flask.ext import login as poop

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
useful, but without warranty. You should have received a copy of the BSD 
license with this program; otherwise, visit 
http://opensource.org/licenses/BSD-3-Clause.
"""

parser.add_option("--config", dest="config_file", metavar="FILE", 
                  help="User credentials for local PostgreSQL database (defaults to '$HOME/.seaice')." + 
                       "If 'heroku' is given, then a connection to a foreign host specified by" + 
                       "DATABASE_URL is established.",
                  default=(os.environ['HOME'] + '/.seaice'))

parser.add_option("-d", "--debug", action="store_true", dest="debug", default=False,
                  help="Start flask in debug mode.")

(options, args) = parser.parse_args()




## Connect to PostgreSQL databse ## 

db_config = None

try: 
  if options.config_file == "heroku": 
    sea = seaice.SeaIceConnector()

  else: 
    db_config = seaice.get_config(options.config_file)
    sea = seaice.SeaIceConnector(db_config.get('default', 'user'),
                                 db_config.get('default', 'password'),
                                 db_config.get('default', 'dbname'))

except pqdb.DatabaseError, e:
  print 'error: %s' % e    
  sys.exit(1)




## Setup flask application ##

app = Flask(__name__)
app.secret_key = "\x14\x16o2'\x9c\xa3\x9c\x95k\xb3}\xac\xbb=\x1a\xe1\xf2\xc8!"

  ## Google authentication (Oauth) ##

oauth = OAuth()

GOOGLE_CLIENT_ID = '173499658661-cissqtglckjctv5rgh9a6mguln721rqr.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = '_Wmt-6SZXRMeaJVFXkuRH-rm'
REDIRECT_URI = '/authorized' # TODO move these parameters to local config file 

google = oauth.remote_app('google',
                          base_url='https://www.google.com/accounts/',
                          authorize_url='https://accounts.google.com/o/oauth2/auth',
                          request_token_url=None,
                          request_token_params={'scope': 'https://www.googleapis.com/auth/userinfo.email',
                                                'response_type': 'code'},
                          access_token_url='https://accounts.google.com/o/oauth2/token',
                          access_token_method='POST',
                          access_token_params={'grant_type': 'authorization_code'},
                          consumer_key=GOOGLE_CLIENT_ID,
                          consumer_secret=GOOGLE_CLIENT_SECRET)

  ## Session logins ##

login_manager = poop.LoginManager()
login_manager.init_app(app)
login_manager.anonymous_user = seaice.AnonymousUser

@login_manager.user_loader
def load_user(id):
  name = sea.getUserNameById(int(id))
  if name:
    return seaice.User(int(id), name)
  return None


## Request wrappers (get a db connector) ##
# It's probably a better idea to only grap a connection when it's
# required. 

@app.before_request
def before_request():
  if poop.current_user.id: 
    view = 'contributor'
  else:
    view = 'viewer'

  # TODO get from pool instead!
  try:

    if options.config_file == "heroku": 
      g.db = seaice.SeaIceConnector()

    else: 
      g.db = seaice.SeaIceConnector(db_config.get(view, 'user'),
                                    db_config.get(view, 'password'),
                                    db_config.get(view, 'dbname'))

  except pqdb.DatabaseError, e:
    print 'error: %s' % e    
    sys.exit(1)

@app.teardown_request
def teardown_request(exception):
  pass # connection closed when g.db goes out of scope. 
       # Once we have a connection pool, we'll release 
       # it to the pool here. TODO




## HTTP request handlers ##

@app.route("/")
def index():
  return render_template("index.html", user_name = poop.current_user.name)

@app.route("/about")
def about():
  return render_template("about.html", user_name = poop.current_user.name)

@app.route("/contact")
def contact():
  return render_template("contact.html", user_name = poop.current_user.name)


  ## Login and logout ##

@app.route("/login")
def login():
  #if request.method == 'POST':
  #  id = int(request.form['user_id'])
  #  name = g.db.getUserNameById(int(id))
  #  if name:
  #    poop.login_user(seaice.User(id, name))
  #    poop.current_user.id = id
  #    flash("Logged in successfully")
  #    return render_template('index.html', user_name = poop.current_user.name)
  #  else: 
  #    return render_template("basic_page.html", title = "Login failed", 
  #                                              content = "Account doesn't exist!")
  if poop.current_user.id:
      return render_template("basic_page.html", user_name = poop.current_user.name,
                                                title = "Oops!", 
                                                content = "You are already logged in!")
    
  form = '''
    <p>
      In order to propose new terms or comment on others', you must first
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
    return google.authorize(callback=callback)

@app.route(REDIRECT_URI)
@google.authorized_handler
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
      return 'poop'
  g_user = json.load(res)
  print g_user

    # TODO login, add user if necessary

  return redirect(url_for('index'))

@google.tokengetter
def get_access_token():
    return session.get('access_token')

@app.route('/logout')
@poop.login_required
def logout():
  poop.logout_user()
  return redirect(url_for('index'))

@login_manager.unauthorized_handler
def unauthorized(): 
  return redirect(url_for('login'))


  ## Look up terms ##

@app.route("/term=<term_id>")
def getTerm(term_id = None):
  
  try: 
    term = g.db.getTerm(int(term_id))
    if term:
      result = g.db.printAsHTML([term], poop.current_user.id)
      return render_template("basic_page.html", user_name = poop.current_user.name, 
                                                title = "Term - %s" % term_id, 
                                                headline = "Term", 
                                                content = Markup(result))
  except ValueError: pass

  return render_template("basic_page.html", user_name = poop.current_user.name, 
                                            title = "Term not found",
                                            headline = "Term", 
                                            content = Markup("Term <strong>#%s</strong> not found!" % term_id))

@app.route("/browse")
def browse():
  terms = g.db.getAllTerms(sortBy="term_string")
  result = "<hr>"

  for term in terms: 
    result += "<p><a href=\"/term=%d\">%s</a> <i>contributed by %s</i></p>" % (
      term['id'], term['term_string'], g.db.getUserNameById(term['owner_id']))

  return render_template("browse.html", user_name = poop.current_user.name, 
                                        title = "Browse", 
                                        headline = "Browse dictionary",
                                        content = Markup(result))


@app.route("/search", methods = ['POST', 'GET'])
def returnQuery():
  if request.method == "POST": 
    terms = g.db.searchByTerm(request.form['term_string'])
    if len(terms) == 0: 
      return render_template("search.html", user_name = poop.current_user.name, 
                                            term_string = request.form['term_string'])
    else:
      result = g.db.printAsHTML(terms, poop.current_user.id)
      return render_template("search.html", user_name = poop.current_user.name, 
        term_string = request.form['term_string'], result = Markup(result))

  else: # GET
    return render_template("search.html", user_name = poop.current_user.name)



  ## Propose or edit terms ##

@app.route("/contribute", methods = ['POST', 'GET'])
@poop.login_required
def addTerm(): 

  if request.method == "POST": 
    term = { 'term_string' : request.form['term_string'],
             'definition' : request.form['definition'],
             'owner_id' : poop.current_user.id }

    g.db.insert(term)
    g.db.commit()

    return render_template("basic_page.html", user_name = poop.current_user.name, 
                                              title = "Contribute",
                                              headline = "Contribute", 
                                              content = Markup(
        """<strong>%s</strong> has been added to the metadictionary.
        Thank you for your contribution!""" % request.form['term_string']))
  
  else: return render_template("contribute.html", user_name = poop.current_user.name, 
                                                  title = "Contribute", 
                                                  headline = "Add a dictionary term")


@app.route("/edit=<term_id>", methods = ['POST', 'GET'])
@poop.login_required
def editTerm(term_id = None): 

  try: 
    term = g.db.getTerm(int(term_id))
    assert poop.current_user.id and term['owner_id'] == poop.current_user.id
    
    if request.method == "POST":
      updatedTerm = { 'term_string' : request.form['term_string'],
                      'definition' : request.form['definition'],
                      'owner_id' : poop.current_user.id } 

      g.db.updateTerm(int(term_id), updatedTerm)
      g.db.commit()

      return render_template("basic_page.html", user_name = poop.current_user.name, 
                                                title = "Edit",
                                                headline = "Edit Term", 
                                                content = Markup(
          """<strong>%s</strong> has been updated in the metadictionary.
          Thank you for your contribution!""" % request.form['term_string']))
  
    else: # GET 
      if term: 
        return render_template("contribute.html", user_name = poop.current_user.name, 
                                                  title = "Edit - %s" % term_id,
                                                  headline = "Edit term",
                                                  edit_id = term_id,
                                                  term_string_edit = term['term_string'],
                                                  definition_edit = term['definition'])
  except ValueError:
    return render_template("basic_page.html", user_name = poop.current_user.name, 
                                              title = "Term not found",
                                              headline = "Term", 
                                              content = Markup("Term <strong>#%s</strong> not found!" % term_id))

  except AssertionError:
    return render_template("basic_page.html", user_name = poop.current_user.name, 
                                              title = "Term - %s" % term_id, 
                                              content = 
              """Error! You may only edit or remove terms and definitions which 
                 you've contributed. However, you may comment or vote on this term. """)


## Start HTTP server. ##

if __name__ == '__main__':
    app.debug = True
    app.run('0.0.0.0', 5000)

