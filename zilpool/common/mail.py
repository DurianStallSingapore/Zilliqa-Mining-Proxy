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
import smtplib
from ssl import SSLError
from email.mime.text import MIMEText


class EmailClient:
    admin_email_sender = ""
    admin_email_to_addrs = []
    smtp_config = None

    @classmethod
    def set_config(cls, config):
        cls.admin_email_to_addrs = config["pool"]["admins"]
        cls.admin_email_sender = cls.admin_email_to_addrs[0]
        cls.smtp_config = config["smtp"]

    @classmethod
    def create_client(cls):
        assert cls.smtp_config is not None

        client_kwargs = {
            "host": cls.smtp_config["host"],
            "port": cls.smtp_config["port"],
            "timeout": cls.smtp_config["timeout"]
        }

        try:
            client = smtplib.SMTP_SSL(**client_kwargs)
        except SSLError:
            client = smtplib.SMTP(**client_kwargs)

        if cls.smtp_config["tls"]:
            client.starttls()
            client.ehlo()

        if cls.smtp_config["username"]:
            client.login(cls.smtp_config["username"],
                         cls.smtp_config["password"])

        return client

    @classmethod
    def send_mail(cls, sender: str, to_addrs, subject: str, msg: str, **kwargs):
        if isinstance(to_addrs, str):
            to_addrs = [to_addrs, ]
        msg = MIMEText(msg, **kwargs)
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = ",".join(to_addrs)

        if cls.smtp_config["debug"]:
            logging.info(f"Debug SMTP Server got a mail:")
            logging.info(msg.as_string())
            return

        client = cls.create_client()
        try:
            client.sendmail(sender, to_addrs, msg.as_string())
            client.quit()
        finally:
            client.close()

    @classmethod
    def send_admin_mail(cls, to_addrs, subject: str, msg: str, **kwargs):
        return cls.send_mail(cls.admin_email_sender, to_addrs, subject, msg, **kwargs)
