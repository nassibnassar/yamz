#!/usr/bin/python
# Copyright (c) 2013, Christopher Patton
# All rights reserved.
#
# TODO
# "if 'user_id' not in session: session['user_id'] = 0" is pasted to the 
# beginning of each function to simplify the code. It'd be nice to have 
# 'user_id' in the defualt session. Investigate how to do this.
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
from flask import render_template, render_template_string, url_for, redirect
from flask import request, session

import sys, MySQLdb as mdb
import seaice

## Create connection pools to local MySQL databse. ## 

try: 

  config = seaice.get_config()

  viewers = [ seaice.SeaIceConnector('localhost', 
                              config.get('viewer', 'user'),
                              config.get('viewer', 'password'),
                              config.get('viewer', 'dbname'))
              for _ in range(5) ]

  contributors = [ seaice.SeaIceConnector('localhost', 
                                   config.get('contributor', 'user'),
                                   config.get('contributor', 'password'),
                                   config.get('contributor', 'dbname'))
              for _ in range(5) ]

  
  # TEMP
  sea = seaice.SeaIceConnector('localhost', 
                         config.get('contributor', 'user'),
                         config.get('contributor', 'password'),
                         config.get('contributor', 'dbname'))


except mdb.Error, e:
  print >>sys.stderr, "error (%d): %s" % (e.args[0],e.args[1])
  sys.exit(1)

print "ice: connection to database established."

## HTTP request handlers ##

app = Flask(__name__)
app.secret_key = "Joseph D. Sanders" # DUMB

@app.route("/")
def index():
  if 'user_id' not in session: session['user_id'] = 0
  return render_template("index.html", user_id = session['user_id'])

@app.route("/about")
def about():
  if 'user_id' not in session: session['user_id'] = 0
  return render_template("about.html", user_id = session['user_id'])

@app.route("/contact")
def contact():
  if 'user_id' not in session: session['user_id'] = 0
  return render_template("contact.html", user_id = session['user_id'])


@app.route("/login", methods = ['POST', 'GET'])
def login():
  if 'user_id' not in session: session['user_id'] = 0
  if request.method == 'POST':
    if sea.getUserNameById(int(request.form['user_id'])):
      session['user_id'] = int(request.form['user_id'])
      return redirect(url_for('index'))
    else: 
      return render_template("basic_page.html", title = "Login failed", 
                                                content = "Account doesn't exist!")
  form = '''
    <p>
      In order to propose new terms or comment on other's, you must first
      sign in. 
    </p>
    <hr>
    <form action="" method="post">
      <p><input type=text name=user_id>
      <p><input type=submit value=Login>
    </form>
    '''
  return render_template("basic_page.html", title = "Login page", 
                                            headline = "Login", 
                                            content = Markup(form))
                                            
@app.route('/logout')
def logout():
  if 'user_id' not in session: session['user_id'] = 0
  # remove the user_id from the session if it's there
  session.pop('user_id', None)
  return redirect(url_for('index'))


## Look up terms ##

@app.route("/term=<term_id>")
def getTerm(term_id = None):
  
  if 'user_id' not in session: session['user_id'] = 0
  try: 
    term = sea.getTerm(int(term_id))
    if term:
      result = sea.printAsHTML([term], session['user_id'])
      return render_template("basic_page.html", user_id = session['user_id'], 
                                                title = "Term - %s" % term_id, 
                                                headline = "Term", 
                                                content = Markup(result))
  except ValueError: pass

  return render_template("basic_page.html", user_id = session['user_id'], 
                                            title = "Term not found",
                                            headline = "Term", 
                                            content = Markup("Term <strong>#%s</strong> not found!" % term_id))

@app.route("/browse")
def browse():
  if 'user_id' not in session: session['user_id'] = 0
  terms = sea.getAllTerms(sortBy="TermString")
  result = "<hr>"

  for term in terms: 
    result += "<p><a href=\"/term=%d\">%s</a> <i>contributed by</i> %d</p>" % (
      term['Id'], term['TermString'], term['OwnerId'])

  return render_template("browse.html", user_id = session['user_id'], 
                                        title = "Browse", 
                                        headline = "Browse dictionary",
                                        content = Markup(result))


@app.route("/search", methods = ['POST', 'GET'])
def returnQuery():
  if 'user_id' not in session: session['user_id'] = 0
  if request.method == "POST": 
    terms = sea.searchByTerm(request.form['term_string'])
    if len(terms) == 0: 
      return render_template("search.html", user_id = session['user_id'], 
                                            term_string = request.form['term_string'])
    else:
      result = sea.printAsHTML(terms, session['user_id'])
      return render_template("search.html", user_id = session['user_id'], 
        term_string = request.form['term_string'], result = Markup(result))

  else: # GET
    return render_template("search.html", user_id = session['user_id'])



## Propose or edit terms ##

@app.route("/contribute", methods = ['POST', 'GET'])
def addTerm(): 
  if 'user_id' not in session or not session['user_id']: 
    return redirect(url_for('login'))

  if request.method == "POST": 
    term = { 'TermString' : request.form['term_string'],
             'Definition' : request.form['definition'],
             'OwnerId' : session['user_id'] }

    sea.insert(term)
    sea.commit()

    return render_template("basic_page.html", user_id = session['user_id'], 
                                              title = "Contribute",
                                              headline = "Contribute", 
                                              content = Markup(
        """<strong>%s</strong> has been added to the metadictionary.
        Thank you for your contribution!""" % request.form['term_string']))
  
  else: return render_template("contribute.html", user_id = session['user_id'], 
                                                  title = "Contribute", 
                                                  headline = "Add a dictionary term")


@app.route("/edit=<term_id>", methods = ['POST', 'GET'])
def editTerm(term_id = None): 
  if 'user_id' not in session: session['user_id'] = 0

  try: 
    term = sea.getTerm(int(term_id))
    assert term['OwnerId'] == session['user_id']
    
    if request.method == "POST":
      updatedTerm = { 'TermString' : request.form['term_string'],
                      'Definition' : request.form['definition'],
                      'OwnerId' : session['user_id'] } 

      sea.updateTerm(int(term_id), updatedTerm)
      sea.commit()

      return render_template("basic_page.html", user_id = session['user_id'], 
                                                title = "Edit",
                                                headline = "Edit Term", 
                                                content = Markup(
          """<strong>%s</strong> has been updated in the metadictionary.
          Thank you for your contribution!""" % request.form['term_string']))
  
    else: # GET 
      if term: 
        return render_template("contribute.html", user_id = session['user_id'], 
                                                  title = "Edit - %s" % term_id,
                                                  headline = "Edit term",
                                                  edit_id = term_id,
                                                  term_string_edit = term['TermString'],
                                                  definition_edit = term['Definition'])
  except ValueError:
    return render_template("basic_page.html", user_id = session['user_id'], 
                                              title = "Term not found",
                                              headline = "Term", 
                                              content = Markup("Term <strong>#%s</strong> not found!" % term_id))

  except AssertionError:
    return render_template("basic_page.html", user_id = session['user_id'], 
                                              title = "Term - %s" % term_id, 
                                              content = 
              """Error! You may only edit or remove terms and definitions which 
                 you've contributed. However, you may comment or vote on this term. """)


@app.route("/temp")
def temp():
  sea.addUser()
  return "got it"

## Start HTTP server. ##

if __name__ == '__main__':
    app.debug = True
    app.run('localhost', 5000)

