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

import sys

from PyQt5.QtWidgets import QCompleter
from PyQt5.QtCore import Qt, QSettings, QStringListModel

completer = None


def get(settings: QSettings):
    global completer
    if completer is None:
        completer = QCompleter(settings.value('completer', []))
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.PopupCompletion)
    return completer


def add(settings: QSettings, value):
    global completer
    l = settings.value('completer', [])
    if not(value in l):
        l.append(value)
    settings.setValue('completer', l)
    settings.sync()
    if not(completer is None):
        completer.setModel(QStringListModel(l, completer))
