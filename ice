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
from flask import render_template
from flask import request

import sys, MySQLdb as mdb
import seaice

## Connect to local MySQL databse. ## 

try: 

  config = seaice.get_config()
  
  sea = seaice.SeaIceDb( 'localhost', 
                          config.get('default', 'user'),
                          config.get('default', 'password'),
                          config.get('default', 'dbname')
                       )

except mdb.Error, e:
  print >>sys.stderr, "error (%d): %s" % (e.args[0],e.args[1])
  sys.exit(1)

print "ice: connection to database established."

## HTTP request handlers ##

app = Flask(__name__)

@app.route("/")
def index():
  return render_template("index.html")

@app.route("/about")
def about():
  return render_template("about.html")

@app.route("/contact")
def contact():
  return render_template("contact.html")

@app.route("/browse")
def browse():
  terms = sea.getAllTerms(sortBy="TermString")
  result = "<hr>"

  for term in terms: 
    result += "<p><a href=\"/term=%d\">%s</a> <i>contributed by</i> %s</p>" % (
      term['Id'], term['TermString'], term['ContactInfo'])

  return render_template("browse.html", title = "Browse", 
                                        headline = "Browse dictionary",
                                        content = Markup(result))

@app.route("/contribute")
def contribute(): 
  return render_template("contribute.html", title = "Contribute", 
                                            headline = "Add a dictionary term")

@app.route("/term=<term_id>")
def term(term_id = None):
  
  try: 
    term = sea.getTerm(int(term_id))
    if term:
      result = seaice.printAsHTML([term])
      return render_template("basic_page.html", title = "Term - %s" % term_id, 
                                                headline = "Term", 
                                                content = Markup(result))
  except ValueError: pass

  return render_template("basic_page.html", title = "Term not found",
                                            headline = "Term", 
                                            content = Markup("Term <strong>#%s</strong> not found!" % term_id))
    
@app.route("/search", methods = ['POST', 'GET'])
def returnQuery():

  if request.method == "POST": 
    terms = sea.searchByTerm(request.form['term_string'])
    if len(terms) == 0: 
      return render_template("search.html", term_string = request.form['term_string'])
    else:
      result = seaice.printAsHTML(terms)
      return render_template("search.html", 
        term_string = request.form['term_string'], result = Markup(result))

  else: # GET
    return render_template("search.html")

## Start HTTP server. ##

if __name__ == '__main__':
    app.debug = True
    app.run('localhost', 5000)

