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
"""
setup file
"""

from zilpool import version
from setuptools import setup

packages = ["zilpool"]
package_data = {"zilpool": ["*.conf", "tests/*"]}

tests_require = ["pytest"]
install_requires = [
    "pyyaml", "jsonrpcserver", "aiohttp", "jsonrpcclient[aiohttp]",
    "mongoengine", "pymongo",
    "fastecdsa", "pyethash", "eth-hash[pycryptodome]",
    "jinja2", "aiohttp_jinja2",
]

setup(
    name="zilpool",
    version=version,
    description="Zilliqa mining proxy",
    long_description="A mining proxy between Zilliqa nodes and GPU miners",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python"
    ],
    keywords="zil mining proxy pool",
    author="Gully Chen",
    author_email="deepgully@gmail.com",
    url="",
    license="GNU General Public License",
    packages=packages,
    include_package_data=True,
    package_data=package_data,
    install_requires=install_requires,
    tests_require=tests_require,
)
