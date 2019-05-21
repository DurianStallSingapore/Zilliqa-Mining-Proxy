import asyncio
import json
import logging
from zilpool.stratum.miner_conn import Connections
from zilpool.common import utils, blockchain
from zilpool.database import pow, miner
from zilpool.pyzil import ethash
from zilpool.pyzil.crypto import hex_str_to_bytes as h2b
from zilpool.pyzil.crypto import hex_str_to_int as h2i
from zilpool.pyzil.crypto import bytes_to_hex_str as b2h

stratumMiners = []

STRATUM_BASIC = 0
STRATUM_NICEHASH = 2

class StratumMiner:
    def __init__(self, transport, stratumVersion = STRATUM_BASIC):
        self._transport = transport
        self._stratusVersion = stratumVersion
        self._boundary = None

    def notify_difficulty(self, diff):
        self._boundary = diff
        if self._stratusVersion == STRATUM_BASIC:
            return
        DIFF_BASE = 0x00000000ffff0000000000000000000000000000000000000000000000000000
        target = DIFF_BASE / int(diff, 16)
        dictOfReply = dict()
        dictOfReply["id"] = None
        dictOfReply["method"] = "mining.set_difficulty"
        dictOfReply["params"] = [target]
        strReply = json.dumps(dictOfReply)
        print("Before append length " + str(len(strReply)))
        strReply += '\n'
        print("After append length " + str(len(strReply)))
        print("Server Reply >" + strReply)
        self._transport.write(strReply.encode())

    def notify_work(self, work):
        dictOfReply = dict()
        dictOfReply["id"] = None
        dictOfReply["method"] = "mining.notify"
        if self._stratusVersion == STRATUM_BASIC:            
            dictOfReply["params"] = [str(work.pk), work.header, work.seed, work.boundary]
        elif self._stratusVersion == STRATUM_NICEHASH:
            dictOfReply["params"] = [work.pk, work.seed, work.header, True]
        strReply = json.dumps(dictOfReply)
        strReply += '\n'
        print("Server Reply >" + strReply)
        self._transport.write(strReply.encode())

