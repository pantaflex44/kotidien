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
import json
from datetime import datetime
import pkg_resources

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from sip import SIP_VERSION_STR

import libs.pycountry
import currency

import libs.completer
import resources
import appinfos
import funcs
import icons
import globalsv

from datamodels import *


class QHLine(QFrame):

    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class AboutDialog(QDialog):

    _settings = None
    _locale = None

    def __init__(self, settings, locale, parent=None, *args, **kwargs):
        self._settings = settings
        self._locale = locale
        super(AboutDialog, self).__init__(parent, Qt.Window |
                                          Qt.WindowTitleHint | Qt.CustomizeWindowHint, *args, **kwargs)
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
        self.setWindowIcon(QIcon(icons.get('about.png')))
        self.tabWidget.setCurrentIndex(0)

        row = 0
        grid_licence = QGridLayout()
        grid_authors = QGridLayout()
        for module in globalsv.modules:

            # licences
            lbl1 = QLabel()
            lbl1.setText('<p><b>{} {}</b></p>'.format(module[0], module[1]))
            grid_licence.addWidget(lbl1, row, 0, 1, 1, Qt.AlignLeft | Qt.AlignVCenter)
            lbl2 = QLabel()
            lbl2.setText('<p><a href="{}"><span style="text-decoration: underline; color:#2980b9;">{}</span></a></p>'.format(module[2][1], module[2][0]))
            lbl2.setOpenExternalLinks(True)
            grid_licence.addWidget(lbl2, row, 1, 1, 1, Qt.AlignLeft | Qt.AlignVCenter)
            grid_licence.addWidget(QHLine(), row + 1, 0, 1, 2, Qt.AlignLeft | Qt.AlignVCenter)

            # authors
            lbl3 = QLabel()
            lbl3.setText('<p><b>{} {}</b></p>'.format(module[0], module[1]))
            grid_authors.addWidget(lbl3, row, 0, 1, 1, Qt.AlignLeft | Qt.AlignTop)
            lbl4 = QLabel()
            lbl4.setText('<p>{}<br/>&lt;<a href="{}"><span style=" text-decoration: underline; color:#2980b9;">{}</span></a>&gt;<br/><a href="{}"><span style="text-decoration: underline; color:#2980b9;">{}</span></a></p>'.format(module[3][0], module[3][1], module[3][1], module[3][2], module[3][2]))
            lbl4.setOpenExternalLinks(True)
            grid_authors.addWidget(lbl4, row, 1, 1, 1, Qt.AlignLeft | Qt.AlignTop)
            grid_authors.addWidget(QHLine(), row + 1, 0, 1, 2, Qt.AlignLeft | Qt.AlignVCenter)

            row += 2

        w_licence = QWidget()
        w_licence.setLayout(grid_licence)
        w_licence.setStyleSheet('background: #fff;')
        self.licenceList.setWidget(w_licence)

        w_authors = QWidget()
        w_authors.setLayout(grid_authors)
        w_authors.setStyleSheet('background: #fff;')
        self.authorsList.setWidget(w_authors)

        # changelog
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cl_filepath = os.path.join(application_path, 'CHANGELOG.md')
        if os.path.exists(cl_filepath):
            with open(cl_filepath, 'r') as f:
                try:
                    self.changelogEdit.setMarkdown(f.read())
                except:
                    self.changelogEdit.setText(f.read())
