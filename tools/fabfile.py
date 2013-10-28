#-*- coding:utf-8 -*-
from fabric.api import *

env.hosts = ['localhost']
env.passwords = {"localhost":"xy1234"}
env.user = "xy"

def deploy():
    home_dir = "/srv/www/lite-mms/"
    lite_mms_dir = "/srv/www/lite-mms/git-lite-mms"
    python_home_dir = "/srv/www/lite-mms/env/bin/activate"
    with cd(lite_mms_dir):
        sudo('cd lite-mms && git pull origin master', user="www-data")
        with prefix('source %s' % python_home_dir):
            run('python -c "import sys; print sys.path"')
            sudo('cd lite-mms && pip install -r requirements.txt && python setup.py install', user='www-data')
    sudo('service uwsgi restart')
    sudo('service nginx restart')
