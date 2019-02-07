# -*- coding: utf-8 -*-
# Zilliqa Mining Proxy
# Copyright (C) 2019  Gully Chen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import io
import csv

import jinja2
import aiohttp_jinja2
from aiohttp import web

from zilpool.apis import stats
from zilpool.web import tools
from zilpool.common import utils
from zilpool.apis import admin as admin_api

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_DIR = os.path.join(CUR_DIR, "static")
TEMPLATE_DIR = os.path.join(CUR_DIR, "template")


def init_web_handlers(app, config):
    root_path = config["api_server"]["website"].get("path", "/")

    jinja2_env = aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(TEMPLATE_DIR))
    jinja2_env.globals["utils"] = utils

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

    @aiohttp_jinja2.template("miner.jinja2")
    async def show_miner(request):
        address = request.match_info.get("address")
        address_worker = address.split(".", 2)    # address.worker_name
        address = address_worker[0]

        miner = stats.miner_stats(address)
        if miner:
            miner["workers_stats"] = [
                stats.worker_stats(address, worker_name, hashrate=False)
                for worker_name in miner["workers"][:100]
            ]

        resp = {
            "config": config,
            "address": address,
            "miner": miner,
        }

        if len(address_worker) > 1:
            worker = stats.worker_stats(address, address_worker[1])
            resp["worker"] = worker

        return resp

    app.router.add_route(
        "GET", f"{root_path}miner/{{address}}", show_miner
    )

    @aiohttp_jinja2.template("node.jinja2")
    async def show_node(request):
        pub_key = request.match_info.get("pub_key")
        node = stats.node_stats(pub_key)

        return {
            "config": config,
            "pub_key": pub_key,
            "node": node,
        }

    app.router.add_route(
        "GET", f"{root_path}node/{{pub_key}}", show_node
    )

    @aiohttp_jinja2.template("admin_login.jinja2")
    async def admin_login(request):
        return {
            "config": config,
        }

    async def admin_dashboard(request):
        data = await request.post()
        admin_email = data.get("email")
        password = data.get("password")
        admin = admin_api.login(request, admin_email, password)

        context = {"config": config}

        if not admin:
            tplt = "admin_login.jinja2"
            context.update({
                "email": admin_email,
                "error": "Invalid Login Credentials",
            })
        else:
            tplt = "admin_dashboard.jinja2"
            context.update({
                "visa": admin.visa_without_ext_data,
                "expire_at": admin.visa_expire_time,
                "summary": stats.summary(),
                "current": stats.current_work(),
                "per_page": 20,
            })

        return aiohttp_jinja2.render_template(tplt, request, context)

    app.router.add_route(
        "GET", f"{root_path}admin", admin_login
    )
    app.router.add_route(
        "POST", f"{root_path}admin", admin_dashboard
    )

    async def admin_export_rewards(request):
        data = await request.post()
        visa = data.get("visa")
        block_num = data.get("block_num", "")

        admin = admin_api.get_admin_from_visa(request, visa)

        block_list = utils.block_num_to_list(block_num)
        blocks_rewards = admin_api.get_rewards(block_list)

        buf = io.StringIO()
        header = ["block_num", "date_time", "miner_wallet",
                  "rewards", "finished", "verified"]
        writer = csv.DictWriter(buf, header, extrasaction="ignore")
        writer.writeheader()
        for block in blocks_rewards:
            for reward in block["rewards"]:
                writer.writerow(reward)

        return web.Response(
            headers={
                "Content-Disposition": "Attachment;filename=rewards.csv"
            },
            body=buf.getvalue()
        )

    app.router.add_route(
        "POST", f"{root_path}admin/export/rewards", admin_export_rewards
    )

