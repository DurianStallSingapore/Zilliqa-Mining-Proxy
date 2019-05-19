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
"""
  Zilliqa Network APIs
"""

import ssl
import asyncio

from aiohttp import ClientSession
from jsonrpcclient.exceptions import JsonRpcClientError
from jsonrpcclient.clients.aiohttp_client import AiohttpClient


INVALID_PARAMS = "INVALID_PARAMS: Invalid method parameters (invalid name and/or type) recognised"

context = ssl._create_unverified_context()

APIError = JsonRpcClientError


class API:
    class APIMethod:
        def __init__(self, api, method_name):
            self.api = api
            self.method_name = method_name

        async def __call__(self, *params, **kwargs):
            resp = await self.api.call(self.method_name, *params, **kwargs)
            return resp and resp.data and resp.data.result

    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.loop = asyncio.get_event_loop()
        self.session = None
        self.api_client = None

    async def init_client(self):
        self.session = ClientSession(loop=self.loop)
        self.api_client = AiohttpClient(
            self.session,
            self.endpoint,
            ssl=context
        )

    def __getattr__(self, item):
        return API.APIMethod(self, method_name=item)

    def __del__(self):
        if self.session is not None:
            self.loop.run_until_complete(self.session.close())

    async def call(self, method, *params, **kwargs):
        if self.api_client is None:
            await self.init_client()

        try:
            return await self.api_client.request(
                method, *params,
                trim_log_values=True, **kwargs
            )
        except JsonRpcClientError as e:
            # fix for jsonrpcclient < 3.3.1
            if str(e) == INVALID_PARAMS:
                if len(params) == 1 and (isinstance(params[0], (dict, list))):
                    params = (list(params),)
                    return await self.api_client.request(
                        method, *params,
                        trim_log_values=True, **kwargs
                    )

            raise e


if "__main__" == __name__:
    loop = asyncio.get_event_loop()

    api = API("https://dev-api.zilliqa.com/")
    block = loop.run_until_complete(api.GetCurrentMiniEpoch())
    print(block)
    block = loop.run_until_complete(api.GetCurrentDSEpoch())
    print(block)
    block = loop.run_until_complete(api.GetCurrentMiniEpoch())
    print(block)

    try:
        balance = loop.run_until_complete(api.GetBalance("4BAF5faDA8e5Db92C3d3242618c5B47133AE003C"))
        print(balance)
    except APIError as e:
        print(f"APIError: {e}")
