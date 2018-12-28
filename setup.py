# -*- coding: utf-8 -*-
"""
zilpool setup file

Copyright 2018, Gully Chen.
Licensed under Apache License, Version 2.0.
"""

from zilpool import version
from setuptools import setup

packages = ["zilpool"]
package_data = {"zilpool": ["*.conf", "tests/*"]}

tests_require = ["pytest"]
install_requires = [
    "pyyaml", "jsonrpcserver", "aiohttp", "jsonrpcclient[aiohttp]",
    "mongoengine", "pymongo",
    "coincurve", "pyethash", "eth-hash[pycryptodome]",
]

setup(
    name="zilpool",
    version=version,
    description="Zilliqa mining pool",
    long_description="A pool proxy between Zilliqa node and GPU miners",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python"
    ],
    keywords="zil mining pool",
    author="Gully Chen",
    author_email="deepgully@gmail.com",
    url="",
    license="Apache Software License",
    packages=packages,
    include_package_data=True,
    package_data=package_data,
    install_requires=install_requires,
    tests_require=tests_require,
)
