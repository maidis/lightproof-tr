# -*- encoding: UTF-8 -*-
import sys, os, zipfile, traceback, Dialog
import configparser as cp
import pythonpath.lightproof_compile___implname__
from string import Template

def dist(fn, a):
    a['locales'] = a["locales"].replace("_", "-")
    a['loc'] = str(dict([[i, [i[0:2], i[3:5], ""]] for i in a["locales"].split(" ")]))
    distname = a['implname'] + "-" + a['version'] + '.oxt'
    z = zipfile.ZipFile(distname, mode='w', compression = zipfile.ZIP_DEFLATED)
    f = open(fn + ".dat", 'r', encoding="utf-8")
    code = pythonpath.lightproof_compile___implname__.c(f.read(), a['lang'])
    a["code"] = code["code"]
    a['data'] = code["rules"]

    for i in ["META-INF/manifest.xml", "description.xml", "Linguistic.xcu", "Lightproof.py", \
        "pythonpath/lightproof_handler___implname__.py", "pythonpath/lightproof_impl___implname__.py", \
        "pythonpath/lightproof___implname__.py" ]:
        z.writestr(i.replace("__implname__", a["implname"]), Template(open(i, "r", encoding="utf-8").read()).safe_substitute(a))

    for i in a["extras"].split(","):
        z.writestr(i.strip().replace("../", "").replace("__implname__", a["implname"]), \
        open(fn[:fn.rfind("/")+1] + i.strip()).read())

    try:
        d = open(fn + ".dlg", "r", encoding="utf-8").readlines()
        Dialog.c(a["implname"], d, z, a["lang"])
    except:
        z.writestr("pythonpath/lightproof_opts_%s.py"%a["implname"], "")

if len(sys.argv) == 1:
    print ("""Synopsis: python make.py config_file
eg. python make.py src/en/en.cfg""")
    sys.exit(0)

fArgs = cp.SafeConfigParser()
for i in sys.argv[1:]:
    try:
        fArgs.read(i)
        dist(i[:-4], fArgs._sections['args'])
    except:
        print (traceback.format_exc())
        print ("missing config file or options: " + str(i))
        sys.exit(0)
