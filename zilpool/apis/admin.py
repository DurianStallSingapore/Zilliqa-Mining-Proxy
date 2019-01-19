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

from jsonrpcserver import method

from zilpool.common.utils import iso_format, get_client_ip
from zilpool.database.ziladmin import ZilAdmin, SiteSettings


def init_apis(config):
    @method
    async def admin_login(request, email: str, password: str):
        ip = get_client_ip(request)
        admin = ZilAdmin.login(email=email, password=password,
                               expire_secs=10*60, ext_data=ip)
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


def get_admin_from_visa(request, visa: str):
    ip = get_client_ip(request)
    admin = ZilAdmin.check_visa(visa=visa, ext_data=ip)
    assert admin, "invalid auth visa"
    return admin
