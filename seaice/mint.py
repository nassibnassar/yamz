# Contributed by Greg Janee

import re
import urllib
import urllib2
import auth

MINTER_URL = "https://n2t-pre.cdlib.org/a/yamz/m/ark/99152/h"
BINDER_URL = "https://n2t-pre.cdlib.org/a/yamz/b"
REALM = "yamz"
USERNAME = "yamz"
PASSWORD = auth.get_config().get('default', 'minter_password')
TARGET_URL_TEMPLATE = "http://yamz.net/term=%d"

_opener = None

def mintArkIdentifier (id):
  # Takes an internal term identifier as an integer (e.g., 123) and
  # returns an ARK identifier as a string (e.g., "ark:/99152/h4232").
  # Note that exceptions are not handled here but passed to the caller.
  global _opener
  if not _opener:
    m = urllib2.HTTPPasswordMgr()
    m.add_password(REALM, MINTER_URL, USERNAME, PASSWORD)
    m.add_password(REALM, BINDER_URL, USERNAME, PASSWORD)
    _opener = urllib2.build_opener(urllib2.HTTPBasicAuthHandler(m))
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
    c = _opener.open(BINDER_URL + "?" +\
      urllib.quote(("%s.set _t " + TARGET_URL_TEMPLATE) % (arkId, id)))
    r = c.readlines()
    assert len(r) == 2 and r[0] == "egg-status: 0\n"
  finally:
    if c: c.close()
  return arkId

def mint_persistent_id(id):
    return 'http://n2t.net/' + mintArkIdentifier(id)

