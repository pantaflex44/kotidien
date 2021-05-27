# Kotidien

![Kotidien](https://a.fsdn.com/allura/p/kotidien/icon?1614505402?&w=90)

Kotidien est une application dédiée à la gestion de votre argent. Comptes bancaires, cartes de paiements autonomes, et portefeuille d'espèces. Totalement libre et gratuite, elle vous permets de tenir vos comptes d'une main de fer. Écrite en Python 3 et compatible Linux (intégration parfaite sous KDE via l'utilisation de QT 5.12), Microsoft Windows 7 et supérieurs, Mac OS 10.11 et supérieurs.
Kotidien vous donne un accès permanent et en temps réel sur vos différents soldes, permets aussi d'automatiser l'écriture de vos transaction récurrentes, de pointer celles mises à jour sur votre interface bancaire, etc
Agencées au jour le jour, supplantées par une vue calendrier, et synthétisées sur des graphiques clairs, toutes vos transactions sont réunies au sein de Kotidien.
La complétion automatique des différentes informations permet une saisie plus rapide des données.
Plusieurs languages vous sont proposés avec par défaut le Français.

## Points forts

* Protection du dossier financier Kotidien par mot de passe
* Copie de sauvegarde (.bak) automatique à chaque ouverture d'un dossier.
* Facilement transportable, ne nécessite pas d'installation!
* Assistant de création de dossiers financiers
* Supporte les comptes en banques, cartes de paiements autonomes et - portefeuilles d'espèces.
* Personnalisation des types de transactions (carte bancaire, virement, prélèvement, etc.)
* Personnalisation des catégories et sous catégories
* Personnalisation des tiers
* Calcul automatique du solde du jour
* Prévision automatique du solde "fin de mois"
* Classement des transactions par jours
* Anticipation du solde à date souhaitée
* Possibilité d'ajouter titre, mémo et commentaire pour chaque transaction
* Complétion automatique des données pour une écriture rapide des transactions
* Gestion du découvert
* Gestion des transferts entre comptes bancaires d'un même dossier Kotidien
* Planification automatique de transactions avec répétitions programmables
* Importation et exportation des données au format CVS programmable
* Importation et exportation des données au format OFX compatible Money 98-2003
* Résumé graphique des différentes évolutions de votre dossier financier
* Statistiques graphiques complètes
* Fichier d'aide disponible directement depuis l'application
* Traduction de l'application en plusieurs langues. Français par défaut.
* Possibilité de personnaliser l'apparence de Kotidien pour redistribuer l'application aux couleurs de votre système.
* Incorporation facile par dossier 'vendor'
* Totalement libre et gratuit! Licence open-source GNU GPL v3
* Écrite en Python, utilise QT. Supporte Windows , Linux et Mac OS.
* ...

![Kotidien - Liste des transactions](https://a.fsdn.com/con/app/proj/kotidien/screenshots/Kotidien2.png/max/max/1)

![Kotidien - Accueil et résumé](https://a.fsdn.com/con/app/proj/kotidien/screenshots/Kotidien1.png/max/max/1)

![Kotidien - Vue calendrier](https://a.fsdn.com/con/app/proj/kotidien/screenshots/Kotidien3.png/max/max/1)

## Installation et utilisation

### Compatibilité

- Microsoft Windows 32bits / 64bits - (7, 8, 10)
- Linux 64bits - (libc6 2.29+ > Ubuntu 19.04+, Debian 11+, Fedora 31+, openSUSE Tumbleweed+)

### Exécution

Aucune installation n'est nécessaire. Décompressez l'archive dans le dossier de votre choix et exécutez le fichier **Kotidien** ou **Kotidien.exe** pour lancer l'application

```bash
# linux
$ chmod +x Kotidien
$ ./Kotidien

# windows
> Kotidien.exe
```

#### Important ####
- Pour la version Linux, requiert libc6 2.29 ou supérieur (GLIBC_2.29+)

## Aide et utilisation

un forum de discussion ainsi que des pages d'aides sont mis en place sur SourceForge.

Rendez-vous sur [Aide et Discussion](https://sourceforge.net/p/kotidien/discussion/aide/)

## Eléments externes

### [Icons8](https://icones8.fr/)

Icones utilisées par l'application.

Licence [CC BY-ND 3.0](https://creativecommons.org/licenses/by-nd/3.0/)

### [pycountry](https://pypi.org/project/pycountry/)

pycountry provides the ISO databases for the standards:

639-3 Languages
3166 Countries
3166-3 Deleted countries
3166-2 Subdivisions of countries
4217 Currencies
15924 Scripts
The package includes a copy from Debian’s pkg-isocodes and makes the data accessible through a Python API.

Translation files for the various strings are included as well.

Licence [GNU Lesser General Public License v2](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)

### [nh-currency](https://pypi.org/project/nh-currency/)

A simple currency module to:

- Retrive various info about currency
- Format currency price
- Convert between currencies

Licence [BSD License](https://fr.wikipedia.org/wiki/Licence_BSD)

### [pyqtgraph](https://pypi.org/project/pyqtgraph/)

PyQtGraph is a pure-python graphics and GUI library built on PyQt4/PyQt5/PySide/PySide2 and numpy.

It is intended for use in mathematics / scientific / engineering applications. Despite being written entirely in python, the library is very fast due to its heavy leverage of numpy for number crunching, Qt’s GraphicsView framework for 2D display, and OpenGL for 3D display.

Licence [MIT](https://choosealicense.com/licenses/mit/)

### [fpdf2](https://pypi.org/project/fpdf2/)

fpdf2 is a minimalist PDF creation library for Python:

It is a fork and the successor of PyFPDF. Compared with other PDF libraries, fpdf2 is simple, small and versatile, with advanced capabilities, and is easy to learn, extend and maintain.

Licence [GNU Lesser General Public License v3](https://www.gnu.org/licenses/lgpl-3.0.en.html)

### [ofxtools](https://pypi.org/project/ofxtools/)

ofxtools is a Python library for working with Open Financial Exchange (OFX) data - the standard format for downloading financial information from banks and stockbrokers. OFX data is widely provided by financial institutions so that their customers can import transactions into financial management software such as Quicken, Microsoft Money, or GnuCash.

If you want to download your transaction data outside of one of these programs - if you wish to develop a Python application to use this data - if you need to generate your own OFX-formatted data… ofxtools is for you!

Licence [MIT](https://choosealicense.com/licenses/mit/)

### [cryptography](https://pypi.org/project/cryptography/)

cryptography is a package which provides cryptographic recipes and primitives to Python developers. Our goal is for it to be your “cryptographic standard library”. It supports Python 3.6+ and PyPy3 7.2+.

cryptography includes both high level recipes and low level interfaces to common cryptographic algorithms such as symmetric ciphers, message digests, and key derivation functions.

Licence [BSD License](https://fr.wikipedia.org/wiki/Licence_BSD)

### [python-dateutil](https://pypi.org/project/python-dateutil/)

The dateutil module provides powerful extensions to the standard datetime module, available in Python.

Licence [BSD License](https://fr.wikipedia.org/wiki/Licence_BSD)

### [glibc](https://pypi.org/project/glibc/)

Pure-Python bindings to glibc (based on ctypes).

Licence [GNU Lesser General Public License v3](https://www.gnu.org/licenses/lgpl-3.0.en.html)

### [six](https://pypi.org/project/six/)

Six is a Python 2 and 3 compatibility library. It provides utility functions for smoothing over the differences between the Python versions with the goal of writing Python code that is compatible on both Python versions. See the documentation for more information on what is provided.

Licence [MIT](https://choosealicense.com/licenses/mit/)

### [pdf2image](https://pypi.org/project/pdf2image/)

A python (3.5+) module that wraps pdftoppm and pdftocairo to convert PDF to a PIL Image object.

Licence [MIT](https://choosealicense.com/licenses/mit/)


## Informations

Copyright (c)2020-2021 [Christophe LEMOINE](pantaflex@tuta.io)

[https://sourceforge.net/projects/kotidien/](https://sourceforge.net/projects/kotidien/)

Date de création 05/11/2020

Kotidien est sous licence libre et open-source GNU GPL v3. Cette licence vous permet de redistribuer, modifier et améliorer Kotidien à votre guise. Elle vous interdit de revendre l'application ou ce qu'elle contient.
Toute modification, redistribution ou amélioration devra citer l'auteur original dans le respect de la licence.


## Licence de Kotidien
[GNU General Public License v3](https://www.gnu.org/licenses/gpl-3.0.en.html)


## Contribuer

### Compiler les ressources

```bash
$ pyrcc5 resources.qrc -o resources.py
```

### Construire l'éxécutable avec 'pyinstaller'

```bash
# linux
# installer pyinstaller
$ pip3 install pyinstaller
# freezer l'application
$ pyinstaller --clean --onefile --windowed --distpath ../dist/Kotidien.linux --workpath ../build/linux -y Kotidien.spec

# windows
# installer pyinstaller
> pip install pyinstaller
# freezer l'application
> pyinstaller.exe --clean --onefile --windowed --distpath ../dist/Kotidien.win --workpath ../build/win -y Kotidien.spec
```

### Traduire et compiler les traductions

```bash
# créé le catalogue
$ lupdate * -ts fr_FR.ts -verbose
# complète le catalogue avec le contenu des scripts Pythons
$ pylupdate5 ./ui/*.py -ts fr_FR.ts -verbose
# corrige certains accents
$ python3 lupdate_ts_repair.py fr_FR.ts
# compile le catalogue
$ lrelease fr_FR.ts -qm fr_FR.qm -verbose
```

### Fichiers de données

#### appinfos.py

Contient les informations relatives à l'application.

#### globalsv.py

Paramètres par défaut et données globales utilisées par l'application.

#### Kotidien.spec / Kotidien.rc.tpl / Kotidien.rc

Paramètres utilisés par pyinstaller.
- *Kotidien.spec*  					: Fichier de configuration pour la compilation
- *Kotidien.rc.tpl / Kotidien.rc	: Fichier de configuration du manifest de l'exécutable pour Microsoft Windows

#### resources.py / resources.qrc

Liste des ressources utilisées dans l'application.

#### datamodels.py

Structure meme d'un portefeuille Kotidien. La base de toute l'application.
