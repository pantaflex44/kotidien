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

import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


def get_key(password: str):
    digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    digest.update(bytes(password, encoding='utf8'))
    return base64.urlsafe_b64encode(digest.finalize())


def encrypt(password: str, token: bytes):
    f = Fernet(get_key(password))
    return f.encrypt(token)


def decrypt(password: str, token: bytes):
    f = Fernet(get_key(password))
    return f.decrypt(token)
