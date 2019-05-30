import asyncio
import json
import logging
import random
from bson import ObjectId

from zilpool.common import utils, blockchain
from zilpool.database import pow, miner
from zilpool.pyzil import ethash
from zilpool.pyzil.crypto import hex_str_to_bytes as h2b
from zilpool.pyzil.crypto import hex_str_to_int as h2i
from zilpool.pyzil.crypto import bytes_to_hex_str as b2h

from zilpool.nicehash import NiceHashClient

stratumMiners = []

STRATUM_BASIC = 0
STRATUM_NICEHASH = 2

class StratumMiner:
    def __init__(self, transport, stratumVersion = STRATUM_BASIC):
        self._transport = transport
        self._stratusVersion = stratumVersion
        self._boundary = None
        self._miningAtBlock = dict()
        self._miningRealJob = False
        self._targetDifficulty = 0

    def notify_difficulty(self, diff):
        self._boundary = diff
        if self._stratusVersion == STRATUM_BASIC:
            return
        DIFF_BASE = 0x00000000ffff0000000000000000000000000000000000000000000000000000
        target = DIFF_BASE / int(diff, 16)
        if self._targetDifficulty == target:
            logging.info("The difficulty is the same, no need send again")
            return
        dictOfReply = dict()
        dictOfReply["id"] = None
        dictOfReply["method"] = "mining.set_difficulty"
        dictOfReply["params"] = [target]
        strReply = json.dumps(dictOfReply)
        strReply += '\n'
        logging.info(f"Server Reply {strReply}")
        self._transport.write(strReply.encode())
        self._targetDifficulty = target

    def notify_work(self, work, realJob):
        if self._miningRealJob and work.block_num in self._miningAtBlock and self._miningAtBlock[work.block_num]:
            logging.info(f"Miner still mining at real job for block {work.block_num}, no need send new work")
            return

        self.notify_difficulty(work.boundary)

        dictOfReply = dict()
        dictOfReply["id"] = None
        dictOfReply["method"] = "mining.notify"
        seed = work.seed
        if seed[0:2] == '0x' or seed[0:2] == '0X':
            seed = seed[2:]

        header = work.header
        if header[0:2] == '0x' or header[0:2] == '0X':
            header = header[2:]

        if self._stratusVersion == STRATUM_BASIC:            
            dictOfReply["params"] = [str(work.pk), header, seed, work.boundary]
        elif self._stratusVersion == STRATUM_NICEHASH:
            dictOfReply["params"] = [str(work.pk), seed, header, True]
        strReply = json.dumps(dictOfReply)
        strReply += '\n'
        logging.info(f"Server Reply {strReply}")
        
        self._transport.write(strReply.encode())
        return True

        self._miningRealJob = realJob
        self._miningAtBlock[work.block_num] = True

    def set_workDone(self, work):
        self._miningAtBlock[work.block_num] = False

