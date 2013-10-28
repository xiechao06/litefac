# -*- coding: utf-8 -*-
"""
"""

import os
import sys
import subprocess
import tempfile

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print "usage: python set_blt_as_service.py [work_env_dir|--undo]"
        exit(-1)   

    if sys.argv[1] == "--undo":
        subprocess.call(["sudo", "rm", "/etc/init/lite-mms-blt"])
        subprocess.call(["sudo", "rm", "/etc/init.d/lite-mms-blt"])
        subprocess.call(["sudo", "service", "lite-mms-blt", "restart"])
    else:
        work_env_dir = os.path.abspath(sys.argv[1])
        init_script_fpath = os.path.join(sys.prefix, "share/lite-mms/lite-mms-blt")

        if not os.path.exists(init_script_fpath):
            print "Error: " + init_script_fpath + " doesn't exist"
            exit(-1)

        with file(init_script_fpath) as init_script_fd:
            s = init_script_fd.read()
            if os.environ.has_key("VIRTUAL_ENV"):
                s = s.replace("${EXEC_VIRTUAL_ENV_ACTIVATE}", 
                          ". " + os.path.join(os.environ["VIRTUAL_ENV"] + "/bin/activate"))
            else:
                s = s.replace("${EXEC_VIRTUAL_ENV_ACTIVATE}", "")
            s = s.replace("${WORK_ENV_DIR}", work_env_dir)
            tmp_fd, tmp_fname = tempfile.mkstemp()
            os.close(tmp_fd)
            with open(tmp_fname, "w") as f:
                f.write(s)
            subprocess.call(["sudo", "cp", tmp_fname, "/etc/init/lite-mms-blt"]) 
            os.unlink(tmp_fname)
            subprocess.call(["sudo", "ln", "-sf", "/etc/init/lite-mms-blt", "/etc/init.d/lite-mms-blt"])
            subprocess.call(["sudo", "chmod", "u+x", "/etc/init.d/lite-mms-blt"])
            subprocess.call(["sudo", "service", "lite-mms-blt", "restart"])
    

