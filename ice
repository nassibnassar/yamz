#!/usr/bin/python
from flask import Flask
from flask import Markup
from flask import render_template
from flask import request

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
  result = Markup("<strong>%s</strong>" % request.form['term_string'])
  return render_template("query_result_template.html", term_string = result)

if __name__ == '__main__':
    app.debug = True
    app.run('localhost', 5000)

