# -*- coding: utf-8 -*-
"""
zilpool setup file

Copyright 2018, Gully Chen.
Licensed under Apache License, Version 2.0.
"""

from zilpool import version
from setuptools import setup, find_packages

packages = find_packages(exclude=[])

install_requires = ["pyyaml", "jsonrpcserver", "aiohttp", "pyMongo"]

setup(name="zilpool",
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
      zip_safe=False,
      install_requires=install_requires,
      )
