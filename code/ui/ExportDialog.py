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
import csv
from datetime import datetime, date
import random
import string
from glob import glob

from PyQt5 import QtCore, QtWidgets, QtGui, uic, QtPrintSupport
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import libs.pycountry
import currency
from fpdf import FPDF
from pdf2image import convert_from_path
from PIL.ImageQt import ImageQt

import libs.completer
import resources
import appinfos
import funcs
import icons
import globalsv

from datamodels import *


class ExportDialog(QDialog):

    _settings = None
    _locale = None
    _fi = None

    def __init__(self, settings, locale, fi: financial, parent=None, *args, **kwargs):
        self._settings = settings
        self._locale = locale
        self._fi = fi
        super(ExportDialog, self).__init__(parent, Qt.Window
                                           | Qt.WindowTitleHint | Qt.CustomizeWindowHint, *args, **kwargs)
        self._init_ui()
        self.populateTypes()
        self.populateAccountsList()

    def _init_ui(self):
        # self
        self.ui = funcs.loadUiResource(funcs.rc('/ui/' + self.__class__.__name__ + '.ui'), self)
        self.setLocale(QLocale(self._locale))
        print(self.ui)
        self.ui.setLocale(QLocale(self._locale))
        self.setModal(True)
        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().geometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())
        self.setFixedSize(self.size())
        self.setWindowIcon(QIcon(icons.get('export.png')))
        # buttonBox
        self.buttonBox.button(
            QDialogButtonBox.Ok).clicked.connect(self.validateForm)
        # exportDir
        self.exportDir.setText(os.path.expanduser('~/'))
        self.directoryChooser.clicked.connect(self.directoryChooserClicked)
        # startDate
        self.startDate.setDate(date.min)
        # endDate
        self.endDate.setDate(date.max)

    def closeEvent(self, event):
        event.ignore()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            obj.setStyleSheet('')
            try:
                obj.setPlaceholderText('')
            except:
                pass
        return super(ExportDialog, self).eventFilter(obj, event)

    def populateTypes(self):
        self.typesList.clear()
        model = QStandardItemModel()
        l = [
            [funcs.tr('Portefeuille ' + appinfos.app_name + ' (.kot)'), 'kot', icons.get('icon.svg')],
            '-',
            [funcs.tr("Document PDF (.pdf)"), 'pdf', icons.get('pdf.png')],
            [funcs.tr("Catalogue de données (.csv)"), 'csv', icons.get('csv.png')],
            [funcs.tr("Open Financial Exchange (.ofx)"), 'ofx', icons.get('ofx.png')],
            '-',
            [funcs.tr("Imprimer un relevé..."), 'print', icons.get('print.png')],
        ]

        separators = []
        selectedidx = 0
        for n in range(len(l)):
            if isinstance(l[n], list) and len(l[n]) >= 2:
                a = QStandardItem(str(l[n][0]))
                a.setData(l[n][1], Qt.UserRole)
                a.setIcon(QIcon(l[n][2]))
                model.appendRow(a)
            elif l[n] == '-':
                separators.append(n)

        self.typesList.setModel(model)

        for idx in separators:
            self.typesList.insertSeparator(idx)

        self.typesList.setCurrentIndex(0)
        self.typesList.currentIndexChanged.connect(self.typesListIndexChanged)

    def typesListIndexChanged(self, index):
        tpe = self.typesList.currentData()
        self.accountsList.setEnabled(not(tpe == 'kot'))
        self.startDate.setEnabled(not(tpe == 'kot'))
        self.endDate.setEnabled(not(tpe == 'kot'))
        self.exportDir.setEnabled(tpe != 'print')

    def populateAccountsList(self):
        if not(self.accountsList.model() is None):
            self.accountsList.model().removeRows(0, self.accountsList.model().rowCount())
        model = QStandardItemModel()

        for a in self._fi.accounts:
            if not(type(a) == bankaccount):
                continue

            t = a.title.strip()
            n = a.name.strip() if hasattr(a, 'name') and a.name.strip() != '' else ''
            if n != '':
                t = t + ' (' + n + ')'
            r = QStandardItem(t)
            r.setData(a.id, Qt.UserRole)
            r.setBackground(QColor(Qt.white))
            r.setCheckable(True)
            r.setCheckState(Qt.Checked)
            model.appendRow(r)

        self.accountsList.setModel(model)

    def directoryChooserClicked(self):
        ofd = QFileDialog(self,
                          funcs.tr("Dossier de sauvegarde"),
                          os.path.expanduser('~'))
        ofd.setLocale(self.locale())
        ofd.setAcceptDrops(False)
        ofd.setFileMode(QFileDialog.DirectoryOnly)
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        options |= QFileDialog.ShowDirsOnly
        ofd.setOptions(options)
        if ofd.exec_():
            dirs = ofd.selectedFiles()
            if len(dirs) >= 1:
                d = dirs[0]
                if os.access(d, os.W_OK):
                    self.exportDir.setText(d)
                else:
                    QMessageBox.warning(self, '' + appinfos.app_name + '', funcs.tr(
                        "Le dossier désiré n'est pas accessible en écriture!"))

    def getCheckedAccounts(self):
        actids = []
        model = self.accountsList.model()
        if model is None:
            return False
        for i in range(model.rowCount()):
            item = model.item(i)
            if item.isCheckable() and item.checkState() == Qt.Checked:
                actids.append(item.data(Qt.UserRole))
        return actids

    def save2kot(self):
        filepath = os.path.join(self.exportDir.text(), appinfos.app_name + str(round(datetime.timestamp(datetime.now()))) + '.kot')
        return self._fi.saveAs(filepath, '')

    def save2csv(self):
        delimiter = self._settings.value('Export/csv_separator')
        decimal = self._settings.value('Export/csv_decimal')
        dateformat = self._settings.value('Export/csv_dateformat')
        startdate = self.startDate.date().toPyDate()
        enddate = self.endDate.date().toPyDate()
        dirpath = self.exportDir.text().strip()
        accountids = self.getCheckedAccounts()
        return self._fi.save2csv(dirpath, accountids, delimiter, decimal, dateformat, startdate, enddate)

    def save2pdf(self):
        decimal = self._settings.value('Export/csv_decimal')
        dateformat = self._settings.value('Export/csv_dateformat')
        startdate = self.startDate.date().toPyDate()
        enddate = self.endDate.date().toPyDate()
        accountids = self.getCheckedAccounts()
        dirpath = self.exportDir.text().strip()
        return self._fi.save2pdf(dirpath, accountids, decimal, dateformat, startdate, enddate)

    def printReport(self):
        tempdirname = ''.join(random.choice(string.ascii_lowercase) for i in range(16))
        tempdir = os.path.join(globalsv.personnal_path, 'tmp_' + tempdirname)
        if not os.path.isdir(tempdir):
            os.mkdir(tempdir)
        self.exportDir.setText(tempdir)

        if self.save2pdf():
            QApplication.restoreOverrideCursor()

            ret = False

            printer = QtPrintSupport.QPrinter(QtPrintSupport.QPrinter.HighResolution)
            printer.setOrientation(QtPrintSupport.QPrinter.Landscape)
            printer.setColorMode(QtPrintSupport.QPrinter.GrayScale)
            printer.setCopyCount(1)
            printer.setCreator('{} {}'.format(appinfos.app_name, appinfos.app_version))
            printer.setDocName(funcs.tr("Relevés de comptes {}").format(appinfos.app_name))
            printer.setOutputFormat(QtPrintSupport.QPrinter.NativeFormat)
            printer.setPageOrder(QtPrintSupport.QPrinter.FirstPageFirst)
            printer.setPaperSource(QtPrintSupport.QPrinter.Auto)
            printer.setResolution(300)

            reply = QtPrintSupport.QPrintDialog(printer, self).exec_()
            if reply == QtPrintSupport.QPrintDialog.Accepted:
                QApplication.setOverrideCursor(Qt.WaitCursor)
                self.setEnabled(False)

                painter = QPainter()
                painter.begin(printer)

                files = glob(os.path.join(tempdir, '*.pdf'))
                resolution = printer.resolution()
                for pdf in files:
                    images = convert_from_path(pdf, dpi=resolution, output_folder=tempdir)

                    for i, image in enumerate(images):
                        if i > 0:
                            printer.newPage()
                        rect = painter.viewport()
                        qtImage = ImageQt(image)
                        qtImageScaled = qtImage.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        painter.drawImage(rect, qtImageScaled)

                painter.end()

                ret = True

            shutil.rmtree(tempdir)

            self.setEnabled(True)
            QApplication.restoreOverrideCursor()

            return ret

        QApplication.restoreOverrideCursor()
        return False

    def save2ofx(self):
        decimal = self._settings.value('Export/csv_decimal')
        dateformat = self._settings.value('Export/csv_dateformat')
        startdate = self.startDate.date().toPyDate()
        enddate = self.endDate.date().toPyDate()
        dirpath = self.exportDir.text().strip()
        accountids = self.getCheckedAccounts()
        return self._fi.save2ofx(dirpath, accountids, decimal, dateformat, startdate, enddate)

    def validateForm(self):
        result = False
        tpe = self.typesList.currentData()

        QApplication.setOverrideCursor(Qt.WaitCursor)

        if tpe == 'kot':
            result = self.save2kot()
        elif tpe == 'csv':
            result = self.save2csv()
        elif tpe == 'pdf':
            result = self.save2pdf()
        elif tpe == 'ofx':
            result = self.save2ofx()
        elif tpe == 'print':
            result = self.printReport()

        QApplication.restoreOverrideCursor()

        if result:
            self.accept()
        else:
            QMessageBox.critical(self, '' + appinfos.app_name + '', funcs.tr(
                "Impossible de réaliser cette opération sous ce format!"))
