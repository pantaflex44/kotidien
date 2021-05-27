#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
@package Kotidien
"""
"""
Kotidien - Finances personnelles assistées par ordinateur
Copyright (C) 2020-2021 Christophe LEMOINE

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import appinfos
import funcs

items = {}


def init():
    global items
    items = {}


def set(filename: str, current: str, default: str):
    global items
    items[filename] = {'current': current, 'default': default}


def get(filename: str):
    global items
    if filename in items:
        return items[filename]['current']
    return funcs.rc('/ui/icons/' + filename)


def get_default(filename: str):
    global items
    if filename in items:
        return items[filename]['default']
    return funcs.rc('/ui/icons/' + filename)
