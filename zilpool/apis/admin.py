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

import logging
from jsonrpcserver import method

from zilpool.pyzil import crypto
from zilpool.common import utils
from zilpool.common.mail import EmailClient
from zilpool.common.utils import iso_format, get_client_ip
from zilpool.database.ziladmin import ZilAdmin, SiteSettings
from zilpool.database.zilnode import ZilNode
from zilpool.database.miner import Miner
from zilpool.database.pow import PowWork, PowResult


def init_apis(config):
    @method
    async def admin_login(request, email: str, password: str):
        ip = get_client_ip(request)
        admin = login(request, email, password)
        assert admin, "wrong email/password"
        return {
            "email": admin.email,
            "visa": admin.visa_without_ext_data,
            "login_ip": ip,
            "expire_at": iso_format(admin.visa_expire_time),
        }

    @method
    async def admin_logout(request, visa: str):
        admin = get_admin_from_visa(request, visa)

        admin = admin.logout()
        if not admin:
            return False

        return True

    @method
    async def admin_generate_password(request, email: str):
        admin = ZilAdmin.get_one(email=email)
        if not admin:
            return False

        password = crypto.rand_string(8)
        if not admin.change_password(password=password):
            return False

        logging.critical(f"Re-generate admin password for {admin.email}: {password}")
        logging.critical(f"send mail to {admin.email}")

        EmailClient.set_config(config)
        EmailClient.send_admin_mail(
            admin.email,
            subject="password generated",
            msg=f"admin email: {admin.email}\npassword: {password}"
        )

        return True

    @method
    async def admin_set_notification(request, visa: str, notification: str):
        admin = get_admin_from_visa(request, visa)

        new_setting = SiteSettings.update_setting(
            admin=admin.email, notification=notification
        )
        if not new_setting:
            return False

        return True

    @method
    async def admin_settings(request, visa: str,
                             min_fee=None, max_dispatch=None, inc_expire=None):
        admin = get_admin_from_visa(request, visa)

        new_setting = SiteSettings.update_setting(
            admin=admin.email,
            min_fee=min_fee, max_dispatch=max_dispatch, inc_expire=inc_expire
        )
        if not new_setting:
            return None

        return {
            "admin": new_setting.admin,
            "created": iso_format(new_setting.created),
            "min_fee": new_setting.min_fee,
            "max_dispatch": new_setting.max_dispatch,
            "inc_expire": new_setting.inc_expire,
        }

    @method
    async def admin_approve_node(request, visa: str,
                                 pub_key: str):
        assert len(pub_key) == 68, "Invalid Public Key"

        admin = get_admin_from_visa(request, visa)
        node = admin_auth_node(pub_key, approve=True)

        return {
            "pub_key": node.pub_key,
            "authorized": node.authorized,
        }

    @method
    async def admin_revoke_node(request, visa: str,
                                pub_key: str):
        assert len(pub_key) == 68, "Invalid Public Key"

        admin = get_admin_from_visa(request, visa)
        node = admin_auth_node(pub_key, approve=False)

        return {
            "pub_key": node.pub_key,
            "authorized": node.authorized,
        }

    @method
    async def admin_list_miners(request, visa: str, page=0, per_page=50, order_by="-work_finished"):
        admin = get_admin_from_visa(request, visa)
        return [
            {
                "email": m.email,
                "nick_name": m.nick_name,
                "authorized": m.authorized,
                "email_verified": m.email_verified,
                "wallet_address": m.wallet_address,
                "join_date": iso_format(m.join_date),
                "rewards": m.rewards,
                "paid": m.paid,
                "workers": m.workers_name,
                "works": m.works_stats(),
            }
            for m in Miner.paginate(page=page, per_page=per_page, order_by=order_by)
        ]

    @method
    async def admin_list_nodes(request, visa: str, page=0, per_page=50, order_by="authorized, email"):
        admin = get_admin_from_visa(request, visa)
        return [
            {
                "email": node.email,
                "authorized": node.authorized,
                "pow_fee": node.pow_fee,
                "pub_key": node.pub_key,
                "works": node.works_stats()
            }
            for node in ZilNode.paginate(page=page, per_page=per_page, order_by=order_by)
        ]

    @method
    async def admin_rewards(request, visa: str, block_num=None):
        admin = get_admin_from_visa(request, visa)

        blocks_list = utils.block_num_to_list(block_num)

        return get_rewards(blocks_list)


def login(request, email, password):
    ip = get_client_ip(request)
    admin = ZilAdmin.login(email=email, password=password,
                           expire_secs=10*60, ext_data=ip)
    return admin


def get_admin_from_visa(request, visa: str):
    ip = get_client_ip(request)
    admin = ZilAdmin.check_visa(visa=visa, ext_data=ip)
    assert admin, "invalid auth visa"
    return admin


def admin_auth_node(pub_key, approve):
    from zilpool.web import tools

    node = ZilNode.get_by_pub_key(pub_key, authorized=None)
    assert node, "Node not found"

    if approve != node.authorized:
        node = node.update(authorized=approve)
        assert node, "failed to update database"

        action = "Approved" if approve else "Revoked"
        messages = f"Node Register {action}: {node.pub_key}"

        logging.info(messages)

        if node.email:
            tools.send_auth_notification_email(
                node.email, messages=messages
            )

    return node


def get_rewards(blocks_list):
    cur_block_num = PowWork.get_latest_block_num()
    rewards = []
    for block_num in blocks_list:
        if block_num is None:
            block_num = cur_block_num
        if block_num > cur_block_num:
            continue

        block_rewards = PowResult.rewards_by_miners(block_num)
        for r in block_rewards:
            r["date"] = utils.date_format(r["date"])
            r["date_time"] = utils.iso_format(r["date_time"])

        work = PowWork.get_one(block_num=block_num)

        rewards.append({
            "block_num": block_num,
            "date": utils.date_format(work and work.start_time),
            "count": PowWork.count(block_num=block_num),
            "rewards": block_rewards,
        })

    return rewards
