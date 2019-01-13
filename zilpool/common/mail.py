# -*- coding: utf-8 -*-
# Zilliqa Mining Pool
# Copyright  @ 2018-2019 Gully Chen
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

import smtplib
import asyncio
from ssl import SSLError
from email.mime.text import MIMEText
from .utils import run_in_thread


class EmailClient:
    smtp_config = None

    @classmethod
    def set_config(cls, config):
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
            print(f"fake smtp server:")
            print(msg.as_string())
            return

        client = cls.create_client()
        try:
            client.sendmail(sender, to_addrs, msg.as_string())
            client.quit()
        finally:
            client.close()
