#!/usr/bin/python
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

## Setup HTTP server. ##

app = Flask(__name__)

@app.route("/")
def index():
  return render_template("index.html")

@app.route("/about")
def about():
  return render_template("basic_page.html")

@app.route("/contact")
def about():
  return render_template("basic_page.html")

@app.route("/search")
def searchByTerm():
  return render_template("search_by_term.html")

@app.route("/result", methods = ['POST'])
def returnQuery():
  terms = sea.searchByTerm(request.form['term_string'])
  if len(terms) == 0: 
    return render_template("query_result_template.html", term_string = request.form['term_string'])
  else: 
    result = "<table>" 
    for term in terms:
      result += "<tr>"
      result += "  <td width=%s><i>Term:</i> <strong>%s</strong> (#%d)</td>" % (repr("65%"), term['TermString'], term['Id'])
      result += "  <td><i>Created</i>: %s</td>" % term['Modified']
      result += "</tr><tr>"
      result += "  <td><i>Score</i>: %s</td>" % term['Score']
      result += "  <td><i>Last Modified</i>: %s</td>" % term['Modified']
      result += "</tr><tr colspan=2>"
      result += "  <td><i>Definition:</i> %s</td>" % term['Definition']
      result += "</tr><tr colspan=2>"
      result += "  <td><i>Ownership:</i> %s<br><br></td></tr>" % term['ContactInfo']
    result += "</table>"

    return render_template("query_result_template.html", 
      term_string = request.form['term_string'], result = Markup(result))

if __name__ == '__main__':
    app.debug = True
    app.run('localhost', 5000)

