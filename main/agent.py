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
import stat
import shutil
import zipfile
import tempfile
import argparse
import platform
import traceback
import subprocess

from io import StringIO

from flask import Flask
from flask import request
from flask import jsonify
from flask import send_file
from flask import make_response

from main.version import AGENT_VERSION

# Create the in-memory "file"
temp_stdout = StringIO()
temp_stderr = StringIO()

# Replace default stdout (terminal) with our stream
sys.stdout = temp_stdout
sys.stderr = temp_stderr


app = Flask(__name__)
state = {}


@app.route('/')
def get_index():
    msg = jsonify(message="PandaSandbox::Guest Agent", version=AGENT_VERSION)
    return make_response(msg, 200)


@app.route("/system")
def get_system():
    msg = jsonify(message="PandaSandbox::System Platform", system=platform.system())
    return make_response(msg, 200)


@app.route("/environ")
def get_environ():
    msg = jsonify(message="PandaSandbox::Environment variables", environ=dict(os.environ))
    return make_response(msg, 200)


@app.route("/logging")
def get_logging():
    msg = jsonify(message="PandaSandbox::Analysis logs",
                  stdout=sys.stdout.getvalue(),
                  stderr=sys.stderr.getvalue())
    return make_response(msg, 200)


@app.route("/status")
def get_status():
    msg = jsonify(message="PandaSandbox::Analysis status",
                  status=state.get("status"),
                  description=state.get("description"))
    return make_response(msg, 200)


@app.route("/status", methods=["POST"])
def put_status():
    if "status" not in request.form:
        msg = jsonify(message="PandaSandbox::No status has been provided", error_code=400)
        return make_response(msg, 400)

    state["status"] = request.form["status"]
    state["description"] = request.form.get("description")
    msg = jsonify(message="PandaSandbox::Analysis status updated")
    return make_response(msg, 200)


@app.route("/mkdir", methods=["POST"])
def do_mkdir():
    if "dirpath" not in request.form:
        msg = jsonify(message="PandaSandbox::No dirpath has been provided", error_code=400)
        return make_response(msg, 400)

    mode = int(request.form.get("mode", 0o777))

    try:
        os.makedirs(request.form["dirpath"], mode=mode)
    except OSError:
        msg = jsonify(message="PandaSandbox::Error creating directory", error_code=500,
                      traceback=traceback.format_exc())
        return make_response(msg, 500)

    msg = jsonify(message="PandaSandbox::Successfully created directory")
    return make_response(msg, 200)


@app.route("/mktemp", methods=["GET", "POST"])
def do_mktemp():
    suffix = request.form.get("suffix", "")
    prefix = request.form.get("prefix", "tmp")
    dirpath = request.form.get("dirpath")

    try:
        fd, filepath = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dirpath)
    except OSError:
        msg = jsonify(message="PandaSandbox::Error creating temporary file", error_code=500,
                      traceback=traceback.format_exc())
        return make_response(msg, 500)

    os.close(fd)

    msg = jsonify(message="PandaSandbox::Successfully created temporary file", filepath=filepath)
    return make_response(msg, 200)


@app.route("/mkdtemp", methods=["GET", "POST"])
def do_mkdtemp():
    suffix = request.form.get("suffix", "")
    prefix = request.form.get("prefix", "tmp")
    dirpath = request.form.get("dirpath")

    try:
        dirpath = tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=dirpath)
    except OSError:
        msg = jsonify(message="PandaSandbox::Error creating temporary directory", error_code=500,
                      traceback=traceback.format_exc())
        return make_response(msg, 500)

    msg = jsonify(message="PandaSandbox::Successfully created temporary directory", dirpath=dirpath)
    return make_response(msg, 200)


@app.route("/store", methods=["POST"])
def do_store():
    if "filepath" not in request.form:
        msg = jsonify(message="PandaSandbox::No filepath has been provided", error_code=400)
        return make_response(msg, 400)

    if "file" not in request.files:
        msg = jsonify(message="PandaSandbox::No file has been provided", error_code=400)
        return make_response(msg, 400)

    try:
        with open(request.form["filepath"], "wb") as f:
            shutil.copyfileobj(request.files["file"], f, 10 * 1024 * 1024)
    except OSError:
        msg = jsonify(message="PandaSandbox::Error storing file", error_code=500,
                      traceback=traceback.format_exc())
        return make_response(msg, 500)

    return make_response(jsonify(message="PandaSandbox::Successfully stored file"), 200)


@app.route("/retrieve", methods=["POST"])
def do_retrieve():
    if "filepath" not in request.form:
        msg = jsonify(message="PandaSandbox::No filepath has been provided", error_code=400)
        return make_response(msg, 400)

    return send_file(request.form["filepath"])


