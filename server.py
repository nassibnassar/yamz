from flask import Flask
from flask import render_template
from flask import request

app = Flask(__name__)

@app.route('/create_term')
def hello(name = None):
    return render_template('create_term.html', name = name)

@app.route('/create_term_post', methods = ['POST'])
def create_term_post():
    return 'Well done, %s!' % request.form['term_string']

if __name__ == '__main__':
    app.debug = True
    app.run('0.0.0.0', 8080)