class StratumServerProtocol(asyncio.Protocol):
    def __init__(self):
        self._server = None
        self.transport = None
        self.stratumMiner = None
        self.subscribed = False
        self.miner_wallet = None

    # Deleting (Calling destructor) 
    def __del__(self): 
        print('Destructor called, StratumServerProtocol deleted.')

    async def start(self):
        loop = asyncio.get_running_loop()
        server = await loop.create_server(self, '127.0.0.1', 9999)

        async with server:
            await server.serve_forever()
    
    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(peername))
        self.transport = transport

    def connection_lost(self, exc):
        print("Connection lost")
        print(exec)

    def data_received(self, data):
        message = data.decode()
        print('Data received: {!r}'.format(message))
        for subMessage in message.split('\n'):
            if (len(subMessage) <= 0):
                break
            jsonMsg = json.loads(subMessage)
            if (jsonMsg['id'] == 1 and jsonMsg["method"] == "mining.subscribe"):
                self.process_subscribe(jsonMsg)
            elif (jsonMsg['id'] == 3 and jsonMsg["method"] == "mining.authorize"):
                self.process_authorize(jsonMsg)
            elif (jsonMsg['id'] == 2 and jsonMsg["method"] == "mining.extranonce.subscribe"):
                self.send_extranonce_reply()
            elif(jsonMsg["method"] == "mining.submit"):
                self.process_submit(jsonMsg)

    def notify(self, data):
        self.transport.write("Notify something")

    def process_subscribe(self, jsonMsg):
        stratumVersion = STRATUM_BASIC
        if jsonMsg["params"] is not None and len(jsonMsg["params"]) >= 2 and jsonMsg["params"][1] == "EthereumStratum/1.0.0":
            stratumVersion = STRATUM_NICEHASH
        self.stratumMiner = StratumMiner(self.transport, stratumVersion)
        stratumMiners.append(self.stratumMiner)
        logging.info("Subcribed with stratum version " + str(stratumVersion))
        self.send_subscribe_reply()
        self.subscribed = True

    def send_subscribe_reply(self):
        dictOfReply = dict()
        dictOfReply["id"] = 1
        dictOfReply["result"] = []
        replyArray1 = ["mining.notify", "ae6812eb4cd7735a302a8a9dd95cf71f", "EthereumStratum/1.0.0"]
        dictOfReply["result"].append(replyArray1)

        replyArray2 = "080c"
        dictOfReply["result"].append(replyArray2)

        dictOfReply["error"] = None

        strReply = json.dumps(dictOfReply)
        strReply += '\n'
        print("Server Reply >" + strReply)
        self.transport.write(strReply.encode())

    def send_success_reply(self):
        dictOfReply = dict()
        dictOfReply["id"] = 3
        dictOfReply["result"] = True
        dictOfReply["error"] = None
        strReply = json.dumps(dictOfReply)
        strReply += '\n'
        print("Server Reply >" + strReply)
        self.transport.write(strReply.encode())

    def process_authorize(self, jsonMsg):
        # Need to check the user and password if it valid, skipped for now
        minerInfos = jsonMsg["params"][0].split('.')
        self.miner_wallet = minerInfos[0]
        print("miner wallet " + self.miner_wallet)
        self.send_success_reply()

    def send_extranonce_reply(self):
        dictOfReply = dict()
        dictOfReply["id"] = None
        dictOfReply["method"] = "mining.set_extranonce"
        dictOfReply["params"] = [0xaf4c]
        strReply = json.dumps(dictOfReply)
        strReply += '\n'
        print("Server Reply >" + strReply)
        self.transport.write(strReply.encode())

    def process_submit(self, jsonMsg):
        if self.stratumMiner._stratusVersion == STRATUM_BASIC:
            nonce = jsonMsg["params"][2]
            nonce_int = h2i(nonce)            
            header = jsonMsg["params"][3]
            mix_digest = jsonMsg["params"][4]
            boundary = self.stratumMiner._boundary
            mix_digest_bytes = h2b(mix_digest)
            worker_name = jsonMsg["worker"]
            miner_wallet = self.miner_wallet

            # 3. check work existing
            work = pow.PowWork.find_work_by_header_boundary(header=header, boundary=boundary,
                                                            check_expired=True)
            if not work:
                logging.warning(f"work not found or expired, {header} {boundary}")
                #_worker.update_stat(inc_failed=1)
                return False

            # 4. verify result
            seed, header = h2b(work.seed), h2b(work.header)
            boundary_bytes = h2b(work.boundary)
            block_num = ethash.seed_to_block_num(seed)
            hash_result = ethash.verify_pow_work(block_num, header, mix_digest_bytes,
                                                nonce_int, boundary_bytes)
            if not hash_result:
                logging.warning(f"wrong result from miner {miner_wallet}-{worker_name}, {work}")
                #_worker.update_stat(inc_failed=1)
                return False

            # 5. check the result if lesser than old one
            if work.finished:
                prev_result = pow.PowResult.get_pow_result(work.header, work.boundary)
                if prev_result:
                    if prev_result.verified:
                        logging.info(f"submitted too late, work is verified. {work.header} {work.boundary}")
                        #_worker.update_stat(inc_failed=1)
                        return False

                    if ethash.is_less_or_equal(prev_result.hash_result, hash_result):
                        logging.info(f"submitted result > old result, ignored. {work.header} {work.boundary}")
                        #_worker.update_stat(inc_failed=1)
                        return False

            # 6. save to database
            hash_result_str = b2h(hash_result, prefix="0x")
            if not work.save_result(nonce, mix_digest, hash_result_str, miner_wallet, worker_name):
                logging.warning(f"failed to save result for miner "
                                f"{miner_wallet}-{worker_name}, {work}")
                return False

            logging.critical(f"Work submitted, {work.header} {work.boundary}")

            self.send_success_reply()

            #_worker.update_stat(inc_finished=1)

            # 6. todo: miner reward
            return True


