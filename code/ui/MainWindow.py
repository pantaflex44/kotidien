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
import gc
import shutil
import json
import time
import importlib
import locale
import webbrowser
import subprocess

import libs.pycountry
import currency
import libs.completer
import libs.currencies
import appinfos
import funcs
import icons
from globalsv import help_link

import datamodels
from datamodels import *

from datetime import datetime
from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from ui.OpenDialog import OpenDialog
from ui.EditDialog import EditDialog
from ui.ThirdpartiesDialog import ThirdpartiesDialog
from ui.CategoriesDialog import CategoriesDialog
from ui.PaytypesDialog import PaytypesDialog
from ui.AboutDialog import AboutDialog
from ui.ExportDialog import ExportDialog
from ui.ImportCsvDialog import ImportCsvDialog
from ui.ImportOfxDialog import ImportOfxDialog
from ui.MdiFrame import MdiFrame
from ui.MdiHome import MdiHome
from ui.MdiAccount import MdiAccount
from ui.MdiStats import MdiStats
from ui.MdiTrends import MdiTrends
from ui.SettingsDialog import SettingsDialog


class QHLine(QFrame):

    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Plain)
        self.setEnabled(False)


class QVLine(QFrame):

    def __init__(self):
        super(QVLine, self).__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Plain)
        self.setEnabled(False)


class QPageContent(QFrame):

    @property
    def waitText(self):
        return self._waitText

    @waitText.setter
    def waitText(self, value):
        self._waitText = value
        self.update()

    def __init__(self, parent=None, waitText="Chargement en cours..."):
        self._waitText = waitText
        super(QPageContent, self).__init__(parent)
        self.setSizePolicy(QSizePolicy(
            QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding))
        self.setFrameShape(QFrame.NoFrame)
        self.setFrameShadow(QFrame.Plain)

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)

        f = self.font()
        f.setBold(True)
        f.setPointSize(8)
        qp.setFont(f)

        qp.setPen(QColor(Qt.darkGray).lighter(130))
        qp.drawText(event.rect().adjusted(0, 2, 2, 0),
                    Qt.AlignCenter, self._waitText)

        qp.setPen(QColor(Qt.darkGray))
        qp.drawText(event.rect().adjusted(0, 1, 1, 0),
                    Qt.AlignCenter, self._waitText)

        qp.setPen(QColor('#D6D300'))
        qp.drawText(event.rect(), Qt.AlignCenter, self._waitText)

        qp.end()


