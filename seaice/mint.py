# Contributed by Greg Janee

# XXX TODO Delete persistent identifier on removal of term. 


import re
import os
import urllib
import urllib2
import ssl
import auth
import sys
import time

REALM = "yamz"
USERNAME = "yamz"

# Be careful to use these URLs only in "production" yamz,
# as the identifiers they create are meant to last forever.
REAL_MINTER_URL = "https://n2t.net/a/yamz/m/ark/99152/h"
REAL_BINDER_URL = "https://n2t.net/a/yamz/b"

# The identifiers created with these URLs are meant to be thrown away.
TEST_MINTER_URL = "https://n2t.net/a/yamz/m/ark/99152/fk2"
TEST_BINDER_URL = "https://n2t.net/a/yamz_test/b"

# FIXME Location for `minter_password` is needlessly hardcoded. 
deploy = 'heroku' 
CONFIG = auth.get_config('.seaice_auth')
if CONFIG.has_option(deploy, 'minter_password'):
    PASSWORD = CONFIG.get(deploy, 'minter_password')
else:
    PASSWORD = os.environ.get('MINTER_PASSWORD')

TARGET_URL_TEMPLATE = "http://yamz.net/term/concept=%s"

_opener = None
_minter = None
_binder = None

def minderOpener (prod_mode):
  # Note that exceptions are not handled here but passed to the caller.
  ctxt = ssl.create_default_context()
  ctxt.check_hostname = False
  ctxt.verify_mode = ssl.CERT_NONE

  global _opener, _minter, _binder
  if not _minter:
    if prod_mode == "enable":
      _minter = REAL_MINTER_URL
      _binder = REAL_BINDER_URL
    else:
      _minter = TEST_MINTER_URL
      _binder = TEST_BINDER_URL
  if not _opener:
    m = urllib2.HTTPPasswordMgr()
    m.add_password(REALM, _minter, USERNAME, PASSWORD)
    m.add_password(REALM, _binder, USERNAME, PASSWORD)
    _opener = urllib2.build_opener(
      urllib2.HTTPSHandler(debuglevel=0, context=ctxt),
      urllib2.HTTPBasicAuthHandler(m))
    _opener.addheaders = [("Content-Type", "text/plain")]
    return _opener

def mintArkIdentifier (prod_mode):
  # Returns an ARK identifier as a string (e.g., "ark:/99152/h4232").
  global _opener, _minter
  if not _opener: 
    _opener = minderOpener(prod_mode)
  c = None
  try:
    c = _opener.open(_minter + "?mint%201")
    r = c.readlines()
    assert len(r) == 3 and r[0].startswith("s:") and r[1] == "nog-status: 0\n"
    arkId = r[0][3:].strip()
    assert re.match("99152/[a-z]+\d+$", arkId)
    arkId = "ark:/" + arkId
  finally:
    if c: c.close()
  return arkId
 
enc_pat = re.compile("%|[^!-~]")	# encode all non-visible ascii
def _encode (s):		# ^HH encodes chars (for egg :hx)
  if len(s) == 0:
    return '""'			# empty string must be explicit
  return enc_pat.sub(lambda c: "^%02X" % ord(c.group(0)), s.encode("UTF-8"))

def bindArkIdentifier (arkId, prod_mode, who, what, peek):
  # Returns the identifier passed in as a string.
  global _opener, _binder
  if not _opener: 
    _opener = minderOpener(prod_mode)
  # compute our own, since caller often only knows the string 'now()'
  when = time.strftime("%Y.%m.%d_%H:%M:%S", time.gmtime())	# TEMPER-style
  c = None
  try:
    concept_id = arkId.split('/')[-1]
    op = ':hx ' + arkId + '.set'	# all our bind operations start this way
    d = ("%s _t " + TARGET_URL_TEMPLATE + "\n") % (op, concept_id)
    d += "%s how %s\n" % (op, "term")		# metadata/resource type
    d += "%s who %s\n" % (op, _encode(who))	# term label/string
    d += "%s what %s\n" % (op, _encode(what))	# definition
    d += "%s when %s\n" % (op, _encode(when))	# created
    d += "%s peek %s\n" % (op, _encode(peek))	# examples

    c = _opener.open(_binder + "?-", d)
    r = c.readlines()
    assert len(r) == 2 and r[0] == "egg-status: 0\n"
  finally:
    if c: c.close()
  return arkId

_resolver_base = 'http://n2t.net/'
_resolver_base_len = len(_resolver_base)

def ark2pid (ark):
  return _resolver_base + ark

def pid2ark (pid):
  return pid[_resolver_base_len:]

def create_persistent_id (prod_mode, who, what, peek):
  arkId = mintArkIdentifier(prod_mode)
  bindArkIdentifier(arkId, prod_mode, who, what, peek)
  return ark2pid(arkId)
  #return 'http://n2t.net/' + arkId

