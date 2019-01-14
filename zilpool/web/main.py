# -*- coding: utf-8 -*-
# Copyright 2018-2019 Gully Chen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import jinja2
import aiohttp_jinja2

from zilpool.apis import stats
from zilpool.web import tools
from zilpool.database import zilnode, ziladmin

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_DIR = os.path.join(CUR_DIR, "static")
TEMPLATE_DIR = os.path.join(CUR_DIR, "template")


def init_web_handlers(app, config):
    root_path = config["api_server"]["website"].get("path", "/")

    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(TEMPLATE_DIR))

    # add handles
    app.router.add_static(f"{root_path}static", STATIC_DIR)

    @aiohttp_jinja2.template("index.jinja2")
    async def index(request):
        return {
            "config": config,
            "summary": stats.summary(),
            "current": stats.current_work(),
        }
    app.router.add_route("GET", root_path, index)

    @aiohttp_jinja2.template("verify.jinja2")
    async def verify(request):
        action = request.match_info.get("action")
        token = request.match_info.get("token")

        verified, message = tools.verify_token(token, action)

        return {
            "config": config,
            "verified": verified,
            "message": message,
        }

    app.router.add_route(
        "GET",
        f"{root_path}verify/{{action}}/{{token}}",
        verify
    )


