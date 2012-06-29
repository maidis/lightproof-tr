import xml.etree.ElementTree as ET
import string
import re

tree = ET.parse("grammar.xml")

def poscorr(s, markerpos): # increase group positions in the replacement string, if needed
  if markerpos:
    return re.sub(r"(?<=\\)([%d-9])" % markerpos, lambda r: str(int(r.group(0)) + 1), s)
  return s
  
def cleaner(a):
  a = ' '.join(a)
  a = string.replace(a," ,",",")
  a = string.replace(a," .",".")
  a = string.replace(a," ???","")
  a = string.replace(a," (???)","")
  a = string.replace(a,"??? ","")
  return a

for rule in tree.iter("rule"):
  pattern = []
  for markertrue in rule.findall('pattern/marker'):
      if markertrue.tag == "marker":
	continue
#  if rule.find('pattern/marker') is None:  # check only rules with <marker>
#    continue
  markerpos = 0
  n = 0
  for item in rule.findall('pattern/*'):
    n += 1
    if item.attrib and item.attrib.keys() != ["regexp"]: 
      pattern = []
      break
    if item.tag == 'marker':
	markerpos = n
	for i in item.iter('token'):
	    pattern += ["%s" % (i.text or "???")]
	pattern[n - 1] = "(" + pattern[n - 1]
	pattern[-1] += ')'
    else:
    	pattern += ["%s" % (item.text or "???")]
  if pattern:
    try:
      print cleaner(pattern), "-%d>" % markerpos, poscorr(rule.find('message').find('suggestion').text, markerpos), "# Did you mean?"
    except:
      print "# Did you mean?"

