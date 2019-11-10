from datetime import datetime
from time import mktime
import uuid
import hmac
import requests
import json
from hashlib import sha256
import optparse
import sys
import logging
import random
import time

class public_api:

    def __init__(self, host, verbose=False):
        self.host = host
        self.verbose = verbose

    def request(self, method, path, query, body):
        url = self.host + path
        if query:
            url += '?' + query

        if self.verbose:
            print(method, url)

        s = requests.Session()
        if body:
            body_json = json.dumps(body)
            response = s.request(method, url, data=body_json)
        else:
            response = s.request(method, url)

        if response.status_code == 200:
            return response.json()
        elif response.content:
            raise Exception(str(response.status_code) + ": " + response.reason + ": " + str(response.content))
        else:
            raise Exception(str(response.status_code) + ": " + response.reason)

    def get_current_global_stats(self):
        return self.request('GET', '/main/api/v2/public/stats/global/current/', '', None)

    def get_global_stats_24(self):
        return self.request('GET', '/main/api/v2/public/stats/global/24h/', '', None)

    def get_active_orders(self):
        response = self.request('GET', '/main/api/v2/public/orders/active/', '', None)
        daggerOrders = [order for order in response['list'] if order['algorithm']['algorithm'] == 'DAGGERHASHIMOTO' and order['market'] == 'USA']
        return daggerOrders

    def get_active_orders2(self):
        response = self.request('GET', '/main/api/v2/public/orders/active2/', '', None)
        daggerOrders = [order for order in response['list'] if order['algorithm'] == 'DAGGERHASHIMOTO' and order['market'] == 'USA']
        return daggerOrders

    def buy_info(self):
        return self.request('GET', '/main/api/v2/public/buy/info/', '', None)

    def get_algorithms(self):
        return self.request('GET', '/main/api/v2/mining/algorithms/', '', None)

    def get_markets(self):
        return self.request('GET', '/main/api/v2/mining/markets/', '', None)

    def get_curencies(self):
        return self.request('GET', '/api/v2/enum/currencies/', '', None)

    def get_multialgo_info(self):
        return self.request('GET', '/main/api/v2/public/simplemultialgo/info/', '', None)

    def get_exchange_markets_info(self):
        return self.request('GET', '/exchange/api/v2/info/status', '', None)

    def get_exchange_trades(self, market):
        return self.request('GET', '/exchange/api/v2/trades', 'market=' + market, None)

    def get_candlesticks(self, market, from_s, to_s, resolution):
        return self.request('GET', '/exchange/api/v2/candlesticks', "market={}&from={}&to={}&resolution={}".format(market, from_s, to_s, resolution), None)

    def get_exchange_orderbook(self, market, limit):
        return self.request('GET', '/exchange/api/v2/orderbook', "market={}&limit={}".format(market, limit), None)

