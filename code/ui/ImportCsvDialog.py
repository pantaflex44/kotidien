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

from ui.CsvFormatDialog import CsvFormatDialog


class HTMLDelegate(QStyledItemDelegate):

    def __init__(self, parent, settings):
        super(HTMLDelegate, self).__init__(parent)
        self.pen = QPen(QColor(Qt.lightGray))
        self._settings = settings

    def paint(self, painter, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        style = QApplication.style() if options.widget is None else options.widget.style()
        painter.save()

        ctx = QAbstractTextDocumentLayout.PaintContext()
        mouseOver = (option.state & QStyle.State_MouseOver)

        if type(options.widget) == QTreeView:
            if mouseOver and options.widget.objectName() == 'opeList':
                viewportPos = options.widget.viewport().mapFromGlobal(QCursor.pos())
                if viewportPos.x() >= 0 and viewportPos.y() >= 0:
                    color = option.palette.color(QPalette.Active, QPalette.Highlight)
                    color.setAlpha(30)
                    painter.fillRect(option.rect, color)

        style.drawControl(QStyle.CE_ItemViewItem, options, painter)
        painter.restore()

    def sizeHint(self, option, index):
        size = super(HTMLDelegate, self).sizeHint(option, index)
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        return size


class ImportCsvDialog(QDialog):

    _settings = None
    _locale = None

    _delimiter = ';'
    _decimal = ','
    _dateformat = '%x'
    _file = ''
    _fi = None

    def __init__(self, settings, locale, fi: financial, file:str=None, parent=None, *args, **kwargs):
        self._settings = settings
        self._locale = locale
        self._fi = fi
        self._file = file
        super(ImportCsvDialog, self).__init__(parent, Qt.Window
                                           | Qt.WindowTitleHint | Qt.CustomizeWindowHint, *args, **kwargs)
        self._init_ui()
        self.setWindowTitle(os.path.basename(self._file))
        self.populateAccountsList()
        self.openCsvFile()

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
        self.setWindowIcon(QIcon(icons.get('import.png')))
        self.setMouseTracking(True)
        # buttonBox
        self.buttonBox.button(QDialogButtonBox.Ok).clicked.connect(self.validateForm)
        # links
        self.selectAll.linkActivated.connect(self.selectCmdClicked)
        self.unselectAll.linkActivated.connect(self.selectCmdClicked)
        # opeList
        self.opeList.viewport().setMouseTracking(True)

    def closeEvent(self, event):
        event.ignore()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            obj.setStyleSheet('')
            try:
                obj.setPlaceholderText('')
            except:
                pass
        return super(ImportCsvDialog, self).eventFilter(obj, event)

    def populateAccountsList(self):
        self.accountsList.clear()
        model = QStandardItemModel()

        r = QStandardItem('')
        r.setData(None, Qt.UserRole)
        r.setBackground(QColor(Qt.white))
        model.appendRow(r)
        for a in self._fi.accounts:
            if not(type(a) == bankaccount):
                continue

            t = a.title.strip()
            n = a.name.strip() if hasattr(a, 'name') and a.name.strip() != '' else ''
            if n != '':
                t = t + ' (' + n + ')'
            r = QStandardItem(t)
            r.setData(a, Qt.UserRole)
            r.setBackground(QColor(Qt.white))
            model.appendRow(r)

        self.accountsList.setModel(model)

    def openCsvFile(self):
        if not os.path.isfile(self._file) or \
           not os.access(self._file, os.R_OK):
            QMessageBox.critical(self, appinfos.app_name, funcs.tr(
                "Impossible de lire le catalogue de données sélectionné!"))
            self.reject()

        self._delimiter = self._settings.value('Export/csv_separator')
        self._decimal = self._settings.value('Export/csv_decimal')
        self._dateformat = self._settings.value('Export/csv_dateformat')
        cfd = CsvFormatDialog(self._settings,
                              self._locale,
                              parent=self)
        if cfd.exec_() == QDialog.Accepted:
            self._delimiter = cfd.delimiter
            self._decimal = cfd.decimal
            self._dateformat = cfd.dateformat
        cfd.destroy()

        try:
            with open(self._file, mode='r', encoding='utf-8', errors='ignore') as csvfile:
                reader = csv.reader(csvfile, delimiter=self._delimiter)
                columns = reader.__next__()

                self.opeList.setModel(None)

                m = QStandardItemModel()
                m.setColumnCount(len(columns))
                for i in range(len(columns)):
                    m.setHeaderData(i, QtCore.Qt.Horizontal, columns[i])

                for row in reader:
                    data = dict(zip(columns, row))
                    items = []
                    for j in range(len(row)):
                        r = QStandardItem()
                        r.setText(row[j])
                        r.setEditable(False)
                        r.setData(data, Qt.UserRole)
                        if j == 0:
                            r.setCheckable(True)
                            r.setCheckState(Qt.Checked)
                        items.append(r)
                    m.appendRow(items)

                self.opeList.setModel(m)
                self.opeList.setItemDelegate(HTMLDelegate(parent=None, settings=self._settings))

                for i in range(len(columns)):
                    self.opeList.resizeColumnToContents(i)

            self.populateColumns(columns)
        except:
            QMessageBox.critical(self, appinfos.app_name, funcs.tr(
                "Impossible de lire les données à importer."))
            self.destroy()

    def selectItem(self, item, state:bool):
        item.setCheckState(Qt.Checked if state else Qt.Unchecked)
        for i in range(item.rowCount()):
            child = item.child(i)
            self.selectItem(child, state)

    def selectCmdClicked(self, cmd):
        if not(self.opeList.model() is None) and not(self.opeList.model().invisibleRootItem() is None):
            self.selectItem(self.opeList.model().invisibleRootItem(), cmd == 'selectall')

    def populateCombo(self, cbx:QComboBox, l:list, selectedText:list=[]):
        cbx.clear()
        model = QStandardItemModel()
        selectedIdx = 0
        for n in range(len(l)):
            if isinstance(l[n], list) and len(l[n]) >= 2:
                t = str(l[n][0])
                d = l[n][1]
                if t.strip().lower() in selectedText:
                    selectedIdx = n
                a = QStandardItem(t)
                a.setData(d, Qt.UserRole)
                model.appendRow(a)
        cbx.setModel(model)
        cbx.setCurrentIndex(selectedIdx)
        cbx.currentIndexChanged.connect(lambda index: self.cbsIndexChanged(cbx, index))

    def populateColumns(self, columns:list):
        l = [['', None]]
        for c in columns:
            l.append([c, c])
        self.populateCombo(self.linkDate, l, ['date'])
        self.populateCombo(self.linkName, l, ['libellé', 'libell', 'nom', 'name', 'tiers', 'to'])
        self.populateCombo(self.linkMemo, l, ['mémo', 'mmo', 'memo'])
        self.populateCombo(self.linkComment, l, ['commentaire', 'commentaires', 'comment', 'comments'])
        self.populateCombo(self.linkType, l, ['type', 'paytype'])
        self.populateCombo(self.linkCat, l, ['catégorie', 'catgorie', 'category'])
        self.populateCombo(self.linkAmount, l, ['montant', 'price'])

    def cbsIndexChanged(self, cbx:QComboBox, index):
        t = cbx.currentText()
        exists = False
        if (not(cbx is self.linkDate) and self.linkDate.currentText() == t and self.linkDate.currentText() != '') or \
           (not(cbx is self.linkName) and self.linkName.currentText() == t and self.linkName.currentText() != '') or \
           (not(cbx is self.linkMemo) and self.linkMemo.currentText() == t and self.linkMemo.currentText() != '') or \
           (not(cbx is self.linkComment) and self.linkComment.currentText() == t and self.linkComment.currentText() != '') or \
           (not(cbx is self.linkType) and self.linkType.currentText() == t and self.linkType.currentText() != '') or \
           (not(cbx is self.linkCat) and self.linkCat.currentText() == t and self.linkCat.currentText() != '') or \
           (not(cbx is self.linkAmount) and self.linkAmount.currentText() == t and self.linkAmount.currentText() != ''):
            exists = True
        if exists:
            cbx.setCurrentIndex(0)
            QMessageBox.warning(self, appinfos.app_name, funcs.tr(
                "Une correspondance existe déjà!"))

    def validateForm(self):
        datas = []
        model = self.opeList.model()
        checked = model.match(
            model.index(0, 0), Qt.CheckStateRole, Qt.Checked, -1,
            Qt.MatchExactly | Qt.MatchRecursive)
        for index in checked:
            item = model.itemFromIndex(index)
            datas.append(item.data(Qt.UserRole))
        if len(datas) == 0:
            QMessageBox.warning(self, appinfos.app_name, funcs.tr(
                "<b>Erreur</b><br />Veuillez cocher les transactions à importer."))
            return

        acct = self.accountsList.currentData()
        if acct is None:
            QMessageBox.warning(self, appinfos.app_name, funcs.tr(
                "<b>Erreur</b><br />Veuillez sélectionner le compte concerné par les données à importer."))
            return

        keys = { 'fromdate': self.linkDate.currentText(),
                 'to': self.linkName.currentText(),
                 'amount': self.linkAmount.currentText(),
                 'memo': self.linkMemo.currentText(),
                 'comment': self.linkComment.currentText(),
                 'paytype': self.linkType.currentText(),
                 'category': self.linkCat.currentText() }
        if keys['fromdate'] == '':
            QMessageBox.warning(self, appinfos.app_name, funcs.tr(
                "<b>Erreur</b><br />Veuillez définir la correspondance des données de type 'Date'."))
            return
        if keys['to'] == '':
            QMessageBox.warning(self, appinfos.app_name, funcs.tr(
                "<b>Erreur</b><br />Veuillez définir la correspondance des données de type 'Tiers'."))
            return
        if keys['amount'] == '':
            QMessageBox.warning(self, appinfos.app_name, funcs.tr(
                "<b>Erreur</b><br />Veuillez définir la correspondance des données de type 'Montant'."))
            return

        for d in datas:
            paytype = d[keys['paytype']].strip() if keys['paytype'] in d and keys['paytype'] != '' else funcs.tr("Transaction diverse")
            if paytype != '' and not(paytype in self._fi.paytypes):
                self._fi.paytypes.append(paytype)

            category = d[keys['category']].strip() if keys['category'] in d and keys['category'] != '' else funcs.tr("Importation")
            if category != '':
                pc = category.split(':')
                p = pc[0].strip()
                c = pc[1].strip() if len(pc) > 1 else ''
                category = p
                if not(p in self._fi.categories.keys()):
                    self._fi.categories[p] = []
                if c != '':
                    category += ': ' + c
                    if not(c in self._fi.categories[p]):
                        self._fi.categories[p].append(c)

            fromdate = datetime.strptime(d[keys['fromdate']].strip(), self._dateformat).date()

            amount = float(d[keys['amount']].strip().replace(self._decimal, '.'))

            to = d[keys['to']].strip()

            memo = d[keys['memo']].strip() if keys['memo'] in d and keys['memo'] != '' else to
            comment = d[keys['comment']].strip() if keys['comment'] in d and keys['comment'] != '' else ''

            if paytype == 'Transfert':
                aid = d['ID'].strip() if 'ID' in d else ''
                try:
                    aid = float(aid)
                except:
                    aid = -1

                ta = None
                for a in self._fi.accounts:
                    if a.id == aid:
                        ta = a
                        break
                if not(ta is None):
                    fromactid = -1
                    toactid = -1
                    if amount < 0:
                        toactid = ta.id
                        fromactid = acct.id
                    else:
                        fromactid = ta.id
                        toactid = acct.id
                    if fromactid != -1 and toactid != -1:
                        amount = abs(amount)
                        t = transfer(title=memo,
                                     amount=amount,
                                     fromdate=fromdate,
                                     comment=comment,
                                     fromactid=fromactid,
                                     toactid=toactid,
                                     state=False)
                        self._fi.transfers.append(t)
            else:
                o = operation(title=memo,
                              amount=amount,
                              fromdate=fromdate,
                              comment=comment,
                              to=to,
                              paytype=paytype,
                              category=category,
                              state=False)
                acct.operations.append(o)

        self.accept()
