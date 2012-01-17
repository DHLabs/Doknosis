#!/usr/bin/env python
# encoding: utf-8
"""
main.py

Created by Andrew Huynh on 2012-01-17.
Copyright (c) 2011 athlabs. All rights reserved.
"""
from server import create_app

if __name__ == '__main__':
    MAIN = create_app()
    MAIN.run()