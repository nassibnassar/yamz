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

import sys, json, time, re, datetime

## TODO find a better home for these scripts ##

js_confirmRemoveTerm = """
  function ConfirmRemoveTerm(id) {
    var r=window.confirm("Are you sure you want to delete term #" + id + "?");
    if (r==true) { 
      x=id; 
      var form = document.createElement("form");
      form.setAttribute("method", "post");
      form.setAttribute("action", "/term=" + id + "/remove");
      field = document.createElement("input");
      field.setAttribute("name", "id");
      field.setAttribute("value", id);
      form.appendChild(field);
      document.body.appendChild(form); 
      form.submit();
    } else { x="nil"; } } """

js_confirmRemoveComment = """
  function ConfirmRemoveComment(id) {
    var r=window.confirm("Are you sure you want to your comment?");
    if (r==true) { 
      x=id; 
      var form = document.createElement("form");
      form.setAttribute("method", "post");
      form.setAttribute("action", "/comment=" + id + "/remove");
      field = document.createElement("input");
      field.setAttribute("name", "id");
      field.setAttribute("value", id);
      form.appendChild(field);
      document.body.appendChild(form); 
      form.submit();
    } else { x="nil"; } } """

js_termAction = """
  function TermAction(id, v) {
    var form = document.createElement("form"); 
    form.setAttribute("method", "post");
    if (v == "up" || v == "down") {
      var action = "vote"; 
    } else {
      var action = "track"; 
    }
    form.setAttribute("action", "/term=" + id + "/" + action); 
    field = document.createElement("input"); 
    field.setAttribute("name", "action")
    field.setAttribute("value", v);
    form.appendChild(field);
    document.body.appendChild(form);
    form.submit(); 
  } """

colorOf = { 'vernacular' : '#FFFF66', 
            'stable' : '#339933', 
            'deprecated' : '#E8E8E8' }

## Pretty prints ##

##
# Print date (to string). If a small amount of time 
# has elapsed, then give this info. TODO
#
def printPrettyDate(t, gmt=False): 
  return "%s/%s/%s %s:%02d" % (t.day, t.month, t.year, t.hour, t.minute)#, t.tzname)
  
##
# Write table rows in JSON format to 'fd'. 
#
def printAsJSObject(rows, fd = sys.stdout):
  for row in rows:
    for (col, value) in row.iteritems(): 
      if type(value) == datetime.datetime:
        row[col] = str(value)
  print >>fd, json.dumps(rows, sort_keys=True, indent=2, separators=(',', ': '))

##
# Print a nice paragraph. 
#
def printParagraph(db_con, text, leftMargin=8, width=60): 
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
    
##
# Print Terms table rows to the terminal. 
#
def printTermsPretty(db_con, rows):
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

##
# Print a list of terms with HTML links to term pages (to string)
#
def printTermsAsLinks(rows): 
  string = ""
  for row in rows: 
    string += '<li><a href="/term=%d">%s</a></li>' % (row['id'], row['term_string'])
  return string

##
# Print Term in HTML (to string) 
# 
def printTermAsHTML(db_con, row, owner_id=0): 
  vote = db_con.getVote(0 if not owner_id else owner_id, row['id'])
  string = '<script>' + js_confirmRemoveTerm + js_termAction + '</script>'

  # Voting
  string += '<table>' 
  string += "  <tr><td width=15% rowspan=4 align=center valign=top>"
  string += '    <a id="voteUp" title="+1" href="#up" onclick="return TermAction(%s, \'up\');">' % row['id']
  string += '     <img src="/static/img/%s.png"></a><br>' % ('up_set' if vote == 1 else 'up')
  string += '    <h4>%s</h4>' % (row['score'])
  string += '    <a id="voteDown" title="-1" href="#down" onclick="return TermAction(%s, \'down\');">' % row['id']
  string += '     <img src="/static/img/%s.png"></a><br>' % ('down_set' if vote == -1 else 'down')
  
  string += '    <br><a id="star" title="Track this term" href="#star"' + \
            '     onclick="return TermAction({1}, \'{0}\');">[{0}]</a><br> '.format(
             ("unstar" if vote != None else "star"), row['id'])
  string += "  </td></tr>"
  
  # Name/Class
  string += "  <tr>"
  string += "    <td valign=top width=8%><i>Term:</i></td>"
  string += "    <td valign=top width=25%><font size=\"3\"><strong>{0}</strong></font><td>".format(row['term_string']) 
  string += "    <td valign=top width=5%><i>Class:</i></td>"
  string += '    <td valign=top width=16%>&nbsp'
  string += '      <font style="background-color:{2}">&nbsp;{0}&nbsp;</font> <i>&nbsp({1}%)</i></td>'.format(
              row['class'], int(100 * row['consensus']), colorOf[row['class']])

  # Created/modified/Owner 
  string += "    <td valign=top width=20% rowspan=3>"
  string += "      <nobr><i>Created</i> %s</nobr><br>" % printPrettyDate(row['created'])
  string += "      <nobr><i>Last modified</i> %s</nobr><br>" % printPrettyDate(row['modified'])
  string += "      <nobr><i>Contributed by</i> %s</nobr><br>"% db_con.getUserNameById(row['owner_id'], full=True)
  if owner_id == row['owner_id']:
    string += "    <br><a href=\"/term=%d/edit\">[edit]</a>" % row['id']
    string += """  <a id="removeTerm" title="Click to delete term" href="#"
                   onclick="return ConfirmRemoveTerm(%s);">[remove]</a>""" % row['id']
  string += "    </td>"
  string += "  </tr>"

  # Definition/Examples
  string += "  <tr>"
  string += "    <td valign=top><i>Definition:</i></td>"
  string += "    <td colspan=4 valign=top><font size=\"3\"> %s</font></td>" % row['definition']
  string += "  </tr>"
  string += "  <tr>"
  string += "    <td valign=top><i>Examples:</i></td>"
  string += "    <td colspan=4 valign=top><font size=\"3\"> %s</font></td>" % row['examples']
  string += "  </tr>"
  string += "</table>"
  return string


