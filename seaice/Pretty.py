# Pretty.py - Pretty formatting for db table rows. There are routines defined
# here for use in a terminal as well as on the web. 
#
# Copyright (c) 2013, Christopher Patton, all rights reserved.
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

import sys, json, time, re

## Pretty prints ##

def printPrettyDate(t, gmt=False): 
#
# Print date (to string). If a small amount of time 
# has elapsed, then give this info. TODO
#

  return "%s/%s/%s %s:%02d" % (t.day, t.month, t.year, t.hour, t.minute)#, t.tzname)
  


def printAsJSObject(rows, fd = sys.stdout):
#
# Write table rows in JSON format to 'fd'. 
#
  for row in rows:
    if row.get('modified'): row['modified'] = str(row['modified'])
    if row.get('created'): row['created'] = str(row['created'])
  print >>fd, json.dumps(rows, sort_keys=True, indent=2, separators=(',', ': '))

def printParagraph(db_con, text, leftMargin=8, width=60): 
#
# Print a nice paragraph. 
#
  lineLength = 0
  print " " * (leftMargin-1), 
  for word in text.split(" "):
    if lineLength < width:
      print word, 
      lineLength += len(word) + 1
    else:
      print "\n" + (" " * (leftMargin-1)),
      lineLength = 0
  print
    
def printTermsPretty(db_con, rows):
#
# Print Terms table rows to the terminal. 
#
  for row in rows:
    print "Term: %-26s id No. %-7d created: %s" % ("%s (%d)" % (row['term_string'], 
                                                                row["score"]),
                                                   row['id'],
                                                   row['created']) 

    print " " * 42 + "Last modified: %s" % row['modified']

    print "\n    definition:\n"    
    printParagraph(db_con, row['definition'])
    
    print "\n    Ownership: %s" % db_con.getUserNameById(row['owner_id'])
    print

def printTermsAsHTML(db_con, rows, owner_id=0): 
#
# Print Terms table rows as an HTML table (to string) 
# TODO think of a better place for this javascript funciton. 
# 
  script = """
  <script>function ConfirmRemoveTerm(id) {
    var r=window.confirm("Are you sure you want to delete term #" + id + "?");
    if (r==true) { 
      x=id; 
      var form = document.createElement("form");
      form.setAttribute("method", "post");
      form.setAttribute("action", "term=" + id + "/remove");
      field = document.createElement("input");
      field.setAttribute("name", "id");
      field.setAttribute("value", id);
      form.appendChild(field);
      document.body.appendChild(form); 
      form.submit();
    } else { x="nil"; } } </script>"""
  string = script + "<table>" 
  for row in rows:
    string += "<tr>"
    string += "  <td valign=top width=%s><i>Term:</i> <strong>%s</strong> " % (
      repr("70%"), row['term_string'])
    if owner_id == row['owner_id']:
      string += " <nobr><a href=\"/term=%d/edit\">[edit]</a>" % row['id']
      string += """ <a id="removeTerm" title="Click to delete term" href="#"
                    onclick="return ConfirmRemoveTerm(%s);">[remove]</a></nobr>""" % row['id']
    string += "  </td>" 
    string += "  <td valign=top><i>created</i>: %s</td>" % printPrettyDate(row['created'])
    string += "</tr><tr>"
    string += "  <td valign=top><i>score</i>: %s</td>" % row['score']
    string += "  <td valign=top><i>Last modified</i>: %s</td>" % printPrettyDate(row['modified'])
    string += "</tr><tr>"
    string += "  <td valign=top><i>definition:</i> %s</td>" % row['definition']
    string += "  <td valign=top><i>Ownership:</i> %s"% db_con.getUserNameById(row['owner_id'])
    string += "</td></tr><tr height=16><td></td></tr>"
  string += "</table>"
  return string
  
def printCommentsAsHTML(db_con, rows, owner_id=0): 
#
# TODO
# 
  script = """
  <script>function ConfirmRemoveComment(id) {
    var r=window.confirm("Are you sure you want to your comment?");
    if (r==true) { 
      x=id; 
      var form = document.createElement("form");
      form.setAttribute("method", "post");
      form.setAttribute("action", "comment=" + id + "/remove");
      field = document.createElement("input");
      field.setAttribute("name", "id");
      field.setAttribute("value", id);
      form.appendChild(field);
      document.body.appendChild(form); 
      form.submit();
    } else { x="nil"; } } </script>"""
  string = script + "<table>" 
  for row in rows: 
    string += "<tr>"
    string += "<td align=left valign=top width=70%>{0}".format(row['comment_string'])
    if owner_id == row['owner_id']:
      string += " <nobr><a href=\"/comment=%d/edit\">[edit]</a>" % row['id']
      string += """ <a id="removeComment" title="Click to remove this comment" href="#"
                    onclick="return ConfirmRemoveComment(%s);">[remove]</a></nobr>""" % row['id']
    string += "</td>"
    string += "<td align=right valign=top><font color=\"#B8B8B8\"><i>Submitted {0}<br>by {1}</i></font></td>".format(
      printPrettyDate(row['created']), db_con.getUserNameById(row['owner_id']))
    string += "</tr>" 
    string += "</td></tr><tr height=16><td></td></tr>"
  string += "</table>"
  return string
