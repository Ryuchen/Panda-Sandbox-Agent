#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ========================================================
# @Author: Ryuchen
# @Time: 2019/12/10-13:35
# @Site: https://ryuchen.github.io
# @Contact: chenhaom1993@hotmail.com
# @Copyright: Copyright (C) 2019-2020 Panda-Sandbox-Agent.
# ========================================================
"""
The global agent.py running on multi-platform

This agent main to communication with outside result server to execute malware behavior
"""
import os
import sys
import argparse
import platform

from io import StringIO

from flask import Flask
from flask import jsonify
from flask import make_response

from main.version import AGENT_VERSION

# Create the in-memory "file"
temp_stdout = StringIO()
temp_stderr = StringIO()

# Replace default stdout (terminal) with our stream
sys.stdout = temp_stdout
sys.stderr = temp_stderr


app = Flask(__name__)


@app.route('/')
def get_index():
    msg = jsonify(message="Panda Sandbox Agent", version=AGENT_VERSION, filepath=os.path.abspath(__file__))
    return make_response(msg, 200)


@app.route("/system")
def get_system():
    msg = jsonify(message="System Platform", system=platform.system())
    return make_response(msg, 200)


@app.route("/environ")
def get_environ():
    msg = jsonify(message="Environment variables", environ=dict(os.environ))
    return make_response(msg, 200)


@app.route("/logging")
def get_logging():
    msg = jsonify(message="Panda Sandbox Agent logs",
                  stdout=sys.stdout.getvalue(),
                  stderr=sys.stderr.getvalue())
    return make_response(msg, 200)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("host", nargs="?", default="0.0.0.0")  # By default we should use 0.0.0.0
    parser.add_argument("port", nargs="?", default="63554")
    args = parser.parse_args()

    print("Starting Minimal HTTP Sever at #{0}:{1} ~~~".format(args.host, args.port))

    app.run(host=args.host, port=int(args.port))
