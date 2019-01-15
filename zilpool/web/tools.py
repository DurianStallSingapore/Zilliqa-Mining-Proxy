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
from urllib.parse import urljoin

from zilpool.database import ziladmin, zilnode
from zilpool.common.mail import EmailClient


def verify_url_for(config, action, token):
    """ generate token verify link, must be synced with web handlers """
    site_url = config["api_server"]["website"]["url"]

    return urljoin(site_url, f"verify/{action}/{token}")


def send_email_verification(config, user_email, rule, ext_data=None):
    subject = "Verify your email address"
    site_title = config["pool"]["title"]

    action = f"verify_{rule}_email"
    expire_secs = 24 * 3600
    if ext_data is None:
        ext_data = {}
    ext_data.update({
        "email": user_email
    })

    token = ziladmin.ZilAdminToken.create_token(action, ext_data=ext_data, expire_secs=expire_secs)
    if not token:
        logging.warning(f"failed to create {action} token")
        return False

    email_verify_link = verify_url_for(config, action, token)

    body = f"Thanks for joining {site_title}, " \
           f"please verify your email address {user_email}" \
           f" by clicking\n{email_verify_link}"

    EmailClient.send_admin_mail(to_addrs=user_email, subject=subject, msg=body)
    return True


def send_approve_require_email(config, user_email, pub_keys):
    if not pub_keys:
        logging.warning(f"no public key to approve")
        return False

    owner = zilnode.ZilNodeOwner.get_one(email=user_email)
    if not owner:
        logging.warning(f"{user_email} not exists")
        return False

    subject = "Node Register Request"
    admin_emails = config["pool"]["admins"]
    site_title = config["pool"]["title"]

    approve_action = "approve_nodes"
    reject_action = "reject_nodes"
    expire_secs = 48 * 3600
    ext_data = {
        "email": user_email,
        "pub_keys": pub_keys,
    }

    # create temp token for admin
    approve_token = ziladmin.ZilAdminToken.create_token(
        approve_action, ext_data=ext_data, expire_secs=expire_secs
    )
    if not approve_token:
        logging.warning(f"failed to create {approve_action} token")
        return False
    approve_link = verify_url_for(config, approve_action, approve_token)

    reject_token = ziladmin.ZilAdminToken.create_token(
        reject_action, ext_data=ext_data, expire_secs=expire_secs
    )
    if not approve_token:
        logging.warning(f"failed to create {reject_action} token")
        return False
    reject_link = verify_url_for(config, reject_action, reject_token)

    body = f"{user_email} requests {len(pub_keys)} " \
           f"Nodes to join {site_title}." \
           f"\n\nApprove by clicking\n{approve_link}" \
           f"\n\nReject by clicking\n{reject_link}" \
           f"\n\nNodes Public Keys:\n"

    body += "\n".join(pub_keys)

    EmailClient.send_admin_mail(to_addrs=admin_emails,
                                subject=subject, msg=body)
    return True


def send_auth_notification_email(user_email, messages):
    subject = "Zilliqa Nodes Register Notification"
    EmailClient.send_admin_mail(
        to_addrs=user_email, subject=subject, msg=messages
    )


def verify_token(token, action):
    admin_token = ziladmin.ZilAdminToken.verify_token(token, action)
    if not admin_token:
        return False, "invalid or expired token"

    try:
        return admin_token.do_action()
    except Exception as e:
        return False, str(e)
