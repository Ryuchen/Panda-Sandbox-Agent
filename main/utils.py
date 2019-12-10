#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ========================================================
# @Author: Ryuchen
# @Time: 2019/12/10-20:25
# @Site: https://ryuchen.github.io
# @Contact: chenhaom1993@hotmail.com
# @Copyright: Copyright (C) 2019-2020 Panda-Sandbox-Agent.
# ========================================================
"""
...
DocString Here
...
"""
import asyncio


async def run_no_wait(cmd):
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