class MainWindow(QMainWindow):
    _settings = None
    _locale = None
    _fi = None
    _recents = []
    _splash = None

    _olddate = datetime.now().date()
    newdaySignal = pyqtSignal(date)

    version_numbers = appinfos.app_version
    version_date = appinfos.app_date.strftime('%Y-%m-%d')
    version_url = appinfos.app_url
    version_is_new = False

    def __init__(self, settings, locale, splash:QSplashScreen=None, *args, **kwargs):
        self._settings = settings
        self._locale = locale
        super(MainWindow, self).__init__(*args, **kwargs)
        self.ui = funcs.loadUiResource(funcs.rc('/ui/' + self.__class__.__name__ + '.ui'), self)
        self.setLocale(QLocale(self._locale))
        self.ui.setLocale(QLocale(self._locale))
        self._init_ui()

        self.loadRecents()

        if not(splash is None):
            splash.close()

        self.openFinancial(quit=True)

        # vérifie la présence d'une nouvelle version
        if self._settings.value('verify_update', True):
            funcs.has_new_version(self.setNewVersionAlert)

    def centerUi(self):
        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())

    def _init_ui(self):
        # self
        self.setBaseSize(1024, 650)
        self.setMinimumSize(1024, 650)
        self.setWindowIcon(QIcon(funcs.rc('/ui/icons/icon.svg')))

        if self._settings.value(self.objectName() + '/isMaximized', True):
            self.centerUi()
            self.setWindowState(Qt.WindowMaximized)
        else:
            x = int(self._settings.value(self.objectName() + '/x', 0))
            y = int(self._settings.value(self.objectName() + '/y', 0))
            w = int(self._settings.value(self.objectName() + '/w', 1024))
            h = int(self._settings.value(self.objectName() + '/h', 768))
            self.move(x, y)
            self.resize(w, h)
            if x <= 10 or y <= 10:
                self.centerUi()

        self.ui.closeEvent = self.closeEvent

        self.pageContent = QPageContent(self.splitter, funcs.tr("Chargement en cours..."))
        self.pageContent.setObjectName('pageContent')

        # menu
        self.actionQuit.triggered.connect(self.close)
        self.actionQuit.setIcon(QIcon(icons.get('quit.png')))
        self.actionSettings.triggered.connect(self.actionSettingsClicked)
        self.actionSettings.setIcon(QIcon(icons.get('settings.png')))
        self.actionNouveau_dossier.triggered.connect(self.newFinancial)
        self.actionNouveau_dossier.setIcon(
            QIcon(icons.get('document-new.png')))
        self.actionOuvrir_dossier.triggered.connect(self.openFinancial)
        self.actionOuvrir_dossier.setIcon(
            QIcon(icons.get('document-open.png')))
        self.actionExporter.triggered.connect(self.export)
        self.actionExporter.setIcon(QIcon(icons.get('export.png')))
        self.actionImporter.triggered.connect(self.imports)
        self.actionImporter.setIcon(QIcon(icons.get('import.png')))
        self.actionFermer_dossier.triggered.connect(lambda: self.closeFinancial(reopen=True))
        self.actionFermer_dossier.setIcon(QIcon(icons.get('document-close.png')))
        self.actionEnregistrer_dossier.triggered.connect(self.saveFinancial)
        self.actionEnregistrer_dossier.setIcon(QIcon(icons.get('document-save.png')))
        self.actionProprietes.triggered.connect(self.editFinancial)
        self.actionProprietes.setIcon(QIcon(icons.get('document-edit.png')))
        self.actionAbout.triggered.connect(self.actionAboutClicked)
        self.actionAbout.setIcon(QIcon(icons.get('about.png')))
        self.actionHelp.triggered.connect(self.openHelp)
        self.actionHelp.setIcon(QIcon(icons.get('help.png')))
        # toolBar
        self.actionNew = QAction(
            QIcon(icons.get('document-new.png')), funcs.tr("Nouveau..."), self)
        self.actionNew.setStatusTip(self.actionNew.text())
        self.actionNew.setEnabled(True)
        self.actionNew.triggered.connect(self.newFinancial)
        self.toolBar.addAction(self.actionNew)
        self.actionOpen = QToolButton(self.toolBar)
        self.actionOpen.setText(funcs.tr("Ouvrir..."))
        self.actionOpen.setIcon(QIcon(icons.get('document-open.png')))
        self.actionOpen.setPopupMode(QToolButton.MenuButtonPopup)
        self.actionOpen.setStatusTip(self.actionOpen.text())
        self.actionOpen.setMenu(QMenu())
        self.actionOpen.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.actionOpen.clicked.connect(self.openFinancial)
        self.toolBar.addWidget(self.actionOpen)
        self.actionSave = QAction(
            QIcon(icons.get('document-save.png')), funcs.tr("Enregistrer"), self)
        self.actionSave.setStatusTip(self.actionSave.text())
        self.actionSave.setEnabled(False)
        self.actionSave.triggered.connect(self.saveFinancial)
        self.toolBar.addAction(self.actionSave)
        self.actionClose = QAction(
            QIcon(icons.get('document-close.png')), funcs.tr("Fermer"), self)
        self.actionClose.setStatusTip(self.actionClose.text())
        self.actionClose.setEnabled(False)
        self.actionClose.triggered.connect(
            lambda: self.closeFinancial(reopen=True))
        self.toolBar.addAction(self.actionClose)
        self.toolBar.addSeparator()
        self.actionHome = QToolButton(self.toolBar)
        self.actionHome.setText(funcs.tr("Résumé"))
        self.actionHome.setIcon(QIcon(icons.get('go-home.png')))
        self.actionHome.setIconSize(self.toolBar.iconSize())
        self.actionHome.setStatusTip(self.actionHome.text())
        self.actionHome.setEnabled(True)
        self.actionHome.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.actionHome.clicked.connect(
            lambda: self.loadMdiWidget('MdiHome'))
        self.toolBar.addWidget(self.actionHome)
        self.toolBar.addSeparator()
        self.actionThirdparty = QToolButton(self.toolBar)
        self.actionThirdparty.setText(funcs.tr("Tiers"))
        self.actionThirdparty.setIcon(
            QIcon(icons.get('toolbar-thirdparty.png')))
        self.actionThirdparty.setIconSize(self.toolBar.iconSize())
        self.actionThirdparty.setStatusTip(self.actionThirdparty.text())
        self.actionThirdparty.setEnabled(False)
        self.actionThirdparty.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.actionThirdparty.clicked.connect(self.thirdparties)
        self.toolBar.addWidget(self.actionThirdparty)
        self.actionCategories = QToolButton(self.toolBar)
        self.actionCategories.setText(funcs.tr("Catégories"))
        self.actionCategories.setIcon(
            QIcon(icons.get('toolbar-category.png')))
        self.actionCategories.setIconSize(self.toolBar.iconSize())
        self.actionCategories.setStatusTip(self.actionCategories.text())
        self.actionCategories.setEnabled(False)
        self.actionCategories.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.actionCategories.clicked.connect(self.categories)
        self.toolBar.addWidget(self.actionCategories)
        self.actionPaytypes = QToolButton(self.toolBar)
        self.actionPaytypes.setText(funcs.tr("Moyens de paiements"))
        self.actionPaytypes.setIcon(QIcon(icons.get('toolbar-paytype.png')))
        self.actionPaytypes.setIconSize(self.toolBar.iconSize())
        self.actionPaytypes.setStatusTip(self.actionPaytypes.text())
        self.actionPaytypes.setEnabled(False)
        self.actionPaytypes.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.actionPaytypes.clicked.connect(self.paytypes)
        self.toolBar.addWidget(self.actionPaytypes)
        self.toolBar.addSeparator()
        # statusbar
        self.statusBar().addPermanentWidget(QVLine())
        self.statusBarFinancielFilepath = QLabel('')
        self.statusBar().addPermanentWidget(self.statusBarFinancielFilepath)
        self.statusBarUpdateStateItem = QLabel('')
        self.statusBarUpdateStateItem.setPixmap(QPixmap())
        self.statusBar().addPermanentWidget(self.statusBarUpdateStateItem)
        self.statusBar().addPermanentWidget(QVLine())
        self.statusBarNewVersionAlertIcon = QLabel('')
        self.statusBarNewVersionAlertIcon.setPixmap(QPixmap())
        self.statusBar().addPermanentWidget(self.statusBarNewVersionAlertIcon)
        self.statusBarNewVersionAlertText = QLabel('')
        self.statusBar().addPermanentWidget(self.statusBarNewVersionAlertText)
        self.statusBar().addPermanentWidget(QVLine())
        self.statusBarClockItem = QLabel('')
        self.statusBar().addPermanentWidget(self.statusBarClockItem)
        # langs
        self.actionLangs.setIcon(QIcon(icons.get('lang.png')))
        self.actionLangs.clear()
        for k, v in funcs.get_availlable_locales().items():
            a = QAction(QIcon(v['icon']), v['name'], self.actionLangs)
            a.setObjectName(k)
            a.setText(v['name'])
            a.setToolTip(v['name'])
            a.setStatusTip(v['name'])
            a.setVisible(True)
            f = a.font()
            f.setBold(k == self._locale)
            a.setFont(f)
            a.triggered.connect(lambda state, code=k,
                                locale=v: self.updateLanguage(code, locale))
            self.actionLangs.addAction(a)
        # clock
        self.clockTimer = QtCore.QTimer()
        self.clockTimer.timeout.connect(self.clocktimeRaised)
        self.clockTimer.start(1000 * 1)
        # splitter geometry
        self.splitter.setSizes([96, self.geometry().width() - 96])

    def openDefaultBrowser(self, url:str):
        if sys.platform.startswith('win'):
            os.startfile(url)
        elif sys.platform.startswith('darwin'):
            subprocess.call(('open', url))
        else:
            subprocess.call(('xdg-open', url))

    def clocktimeRaised(self):
        self.statusBarClockItem.setText(
            QDateTime.currentDateTime().toString(Qt.DefaultLocaleLongDate))
        now = datetime.now().date()
        if now > self._olddate:
            self.newdaySignal.emit(now)
        self._olddate = now

        vd = datetime.strptime(self.version_date, '%Y-%m-%d').strftime('%x')
        if self.version_is_new:
            self.statusBarNewVersionAlertIcon.setPixmap(QIcon(icons.get('bullhorn.png')).pixmap(QSize(16, 16)))
            self.statusBarNewVersionAlertText.setText(funcs.tr("<b>Kotidien {} est disponible! Cliquez ici pour télécharger.</b>")
                                                      .format(self.version_numbers))
            self.statusBarNewVersionAlertText.setCursor(QCursor(Qt.PointingHandCursor))
            self.statusBarNewVersionAlertText.mousePressEvent = lambda evt: self.openDefaultBrowser(self.version_url)
            self.statusBarNewVersionAlertText.setToolTip(funcs.tr("Ouvrir la page de téléchargement de la nouvelle version..."))
        else:
            self.statusBarNewVersionAlertIcon.setPixmap(QIcon(icons.get('ope-check.png')).pixmap(QSize(16, 16)))
            self.statusBarNewVersionAlertText.setText(funcs.tr("Votre version de Kotidien est à jour."))
            self.statusBarNewVersionAlertText.setCursor(QCursor(Qt.PointingHandCursor))
            self.statusBarNewVersionAlertText.mousePressEvent = lambda evt: self.openDefaultBrowser(appinfos.app_url)
            self.statusBarNewVersionAlertText.setToolTip(funcs.tr("Aller à l'adresse du site Internet..."))

    def updateLanguage(self, code, locale):
        self._settings.setValue('locale', code)
        self._settings.sync()
        QMessageBox.information(self, appinfos.app_name, self.tr(
            "Veuillez relancer l'application pour appliquer les modifications."))
        self.close()
    def openHelp(self):
        webbrowser.open(help_link, new=2, autoraise=True)

    def actionAboutClicked(self):
        ad = AboutDialog(self._settings, self._locale, self)
        ad.exec_()

    def actionSettingsClicked(self):
        sd = SettingsDialog(self._settings,
                            self._locale,
                            parent=self)
        if sd.exec_() == QMessageBox.Accepted:
            self._settings.setValue('show_splashscreen', sd.show_splashscreen.checkState() == Qt.Checked)
            self._settings.setValue('askOnClose', sd.askOnClose.checkState() == Qt.Checked)
            self._settings.setValue('view_accounts_cb', sd.view_accounts_cb.checkState() == Qt.Checked)
            self._settings.setValue('selective_expand', sd.selective_expand.checkState() == Qt.Checked)
            self._settings.setValue('Accounts/default_sort_descending', sd.default_sort_descending.checkState() == Qt.Checked)
            self._settings.setValue('default_filter_hide_pointed', sd.default_filter_hide_pointed.checkState() == Qt.Checked)
            self._settings.setValue('default_filter_active', sd.default_filter_active.checkState() == Qt.Checked)
            self._settings.setValue('Planner/auto_post', sd.auto_post.checkState() == Qt.Checked)
            self._settings.setValue('Planner/auto_delete_finished', sd.auto_delete_finished.checkState() == Qt.Checked)
            self._settings.setValue('create_save', sd.create_save.checkState() == Qt.Checked)
            self._settings.setValue('Accounts/default_sort_column', sd.default_sort_column.currentData(Qt.UserRole))
            self._settings.setValue('default_filter_date', sd.default_filter_date.currentData(Qt.UserRole))
            self._settings.setValue('short_date_format', sd.short_date_format.text().strip())
            self._settings.setValue('long_date_format', sd.long_date_format.text().strip())
            self._settings.setValue('color_positive_amount', sd.color_positive_amount_value.strip())
            self._settings.setValue('color_negative_amount', sd.color_negative_amount_value.strip())
            self._settings.setValue('color_credit_amount', sd.color_credit_amount_value.strip())
            self._settings.setValue('Export/csv_separator', sd.csv_separator.text().strip())
            self._settings.setValue('Export/csv_decimal', sd.csv_decimal.text().strip())
            self._settings.setValue('Export/csv_dateformat', sd.csv_dateformat.text().strip())
            self._settings.sync()
            QApplication.processEvents()
            sd.destroy()
            self.populateAccountsList(lastselected=True)
            self.loadMdiWidget('MdiHome')

    def setNewVersionAlert(self, version, dte, url, is_new):
        self.version_numbers = version
        self.version_date = dte
        self.version_url = url
        self.version_is_new = is_new

    def setUpdatedState(self, state: bool):
        if state:
            self.statusBarUpdateStateItem.setPixmap(
                QIcon(icons.get('document-save.png')).pixmap(QSize(16, 16)))
            self.actionEnregistrer_dossier.setEnabled(True)
            self.actionSave.setEnabled(True)
            if self.windowTitle()[-1] != "*":
                self.setWindowTitle(self.windowTitle() + "*")
        else:
            self.statusBarUpdateStateItem.setPixmap(QPixmap())
            self.actionEnregistrer_dossier.setEnabled(False)
            self.actionSave.setEnabled(False)
            if self.windowTitle()[-1] == "*":
                self.setWindowTitle(self.windowTitle()[:-1])

    def closeEvent(self, event):
        close = True
        if self._settings.value('askOnClose'):
            reply = QMessageBox.question(self, '' + appinfos.app_name + '', funcs.tr(
                "Voulez-vous quitter " + appinfos.app_name + "?"), QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.No:
                close = False

        if close:
            self.clockTimer.stop()
            self.closeFinancial(ask=False)
            self._settings.sync()
            self._settings.setValue(self.objectName(
            ) + '/isMaximized', (self.windowState() == Qt.WindowMaximized))

            if self.windowState() == Qt.WindowNoState:
                r = self.frameGeometry()
                self._settings.setValue(self.objectName() + '/x', r.x())
                self._settings.setValue(self.objectName() + '/y', r.y())
                self._settings.setValue(self.objectName() + '/w', r.width())
                self._settings.setValue(self.objectName() + '/h', r.height())

            event.accept()
        else:
            event.ignore()

    def loadRecents(self):
        self.menuRecement_ouverts.clear()
        self.menuRecement_ouverts.setEnabled(False)
        self.actionOpen.menu().clear()
        self._recents = []
        rs = self._settings.value( '' + appinfos.app_name + '/recents', self._recents)
        if isinstance(rs, list):
            self._recents = rs
        elif isinstance(rs, str):
            if os.path.exists(rs):
                self._recents = [rs]
        for recent in self._recents:
            if os.path.exists(recent):
                a = QAction(QIcon(icons.get('document-open.png')), '{} [{}]'.format(
                    os.path.basename(recent), recent), self.menuRecement_ouverts)
                a.setObjectName(recent)
                a.setText('{} [{}]'.format(os.path.basename(recent), recent))
                mtime = datetime.fromtimestamp(os.path.getmtime(recent))
                a.setToolTip(funcs.tr("Dernière modification: {}").format(
                    mtime.strftime('%c')))
                a.setStatusTip(funcs.tr("Dernière modification: {}").format(
                    mtime.strftime('%c')))
                a.setVisible(True)
                a.triggered.connect(
                    lambda state, x=recent: self.openRecent(x))
                self.menuRecement_ouverts.addAction(a)
                self.actionOpen.menu().addAction(a)
        self.menuRecement_ouverts.setEnabled(len(self._recents) > 0)

    def saveRecents(self):
        r = []
        for recent in self._recents:
            if os.path.exists(recent):
                r.append(recent)
        if len(r) > 1:
            self._settings.setValue('' + appinfos.app_name + '/recents', r)
        elif len(r) == 1:
            self._settings.setValue(
                '' + appinfos.app_name + '/recents', r[0])
        else:
            self._settings.setValue('' + appinfos.app_name + '/recents', '')
        self._settings.sync()
        self._recents = r

    def openRecent(self, filepath):
        self.openFinancial(quit=False, noclose=False, default=filepath)

    def loadWaiter(self):
        self.pageContent.waitText = funcs.tr("Chargement en cours...")
        QApplication.processEvents()

    def unloadWaiter(self):
        self.pageContent.waitText = ''
        QApplication.processEvents()

    def setFinancialTitle(self, reset: bool = False):
        if not reset:
            self.setWindowTitle('' + appinfos.app_name + ' - {} ({})'.format(
                os.path.basename(self._fi.filepath), '.'.join([str(s) for s in self._fi.version])))
            mess = funcs.tr("Fichier ouvert: {} - {} élément(s) en gestion".format(
                self._fi.filepath, len(self._fi.accounts)))
            self.statusBarFinancielFilepath.setText(mess)
            self.actionMon_dossier.setText(self._fi.title)
            self.actionMon_dossier.setVisible(True)
        else:
            self.setWindowTitle('' + appinfos.app_name + '')
            self.statusBarFinancielFilepath.setText('')
            self.actionMon_dossier.setVisible(False)

    def saveFinancial(self):
        if not (self._fi is None) and self.actionEnregistrer_dossier.isEnabled():
            if not self._fi.save():
                QMessageBox.Warning(self, '' + appinfos.app_name + '', funcs.tr(
                    "<b>Une erreur s'est produite.</b><br /><br /> Impossible de sauvegarder le dossier financier dans <b>{}</b>!".format(self._fi.filepath)))
            else:
                self.setUpdatedState(False)
                self.setFinancialTitle()

    def newFinancial(self, quit: bool = False, noclose: bool = False):
        if not noclose:
            if not self.closeFinancial():
                if quit:
                    sys.exit(0)
                else:
                    return False

        ed = EditDialog(self._settings, self._locale, self, fi=None)
        ed.setWindowTitle(funcs.tr("Nouveau dossier financier"))
        if ed.exec_() == QMessageBox.Accepted:
            if not ed.fi.save():
                QMessageBox.warning(self, '' + appinfos.app_name + '', funcs.tr(
                    "<b>Oh la, il m'est impossible de créer un nouveau dossier financier!</b>"))
                self.newFinancial(quit=False, noclose=False)
            else:
                if self._settings.value('create_save'):
                    shutil.copyfile(ed.fi.filepath, ed.fi.filepath + '.bak')

                fi = financial.load(ed.fi.filepath, ed.fi.password)
                if fi is None:
                    QMessageBox.warning(self, '' + appinfos.app_name + '', funcs.tr(
                        "<b>Oh la, il m'est impossible de créer un nouveau dossier financier!</b>"))
                    self.newFinancial(quit=False, noclose=False)
                    return

                self._openFinancial()
        else:
            if quit:
                sys.exit(0)
            else:
                self.openFinancial(quit=True, noclose=False)

    def editFinancial(self):
        ed = EditDialog(self._settings, self._locale, self, fi=self._fi)
        ed.setWindowTitle(funcs.tr("Contenu du dossier financier"))
        if ed.exec_() == QMessageBox.Accepted:
            if not ed.fi.save():
                QMessageBox.warning(self, '' + appinfos.app_name + '', funcs.tr(
                    "<b>Oh la, il m'est impossible d'enregistrer les modifications du dossier financier!</b>"))
            else:
                self.unloadFinancial()
                self._openFinancial(ed.fi)
        ed.destroy()

    def closeFinancial(self, reopen: bool = False, ask:bool = True):
        ok = True
        if self.actionFermer_dossier.isEnabled():
            if ask:
                reply = QMessageBox.question(self, '' + appinfos.app_name + '', funcs.tr(
                    "Voulez-vous fermer le dossier financier en cours?"), QMessageBox.Yes, QMessageBox.No)
                if reply == QMessageBox.No:
                    ok = False

            if ok:
                self.saveRecents()

                if not (self._fi is None) and self.actionEnregistrer_dossier.isEnabled():
                    reply = QMessageBox.question(self, '' + appinfos.app_name + '',
                                                 funcs.tr(
                                                     "Voulez-vous sauvegarder le dossier financier en cours?"),
                                                 QMessageBox.Yes, QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        self.saveFinancial()

                self.unloadFinancial()
                self._fi = None
                if reopen:
                    self.openFinancial(quit=True, noclose=True)
                    self.loadFinancial()
        return ok

    def _openFinancial(self, fi: financial):
        try:
            self._fi = fi
            if self._fi is None:
                raise Exception()

            dv = tuple(map(lambda v: int(v), list(datamodels.__version__.split('.'))))
            vc_major, vc_minor, vc_revision = tuple(map(lambda i, j: i - j,
                                                        dv,
                                                        self._fi.version))
            if vc_major < 0 or vc_minor < 0 or vc_revision < 0:
                QMessageBox.critical(self, appinfos.app_name, funcs.tr(
                    "<b>Attention</b>: Le portefeuille que vous souhaitez ouvrir a été créé avec une version plus récente de {}.<br />Vous devez mettre à jour cette application avant de continuer.").format(appinfos.app_name))
                return False

            if not (fi.filepath in self._recents):
                self._recents.insert(0, fi.filepath)
                self.saveRecents()

            self.loadFinancial()
            return True
        except Exception as e:
            self.unloadFinancial()
            return False

    def openFinancial(self, quit: bool = True, noclose: bool = False, default: str = ''):
        if not noclose:
            if not self.closeFinancial():
                if quit:
                    sys.exit(0)
                else:
                    return False

        while True:
            filepath = ''
            password = ''
            isdefault = False
            od = OpenDialog(self._settings, self._locale, self, default)
            reply = od.exec_()
            if (reply == QDialog.Rejected):
                od.destroy()
                if self._settings.value('askOnClose'):
                    reply = QMessageBox.question(self, '' + appinfos.app_name + '',
                                                 funcs.tr(
                                                     "Voulez-vous quitter " + appinfos.app_name + "?"),
                                                 QMessageBox.Yes, QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        sys.exit(0)
                else:
                    sys.exit(0)
            else:
                filepath = od.filepath.text().strip()
                password = od.password.text().strip()
                isdefault = od.isdefault.isChecked()

                od.destroy()

                if filepath == '':
                    reply = QMessageBox.warning(self, '' + appinfos.app_name + '',
                                                funcs.tr("<b>Oups!</b>\
                                                    <br />Vous devez renseigner un dossier financier.\
                                                    <br /><br />Voulez-vous essayer d'ouvrir un autre fichier?"),
                                                QMessageBox.Yes, QMessageBox.No)
                    if reply == QMessageBox.No:
                        sys.exit(0)
                    else:
                        continue

                if not funcs.check_file_writable(filepath):
                    reply = QMessageBox.warning(self, '' + appinfos.app_name + '',
                                                funcs.tr("<b>Oh la, ce fichier n'est pas accessible en écriture ou n'éxiste pas!</b>\
                                                    <br />Veuillez modifier les droits d'accès avant de l'ouvrir avec " + appinfos.app_name + ".\
                                                    <br /><br />Voulez-vous essayer d'ouvrir un autre fichier?"),
                                                QMessageBox.Yes, QMessageBox.No)
                    if reply == QMessageBox.No:
                        sys.exit(0)
                    else:
                        continue

                if isdefault:
                    self._settings.setValue(
                        '' + appinfos.app_name + '/defaultfile', filepath)
                    self._settings.sync()

                if os.path.exists(filepath) and self._settings.value('create_save'):
                    shutil.copyfile(filepath, filepath + '.bak')

                fi = financial.load(filepath, password)
                if fi is None or not self._openFinancial(fi):
                    reply = QMessageBox.warning(self, '' + appinfos.app_name + '',
                                                funcs.tr("<b>Oh la, ce fichier ne contient pas de dossier financier ou est corrompu!</b>\
                                                    <br /><br />Voulez-vous essayer d'ouvrir un autre fichier?"),
                                                QMessageBox.Yes, QMessageBox.No)
                    if reply == QMessageBox.No:
                        sys.exit(0)

                    if not (fi is None):
                        if self._settings.value('' + appinfos.app_name + '/defaultfile', '') == fi.filepath:
                            self._settings.setValue(
                                '' + appinfos.app_name + '/defaultfile', '')
                else:
                    break

    def loadFinancial(self):
        self.loadRecents()
        self.setFinancialTitle()
        self.actionFermer_dossier.setEnabled(True)
        self.actionExporter.setEnabled(True)
        self.actionImporter.setEnabled(True)
        self.actionClose.setEnabled(True)
        self.actionProprietes.setEnabled(True)
        self.populateAccountsList()
        self.populateReportsList()
        self.actionThirdparty.setEnabled(True)
        self.actionCategories.setEnabled(True)
        self.actionPaytypes.setEnabled(True)
        self.show()
        QApplication.processEvents()
        self.loadMdiWidget('MdiHome')
        self.pageContent.setFocus()

    def unloadFinancial(self):
        self.unloadMdiWidget()
        self.clearReportsList()
        self.clearAccountsList()
        self.actionThirdparty.setEnabled(False)
        self.actionCategories.setEnabled(False)
        self.actionPaytypes.setEnabled(False)
        self.actionFermer_dossier.setEnabled(False)
        self.actionExporter.setEnabled(False)
        self.actionImporter.setEnabled(False)
        self.actionClose.setEnabled(False)
        self.actionProprietes.setEnabled(False)
        self.setUpdatedState(False)
        self.setFinancialTitle(reset=True)
        self.saveRecents()

    def createMdiWidget(self, name: str, closable: bool = True, *args, **kwargs):
        cls = globals()[name]
        w = cls(self._settings,
                self._locale,
                None,
                self._fi,
                closable,
                *args, **kwargs)
        w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return w

    def loadMdiWidget(self, name: str, *args, **kwargs):
        if not (self._fi is None):
            self.loadWaiter()
            QApplication.processEvents()

            icname = 'icon'
            if 'iconname' in kwargs:
                icname = kwargs['iconname']
                del kwargs['iconname']

            w = self.createMdiWidget(name, *args, **kwargs)
            if w is None:
                w = self.createMdiWidget('MdiHome', *args, **kwargs)

            if (hasattr(w, 'toolbar') and isinstance(w.toolbar, QToolBar)) or (
                    hasattr(w, 'toolbar2') and isinstance(w.toolbar2, QToolBar)):
                self.setUpdatesEnabled(False)
                QApplication.processEvents()

            self.unloadMdiWidget()

            if self.pageContent.layout() is None:
                l = QVBoxLayout(self.pageContent)
                l.setContentsMargins(0, 0, 0, 0)
                l.setSpacing(0)
                l.addWidget(w)
            else:
                self.pageContent.layout().addWidget(w)

            #self.setWindowIcon(w.windowIcon())

            if hasattr(w, 'toolbar') and isinstance(w.toolbar, QToolBar):
                t = funcs.tr(
                    "{} - Dossier {}".format(w.windowTitle(), self._fi.title))
                i = QIcon(icons.get(icname))
                w.toolbar.setMovable(self.toolBar.isMovable())
                w.toolbar.setFloatable(self.toolBar.isFloatable())
                w.toolbar.setIconSize(self.toolBar.iconSize())
                # self.addToolBarBreak()
                self.addToolBar(Qt.TopToolBarArea, w.toolbar)

            if hasattr(w, 'toolbar2') and isinstance(w.toolbar2, QToolBar):
                t = funcs.tr(
                    "{} - Dossier {}".format(w.windowTitle(), self._fi.title))
                i = QIcon(icons.get(icname))
                w.toolbar2.setMovable(self.toolBar.isMovable())
                w.toolbar2.setFloatable(self.toolBar.isFloatable())
                w.toolbar2.setIconSize(self.toolBar.iconSize())
                self.addToolBarBreak()
                self.addToolBar(Qt.TopToolBarArea, w.toolbar2)

            nde = getattr(w, "newdayEmitted", None)
            if callable(nde):
                self.newdaySignal.connect(w.newdayEmitted)

            self.setUpdatesEnabled(True)
            QApplication.processEvents()
            self.update()

            w.updated.connect(self.mdiWidgetUpdateRaised)
            w.forceUpdateRequired.connect(self.mdiWidgetForceUpdateRaised)

            if name == 'MdiHome' or name == 'MdiStats' or name == 'MdiTrends':
                if not (self.accountsList.selectionModel() is None):
                    self.accountsList.selectionModel().clearSelection()
            if name == 'MdiHome' or name == 'MdiAccount':
                if not (self.reportsList.selectionModel() is None):
                    self.reportsList.selectionModel().clearSelection()

            self.unloadWaiter()

    def unloadMdiWidget(self):
        if self.pageContent.layout() is None:
            return

        #self.setWindowIcon(QIcon(funcs.rc('/ui/icons/icon.svg')))

        while self.pageContent.layout().count():
            child = self.pageContent.layout().takeAt(0)
            if child.widget():
                nde = getattr(child.widget(), "newdayEmitted", None)
                if callable(nde):
                    self.newdaySignal.disconnect(
                        child.widget().newdayEmitted)
                if hasattr(child.widget(), 'toolbar') and \
                        isinstance(child.widget().toolbar, QToolBar):
                    # self.removeToolBarBreak(child.widget().toolbar)
                    self.removeToolBar(child.widget().toolbar)
                if hasattr(child.widget(), 'toolbar2') and \
                        isinstance(child.widget().toolbar2, QToolBar):
                    self.removeToolBarBreak(child.widget().toolbar2)
                    self.removeToolBar(child.widget().toolbar2)

                self.pageContent.layout().removeWidget(child.widget())
                child.widget().setParent(None)
                child.widget().deleteLater()
                QApplication.processEvents()
        # self.pageContent.setTitle('')

    def mdiWidgetUpdateRaised(self):
        self.populateAccountsList(lastselected=True)
        self.setUpdatedState(True)

    def mdiWidgetForceUpdateRaised(self, save: bool = False):
        if save:
            self._fi.save()
        self.setUpdatedState(not save)
        self.setFinancialTitle()
        self.populateAccountsList(lastselected=True)

    def populateAccountsList(self, selectedidx = None, lastselected: bool = False):
        lastselectedidx = None
        lastselecteddata = None
        if not (self.accountsList.selectionModel() is None):
            if len(self.accountsList.selectionModel().selectedIndexes()) > 0:
                lastselectedidx = self.accountsList.selectionModel().selectedIndexes()[
                    0]
                lsd = self.accountsList.model().itemFromIndex(
                    lastselectedidx).data(Qt.UserRole)
                if isinstance(lsd, list) and len(lsd) > 0:
                    lastselecteddata = lsd
            self.accountsList.selectionModel().clearSelection()

        self.accountsList.setModel(None)
        m = QStandardItemModel()
        m.setColumnCount(3)
        m.setHeaderData(0, QtCore.Qt.Horizontal, funcs.tr("Gestion"))
        m.setHeaderData(1, QtCore.Qt.Horizontal, funcs.tr("Aujourd'hui"))
        m.setHeaderData(2, QtCore.Qt.Horizontal, funcs.tr("Fin de mois"))
        m.horizontalHeaderItem(1).setTextAlignment(Qt.AlignLeft)
        m.horizontalHeaderItem(2).setTextAlignment(Qt.AlignLeft)
        ba = QStandardItem()
        ba.setText(funcs.tr("Comptes en banque"))
        ba.setIcon(QIcon(icons.get('bank.png')))
        ba.setEditable(False)
        ba.setData(None)
        ba.setEnabled(False)
        ba.setForeground(QColor(Qt.darkGray))
        cc = QStandardItem()
        cc.setText(funcs.tr("CB autonomes"))
        cc.setIcon(QIcon(icons.get('credit-card.png')))
        cc.setEditable(False)
        cc.setData(None)
        cc.setEnabled(False)
        cc.setForeground(QColor(Qt.darkGray))
        cc2 = QStandardItem()
        cc2.setText(funcs.tr("CB liées"))
        cc2.setIcon(QIcon(icons.get('credit-card.png')))
        cc2.setEditable(False)
        cc2.setData(None)
        cc2.setEnabled(False)
        cc2.setForeground(QColor(Qt.darkGray))
        wl = QStandardItem()
        wl.setText(funcs.tr("Portefeuille d'espèces"))
        wl.setIcon(QIcon(icons.get('money.png')))
        wl.setEditable(False)
        wl.setData(None)
        wl.setEnabled(False)
        wl.setForeground(QColor(Qt.darkGray))
        bacnt = 0
        cccnt = 0
        cc2cnt = 0
        wlcnt = 0
        ids = []
        for a in self._fi.accounts:
            if type(a) == creditcard and a.accountid != -1 and not(self._settings.value('view_accounts_cb')):
                continue

            t = a.title
            nm = QStandardItem()
            nm.setText(t)
            nm.setEditable(False)
            f = nm.font()
            f.setBold(True)
            nm.setFont(f)

            thisdayval, endmonthval, endyearval, credit = self._fi.amounts(
                a.accountid if type(a) is creditcard and a.accountid > -1
                else a.id)
            thisday = QStandardItem()
            thisday.setText(libs.currencies.formatCurrency(thisdayval, a.alpha_3))
            thisday.setEditable(False)
            thisday.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            if thisdayval < 0.0:
                thisday.setForeground(
                    QBrush(QColor(self._settings.value('color_negative_amount'))))
            if thisdayval < credit:
                thisday.setForeground(
                    QBrush(QColor(self._settings.value('color_credit_amount'))))
            if thisdayval >= 0.0:
                thisday.setForeground(
                    QBrush(QColor(self._settings.value('color_positive_amount'))))
            endmonth = QStandardItem()
            endmonth.setText(libs.currencies.formatCurrency(
                endmonthval, a.alpha_3))
            endmonth.setEditable(False)
            endmonth.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            if endmonthval < 0.0:
                endmonth.setForeground(
                    QBrush(QColor(self._settings.value('color_negative_amount'))))
            if endmonthval < credit:
                endmonth.setForeground(
                    QBrush(QColor(self._settings.value('color_credit_amount'))))
            if endmonthval >= 0.0:
                endmonth.setForeground(
                    QBrush(QColor(self._settings.value('color_positive_amount'))))

            ids.append(str(a.id))

            if type(a) is bankaccount:
                nm.setData([a.id, -1, 'bank.png'], Qt.UserRole)
                ba.appendRow([nm, thisday, endmonth])
                bacnt = bacnt + 1
            elif type(a) is creditcard:
                if a.accountid == -1:
                    nm.setData([a.id, -1, 'credit-card.png'], Qt.UserRole)
                    cc.appendRow([nm, thisday, endmonth])
                    cccnt = cccnt + 1
                elif a.accountid > -1:
                    nm.setData([a.accountid, a.id, 'bank.png'], Qt.UserRole)
                    cc2.appendRow([nm, thisday, endmonth])
                    cc2cnt = cc2cnt + 1
            elif type(a) is wallet:
                nm.setData([a.id, -1, 'money.png'], Qt.UserRole)
                wl.appendRow([nm, thisday, endmonth])
                wlcnt = wlcnt + 1

        # add all account types as roots
        ba.setText('{} ({})'.format(ba.text(), str(bacnt)))
        cc.setText('{} ({})'.format(cc.text(), str(cccnt)))
        cc2.setText('{} ({})'.format(cc2.text(), str(cc2cnt)))
        wl.setText('{} ({})'.format(wl.text(), str(wlcnt)))
        empties = []
        for i in range(8):
            empty = QStandardItem()
            empty.setEditable(False)
            empty.setEnabled(False)
            empties.append(empty)
        m.appendRow([ba, empties[0], empties[1]])
        m.appendRow([cc, empties[2], empties[3]])
        if self._settings.value('view_accounts_cb'):
            m.appendRow([cc2, empties[4], empties[5]])
        m.appendRow([wl, empties[6], empties[7]])
        self.accountsList.setModel(m)

        # sort and format columns
        self.accountsList.resizeColumnToContents(2)
        self.accountsList.resizeColumnToContents(1)
        self.accountsList.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.accountsList.setColumnWidth(1, 100)
        self.accountsList.setColumnWidth(2, 120)
        self.accountsList.sortByColumn(0, Qt.AscendingOrder)
        self.accountsList.expandAll()

        # auto select account in list
        if not (selectedidx is None):
            self.accountsList.setCurrentIndex(selectedidx)
        elif lastselected and not (lastselectedidx is None):
            for i in range(self.accountsList.model().rowCount()):
                p = self.accountsList.model().itemFromIndex(
                    self.accountsList.model().index(i, 0))
                if p.hasChildren():
                    for j in range(p.rowCount()):
                        c = p.child(j, 0)
                        d = c.data(Qt.UserRole)
                        if not (d is None) and isinstance(d, list) and len(d) > 0:
                            if d == lastselecteddata:
                                self.accountsList.setCurrentIndex(
                                    self.accountsList.model().index(j, 0, p.index()))
                                break
        self.accountsList.selectionModel().selectionChanged.connect(self.accountSelected)

        # clean accounts saved properties
        self._settings.beginGroup('Accounts')
        removes = []
        for k in self._settings.allKeys():
            ks = k.split('_')
            if not (ks[0] in ids):
                removes.append(k)
        for r in removes:
            self._settings.remove(r)
        ids.clear()
        removes.clear()

        self._settings.endGroup()

    def clearAccountsList(self):
        if not (self.accountsList.model() is None):
            self.accountsList.model().removeRows(0,
                                                 self.accountsList.model().rowCount())
        self.accountsList.setModel(None)

    def accountSelected(self, new, old):
        if len(new.indexes()) > 0:
            index = new.indexes()[0]
            row = self.accountsList.model().itemFromIndex(index)
            if not (row is None) and not (row.data(Qt.UserRole) is None):
                id, fromid, iconname = row.data(Qt.UserRole)
                self.loadMdiWidget('MdiAccount', actid=id,
                                   fromactid=fromid, iconname=iconname)

    def populateReportsList(self):
        self.reportsList.setModel(None)
        m = QStandardItemModel()
        m.setColumnCount(1)
        m.setHeaderData(0, QtCore.Qt.Horizontal, funcs.tr("Rapports"))
        reports = [
            [funcs.tr("Classement par tiers"), 'MdiStats', 'thirdparties', 'report-thirdparties.png'],
            [funcs.tr("Classement par catégories"), 'MdiStats', 'categories', 'reports-categories.png'],
            [funcs.tr("Classement par moyens de paiement"), 'MdiStats', 'paytypes', 'reports-paytypes.png']
        ]
        """[funcs.tr("Tendances dans le temps"), 'MdiTrends', 'overtime', 'reports-time.png']"""
        for r in reports:
            row = QStandardItem()
            row.setText(r[0])
            row.setEditable(False)
            row.setData([r[1], r[2], r[3]], Qt.UserRole)
            row.setIcon(QIcon(icons.get(r[3])))
            m.appendRow(row)
        self.reportsList.setModel(m)
        self.reportsList.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.reportsList.sortByColumn(0, Qt.AscendingOrder)
        self.reportsList.expandAll()
        self.reportsList.selectionModel().selectionChanged.connect(self.reportSelected)

    def clearReportsList(self):
        if not (self.reportsList.model() is None):
            self.reportsList.model().removeRows(0,
                                                self.reportsList.model().rowCount())
        self.reportsList.setModel(None)

    def reportSelected(self, new, old):
        if len(new.indexes()) > 0:
            index = new.indexes()[0]
            row = self.reportsList.model().itemFromIndex(index)
            dlgname, ctype, iconname = row.data(Qt.UserRole)
            self.loadMdiWidget(dlgname, title=row.text(), ctype=ctype, iconname=iconname)

    def thirdparties(self):
        td = ThirdpartiesDialog(self._settings,
                                self._locale,
                                fi=self._fi,
                                parent=self)
        if (td.exec_() == QDialog.Accepted):
            if td.updated:
                self.setUpdatedState(True)
                self.loadMdiWidget('MdiHome')
        td.destroy()

    def categories(self):
        cd = CategoriesDialog(self._settings,
                              self._locale,
                              fi=self._fi,
                              parent=self)
        if (cd.exec_() == QDialog.Accepted):
            if cd.updated:
                self.setUpdatedState(True)
                self.loadMdiWidget('MdiHome')
        cd.destroy()

    def paytypes(self):
        pd = PaytypesDialog(self._settings,
                            self._locale,
                            fi=self._fi,
                            parent=self)
        if (pd.exec_() == QDialog.Accepted):
            if pd.updated:
                self.setUpdatedState(True)
                self.loadMdiWidget('MdiHome')
        pd.destroy()

    def export(self):
        ed = ExportDialog(self._settings,
                          self._locale,
                          fi=self._fi,
                          parent=self)
        if (ed.exec_() == QDialog.Accepted):
            QMessageBox.information(self, '' + appinfos.app_name + '', funcs.tr(
                "Opération réussie!"))
        ed.destroy()

    def imports(self):
        ofd = QFileDialog(self,
                          funcs.tr("Importer..."),
                          os.path.expanduser('~'),
                          funcs.tr("Catalogue de données (*.csv)") + ';;' + \
                          funcs.tr("Open Financial Exchange (*.ofx)"))
        ofd.setLocale(self.locale())
        ofd.setAcceptDrops(False)
        if ofd.exec_():
            files = ofd.selectedFiles()
            if len(files) > 0:
                f = files[0]
                filename, extension = os.path.splitext(f)
                id = None
                if extension.strip().lower() == '.csv':
                    id = ImportCsvDialog(self._settings,
                                         self._locale,
                                         fi=self._fi,
                                         file=f,
                                         parent=self)
                elif extension.strip().lower() == '.ofx':
                    id = ImportOfxDialog(self._settings,
                                         self._locale,
                                         fi=self._fi,
                                         file=f,
                                         parent=self)
                if not (id is None):
                    if (id.exec_() == QDialog.Accepted):
                        self.populateAccountsList(lastselected=True)
                        self.loadMdiWidget('MdiHome')
                        QMessageBox.information(self, '' + appinfos.app_name + '', funcs.tr(
                            "Importation réussie!"))
                        id.destroy()
                        self.setUpdatedState(True)

