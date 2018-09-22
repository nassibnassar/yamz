# Contributed by Greg Janee

import re
import os
import urllib
import ssl
from . import auth
import sys
import time

REALM = "yamz"
USERNAME = "yamz"

# Be careful to use these URLs only in "production" yamz,
# as the identifiers they create are meant to last forever.
REAL_MINTER_URL = "https://n2t.net/a/yamz/m/ark/99152/h"
REAL_BINDER_URL = "https://n2t.net/a/yamz/b"

# yyy to do: should we have a test mode in production (ids not meant to
#     be persistent)
# The identifiers created with these URLs are meant to be thrown away.
TEST_MINTER_URL = "https://n2t.net/a/yamz/m/ark/99152/fk2"
TEST_BINDER_URL = "https://n2t.net/a/yamz_test/b"

# FIXME Location for minter_password is needlessly hardcoded. 
deploy = 'heroku' 
CONFIG = auth.get_config('.seaice_auth')
PASSWORD = os.environ.get('MINTER_PASSWORD')
if not PASSWORD and CONFIG.has_option(deploy, 'minter_password'):
  PASSWORD = CONFIG.get(deploy, 'minter_password')

TARGET_URL_TEMPLATE = "http://yamz.net/term/concept=%s"

_opener = None
_minter = None
_binder = None

def minderOpener (prod_mode):
  ctxt = None
  # Note that exceptions are not handled here but passed to the caller.
  ctxt = ssl.create_default_context()
  ctxt.check_hostname = False
  ctxt.verify_mode = ssl.CERT_NONE

  # Note that exceptions are not handled here but passed to the caller.
  global _opener, _minter, _binder
  if not _minter:
    if prod_mode:
      _minter = REAL_MINTER_URL
      _binder = REAL_BINDER_URL
    else:
      _minter = TEST_MINTER_URL
      _binder = TEST_BINDER_URL
  if not _opener:
    m = urllib.request.HTTPPasswordMgr()
    m.add_password(REALM, _minter, USERNAME, PASSWORD)
    m.add_password(REALM, _binder, USERNAME, PASSWORD)
    _opener = urllib.request.build_opener(
      urllib.request.HTTPSHandler(debuglevel=0, context=ctxt),
      urllib.request.HTTPBasicAuthHandler(m))

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
    # xxx catch assert exceptions
    assert len(r) == 3 and r[0].startswith("s:") and r[1] == "nog-status: 0\n"
    arkId = r[0][3:].strip()
    assert re.match("99152/[a-z]+\d+$", arkId)
    arkId = "ark:/" + arkId
  finally:
    if c: c.close()
  return arkId
 
# encode quotes and non-visible ascii
enc_pat = re.compile("""[%'"]|[^!-~]""")
def _encode (s):		# ^HH encodes chars (for egg :hx)
  if len(s) == 0:
    return '""'			# empty string must be explicit
  return enc_pat.sub(lambda c: "^%02X" % ord(c.group(0)), s.encode("UTF-8"))
  # s.encode('UTF-8', 'ignore'))

# XXX redo encoding to use more robust (less prone to shell quotes) @ technique
def bindArkIdentifier (arkId, prod_mode, who, what, peek):
  # Returns the identifier passed in as a string.
  global _opener, _binder
  if not _opener: 
    _opener = minderOpener(prod_mode)
  # compute our own, since caller often only knows the string 'now()'
  when = time.strftime("%Y.%m.%d_%H:%M:%S", time.gmtime())	# TEMPER-style
  c = None
  try:
    concept_id = arkId.split('/')[-1]		# xxx why concept_id here?
    op = ':hx ' + arkId + '.set'	# all our bind operations start this way
    d = ("%s _t " + TARGET_URL_TEMPLATE + "\n") % (op, concept_id)
    d += "%s how %s\n" % (op, "term")		# metadata/resource type
    d += "%s who %s\n" % (op, _encode(who))	# term label/string
    d += "%s what %s\n" % (op, _encode(what))	# definition
    d += "%s when %s\n" % (op, _encode(when))	# created
    d += "%s peek %s\n" % (op, _encode(peek))	# examples

    c = _opener.open(_binder + "?-", d)
    r = c.readlines()
    if len(r) != 2 or r[0] != "egg-status: 0\n":
      print >>sys.stderr, "error: bad binder return (%s), input=%s" % (
        r[0], d)

  finally:
    if c: c.close()
  return arkId

def removeArkIdentifier (arkId, prod_mode):
  # Returns the identifier passed in as a string.
  global _opener, _binder
  if not _opener: 
    _opener = minderOpener(prod_mode)
  c = None
  try:
    d = ':hx ' + arkId + ".purge\n"
    c = _opener.open(_binder + "?-", d)
    r = c.readlines()
    if len(r) != 2 or r[0] != "egg-status: 0\n":
      print >>sys.stderr, "error: purge: bad binder return (%s), input=%s" % (
        r[0], d)

  finally:
    if c: c.close()
  return arkId

_resolver_base = 'http://n2t.net/'
_resolver_base_len = len(_resolver_base)

def ark2pid (ark):
  return _resolver_base + ark		# add URL base

def pid2ark (pid):
  return pid[_resolver_base_len:]	# remove URL base

def create_persistent_id (prod_mode):
  arkId = mintArkIdentifier(prod_mode)
  return ark2pid(arkId)

def bind_persistent_id (prod_mode, arkId, who, what, peek):
  bindArkIdentifier(arkId, prod_mode, who, what, peek)
  return ark2pid(arkId)

# yyy recyle id after suitable waiting period? 
def remove_persistent_id (prod_mode, arkId):
  arkId = removeArkIdentifier(arkId, prod_mode)
  return ark2pid(arkId)			# yyy better return value?

