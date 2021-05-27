#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
@package Kotidien.ui
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
import os

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *


class QSettingsEx(QSettings):

	_default_params = {}

	def __init__(self, filepath:str, default_params:dict):
		self._default_params = default_params
		super(QSettingsEx, self).__init__(filepath, QSettings.IniFormat)

	def value(self, key:str, default=None):
		if default is None:
			default = QVariant()
			if key in self._default_params:
				default = self._default_params[key]

		ret = super(QSettingsEx, self).value(key, default)
		if type(default) == bool:
			ret = (str(ret).lower() == 'true')

		return ret

