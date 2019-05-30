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

import re
import json
import random
import asyncio
import logging
from aiohttp import ClientSession, TCPConnector


class NiceHashClient:
    def __init__(self, config, loop=None):
        self.api_endpoint = "https://api.nicehash.com/api?"
        self.config = config
        if loop is None:
            loop = asyncio.get_event_loop()
        self.loop = loop
        self.cookies = None

    @property
    def site(self):
        return {
            0: "eu",
            1: "us",
        }.get(self.config["location"])

    async def request(self, method="", timeout=10, **params):
        if method:
            params["method"] = method

        async with ClientSession(loop=self.loop,
                                 connector=TCPConnector(verify_ssl=False)) as session:
            async with session.get(self.api_endpoint,
                                   params=params,
                                   timeout=timeout) as response:
                resp = await response.json(content_type=None)
                return resp and resp["result"]

    async def get_api_version(self):
        return await self.request()

    async def get_balance(self):
        params = {
            "id": self.config["api_id"],
            "key": self.config["api_key"],
        }
        return await self.request("balance", **params)

    async def get_orders(self):
        params = {
            "algo": self.config["algo"],
            "location": self.config["location"],
        }
        return await self.request("orders.get", **params)

    async def get_my_orders(self):
        params = {
            "id": self.config["api_id"],
            "key": self.config["api_key"],
            "algo": self.config["algo"],
            "location": self.config["location"],
            "my": 1,
        }
        return await self.request("orders.get", **params)

    async def get_top_price(self, top_n=1, excluded_orders=None,
                            min_limit_speed=0.0, min_accepted_speed=0.0, max_price=None):
        result = await self.get_orders()
        full_orders = result.get("orders")
        if not full_orders:
            return 2.98
        if excluded_orders is None:
            excluded_orders = []
        full_orders = [order for order in full_orders if order["type"] == 0 and order["id"] not in excluded_orders]
        orders = [order for order in full_orders if float(order["limit_speed"]) > min_limit_speed
                  and float(order["accepted_speed"]) > min_accepted_speed]

        if max_price:
            orders = [order for order in orders if float(order["price"]) <= max_price]

        orders = orders[:top_n]
        if not orders:
            orders = full_orders[0]
        if len(orders) > 1:
            orders = orders[1:]
        price = sum([float(order["price"]) for order in orders]) / len(orders)
        return price

    async def set_price(self, order_number, price):
        params = {
            "id": self.config["api_id"],
            "key": self.config["api_key"],
            "algo": self.config["algo"],
            "location": self.config["location"],
            "order": order_number,
            "price": str(price)
        }
        return await self.request("orders.set.price", **params)

    async def create_order(self, amount, price, limit):
        params = {
            "id": self.config["api_id"],
            "key": self.config["api_key"],
            "algo": self.config["algo"],
            "location": self.config["location"],
            "pool_host": self.config["pool_host"],
            "pool_port": self.config["pool_port"],
            "pool_user": self.config["pool_user"],
            "pool_pass": self.config["pool_pass"],
            "amount": str(amount),
            "price": str(price),
            "limit": str(limit),
        }
        result = await self.request("orders.create", **params)
        error = result.get("error", None)
        if error:
            logging.error(f"create_order error: {error}")
            return None

        success = result.get("success", "")
        match = re.search("Order #(?P<order_no>\d+) created", success)
        if match:
            return match.group("order_no")
        return None

    async def remove_order(self, order_number):
        params = {
            "id": self.config["api_id"],
            "key": self.config["api_key"],
            "location": self.config["location"],
            "algo": self.config["algo"],
            "order": order_number,
        }
        return await self.request("orders.remove", **params)

    async def stop_all(self, orders=None, retry=50):
        while retry > 0:
            all_orders = orders
            if orders is None:
                result = await self.get_my_orders()
                logging.info(f"NiceHash get_my_orders result {result}")
                all_orders = result.get("orders", [])
                all_orders = [order["id"] for order in all_orders]

            if not all_orders:
                return

            res = await self.do_stop_all(all_orders)
            if res is True:
                break
            retry -= 1

    async def do_stop_all(self, orders):
        result = True
        for order_number in orders:
            retry = 10
            while retry > 0:
                retry -= 1
                # noinspection PyBroadException
                try:
                    logging.critical(f"Remove NiceHash order {order_number}")
                    resp = await self.remove_order(order_number=order_number)
                    logging.critical(f"Remove NiceHash order result: {resp}")
                    if "RPC flood detected" in resp.get("error", ""):
                        raise Exception("RPC flood detected")
                except:
                    logging.error(f"error in stop_all:", exc_info=True)
                    await asyncio.sleep(0.5)
                    result = False
                    continue
                break

        return result

    async def keep_my_orders_top(self, top_n=5, max_price=8.0, 
                                 nice_hash_min_limit_speed=0.0, nice_hash_min_accepted_speed=0.0):
        result = await self.get_my_orders()
        orders = result.get("orders", [])
        my_orders = [order for order in orders if order["type"] == 0]
        excluded_orders = [order["id"] for order in my_orders]

        my_orders = sorted(my_orders, key=lambda order: float(order["price"]))

        for order in my_orders:
            order_number = order["id"]
            my_order_price = float(order["price"])
            top_price = await self.get_top_price(top_n=top_n, excluded_orders=excluded_orders,
                                                 min_limit_speed=nice_hash_min_limit_speed,
                                                 min_accepted_speed=nice_hash_min_accepted_speed,
                                                 max_price=max_price)
            logging.info(f"My order price {my_order_price}, nice hash top price {top_price}")

            if top_price > max_price:
                logging.warning(f"NiceHash: max price, {top_price} > {max_price}")
                top_price = max_price
            if my_order_price < top_price:
                logging.warning(f"NiceHash: set order {order_number} price to {top_price:.4f}")
                retry = 20
                while retry > 0:
                    retry -= 1
                    resp = await self.set_price(order_number, top_price + random.uniform(0.001, 0.01))
                    logging.warning(f"NiceHash: set price response {resp}")
                    if "RPC flood detected" not in resp.get("error", ""):
                        break
                    await asyncio.sleep(0.5)
