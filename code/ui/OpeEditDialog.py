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

import libs.currencies
import libs.completer
import resources
import appinfos
import funcs
import icons

from datamodels import *


class OpeEditDialog(QDialog):

    _settings = None
    _locale = None
    _fi = None
    _act = None

    ope = None

    added = pyqtSignal()

    def __init__(self, settings, locale, parent, fi: financial, act: account, ope: operation = None, nokeep=False, *args, **kwargs):
        self._settings = settings
        self._locale = locale
        self._fi = fi
        self._act = act
        self.ope = ope
        self._nokeep = nokeep
        self._shortDateFormat = self._settings.value('short_date_format')
        self._longDateFormat = self._settings.value('long_date_format')
        super(OpeEditDialog, self).__init__(parent, Qt.Window |
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
        self.setWindowIcon(QIcon(icons.get('operation.png')))
        # buttonBox
        self.buttonBox.button(
            QDialogButtonBox.Save).clicked.connect(self.validateForm)
        # opeFromdate
        self.opeFromdate.dateChanged.connect(self.dateChanged)
        self.opeFromdate.setDate(datetime.now())
        # opeTo
        self.populateThirdparties()
        # opePaytype
        self.populatePaytypes()
        # opeCategory
        self.populateCategories()
        # opeActualCredit
        self.opeActualCredit.setText(libs.currencies.formatCurrency(
            abs(self._act.credit), self._act.alpha_3))
        # opeAmount
        self.opeAmount.setPrefix(currency.symbol(self._act.alpha_3) + ' ')
        self.opeAmount.valueChanged.connect(self.amountChanged)
        self.opeAmount.installEventFilter(self)
        # opeTitle
        self.opeTitle.setCompleter(libs.completer.get(self._settings))
        # opeComment
        self.opeComment.setCompleter(libs.completer.get(self._settings))
        # saveKeepButton
        self.saveKeepButton.setIcon(QIcon(icons.get('document-save.png')))
        self.saveKeepButton.clicked.connect(
            lambda: self.validateForm(keep=True))
        if not(self.ope is None) or self._nokeep:
            self.saveKeepButton.setVisible(False)

        if not(self.ope is None):
            self.opeTo.setCurrentText(self.ope.to)
            self.opeTitle.setText(self.ope.title)
            self.opeComment.setText(self.ope.comment)
            self.opeCategory.setCurrentText(self.ope.category)
            self.opePaytype.setCurrentText(self.ope.paytype)
            self.opeState.setChecked(self.ope.state)
            self.opeAmount.setValue(self.ope.amount)
            self.opeFromdate.setDate(self.ope.fromdate)

    def closeEvent(self, event):
        event.ignore()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            obj.setStyleSheet('')
            try:
                obj.setPlaceholderText('')
            except:
                pass

        if obj == self.opeAmount:
            if event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_Period:
                    event = QKeyEvent(event.type(),
                                      Qt.Key_Comma,
                                      event.modifiers(),
                                      ",",
                                      event.isAutoRepeat(),
                                      event.count())
                    QApplication.sendEvent(obj, event)
                    return True

        return super(OpeEditDialog, self).eventFilter(obj, event)

    def amountChanged(self, value):
        if value < 0 and abs(value) > self.amountmax:
            self.opeAmount.setStyleSheet(
                "#opeAmount { background: #FFF0F5; }")
        else:
            self.opeAmount.setStyleSheet("")

    def dateChanged(self, dte):
        amt = self._fi.amount_atdate(self._act.id, dte)
        self.opeActualAmount.setText(
            libs.currencies.formatCurrency(amt, self._act.alpha_3))
        if amt < 0.0:
            self.opeActualAmount.setStyleSheet(
                "#opeActualAmount { color: " + self._settings.value('color_negative_amount') + "; }")
        if amt < self._act.credit:
            self.opeActualAmount.setStyleSheet(
                "#opeActualAmount { color: " + self._settings.value('color_credit_amount') + "; }")
        if amt >= 0.0:
            self.opeActualAmount.setStyleSheet(
                "#opeActualAmount { color: " + self._settings.value('color_positive_amount') + "; }")
        self.amountmax = amt + abs(self._act.credit)
        self.amountChanged(self.opeAmount.value())

    def populateThirdparties(self):
        self.opeTo.clear()
        model = QStandardItemModel()
        a = QStandardItem('')
        a.setData(None, Qt.UserRole)
        model.appendRow(a)
        for tp in self._fi.thirdparties:
            i = QStandardItem(funcs.tr(tp.title))
            i.setData(tp, Qt.UserRole)
            model.appendRow(i)
        self.opeTo.setModel(model)
        self.opeTo.currentIndexChanged.connect(self.opeToIndexChanged)
        self.opeTo.setCurrentIndex(0)

    def opeToIndexChanged(self, index):
        tp = self.opeTo.currentData(Qt.UserRole)
        if not(tp is None) and isinstance(tp, thirdparty):
            self.opeCategory.setCurrentText(tp.category)
            self.opePaytype.setCurrentText(tp.paytype)

    def populatePaytypes(self):
        self.opePaytype.clear()
        model = QStandardItemModel()
        a = QStandardItem('')
        a.setData('', Qt.UserRole)
        model.appendRow(a)
        for pt in self._fi.paytypes:
            i = QStandardItem(funcs.tr(pt))
            i.setData(pt, Qt.UserRole)
            model.appendRow(i)
        self.opePaytype.setModel(model)
        self.opePaytype.setCurrentIndex(0)

    def populateCategories(self):
        self.opeCategory.clear()
        model = QStandardItemModel()
        a = QStandardItem('')
        a.setData('', Qt.UserRole)
        a.setBackground(QBrush(QColor.fromRgb(255, 255, 255)))
        model.appendRow(a)
        for k, v in self._fi.categories.items():
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
            if isinstance(v, list):
                for c in v:
                    j = QStandardItem(funcs.tr(k) + ": " + funcs.tr(c))
                    j.setData(k + ": " + c, Qt.UserRole)
                    j.setForeground(i.foreground())
                    j.setBackground(a.background())
                    model.appendRow(j)
        self.opeCategory.setModel(model)
        self.opeCategory.setCurrentIndex(0)

    def validateForm(self, keep=False):
        # thirdparty
        to = self.opeTo.currentText().strip()
        if to == '':
            QMessageBox.warning(self, '' + appinfos.app_name + '', funcs.tr(
                "Vous avez oublié de définir le tiers, destinataire de cette opération!"))
            return
        # category
        category = self.opeCategory.currentText().strip()
        if category == '':
            QMessageBox.warning(self, '' + appinfos.app_name + '', funcs.tr(
                "Vous avez oublié de définir une catégorie pour cette opération!"))
            return
        # paytype
        paytype = self.opePaytype.currentText().strip()
        if paytype == '':
            QMessageBox.warning(self, '' + appinfos.app_name + '', funcs.tr(
                "Vous avez oublié de définir un moyen de paiement pour cette opération!"))
            return
        # add new thierparty?
        exists = False
        for tp in self._fi.thirdparties:
            if to.lower() == tp.title.lower():
                to = tp.title
                exists = True
                break
        if not exists:
            reply = QMessageBox.question(self, '' + appinfos.app_name + '', funcs.tr(
                "Enregistrer le nouveau tiers '{}' sous la catégorie '{}' avec le moyen de paiement '{}'?".format(
                    to, category, paytype)),
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                tp = thirdparty(to, category, paytype)
                self._fi.thirdparties.append(tp)
        # add new paytype?
        if not(paytype.lower() in map(str.lower, self._fi.paytypes)):
            reply = QMessageBox.question(self, '' + appinfos.app_name + '', funcs.tr(
                "Enregistrer le nouveau moyen de paiement '{}'?".format(paytype)),
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self._fi.paytypes.append(paytype)
        # add new category?
        prt = ''
        cat = category.split(':')
        if len(cat) > 1:
            prt = cat[0].strip()
            cat.pop(0)
            cat = (':'.join(cat)).strip()
        if prt == '':
            prt = cat[0] if type(cat) == list else str(cat)
            cat = ''
        exists = False
        for k, v in self._fi.categories.items():
            if (prt.lower() == k.lower()) and (cat != ''):
                if not(cat.lower() in map(str.lower, v)):
                    reply == QMessageBox.question(self, '' + appinfos.app_name + '', funcs.tr(
                        "Enregistrer la nouvelle categorie '{}'?".format(category)),
                        QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        self._fi.paytypes.categories[k].append(cat)
                exists = True
                break
            elif (prt.lower() == k.lower()) and (cat == ''):
                exists = True
                break
        if not exists:
            reply == QMessageBox.question(self, '' + appinfos.app_name + '', funcs.tr(
                "Enregistrer la nouvelle categorie '{}'?".format(category)),
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self._fi.categories[prt] = []
                if cat != '':
                    self._fi.categories[prt].append(cat)
        # title
        title = self.opeTitle.text().strip()
        # comment
        comment = self.opeComment.text().strip()
        # fromdate
        fromdate = self.opeFromdate.date().toPyDate()
        # amount
        amt = self.opeAmount.value()
        # state
        state = self.opeState.isChecked()

        if self.opeTitle.text().strip() != '':
            libs.completer.add(self._settings, self.opeTitle.text())
        if self.opeComment.text().strip() != '':
            libs.completer.add(self._settings, self.opeComment.text())

        id = self.ope.id if not(self.ope is None) else datetime.now().timestamp()
        self.ope = operation(title=title,
                             id=id,
                             amount=amt,
                             fromdate=fromdate,
                             comment=comment,
                             to=to,
                             paytype=paytype,
                             category=category,
                             state=state)

        if keep:
            self.added.emit()
            return

        self.accept()
