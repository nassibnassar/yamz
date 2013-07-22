from flask import Flask

class SeaIceFlask (Flask): 
  
  def __init__(self, import_name, static_path=None, static_url_path=None,
                     static_folder='static', template_folder='templates',
                     instance_path=None, instance_relative_config=False):

    Flask.__init__(self, import_name, static_path, static_url_path, 
                         static_folder, template_folder,
                         instance_path, instance_relative_config)

  def __del__(self):
    print "shiiiit"
