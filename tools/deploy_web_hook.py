#! /usr/bin/env python
# -*- coding: UTF-8 -*-
"""
A WEB HOOK for github
SYNOPSIS
    python deploy_web_hook.py [options]
OPTIONS
    -h 
        show this help
    -p  <port>
        the port of server runs on
    -s  <host>
        the ip of the server runs on
    -f  <fabfile>
        the fabfile to execute
"""
import sys
import subprocess
import json
from getopt import getopt
from flask import Flask, request


app = Flask(__name__)

fabfile = "fabfile.py"

@app.route("/deploy", methods=["POST"])
def deploy():
    subprocess.call(["fab", "-f", fabfile, "deploy"])
    return "done"

@app.route("/make-test-data")
def make_test_data():
    # we only deploy when push to origin/master
    subprocess.call(["fab", "-f", fabfile, "make_test_data"])
    return "done"

