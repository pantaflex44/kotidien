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

import gc
import os
import sys
import shutil

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import appinfos
import funcs
import globalsv
import icons
from settings import QSettingsEx

from ui.MainWindow import MainWindow

# créé le kit vendeur par défaut (argument --mkvendor)
_createVendor = False

# parametres principaux de l'application
settings = QSettingsEx(os.path.join(globalsv.personnal_path, appinfos.app_name + '.conf'),
                       globalsv.default_params)
# code language utilisé
locale = 'fr_FR'

# liste des traducteurs chargés par au démarrage (pour les conserver en mémoire)
translators = []

# fenêtre signalant une nouvelle version
version_dialog = None


class ProxyStyleEx(QProxyStyle):
    """
    Modification du rendu graphique des widgets
    """

    def drawPrimitive(self, element, option, painter, widget=None):
        # empeche de dessiner les rectangles de focus
        if element != QStyle.PE_FrameFocusRect:
            super(ProxyStyleEx, self).drawPrimitive(
                element, option, painter, widget)



def cleanTmpDirs():
    """
    Nettoie les dossiers temporaires créés pendant l'instance
    """

    for d in os.listdir(globalsv.personnal_path):
        path = os.path.join(globalsv.personnal_path, d)
        if os.path.isdir(path) and \
           os.access(path, os.W_OK) and \
           d.startswith('tmp'):
            shutil.rmtree(path)


def onExit():
    """
    Interception du signal d'extinction de l'application
    """

    # sauvegarde des paramètres
    settings.sync()

    # nettoyage des éléments temporaires créés
    cleanTmpDirs()

    # nettoyage de la mémoire tampon
    gc.collect()


def initDirs():
    """
    Création des dossiers généraux
    """

    parent_pp = os.path.dirname(globalsv.personnal_path)
    if os.path.isdir(parent_pp) and os.access(parent_pp, os.W_OK):
        if not os.path.isdir(globalsv.personnal_path):
            os.mkdir(globalsv.personnal_path)
        if not os.path.isdir(globalsv.i18n_path):
            os.mkdir(globalsv.i18n_path)
        if not os.path.isdir(globalsv.vendor_path):
            os.mkdir(globalsv.vendor_path)


def initSettings():
    """
    Initialisation des paramètres globaux
    """

    global settings, locale

    # if str(settings.value('firstrun', True)).lower() == 'true':
    if settings.value('firstrun'):
        # enregistrement des paramètres par défaut
        for k, v in globalsv.default_params.items():
            settings.setValue(k, v)
        settings.sync()


def initTranslators(app: QApplication):
    """
    Initialisation des traducteurs
    """

    global settings, locale, translators

    # code langue
    locale = settings.value(
        'locale', QLocale.system().name()).replace('-', '_')

    # chargement des traducteurs par défaut
    default_translators = ['qt_', 'qtbase_',
                           'qtdeclarative_', 'linguist_', 'designer_']
    default_location = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
    default_code = locale.split('_')[0].split('.')[0].strip().lower()
    for dt in default_translators:
        t = QTranslator()
        if t.load(dt + default_code, default_location):
            translators.append(t)
            app.installTranslator(t)

    # chargement du traducteur personnalisé
    qmfile = os.path.join(globalsv.i18n_path, locale + '.qm')
    t = QTranslator()
    if t.load(qmfile):
        translators.append(t)
        app.installTranslator(t)

    globalsv.translator = app.translate


def loadThemeColors(app: QApplication):
    """
    Chargement du thème et ses couleurs
    """

    # base du thème au style par défaut 'Fusion'
    app.setStyle(QStyleFactory.create(settings.value('style', 'Fusion')))
    # suppression du rectangle de focus
    app.setStyle(ProxyStyleEx())

    palette = QPalette()

    # chargement du thème personnalisé
    theme_filepath = os.path.join(globalsv.vendor_path, 'vendor.ini')
    custom = QSettings(theme_filepath, QSettings.IniFormat)
    for k, v in globalsv.theme.items():
        if hasattr(QPalette, k):
            key = 'Palette/normal_' + k
            if _createVendor:
                custom.setValue(key, v)
                custom.sync()
            color = custom.value(key, v)
            palette.setColor(getattr(QPalette, k), QColor(color))
    for k, v in globalsv.theme_disabled.items():
        if hasattr(QPalette, k):
            key = 'Palette/disabled_' + k
            if _createVendor:
                custom.setValue(key, v)
                custom.sync()
            color = custom.value(key, v)
            palette.setColor(QPalette.Disabled, getattr(
                QPalette, k), QColor(color))

    app.setPalette(palette)
    # utilisation des icones en haute définition
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)


