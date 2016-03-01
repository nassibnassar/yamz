# Contributed by Greg Janee

# XXX TODO Delete persistent identifier on removal of term. 


import re
import os
import urllib
import urllib2
import ssl
import auth

REALM = "yamz"
USERNAME = "yamz"

REAL_MINTER_URL = "https://n2t.net/a/yamz/m/ark/99152/h"
REAL_BINDER_URL = "https://n2t.net/a/yamz/b"

TEST_MINTER_URL = "https://n2t.net/a/yamz/m/ark/99152/fk2"
TEST_BINDER_URL = "https://n2t.net/a/yamz_test/b"

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

def mintArkIdentifier (prod_mode):
  # Returns an ARK identifier as a string (e.g., "ark:/99152/h4232").
  # Note that exceptions are not handled here but passed to the caller.
  global _opener
  if not _opener:
    m = urllib2.HTTPPasswordMgr()
    if prod_mode == "enable":
      minter = REAL_MINTER_URL
      binder = REAL_BINDER_URL
    else:
      minter = TEST_MINTER_URL
      binder = TEST_BINDER_URL
    m.add_password(REALM, minter, USERNAME, PASSWORD)
    m.add_password(REALM, binder, USERNAME, PASSWORD)
    _opener = urllib2.build_opener(
      urllib2.HTTPSHandler(debuglevel=0, context=ctx),
      urllib2.HTTPBasicAuthHandler(m))
  c = None
  try:
    c = _opener.open(minter + "?mint%201")
    r = c.readlines()
    assert len(r) == 3 and r[0].startswith("s:") and r[1] == "nog-status: 0\n"
    arkId = r[0][3:].strip()
    assert re.match("99152/[a-z]+\d+$", arkId)
    arkId = "ark:/" + arkId
  finally:
    if c: c.close()
  c = None
  try:
    concept_id = arkId.split('/')[-1]
    c = _opener.open(binder + "?" +\
      urllib.quote(("%s.set _t " + TARGET_URL_TEMPLATE) % (arkId, concept_id)))
    r = c.readlines()
    assert len(r) == 2 and r[0] == "egg-status: 0\n"
  finally:
    if c: c.close()
  return arkId

# XXX change this to indicate that fake ids don't resolve
def mint_persistent_id(prod_mode):
    return 'http://n2t.net/' + mintArkIdentifier(prod_mode)

