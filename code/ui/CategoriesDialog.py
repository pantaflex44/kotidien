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


class CategoriesDialog(QDialog):

    _settings = None
    _locale = None

    _thirdparties = []

    fi = None
    updated = False

    def __init__(self, settings, locale, fi: financial, parent=None, *args, **kwargs):
        self._settings = settings
        self._locale = locale
        self.fi = fi
        super(CategoriesDialog, self).__init__(parent, Qt.Window |
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
        self.setWindowIcon(QIcon(icons.get('toolbar-category.png')))
        # buttonBox
        self.buttonBox.button(
            QDialogButtonBox.Close).clicked.connect(self.validateForm)
        # cList
        self.populateCList()
        # tpTitle
        self.cTitle.textChanged.connect(self.cTitleChanged)
        # tpCategory
        self.populateCategories()
        # saveButton
        self.saveButton.setIcon(QIcon(icons.get('document-save.png')))
        self.saveButton.clicked.connect(self.saveButtonClicked)
        # removeButton
        self.removeButton.setIcon(QIcon(icons.get('document-delete.png')))
        self.removeButton.clicked.connect(self.removeButtonClicked)
        # clearButton
        self.clearButton.setIcon(QIcon(icons.get('clear.png')))
        self.clearButton.clicked.connect(self.clearButtonClicked)

    def closeEvent(self, event):
        event.ignore()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            obj.setStyleSheet('')
            try:
                obj.setPlaceholderText('')
            except:
                pass
        return super(CategoriesDialog, self).eventFilter(obj, event)

    def validateForm(self):
        self.accept()

    def foundC(self, name: str, parent: str = ''):
        getrow = -1
        getitem = None
        for row in range(self.cList.model().rowCount()):
            item = self.cList.model().itemFromIndex(
                self.cList.model().index(row, 0))
            d = item.data(Qt.UserRole)
            if isinstance(d, list) and \
                d[0].lower() == name.strip().lower() and \
                    ((parent.strip() != '' and
                        d[1].lower() == parent.strip().lower()) or
                     parent.strip() == ''):
                getrow = row
                getitem = item
                break
        return getrow, getitem

    def populateCList(self, selected: str = ''):
        self.cList.setModel(None)
        model = QStandardItemModel()
        model.setColumnCount(1)
        model.setHeaderData(0, QtCore.Qt.Horizontal, funcs.tr(
            "Liste des catégories"))
        for k, v in self.fi.categories.items():
            i = QStandardItem(funcs.tr(k))
            f = i.font()
            f.setBold(True)
            i.setFont(f)
            i.setData([k, ''], Qt.UserRole)
            color, html = funcs.text2color(funcs.tr(k))
            i.setForeground(
                QBrush(QColor.fromRgb(color[0], color[1], color[2])))
            if isinstance(v, list):
                for c in v:
                    j = QStandardItem(funcs.tr(c))
                    j.setData([c, k], Qt.UserRole)
                    j.setForeground(i.foreground())
                    i.appendRow(j)
            model.appendRow(i)
        self.cList.setModel(model)
        self.cList.header().setSectionResizeMode(0, QHeaderView.Stretch)
        f = self.cList.header().font()
        f.setBold(True)
        self.cList.header().setFont(f)
        self.cList.sortByColumn(0, Qt.AscendingOrder)
        self.cList.expandAll()
        self.cList.selectionModel().selectionChanged.connect(self.cListSelected)
        self.cTitle.setFocus()
        if selected.strip() != '':
            row, item = self.foundC(selected)
            if row > -1 and not(self.cList.selectionModel() is None):
                self.cList.setCurrentIndex(self.cList.model().index(row, 0))
                self.cListSelected(item, None)
                self.cList.setFocus()

    def cTitleChanged(self, text):
        row, item = self.foundC(text)
        if row > -1:
            self.cList.setCurrentIndex(self.cList.model().index(row, 0))
        self.saveButton.setEnabled(text.strip() != '')

    def cListSelected(self, new, old):
        self.removeButton.setEnabled(False)
        index = None
        if isinstance(new, QItemSelection):
            if len(new.indexes()) > 0:
                index = new.indexes()[0]
        else:
            index = new.index()
        if not(index is None):
            row = self.cList.model().itemFromIndex(index)
            title, parent = row.data(Qt.UserRole)
            self.cTitle.setText(title)
            i = self.cCategory.findData(parent)
            if i > -1:
                self.cCategory.setCurrentIndex(i)
            self.removeButton.setEnabled(True)
            self.clearButton.setEnabled(True)
        self.saveButton.setEnabled(False)

    def populateCategories(self, selected: str = ''):
        self.cCategory.clear()
        model = QStandardItemModel()
        a = QStandardItem('')
        a.setData('', Qt.UserRole)
        a.setBackground(QBrush(QColor.fromRgb(255, 255, 255)))
        model.appendRow(a)
        for k, v in self.fi.categories.items():
            i = QStandardItem(funcs.tr(k))
            f = i.font()
            f.setBold(True)
            i.setFont(f)
            i.setData(k, Qt.UserRole)
            color, html = funcs.text2color(funcs.tr(k))
            i.setForeground(
                QBrush(QColor.fromRgb(color[0], color[1], color[2])))
            i.setBackground(a.background())
            model.appendRow(i)
        self.cCategory.setModel(model)
        self.cCategory.currentIndexChanged.connect(
            self.cCategoryIndexChanged)
        if selected.strip() != '':
            index = self.cCategory.findData(selected.strip())
            if index == -1:
                index = 0
            self.cCategory.setCurrentIndex(index)

    def cCategoryIndexChanged(self, index):
        self.cTitleChanged(self.cTitle.text())

    def saveButtonClicked(self):
        n = self.cTitle.text().strip()
        c = self.cCategory.currentData(Qt.UserRole)
        if c == '':
            if not(n in self.fi.categories):
                self.fi.categories[n] = []
        else:
            if n in self.fi.categories:
                del self.fi.categories[n]
            if not(n in self.fi.categories[c]):
                self.fi.categories[c].append(n)
        self.updated = True
        self.cTitle.clear()
        self.cCategory.setCurrentIndex(0)
        self.populateCList(n)
        self.populateCategories()

    def removeButtonClicked(self):
        if self.cList.selectionModel() is None:
            self.removeButton.setEnabled(False)
        if len(self.cList.selectionModel().selectedIndexes()) == 0:
            self.removeButton.setEnabled(False)
        selected = self.cList.selectionModel().selectedIndexes()[0]
        item = self.cList.model().itemFromIndex(selected)
        title, parent = item.data(Qt.UserRole)
        reply = QMessageBox.question(self, '' + appinfos.app_name + '', funcs.tr(
            "Etes-vous certain de vouloir supprimer la catégorie '{}'".format(title)),
            QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if parent == '':
                if title in self.fi.categories:
                    del self.fi.categories[title]
                    self.updated = True
            else:
                if (parent in self.fi.categories) and \
                        (title in self.fi.categories[parent]):
                    self.fi.categories[parent].remove(title)
                    self.updated = True
            self.cTitle.clear()
            self.cCategory.setCurrentIndex(0)
            self.populateCList()
            self.populateCategories()

    def clearButtonClicked(self):
        self.cTitle.clear()
        self.cCategory.setCurrentIndex(-1)
        self.cList.selectionModel().clearSelection()
        self.cTitle.setFocus()
        self.clearButton.setEnabled(False)


