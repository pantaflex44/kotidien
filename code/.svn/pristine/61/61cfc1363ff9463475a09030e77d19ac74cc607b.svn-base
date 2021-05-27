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
import csv
from datetime import datetime

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import libs.pycountry
import currency

import libs.completer
import resources
import appinfos
import funcs
import icons

from datamodels import *


class CsvFormatDialog(QDialog):

    _settings = None
    _locale = None

    delimiter = ';'
    decimal = ','
    dateformat = '%x'


    def __init__(self, settings, locale, parent=None, *args, **kwargs):
        self._settings = settings
        self._locale = locale
        self.delimiter = self._settings.value('Export/csv_separator')
        self.decimal = self._settings.value('Export/csv_decimal')
        self.dateformat = self._settings.value('Export/csv_dateformat')
        super(CsvFormatDialog, self).__init__(parent, Qt.Window
                                           | Qt.WindowTitleHint | Qt.CustomizeWindowHint, *args, **kwargs)
        self._init_ui()

    def _init_ui(self):
        # self
        self.ui = funcs.loadUiResource(funcs.rc('/ui/' + self.__class__.__name__ + '.ui'), self)
        self.setLocale(QLocale(self._locale))
        self.ui.setLocale(QLocale(self._locale))
        self.setModal(True)
        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().geometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())
        self.setFixedSize(self.size())
        self.setWindowIcon(QIcon(icons.get('csv.png')))
        # buttonBox
        self.buttonBox.button(
            QDialogButtonBox.Ok).clicked.connect(self.validateForm)
        self.delimiterEdit.setText(self.delimiter)
        self.decimalEdit.setText(self.decimal)
        self.dateformatEdit.textChanged.connect(self.dateformatChanged)
        self.dateformatEdit.setText(self.dateformat)

    def closeEvent(self, event):
        event.ignore()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            obj.setStyleSheet('')
            try:
                obj.setPlaceholderText('')
            except:
                pass
        return super(CsvFormatDialog, self).eventFilter(obj, event)

    def dateformatChanged(self, text):
        try:
            dt = datetime.now().strftime(text)
            self.dateformatTestLabel.setText("<small>➲ {}</small>".format(dt))
        except:
            self.dateformatTestLabel.setText(funcs.tr("<small><i>Erreur de format</i></small>"))

    def validateForm(self):
        self.delimiter = self.delimiterEdit.text().strip()
        self.decimal = self.decimalEdit.text().strip()
        self.dateformat = self.dateformatEdit.text().strip()
        self.accept()