##
# Print Terms table rows as an HTML table (to string) 
# 
def printTermsAsHTML(db_con, rows, owner_id=0): 
  string = '<script>' + js_confirmRemoveTerm + '</script><table>'
  for row in rows:
    string += "  <tr>"
    string += "    <td valign=top width=75%><i>Term:</i>"
    string += "     <font size=\"3\"><strong>{0}</strong></font>".format(row['term_string'])
    string += "      <a href=\"/term=%d\">[view]</a>" % row['id']
    if owner_id == row['owner_id']:
      string += "    <a href=\"/term=%d/edit\">[edit]</a>" % row['id']
      string += """  <a id="removeTerm" title="Click to delete term" href="#"
                     onclick="return ConfirmRemoveTerm(%s);">[remove]</a>""" % row['id']
    string += '      &nbsp<i>Class:</i>&nbsp<font style="background-color:{2}">&nbsp;{0}&nbsp;</font> <i>&nbsp({1}%)</i>'.format(
                 row['class'], int(100 * row['consensus']), colorOf[row['class']])
    string += "    </td>" 
    string += "    <td valign=top rowspan=2>"
    string += "      <nobr><i>Created</i> %s</nobr><br>" % printPrettyDate(row['created'])
    string += "      <nobr><i>Last modified</i> %s</nobr><br>" % printPrettyDate(row['modified'])
    string += "      <nobr><i>Contributed by</i> %s</nobr><br>" % db_con.getUserNameById(row['owner_id'], full=True)
    string += "    </td>"
    string += "  </tr>"
    string += "  <tr>"
    string += "    <td valign=top>"
    string += "     <i>Definition:</i>&nbsp;<font size=\"3\"> %s</font>&nbsp;" % row['definition']
    string += "     <i>Examples:</i>&nbsp;<font size=\"3\"> %s</font></td>" % row['examples']
    string += "  </tr>"
    string += "  <tr height=16><td></td></tr>"
  string += "</table>"
  return string

##
# Print Terms table rows as abbreviated HTML table (to string)
#
def printTermsAsBriefHTML(db_con, rows, owner_id=0): 
  string =  '<table width=70%>'
  string += '''<tr style="background-color:#E8E8E8"><td>Term</td>
                  <td>Votes</td><td>Consensus</td><td>Class</td><td>Contributed by</td>
                  <td>Last modified</td></tr>'''
  for row in rows:
    string += '''<tr><td><a href=/term={5}>{0}</a></td><td>{1}</td><td>{2}%</td>
                     <td><font style="background-color:{6}">&nbsp;{3}&nbsp;</font></td>
                     <td>{4}</td>
                     <td>{7}</tr>'''.format(
      row['term_string'], row['score'], int(100 * row['consensus']), row['class'], 
      db_con.getUserNameById(row['owner_id'], full=True), row['id'], colorOf[row['class']],
      printPrettyDate(row['modified']))
  string += "</table>"
  return string
  
##
# Print Comments table rows as an HTML table (to string)
# 
def printCommentsAsHTML(db_con, rows, owner_id=0): 
  string = '<script>' + js_confirmRemoveComment + '</script><table>'
  for row in rows:
    string += "<tr>"
    string += "  <td align=left valign=top width=70%>{0}".format(row['comment_string'])
    if owner_id == row['owner_id']:
      string += " <nobr><a href=\"/comment=%d/edit\">[edit]</a>" % row['id']
      string += """ <a id="removeComment" title="Click to remove this comment" href="#"
                    onclick="return ConfirmRemoveComment(%s);">[remove]</a></nobr>""" % row['id']
    string += "  </td>"
    string += "  <td align=right valign=top><font color=\"#B8B8B8\"><i>Submitted {0}<br>by {1}</i></font></td>".format(
      printPrettyDate(row['created']), db_con.getUserNameById(row['owner_id']))
    string += "</tr>" 
    string += "</tr><tr height=16><td></td></tr>"
  string += "</table>"
  return string