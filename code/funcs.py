#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
@package Kotidien
'''
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
import glob
import datetime
import inspect
import re
import json
import requests
import threading
from datetime import datetime, date, timedelta

from PyQt5.QtCore import QCoreApplication, QFile, QTextStream, QByteArray, QIODevice
from PyQt5.QtGui import QIcon
from PyQt5.uic import loadUi

import libs.pycountry

import resources
import appinfos
import globalsv


def replace_encoding(text):
    return text


def tr(message:str, classname:str='funcs'):
    message = str(message)

    if not(globalsv.translator is None):
        trad = globalsv.translator(classname, message.encode('utf-8'))
        if trad.strip() != '':
            return replace_encoding(trad)

    return replace_encoding(message)


def rc(name: str, prefix: str=''):
    if prefix.strip() == '':
        prefix = appinfos.app_name

    path = ':/' + prefix + name
    return path


def save_rc(rcpath: str, destfile: str, overwrite:bool=True):
    if not overwrite and os.path.exists(destfile):
        return False

    try:
        s = QFile(rcpath)
        s.open(QIODevice.ReadOnly)
        d = QFile(destfile)
        d.open(QIODevice.WriteOnly)
        d.write(s.readAll())
        d.close()
        s.close()
        return True
    except:
        return False


def get_availlable_locales(default:str='fr_FR'):
    extension = '.qm'
    langs = {}

    code, country = default.split('_')
    locale = libs.pycountry.countries.get(alpha_2=country)
    langs[default] = {'name': locale.name,
                      'official': locale.official_name,
                      'alpha_2': locale.alpha_2.upper(),
                      'alpha_3': locale.alpha_3.lower(),
                      'icon': rc('/ui/flags/' + locale.alpha_3.lower() + '.png', 'Extras')}

    for lf in glob.glob(os.path.join(globalsv.i18n_path, '*' + extension), recursive=True):
        lang = os.path.basename(lf).replace(extension, '')
        if lang == default:
            continue
        try:
            code, country = lang.split('_')
            locale = libs.pycountry.countries.get(alpha_2=country)
            if not(locale is None):
                langs[lang] = {'name': locale.name,
                               'official': locale.official_name,
                               'alpha_2': locale.alpha_2.upper(),
                               'alpha_3': locale.alpha_3.lower(),
                               'icon': rc('/ui/flags/' + locale.alpha_3.lower() + '.png', 'Extras')}
        except:
            continue

    return langs


def check_file_writable(fnm):
    if os.path.exists(fnm):
        if os.path.isfile(fnm):
            return os.access(fnm, os.W_OK)
        else:
            return False
    pdir = os.path.dirname(fnm)
    if not pdir:
        pdir = '.'
    return os.access(pdir, os.W_OK)


def text2color(text: str, length: int = 180) -> list:
    t = text.strip()
    if t == '':
        return [0, 0, 0], "#000000"
    hash = 0
    for i in range(len(t)):
        hash = ord(t[i]) + ((hash << 5) - hash)
    b = hash & length
    g = (hash >> 8) & length
    r = (hash >> 16) & length
    html = "#{:02x}{:02x}{:02x}".format(r, g, b)
    return [r, g, b], html


def first_day_of_month(any_day):
    return any_day.replace(day=1)


def last_day_of_month(any_day):
    try:
        next_month = any_day.replace(day=28) + timedelta(days=4)
        return next_month - timedelta(days=next_month.day)
    except:
        return any_day


def until_now(dte: date):
    return (dte <= datetime.now().date())


def until_last_day_of_month(dte: date):
    return (dte <= last_day_of_month(datetime.now().date()))


def until_last_day_of_year(dte: date):
    return (dte <= datetime.now().date().replace(month=12, day=31))


def loadUiResource(respath, parent):
    stream = QFile(respath)
    stream.open(QFile.ReadOnly)
    ts = QTextStream(stream)
    ts.setCodec('utf-8')
    data = ts.readAll()
    stream.close()

    # traduit toutes les chaines de caracteres des fichiers contenant les interfaces graphiques (*.ui)
    cn = os.path.basename(respath).replace('.ui', '')
    ms = '(?<=<string>).*?(?=<\/string>)'
    pattern = re.compile(ms)
    matches = pattern.finditer(data)
    for m in matches:
        key = data[m.start():m.end()]
        trad = tr(key, classname=cn)
        data.replace(key, trad)

    # remplace les mots clefs correspondant aux clefs 'appinfos'
    # eg: {app_name} | {app_version} | ...
    module = globals().get('appinfos', None)
    for key, value in module.__dict__.items():
        if key.startswith('app_'):
            if type(value) == date:
                value = value.strftime('%x')
            if type(value) == str:
                data = data.replace('{' + key + '}', value)

    # remplace les mots clefs indiquant les versions des modules
    # eg: {version_python} | {version_pycountry} | ...
    for m in globalsv.modules:
        data = data.replace('{version_' + m[0].lower() + '}', m[1])

    try:
        uidata = QByteArray()
        uidata.append(data)
        uistream = QTextStream(uidata)
        uistream.setCodec('utf-8')
        ui = loadUi(uistream, parent)
        return ui
    except Exception as e:
        print(e)
        return None
    finally:
        stream.close()


def qicon2png(icon:QIcon, filepath:str, sizes:list=[16,24,32,48,64,96,128,192,256]):
    created = []
    path = os.path.dirname(filepath)
    if os.path.isdir(path) and \
       os.access(path, os.W_OK) and \
       not(icon is None):
        filename, extension = os.path.splitext(filepath)
        icon_filepath = os.path.join(path, filename + '{}.png')
        for s in sizes:
            filepath = icon_filepath.format(str(s))
            if not os.path.exists(filepath):
                img = icon.pixmap(QSize(s, s))
                fi = QFile(filepath)
                fi.open(QIODevice.WriteOnly)
                img.save(fi, 'PNG')
                fi.close()
            created.append(filepath)
    return created


def get_current_version():
    v = appinfos.app_version
    d = datetime.now().strftime('%Y-%m-%d')
    u = ''
    try:
        r = requests.get(globalsv.sourceforge_files_url.format(globalsv.version_filename),
                         timeout=5)
        version = json.loads(r.content)

        dct = None
        if sys.platform.startswith('linux'):
            dct = version['linux']
        elif sys.platform == 'win32':
            dct = version['windows']
        if type(dct) == dict:
            v = dct['lastest']
            d = dct['date']
            u = dct['url']
    except:
        pass

    return (v, d, u)


def is_new_version(old, new):
    o = [0, 0, 0, 0]
    for i,x in enumerate(old.split('.')):
        if i <= len(o) - 1:
            o[i] = (int(x) if x.isdigit() else 0)

    n = [0, 0, 0, 0]
    for i,x in enumerate(new.split('.')):
        if i <= len(n) - 1:
            n[i] = (int(x) if x.isdigit() else 0)

    ret = False
    for i,x in enumerate(o):
        if n[i] > x:
            ret = True
            break

    return ret


def has_new_version(callback=None):
    if callback is None or \
       not callable(callback):
        return

    def has_new_version_callback(cb):
        vs, dte, url = get_current_version()
        inv = is_new_version(appinfos.app_version, vs)
        cb(vs, dte, url, inv)

    t = threading.Thread(target=has_new_version_callback,
                         kwargs=dict(cb=callback),
                         name='has_new_version',
                         daemon=True)
    t.start()
