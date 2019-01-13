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

import logging

from zilpool.database import ziladmin, zilnode
from zilpool.common.mail import EmailClient


def send_email_verification(config, user_email, rule):
    owner = zilnode.ZilNodeOwner.get_one(email=user_email)
    if not owner:
        logging.warning(f"{user_email} not exists")
        return False

    subject = "Verify your email address"
    admin = config["pool"]["admin"]
    site_title = config["pool"]["title"]
    site_url = config["api_server"]["website"]["url"]
    code = owner.create_verify_code(expire_secs=48*3600)

    email_verify_link = f"{site_url}verify/{rule}/email/{code}"

    body = f"Thanks for joining {site_title}, " \
           f"please verify your email address {user_email}" \
           f" by clicking\n{email_verify_link}"

    EmailClient.send_mail(sender=admin, to_addrs=user_email, subject=subject, msg=body)
    return True


def verify_code(rule, action, code):
    if rule == "node":
        obj = zilnode.ZilNodeOwner.check_verify_code(code)
    else:
        raise NotImplementedError

    if not obj:
        return False

    if action == "email":
        return obj.update(email_verified=True)
    else:
        raise NotImplementedError


def send_approve_require_email(config, user_email, pub_key):
    if not pub_key:
        return False

    owner = zilnode.ZilNodeOwner.get_one(email=user_email)
    if not owner:
        logging.warning(f"{user_email} not exists")
        return False

    subject = "Node Register Request"
    admin_email = config["pool"]["admin"]
    site_title = config["pool"]["title"]
    site_url = config["api_server"]["website"]["url"]

    # create temp token for admin
    token = ziladmin.ZilAdminToken.create_token(admin_email, "node_register",
                                                ext_data=pub_key)
    if not token:
        logging.warning("failed to create admin token")
        return False

    admin_pending_link = f"{site_url}admin/pending?token={token}&pub_key={pub_key}"

    body = f"A node has requests to join {site_title} from {user_email}," \
           f" the public key is {pub_key}. " \
           f" \nApprove by clicking\n{admin_pending_link}&action=approve" \
           f" \nReject by clicking\n{admin_pending_link}&action=reject"

    EmailClient.send_mail(sender=admin_email, to_addrs=admin_email,
                          subject=subject, msg=body)
    return True


def approve_node_register(token, pub_key, approve=False):
    admin_token = ziladmin.ZilAdminToken.check_token(token, "node_register")
    if not admin_token:
        raise Exception("unauthorized or expired admin token")

    if pub_key != admin_token.ext_data:
        raise Exception("public key mismatch")

    node = zilnode.ZilNode.get_by_pub_key(pub_key, authorized=None)
    if not node:
        raise Exception("node not found")

    if not node.update(authorized=approve):
        raise Exception("failed to update node")

    owner = zilnode.ZilNodeOwner.get_one(email=node.email)
    if owner:
        owner.node_approved(pub_key)

    admin_token.delete()

    return node.authorized