@app.route("/extract", methods=["POST"])
def do_extract():
    if "dirpath" not in request.form:
        msg = jsonify(message="PandaSandbox::No dirpath has been provided", error_code=400)
        return make_response(msg, 400)

    if "zipfile" not in request.files:
        msg = jsonify(message="PandaSandbox::No zip file has been provided", error_code=400)
        return make_response(msg, 400)

    try:
        with zipfile.ZipFile(request.files["zipfile"], "r") as archive:
            archive.extractall(request.form["dirpath"])
    except OSError:
        msg = jsonify(message="PandaSandbox::Error extracting zip file", error_code=500,
                      traceback=traceback.format_exc())
        return make_response(msg, 500)

    return make_response(jsonify(message="Successfully extracted zip file"), 200)


@app.route("/remove", methods=["POST"])
def do_remove():
    if "path" not in request.form:
        msg = jsonify(message="PandaSandbox::No path has been provided", error_code=400)
        return make_response(msg, 400)

    try:
        if os.path.isdir(request.form["path"]):
            # Mark all files as readable so they can be deleted.
            for dirpath, _, filenames in os.walk(request.form["path"]):
                for filename in filenames:
                    os.chmod(os.path.join(dirpath, filename), stat.S_IWRITE)

            shutil.rmtree(request.form["path"])
            message = "Successfully deleted directory"
        elif os.path.isfile(request.form["path"]):
            os.chmod(request.form["path"], stat.S_IWRITE)
            os.remove(request.form["path"])
            message = "Successfully deleted file"
        else:
            msg = jsonify(message="PandaSandbox::Path provided does not exist", error_code=400)
            return make_response(msg, 400)
    except OSError:
        msg = jsonify(message="PandaSandbox::Error removing file or directory", error_code=500,
                      traceback=traceback.format_exc())
        return make_response(msg, 500)

    return make_response(jsonify(message=message), 200)


@app.route("/execute", methods=["POST"])
def do_execute():
    if "command" not in request.form:
        msg = jsonify(message="PandaSandbox::No command has been provided", error_code=400)
        return make_response(msg, 400)

    waite = "waite" in request.form
    shell = "shell" in request.form

    cwd = request.form.get("cwd")
    stdout = stderr = None

    try:
        if not waite:
            subprocess.Popen(request.form["command"], shell=shell, cwd=cwd)
        else:
            p = subprocess.Popen(
                request.form["command"], shell=shell, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = p.communicate()
    except:
        msg = jsonify(message="PandaSandbox::Error executing command", error_code=500,
                      traceback=traceback.format_exc())
        return make_response(msg, 500)

    msg = jsonify(message="PandaSandbox::Successfully executed command", stdout=stdout, stderr=stderr)
    return make_response(msg, 200)


@app.route("/execpy", methods=["POST"])
def do_execpy():
    if "filepath" not in request.form:
        msg = jsonify(message="PandaSandbox::No Python file has been provided", error_code=400)
        return make_response(msg, 400)

    waite = "waite" in request.form

    cwd = request.form.get("cwd")
    stdout = stderr = None

    params = [
        sys.executable,
        request.form["filepath"],
    ]

    try:
        if not waite:
            subprocess.Popen(params, cwd=cwd)
        else:
            p = subprocess.Popen(params, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
    except:
        msg = jsonify(message="PandaSandbox::Error executing command", error_code=500,
                      traceback=traceback.format_exc())
        return make_response(msg, 500)

    msg = jsonify(message="PandaSandbox::Successfully executed command", stdout=stdout, stderr=stderr)
    return make_response(msg, 200)


@app.route("/pinning")
def do_pinning():
    if "client_ip" in state:
        msg = jsonify(message="PandaSandbox::Agent has already been pinned to an IP!", error_code=500)
        return make_response(msg, 500)

    state["client_ip"] = request.client_ip
    msg = jsonify(message="PandaSandbox::Successfully pinned Agent", client_ip=request.client_ip)
    return make_response(msg, 200)


@app.route("/kill")
def do_kill():
    shutdown = request.environ.get("werkzeug.server.shutdown")
    if shutdown is None:
        msg = jsonify(message="PandaSandbox::Not running with the Werkzeug server", error_code=500)
        return make_response(msg, 500)

    shutdown()
    return make_response(jsonify(message="PandaSandbox::Quit the Cuckoo Agent"), 200)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("host", nargs="?", default="0.0.0.0")  # By default we should use 0.0.0.0
    parser.add_argument("port", nargs="?", default="63554")
    args = parser.parse_args()

    print("Starting Minimal HTTP Sever at #{0}:{1} ~~~".format(args.host, args.port))

    app.run(host=args.host, port=int(args.port))
