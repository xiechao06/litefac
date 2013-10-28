# -*- coding: UTF-8 -*-
"""
this is the default settings, don't insert into your customized settings!
"""

DEBUG = True
SECRET_KEY = "5L)0K%,i.;*i/s("
SECURITY_SALT = "mohnooso"

#DB config
import os.path
import sys
#if os.path.exists("lite_mms.db"):
DBSTR = "sqlite:///lite_mms.db"
#else:
#    DBSTR = "sqlite:///" + os.path.join(sys.prefix, "share/lite-mms/lite_mms.db")
SQLALCHEMY_ECHO = True

UPLOAD_FOLDER = "upload"

BROKER_IP = "192.168.0.161"
BROKER_PORT = 9090
BROKER_TIMEOUT = 2 #单位秒
SQLALCHEMY_ECHO=True
LOCALE = "zh_CN"
BABEL_DEFAULT_LOCALE = "zh_CN"
# the option could be "web", "webservice" or "both"(which stands for both as
# web and webservice)
SERVE_TYPE = "both"

import os
LOG_FILE = os.path.join(os.getcwd(), "lite-mms.log")
REPORT_DIR = 'report_conf'
SENDERS = []
CODERNITY_DATABASE_PATH = "codernity_db"
FLASK_REPORT_SEND_NOTIFICATION = False
