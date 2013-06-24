import sys, json, time, re

## Pretty prints ##

def printPrettyDate(t, gmt=False): 
#
# Print date (to string). If a small amount of time 
# has elapsed, then give this info. TODO
#

  return "%s/%s/%s %s:%s %s" % (t.day, t.month, t.year, t.hour, t.minute, t.tzname)
  


def printAsJSObject(db_con, rows, fd = sys.stdout):
#
# Write table rows in JSON format to 'fd'. 
#
  for row in rows:
    row['modified'] = str(row['modified'])
    row['created'] = str(row['created'])
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
    
def printPretty(db_con, rows):
#
# Print table rows to the terminal. 
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

def printAsHTML(db_con, rows, owner_id=0): 
#
# Print table rows as an HTML table (to string) 
# 
  script = """
  <script>function ConfirmRemove(id) {
    var r=window.confirm("Are you sure you want to delete term #" + id + "?");
    if (r==true) { 
      x=id; 
      var form = document.createElement("form");
      form.setAttribute("method", "post");
      form.setAttribute("action", "remove");
      field = document.createElement("input");
      field.setAttribute("name", "id");
      field.setAttribute("value", id);
      form.appendChild(field);
      document.body.appendChild(form); 
      form.submit();
    } else { x="nil"; } } </script>"""
  string = script + "<table colpadding=16>" 
  for row in rows:
    string += "<tr>"
    string += "  <td valign=top width=%s><i>Term:</i> <strong>%s</strong> (#%d)</td>" % (
      repr("70%"), row['term_string'], row['id'])
    string += "  <td valign=top><i>created</i>: %s</td>" % printPrettyDate(row['created'])
    string += "</tr><tr>"
    string += "  <td valign=top><i>score</i>: %s</td>" % row['score']
    string += "  <td valign=top><i>Last modified</i>: %s</td>" % printPrettyDate(row['modified'])
    string += "</tr><tr>"
    string += "  <td valign=top><i>definition:</i> %s</td>" % row['definition']
    string += "  <td valign=top><i>Ownership:</i> %s"% db_con.getUserNameById(row['owner_id'])
    if owner_id == row['owner_id']:
      string += " <a href=\"/edit=%d\">[edit]</a>" % row['id']
      string += """ <a id="myLink" title="Click to delete term" href="#"
                    onclick="return ConfirmRemove(%s);">[remove]</a><br>""" % row['id']
    string += "</td></tr><tr height=16><td></td></tr>"
  string += "</table>"
  return string
  

