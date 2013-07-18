# Auth.py - credentials and datastructures for authenticating users through
# third party accounts. So far we have Google via the Oauth2 protocol. 
#
# Copyright (c) 2013, Christopher Patton, Nassib Nassar 
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

from flask_oauth import OAuth
import os, stat, configparser

## Local PostgreSQL server configuration ## 

##
# Verify permissions of configuration file. 
#
def accessible_by_group_or_world(file):
  st = os.stat(file)
  return bool( st.st_mode & (stat.S_IRWXG | stat.S_IRWXO) )

## 
# Get Local db configuration from $HOME/.seaice 
# or file specified. 
#
def get_config(config_file = os.environ['HOME'] + '/.seaice'):
  if accessible_by_group_or_world(config_file):
    print ('error: config file ' + config_file +
      ' has group or world ' +
      'access; permissions should be set to u=rw')
    sys.exit(1)
  config = configparser.RawConfigParser()
  config.read(config_file)
  return config

## Google authentication (Oauth) ##

oauth = OAuth()

##
# Google redirect URI 
# @REDIRECT_URI
REDIRECT_URI = '/authorized' # TODO Change to '/authorized/google' (also on 
                             # code.google.com/apis/console). 
##
# These credentials are for localhost testing. The actual values for 
# the SeaIce dictionary deployed to seaice.herokuapp.com are not 
# published. 
# @GOOGLE_CLIENT_ID
# @GOOGLE_CLIENT_SECRET
GOOGLE_CLIENT_ID = '173499658661-cissqtglckjctv5rgh9a6mguln721rqr.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = '_Wmt-6SZXRMeaJVFXkuRH-rm'

##
# Google authentication. 
#
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