class StratumServerProtocol(asyncio.Protocol):
    def __init__(self, config):
        self._server = None
        self.transport = None
        self.stratumMiner = None
        self.subscribed = False
        self.miner_wallet = None
        self.strExtraNonceHex = None
    
    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        logging.critical(f'Connection from {peername}')
        self.transport = transport

    def connection_lost(self, exc):
        logging.critical("Connection lost")
        stratumMiners.remove(self.stratumMiner)

    def data_received(self, data):
        message = data.decode()
        logging.critical('Data received: {!r}'.format(message))
        for subMessage in message.split('\n'):
            if (len(subMessage) <= 0):
                break
            try:
                jsonMsg = json.loads(subMessage)
                if jsonMsg["method"] == "mining.subscribe":
                    self.process_subscribe(jsonMsg)
                elif jsonMsg["method"] == "mining.authorize":
                    self.process_authorize(jsonMsg)
                elif jsonMsg["method"] == "mining.extranonce.subscribe":
                    self.send_extranonce_reply()
                elif jsonMsg["method"] == "mining.submit":
                    self.process_submit(jsonMsg)
            except ValueError:
                logging.critical(f"Failed to parse json message {subMessage}")

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

        self.strExtraNonceHex = hex(random.randrange(0xffff))[2:]
        dictOfReply["result"].append(self.strExtraNonceHex)

        dictOfReply["error"] = None

        strReply = json.dumps(dictOfReply)
        strReply += '\n'
        logging.info("Server Reply > " + strReply)
        self.transport.write(strReply.encode())

    def send_success_reply(self, id):
        dictOfReply = dict()
        dictOfReply["id"] = id
        dictOfReply["result"] = True
        dictOfReply["error"] = None
        strReply = json.dumps(dictOfReply)
        strReply += '\n'
        logging.info("Server Reply > " + strReply)
        self.transport.write(strReply.encode())

    def process_authorize(self, jsonMsg):
        # Need to check the user and password if it valid, skipped for now
        id = jsonMsg["id"]
        minerInfos = jsonMsg["params"][0].split('.')
        self.miner_wallet = minerInfos[0]
        logging.info(f"miner wallet {self.miner_wallet}")
        self.send_success_reply(id)

    def send_extranonce_reply(self):
        dictOfReply = dict()
        dictOfReply["id"] = None
        dictOfReply["method"] = "mining.set_extranonce"

        self.strExtraNonceHex = hex(random.randrange(0xffff))[2:]
        dictOfReply["params"] = [self.strExtraNonceHex]

        strReply = json.dumps(dictOfReply)
        strReply += '\n'
        logging.info("Server Reply > " + strReply)
        self.transport.write(strReply.encode())

    def process_submit(self, jsonMsg):
        work = None
        mix_digest = None
        miner_wallet = self.miner_wallet
        worker_name = None
        hash_result = None
        _worker = None
        if jsonMsg["id"] is None:
            logging.warning("Submitted result message without id")
            return

        id = jsonMsg["id"]
        if self.stratumMiner._stratusVersion == STRATUM_BASIC:
            nonce = jsonMsg["params"][2]
            nonce_int = h2i(nonce)            
            header = jsonMsg["params"][3]
            mix_digest = jsonMsg["params"][4]
            boundary = self.stratumMiner._boundary
            mix_digest_bytes = h2b(mix_digest)
            worker_name = jsonMsg["worker"]
            _worker = miner.Worker.get_or_create(miner_wallet, worker_name)

            # 3. check work existing
            work = pow.PowWork.find_work_by_header_boundary(header=header, boundary=boundary,
                                                            check_expired=True)
            if not work:
                logging.warning(f"work not found or expired, {header} {boundary}")
                _worker.update_stat(inc_failed=1)
                return False

            # 4. verify result
            seed, header = h2b(work.seed), h2b(work.header)
            boundary_bytes = h2b(work.boundary)
            block_num = ethash.seed_to_block_num(seed)
            hash_result = ethash.verify_pow_work(block_num, header, mix_digest_bytes,
                                                nonce_int, boundary_bytes)
            if not hash_result:
                logging.warning(f"wrong result from miner {miner_wallet}-{worker_name}, {work}")
                _worker.update_stat(inc_failed=1)
                return False

        elif self.stratumMiner._stratusVersion == STRATUM_NICEHASH:
            if jsonMsg["params"] is None:
                logging.critical("The message is without params section")
                return False

            worker_name = jsonMsg["params"][0]
            strJobId = jsonMsg["params"][1]
            joibId = ObjectId(strJobId)
            nonce = jsonMsg["params"][2]
            if self.strExtraNonceHex is not None:
                nonce = self.strExtraNonceHex + nonce
            nonce_int = h2i(nonce)
            logging.info(f"worker_name {worker_name}")
            _worker = miner.Worker.get_or_create(miner_wallet, worker_name)

            # 3. check work existing
            work = pow.PowWork.find_work_by_id(joibId, check_expired=True)
            if not work:
                logging.warning(f"work not found or expired, {strJobId}")
                _worker.update_stat(inc_failed=1)
                return False

            # 4. verify result
            seed, header = h2b(work.seed), h2b(work.header)
            calc_mix_digest, calc_result = ethash.pow_hash(work.block_num, header, nonce_int)
            boundary_bytes = h2b(work.boundary)
            block_num = ethash.seed_to_block_num(seed)
            hash_result = ethash.verify_pow_work(block_num, header, calc_mix_digest,
                                                nonce_int, boundary_bytes)
            if not hash_result:
                logging.warning(f"wrong result from miner {miner_wallet}-{worker_name}, {work}")
                _worker.update_stat(inc_failed=1)
                return False

            mix_digest = b2h(calc_mix_digest)

        self.stratumMiner.set_workDone(work)

        # 5. check the result if lesser than old one
        if work.finished:
            prev_result = pow.PowResult.get_pow_result(work.header, work.boundary)
            if prev_result:
                if prev_result.verified:
                    logging.info(f"submitted too late, work is verified. {work.header} {work.boundary}")
                    _worker.update_stat(inc_failed=1)
                    return False

                if ethash.is_less_or_equal(prev_result.hash_result, hash_result):
                    logging.info(f"submitted result > old result, ignored. {work.header} {work.boundary}")
                    _worker.update_stat(inc_failed=1)
                    return False

        # 6. save to database
        hash_result_str = b2h(hash_result, prefix="0x")
        if not work.save_result(nonce, mix_digest, hash_result_str, miner_wallet, worker_name):
            logging.warning(f"failed to save result for miner "
                            f"{miner_wallet}-{worker_name}, {work}")
            return False

        logging.critical(f"Work submitted, {work.header} {work.boundary}")

        self.send_success_reply(id)

        _worker.update_stat(inc_finished=1)

        #logging.info("Stopping all nice hash orders")
        #client = NiceHashClient(self.config.nicehash)
        #asyncio.create_task(client.stop_all())

        # 6. todo: miner reward
        return True


