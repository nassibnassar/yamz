from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello_world():
  return 'Hello World!'

@app.route('/fella')
def stuff(): 
  return "<b> guy!!! </b>"

if __name__ == '__main__':
  app.run()


