# -*- coding: utf-8 -*-
"""
BRIEF
    将portal设置为系统服务，web server目前仅仅支持nginx。不要利用sudo来执行此
    脚本
SYNOPSIS
    python set_portal_as_service.py [options]
OPTIONS
    -h 
        show this help
    -e <work environment directory>
        the service will read the config file under this directory
    -p <port>
    --undo 
"""
from getopt import getopt
import sys
import os
import subprocess

if __name__ == "__main__":
    
    opts, _ = getopt(sys.argv[1:], "he:p:", "undo")

    undo = False
    for o, v in opts:
        if o == "-e":
            work_env_dir = v
            work_env_dir = os.path.abspath(work_env_dir)
        elif o == "-p":
            port = int(v)
        elif o == "-h":
            print __doc__
            exit(1)
        elif o == "--undo":
            undo = True
        else:
            print "unknown option: " + v
            print __doc__
            exit(1)

    if not undo:
        try:
            work_env_dir
            port
        except NameError:
            print __doc__
            exit(1)
        server_fpath = os.path.join(sys.prefix, "share/lite-mms/lite-mms")
        if not os.path.exists(server_fpath):
            print "Error: " + server_fpath + " doesn't exist"
            exit(1)

        # install as uwsgi app
        subprocess.call(["sudo", "./add_uwsgi_app.sh"])
        subprocess.call(["sudo", "service", "uwsgi", "restart", "lite-mms"])
    
    # add nginx site
        with open(server_fpath) as server_fd:
            s = server_fd.read()
            s = s.replace("${PORT}", str(port))
            s = s.replace("${PYHOME}", sys.prefix)
            s = s.replace("${PYENV}", work_env_dir)
            import litefac
            s = s.replace("${STATIC_DIR}", os.path.join(litefac.__path__[0], "static"))
            import tempfile
            tmp_fd, tmp_fname = tempfile.mkstemp()
            os.close(tmp_fd)
            with open(tmp_fname, "w") as tmp_fd:
                tmp_fd.write(s) 
            subprocess.call(["sudo", "mv", tmp_fname, "/etc/nginx/sites-available/lite-mms"])
            subprocess.call(["sudo", "ln", "-sf", "/etc/nginx/sites-available/lite-mms",
                             "/etc/nginx/sites-enabled/lite-mms"])
            subprocess.call(["sudo", "service", "nginx", "restart"])
    else:
        subprocess.call(["sudo", "rm", "/etc/nginx/sites-available/lite-mms"])
        subprocess.call(["sudo", "rm", "/etc/nginx/sites-enabled/lite-mms"])
        subprocess.call(["sudo", "service", "nginx", "restart"])
        subprocess.call(["sudo", "rm", "/etc/uwsgi/apps-available/lite-mms.xml"])
        subprocess.call(["sudo", "rm", "/etc/uwsgi/apps-enabled/lite-mms.xml"])
        subprocess.call(["sudo", "service", "uwsgi", "stop", "lite-mms"])
