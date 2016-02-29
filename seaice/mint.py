# Contributed by Greg Janee

# TODO Delete persistent identifier on removal of term. 


import re
import os
import urllib
import urllib2
import ssl
import auth

#MINTER_URL = "https://n2t-pre.cdlib.org/a/yamz/m/ark/99152/h"
#BINDER_URL = "https://n2t-pre.cdlib.org/a/yamz/b"
MINTER_URL = "https://n2t.net/a/yamz/m/ark/99152/fk2"
BINDER_URL = "https://n2t.net/a/yamz_test/b"
REALM = "yamz"
USERNAME = "yamz"

# FIXME Location for `minter_password` is needlessly hardcoded. 
deploy = 'heroku' 
CONFIG = auth.get_config('.seaice_auth')
if CONFIG.has_option(deploy, 'minter_password'):
    PASSWORD = CONFIG.get(deploy, 'minter_password')
else:
    PASSWORD = os.environ.get('MINTER_PASSWORD')

# xxx change this host to match our actual hostname
# xxx use non-real minter/binder for ANY non-"yamz" host
# xxx turn off certificate check
TARGET_URL_TEMPLATE = "http://yamz.net/term/concept=%s"

_opener = None

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def mintArkIdentifier ():
  # Returns an ARK identifier as a string (e.g., "ark:/99152/h4232").
  # Note that exceptions are not handled here but passed to the caller.
  global _opener
  if not _opener:
    m = urllib2.HTTPPasswordMgr()
    m.add_password(REALM, MINTER_URL, USERNAME, PASSWORD)
    m.add_password(REALM, BINDER_URL, USERNAME, PASSWORD)
    _opener = urllib2.build_opener(
      urllib2.HTTPSHandler(debuglevel=0, context=ctx),
      urllib2.HTTPBasicAuthHandler(m))
  c = None
  try:
    c = _opener.open(MINTER_URL + "?mint%201")
    r = c.readlines()
    assert len(r) == 3 and r[0].startswith("id:") and r[1] == "nog-status: 0\n"
    arkId = r[0][3:].strip()
    assert re.match("99152/h\d+$", arkId)
    arkId = "ark:/" + arkId
  finally:
    if c: c.close()
  c = None
  try:
    concept_id = arkId.split('/')[-1]
    c = _opener.open(BINDER_URL + "?" +\
      urllib.quote(("%s.set _t " + TARGET_URL_TEMPLATE) % (arkId, concept_id)))
    r = c.readlines()
    assert len(r) == 2 and r[0] == "egg-status: 0\n"
  finally:
    if c: c.close()
  return arkId

def mint_persistent_id():
    return 'http://n2t.net/' + mintArkIdentifier()

