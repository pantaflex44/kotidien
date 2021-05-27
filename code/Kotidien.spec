# -*- mode: python -*-
import sys
import os
import io
import shutil
import json
import requests
from datetime import datetime, date
from pkgutil import iter_modules

path = os.environ.get("_MEIPASS2", os.path.abspath("."))
sys.path.append(path)
import appinfos
import globalsv

def module_exists(module_name):
    return module_name in (name for loader, name, ispkg in iter_modules())

def generate_rc(template='Kotidien.rc.tpl', output='Kotidien.rc'):
    version_str = appinfos.app_version
    version_tuple = tuple(map(int, version_str.split('.')))
    date_tuple = (appinfos.app_date.year, appinfos.app_date.month, appinfos.app_date.day)
    tpl = io.open(template, encoding='utf-8')
    out = io.open(output, 'w', encoding='utf-8')
    with tpl, out:
        out.write(tpl.read().format(
            version=version_str,
            version_tuple=version_tuple,
            name=appinfos.app_name,
            exe=appinfos.app_exe,
            description=appinfos.app_description,
            author=appinfos.app_author,
            copyright=appinfos.app_copyright,
            date_tuple=date_tuple))
        return output

def generate_desktop_entry(template='Kotidien.desktop.tpl', output='Kotidien.desktop'):
    tpl = io.open(template, encoding='utf-8')
    out = io.open(output, 'w', encoding='utf-8')
    with tpl, out:
        name = appinfos.app_name
        version = appinfos.app_version
        description = appinfos.app_description
        shortdescription = appinfos.app_shortdescription
        desktopicon = appinfos.app_desktopicon
        out.write(tpl.read().format(
            name=name,
            version=version,
            description=description,
            shortdescription=shortdescription,
            desktopicon=desktopicon))
        return output

def generate_debian_control(template='Kotidien.debian_control.tpl', output='Kotidien.debian_control'):
    tpl = io.open(template, encoding='utf-8')
    out = io.open(output, 'w', encoding='utf-8')
    with tpl, out:
        name = appinfos.app_name
        version = appinfos.app_version
        description = appinfos.app_description
        author = appinfos.app_author
        mail = appinfos.app_mail
        url = appinfos.app_url
        out.write(tpl.read().format(
            name=name,
            version=version,
            description=description,
            author=author,
            mail=mail,
            url=url))
        return output

def create_version_json(output='../dist/VERSION.json'):
    version = {'linux': {'lastest': '0.0.0.0', 'date': '1970-01-01', 'url': globalsv.sourceforge_dwlnd_url_linux},
               'windows': {'lastest': '0.0.0.0', 'date': '1970-01-01', 'url': globalsv.sourceforge_dwlnd_url_windows}}

    if os.path.exists(output):
        v = io.open(output, 'r', encoding='utf-8')
        with v:
            version = json.loads(v.read())
    else:
        try:
            r = requests.get(globalsv.sourceforge_files_url.format(globalsv.version_filename))
            version = json.loads(r.content)
        except:
            pass

    pltf = ''
    if sys.platform.startswith('linux'):
        pltf = 'linux'
    elif sys.platform.startswith('win'):
        pltf = 'windows'

    if pltf != '':
        version[pltf]['lastest'] = appinfos.app_version
        version[pltf]['date'] = datetime.now().strftime('%Y-%m-%d')

    out = io.open(output, 'w', encoding='utf-8')
    with out:
        json.dump(version, out)

create_version_json()

copyfiles = [
                (os.path.join(path, 'LICENCE_icons8.pdf'), '.'),
                (os.path.join(path, 'LICENCE_pycountry.txt'), '.'),
                (os.path.join(path, 'LICENCE.txt'), '.'),
                (os.path.join(path, 'CHANGELOG.md'), '.'),
                (os.path.join(path, 'README.md'), '.'),
                (os.path.join(path, 'HOWTO.md'), '.'),
                (os.path.join(path, 'Icon.ico'), '.'),
                (os.path.join(path, 'libs', 'pycountry'), 'pycountry')
            ]
if sys.platform.startswith('linux'):
    copyfiles.append((os.path.join(path, 'icons', 'Icon.png'), '.'))
    copyfiles.append((os.path.join(path, generate_desktop_entry()), '.'))
    copyfiles.append((os.path.join(path, generate_debian_control()), '.'))
    copyfiles.append((os.path.join(path, 'COPYRIGHT.txt'), '.'))
for file in copyfiles:
    if os.path.isdir(file[0]):
        topath = os.path.join(DISTPATH, file[1])
        if os.path.exists(topath):
            continue
        shutil.copytree(file[0], topath)
    else:
        topath = os.path.join(DISTPATH, file[1], os.path.basename(file[0]))
        if os.path.exists(topath):
            continue
        shutil.copyfile(file[0], topath)

sitepackages = [p for p in sys.path if 'site-packages' in p]
distpackages = [p for p in sys.path if 'dist-packages' in p]
hiddenimports = [m[4] for m in globalsv.modules if module_exists(m[4])]

block_cipher = None

# pathex=[path] + sitepackages + distpackages

a = Analysis([appinfos.app_mainscript],
             pathex=[path],
             binaries=[],
             datas=[],
             hiddenimports=hiddenimports,
             hookspath=[],
             runtime_hooks=[],
             excludes=['PySide2', 'FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter', 'cpython'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=appinfos.app_name,
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          icon=appinfos.app_exeicon,
          version=generate_rc())