def loadThemeFonts(app: QApplication):
    """
    Chargement de la police de caractères
    """

    global settings

    fontfile = funcs.rc('/ui/NotoSans-Regular.ttf')
    vendor_fontfile = os.path.join(globalsv.vendor_path, 'vendor.ttf')

    if _createVendor:
        if not funcs.save_rc(fontfile, vendor_fontfile):
            print(funcs.tr("Impossible de créer une copie 'vendor' du fichier {}.".format(
                os.path.basename(fontfile))))

    font_id = -1
    if os.path.exists(vendor_fontfile) and os.access(vendor_fontfile, os.R_OK):
        font_id = QFontDatabase.addApplicationFont(vendor_fontfile)
    if font_id == -1:
        font_id = QFontDatabase.addApplicationFont(fontfile)

    font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
    f = QFont(font_family)
    f.setPointSize(9)
    f.setKerning(True)
    app.setFont(f)


def loadThemeIcons(app: QApplication):
    """
    Pré-chargement des icones
    """

    global settings

    it = QDirIterator(funcs.rc(''), QDirIterator.Subdirectories)
    icons.init()
    while it.hasNext():
        uri = it.next()
        filepath, extension = os.path.splitext(uri)
        filename = os.path.basename(uri)
        if extension.lower() == '.png':
            current = uri
            default = uri

            vendor_uri = os.path.join(globalsv.vendor_path, filename)

            if _createVendor:
                if not funcs.save_rc(uri, vendor_uri):
                    print(funcs.tr("Impossible de créer une copie 'vendor' du fichier {}.".format(
                        os.path.basename(uri))))

            if os.path.exists(vendor_uri) and os.access(vendor_uri, os.R_OK):
                current = vendor_uri

            icons.set(filename, current, default)


def createApp():
    """
    Créé l'application et configure les informations de base
    """

    QCoreApplication.setApplicationName(appinfos.app_name)
    QCoreApplication.setOrganizationName(appinfos.app_author)
    QCoreApplication.setApplicationVersion(appinfos.app_version)

    app = QtGui.QApplication(sys.argv)
    app.setApplicationDisplayName(appinfos.app_name)
    app.setApplicationName(appinfos.app_name)
    app.setApplicationVersion(appinfos.app_version)
    app.setOrganizationName(appinfos.app_author)
    app.setWindowIcon(QIcon(funcs.rc('/Icon.ico')))

    return app


def loadApp(app: QApplication, splash: QSplashScreen = None):
    """
    Chargement de l'application
    """

    global settings, locale

    initTranslators(app)
    loadThemeColors(app)
    loadThemeFonts(app)
    loadThemeIcons(app)

    if _createVendor:
        QMessageBox.information(None, appinfos.app_name, funcs.tr(
            "Le dossier 'vendor' est créé et peuplé avec succès.<br /><br />Vous pouvez le retrouver ici: <b>{}</b>").format(globalsv.vendor_path))
        sys.exit(0)

    # ouverture de la fenetre principale
    mw = MainWindow(settings, locale, splash=splash)
    mw.show()


def loadSplashScreen(app: QApplication):
    """
    Charge l'écran d'accueil
    """

    splash = QSplashScreen(QPixmap(funcs.rc('/ui/icons/iconlarge.png')))
    splash.show()
    splash.showMessage("<big>&nbsp;&nbsp;&nbsp;<b>{}</b></big>".format(appinfos.app_version), alignment=(0x0001 | 0x0080), color=Qt.black)

    QApplication.processEvents()
    __import__('time').sleep(0.5)
    QApplication.processEvents()

    loadApp(app, splash=splash)


# point d'entrée de l'application
if __name__ == '__main__':
    # demande d'initialisation du dossier 'Vendor'
    _createVendor = ('--mkvendor' in sys.argv)

    initDirs()
    initSettings()

    app = createApp()
    # garde le controle sur la fermeture de l'application
    app.aboutToQuit.connect(onExit)

    # if str(settings.value('show_splashscreen', False)).lower() == 'true':
    if settings.value('show_splashscreen'):
        loadSplashScreen(app)
    else:
        loadApp(app)

    sys.exit(app.exec_())