class private_api:

    def __init__(self, config, algorithms=None, verbose=False):
        self.key = config["api_key"]
        self.secret = config["api_secret"]
        self.organisation_id = config["organisation_id"]
        self.host = config["host"]
        self.config = config
        self.algorithms = algorithms
        self.verbose = verbose

    def request(self, method, path, query, body):

        xtime = self.get_epoch_ms_from_now()
        xnonce = str(uuid.uuid4())

        message = bytearray(self.key, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(str(xtime), 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(xnonce, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(self.organisation_id, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(method, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(path, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(query, 'utf-8')

        if body:
            body_json = json.dumps(body)
            message += bytearray('\x00', 'utf-8')
            message += bytearray(body_json, 'utf-8')

        digest = hmac.new(bytearray(self.secret, 'utf-8'), message, sha256).hexdigest()
        xauth = self.key + ":" + digest

        headers = {
            'X-Time': str(xtime),
            'X-Nonce': xnonce,
            'X-Auth': xauth,
            'Content-Type': 'application/json',
            'X-Organization-Id': self.organisation_id,
            'X-Request-Id': str(uuid.uuid4())
        }

        s = requests.Session()
        s.headers = headers

        url = self.host + path
        if query:
            url += '?' + query

        if self.verbose:
            print(method, url)

        if body:
            response = s.request(method, url, data=body_json)
        else:
            response = s.request(method, url)

        if response.status_code == 200:
            return response.json()
        elif response.content:
            raise Exception(str(response.status_code) + ": " + response.reason + ": " + str(response.content))
        else:
            raise Exception(str(response.status_code) + ": " + response.reason)

    def get_epoch_ms_from_now(self):
        now = datetime.now()
        now_ec_since_epoch = mktime(now.timetuple()) + now.microsecond / 1000000.0
        return int(now_ec_since_epoch * 1000)

    def algo_settings_from_response(self, algorithm, algo_response):
        algo_setting = None
        for item in algo_response['miningAlgorithms']:
            if item['algorithm'] == algorithm:
                algo_setting = item

        if algo_setting is None:
            raise Exception('Settings for algorithm not found in algo_response parameter')

        return algo_setting

    def get_accounts(self):
        return self.request('GET', '/main/api/v2/accounting/accounts/', '', None)

    def get_accounts_for_currency(self, currency):
        return self.request('GET', '/main/api/v2/accounting/account/' + currency, '', None)

    def get_my_active_orders(self, algorithm, market, limit):

        ts = self.get_epoch_ms_from_now()
        params = "algorithm={}&market={}&ts={}&limit={}&op=LT&active=true".format(algorithm, market, ts, limit)

        return self.request('GET', '/main/api/v2/hashpower/myOrders', params, None)

    def create_pool(self, name, algorithm, pool_host, pool_port, username, password):
        pool_data = {
            "name": name,
            "algorithm": algorithm,
            "stratumHostname": pool_host,
            "stratumPort": pool_port,
            "username": username,
            "password": password
        }
        return self.request('POST', '/main/api/v2/pool/', '', pool_data)

    def delete_pool(self, pool_id):
        return self.request('DELETE', '/main/api/v2/pool/' + pool_id, '', None)

    def get_my_pools(self, page, size):
        return self.request('GET', '/main/api/v2/pools/', '', None)

    def create_hashpower_order(self, market, type, algorithm, price, limit, amount, pool_id):

        algo_setting = self.algo_settings_from_response(algorithm, self.algorithms)

        order_data = {
            "market": market,
            "algorithm": algorithm,
            "amount": amount,
            "price": price,
            "limit": limit,
            "poolId": pool_id,
            "type": type,
            "marketFactor": algo_setting['marketFactor'],
            "displayMarketFactor": algo_setting['displayMarketFactor']
        }
        return self.request('POST', '/main/api/v2/hashpower/order/', '', order_data)

    def cancel_hashpower_order(self, order_id):
        return self.request('DELETE', '/main/api/v2/hashpower/order/' + order_id, '', None)

    def stop_all(self, orders=None, retry=50):
        while retry > 0:
            all_orders = orders
            if orders is None:
                result = self.get_my_active_orders(self.config["algo"], self.config["location"], 100)
                logging.info(f"NiceHash get_my_active_orders result {result}")
                all_orders = result.get("list", [])
                all_orders = [order["id"] for order in all_orders]

            if not all_orders:
                return

            res = self.do_stop_all(all_orders)
            if res is True:
                break
            retry -= 1

    def do_stop_all(self, orders):
        result = True
        for order_id in orders:
            retry = 10
            while retry > 0:
                retry -= 1
                # noinspection PyBroadException
                try:
                    logging.critical(f"Remove NiceHash order {order_id}")
                    resp = self.cancel_hashpower_order(order_id=order_id)
                    logging.critical(f"Remove NiceHash order result: {resp}")
                    if "RPC flood detected" in resp.get("error", ""):
                        raise Exception("RPC flood detected")
                except:
                    logging.error(f"error in stop_all:", exc_info=True)
                    result = False
                    continue
                break

        return result

    def refill_hashpower_order(self, order_id, amount):
        refill_data = {
            "amount": amount
        }
        return self.request('POST', '/main/api/v2/hashpower/order/' + order_id + '/refill/', '', refill_data)

    def get_orders(self):
        ts = self.get_epoch_ms_from_now()
        params = "algorithm={}&market={}&ts={}&op=LT".format(self.config['algo'], self.config['location'], ts)
        return self.request('GET', '/main/api/v2/public/orders/active/', params, None)

    def get_top_price(self, top_n=1, excluded_orders=None,
                            min_limit_speed=0.0, min_accepted_speed=0.0, max_price=None):
        pubAPI = public_api(self.host)
        #result = self.get_orders()
        full_orders = pubAPI.get_active_orders2()
        logging.info(f"full orders: {full_orders}")
        if not full_orders:
            return 2.98
        if excluded_orders is None:
            excluded_orders = []
        full_orders = [order for order in full_orders if order["type"] == 'STANDARD' and order["id"] not in excluded_orders]
        orders = [order for order in full_orders if float(order["speedLimit"]) >= min_limit_speed
                  and float(order["acceptedCurrentSpeed"]) >= min_accepted_speed]

        if max_price:
            orders = [order for order in orders if float(order["price"]) <= max_price]

        logging.info("Before filter, orders = " + str(orders))

        orders = orders[:top_n]
        if not orders:
            orders = full_orders[0]
        logging.info(f"top_n = {top_n}, lenth of order = {len(orders)}, orders = {orders}")

        if len(orders) > 1:
            orders = orders[1:]
        price = sum([float(order["price"]) for order in orders]) / len(orders)
        return price
    
    def keep_my_orders_top(self, top_n=5, max_price=8.0, 
                                 nice_hash_min_limit_speed=0.0, nice_hash_min_accepted_speed=0.0):
        result = self.get_my_active_orders(self.config["algo"], self.config["location"], 100)
        orders = result.get("list", [])
        my_orders = [order for order in orders if order["type"]["code"] == "STANDARD"]
        excluded_orders = [order["id"] for order in my_orders]

        my_orders = sorted(my_orders, key=lambda order: float(order["price"]))

        for order in my_orders:
            order_number = order["id"]
            my_order_price = float(order["price"])
            top_price = self.get_top_price(top_n=top_n, excluded_orders=excluded_orders,
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
                    resp = self.set_price_hashpower_order(order_number, top_price + random.uniform(0.001, 0.01), self.config['algo'], self.algorithms)
                    logging.warning(f"NiceHash: set price response {resp}")
                    if "RPC flood detected" not in resp.get("error", ""):
                        break
                    time.sleep(0.5)

    def set_price_hashpower_order(self, order_id, price, algorithm, algo_response):

        algo_setting = self.algo_settings_from_response(algorithm, algo_response)

        price_data = {
            "price": price,
            "marketFactor": algo_setting['marketFactor'],
            "displayMarketFactor": algo_setting['displayMarketFactor']
        }
        return self.request('POST', '/main/api/v2/hashpower/order/' + order_id + '/updatePriceAndLimit/', '',
                            price_data)

    def set_limit_hashpower_order(self, order_id, limit, algorithm, algo_response):
        algo_setting = self.algo_settings_from_response(algorithm, algo_response)
        limit_data = {
            "limit": limit,
            "marketFactor": algo_setting['marketFactor'],
            "displayMarketFactor": algo_setting['displayMarketFactor']
        }
        return self.request('POST', '/main/api/v2/hashpower/order/' + order_id + '/updatePriceAndLimit/', '',
                            limit_data)

    def set_price_and_limit_hashpower_order(self, order_id, price, limit, algorithm, algo_response):
        algo_setting = self.algo_settings_from_response(algorithm, algo_response)

        price_data = {
            "price": price,
            "limit": limit,
            "marketFactor": algo_setting['marketFactor'],
            "displayMarketFactor": algo_setting['displayMarketFactor']
        }
        return self.request('POST', '/main/api/v2/hashpower/order/' + order_id + '/updatePriceAndLimit/', '',
                            price_data)

    def get_my_exchange_orders(self, market):
        return self.request('GET', '/exchange/api/v2/myOrders', 'market=' + market, None)

    def get_my_exchange_trades(self, market):
        return self.request('GET','/exchange/api/v2/myTrades', 'market=' + market, None)

    def create_exchange_limit_order(self, market, side, quantity, price):
        query = "market={}&side={}&type=limit&quantity={}&price={}".format(market, side, quantity, price)
        return self.request('POST', '/exchange/api/v2/order', query, None)

    def create_exchange_buy_market_order(self, market, quantity):
        query = "market={}&side=buy&type=market&secQuantity={}".format(market, quantity)
        return self.request('POST', '/exchange/api/v2/order', query, None)

    def create_exchange_sell_market_order(self, market, quantity):
        query = "market={}&side=sell&type=market&quantity={}".format(market, quantity)
        return self.request('POST', '/exchange/api/v2/order', query, None)

    def cancel_exchange_order(self, market, order_id):
        query = "market={}&orderId={}".format(market, order_id)
        return self.request('DELETE', '/exchange/api/v2/order', query, None)


if __name__ == "__main__":
    parser = optparse.OptionParser()

    parser.add_option('-b', '--base_url', dest="base", help="Api base url", default="https://api2.nicehash.com")
    parser.add_option('-o', '--organization_id', dest="org", help="Organization id")
    parser.add_option('-k', '--key', dest="key", help="Api key")
    parser.add_option('-s', '--secret', dest="secret", help="Secret for api key")
    parser.add_option('-m', '--method', dest="method", help="Method for request", default="GET")
    parser.add_option('-p', '--path', dest="path", help="Path for request", default="/")
    parser.add_option('-q', '--params', dest="params", help="Parameters for request")
    parser.add_option('-d', '--body', dest="body", help="Body for request")

    options, args = parser.parse_args()

    private_api = private_api(options.base, options.org, options.key, options.secret)

    params = ''
    if options.params is not None:
        params = options.params

    try:
        response = private_api.request(options.method, options.path, params, options.body)
    except Exception as ex:
        print("Unexpected error:", ex)
        exit(1)

    print(response)
    exit(0)
