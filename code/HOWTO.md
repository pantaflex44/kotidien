# Do it yourself

## Compilation (freeze)

Kotidien requiert différents éléments pour fonctionner.
Idem pour le compiler (freeze comme on dit par ici 😉)

### La base

- tout d'abord: Python 3. Je vous recommande [Python 3.8.5](https://www.python.org/downloads/release/python-385/) mais une version inférieure jusqu'à Python 3.6 devrait faire l'affaire.
- ensuite il nous faut la bibliothèque graphique pour afficher l'interface et ses fenêtres : [QT 5.12.8](https://www.qt.io/blog/qt-5.12.8-released). La encore une version inférieure pourra surement faire l'affaire.

De part cette base, Kotidien devient donc compatible Linux 32/64bits, Microsoft Windows 7 et supérieur 32/64bits, ainsi que Mac OS 10.9 et supérieur.
Le côté 32 bits et 64 bits dépendent de l'environnement sur lequel les scripts Python sont freezés.
Par exemple, si vous tournez sous Windows 10 32 bits, Python et pré-requis installés, 'pyinstaller' compilera les sources pour Microsoft Windows 32 bits.

### Les modules

Pourquoi réinventer la roue?

Kotidien utilise divers modules partagés par la communauté et bien évidemment open-sources.
En voici la liste nécessaire à son bon fonctionnement :


- [PyQt5](https://pypi.org/project/PyQt5/) 5.15.1

```bash
pip3 install PyQt5
```

- [pycountry](https://pypi.org/project/pycountry/) 20.7.3

```bash
pip3 install pycountry
```

- [nh-currency](https://pypi.org/project/nh-currency/) 1.0.1

```bash
pip3 install nh-currency
```

- [pyqtgraph](https://pypi.org/project/pyqtgraph/) 0.11.1

```bash
pip3 install pyqtgraph
```

- [fpdf2](https://pypi.org/project/fpdf2/) 2.2.0

```bash
pip3 install fpdf2
```

- [ofxtools](https://pypi.org/project/ofxtools/) 0.9.1

```bash
pip3 install ofxtools
```

- [cryptography](https://pypi.org/project/cryptography/) 2.8

```bash
pip3 install cryptography
```

- [python-dateutil](https://pypi.org/project/python-dateutil/) 2.8.1

```bash
pip3 install python-dateutil
```

- [glibc](https://pypi.org/project/glibc/) 0.6.1

```bash
pip3 install glibc
```

- [six](https://pypi.org/project/six/) 1.15.0

```bash
pip3 install six
```

- [pdf2image]( 2.8.1https://pypi.org/project/pdf2image/) 1.14.0

```bash
pip3 install pdf2image
```


Pour compiler ou exécuter les sources de Kotidien, ces modules doivent être préalablement installés.

### Le coup de froid (freezer)

Pour freezer, comme dit plus haut, j'utilise 'pyinstaller'. Le fichier 'Kotidien.spec' à la racine sert à cela.
Freezer permet de compiler un script Python pour le rendre exécutable et portatif sans devoir installer Python et ses dépendances. Les dépendances seront directement incluses dans le dossier résultant.

Dans un premier temps installer 'pyinstaller'

```bash
pip3 install pyinstaller
```

Puis aller dans le dossier contenant les sources de Kotidien pour exécuter:

```bash
# linux
$ pyinstaller --clean --onefile --windowed --distpath ../dist/Kotidien.linux --workpath ../build/linux -y Kotidien.spec

# windows
> pyinstaller.exe --clean --onefile --windowed --distpath ../dist/Kotidien.win --workpath ../build/win -y Kotidien.spec
```

Et c'est tout!

Désormais, vous trouvez dans le dossier des sources, un répertoire 'build' contenant une version exécutable de Kotidien adaptée à votre système d'exploitation et compatibles.

## Customization

Kotidien offre la possibilité d'adapter l'interface graphique  aux couleurs de votre choix.
Cela permet par exemple, d'adapter couleurs et icones au style d'un environnement à partager.

### Le dossier 'Vendor'

Kotidien permet de créer un dossier nommé 'Vendor'. Ce dossier contiendra les éléments visuels personnalisant l'application.

Dans un premier temps, créons ce dossier. Pour celà il vous faudra lancer l'application en ligne de commande:

```bash
# linux
$ ./Kotidien --mkvendor

# Windows
> Kotidien.exe --mkvendor
```

L'application vous informe que le dossier 'Vendor' à correctement été créé, son contenu par défaut peuplé, et le chemin d'accès à celui-ci.

```bash
$ cd ~/.Kotidien/vendor
```

### Les icones

Le dossier 'Vendor' contient une liste d’icônes au format PNG et précisément nommées.
Il vous suffit de remplacer les icônes par celles de votre choix en faisant très attention de conserver les noms des fichiers.

### La police de caractère

Kotidien utilise par défaut la police de caractère _NotoSans-Regular.ttf_ .
Le dossier 'Vendor' permet de remplacer la police par défaut en remplaçant le fichier nommé _vendor.ttf_ . Encore une fois, faire attention à respecter le nom du fichier.

### Palette de couleurs

Le dossier 'Vendor' contient un fichier nommé _vendor.ini_ . Ce fichier contient les réglages de la palette de couleurs utilisée par Kotidien.
Il se compose comme suit:

```ini
[Palette]
disabled_AlternateBase=#eeeeee
disabled_Base=#eeeeee
disabled_BrightText=#808080
disabled_Button=#eeeeee
disabled_ButtonText=#808080
disabled_HighlightedText=#808080
disabled_Link=#808080
disabled_LinkVisited=#808080
disabled_NoRole=#808080
disabled_Text=#808080
disabled_ToolTipBase=#eeeeee
disabled_ToolTipText=#808080
disabled_Window=#eeeeee
disabled_WindowText=#808080
normal_AlternateBase=#eff0f1
normal_Base=#fcfcfc
normal_BrightText=#ffffff
normal_Button=#eff0f1
normal_ButtonText=#232627
normal_Dark=#888e93
normal_Highlight=#00c5b5
normal_HighlightedText=#000000
normal_Light=#ffffff
normal_Link=#009589
normal_LinkVisited=#7f8c8d
normal_Midlight=#f7f7f8
normal_NoRole=#000000
normal_Shadow=#474a4c
normal_Text=#232627
normal_ToolTipBase=#232627
normal_ToolTipText=#fcfcfc
normal_Window=#eff0f1
normal_WindowText=#232627
```

Il vous suffit de modifier le code couleur hexadécimal derrière chaque mots clefs pour personnaliser les couleurs de l'application!

## Traductions

Rien de mieux que de pouvoir utiliser Kotidien dans sa langue natale. Et cela est possible.
Vous pouvez participer à l'effort de guerre en proposant vos propres traductions. Ces traductions devront etre copiées dans le dossier 'languages':

```bash
$ cd ~/.Kotidien/languages
```

Les fichiers de traductions sont composés d'un 'catalogue de traductions' au format .ts éditable depuis l'application **Qt Linguist** fournie par **Qt**.
Pour être utilisés dans Kotidien, vous devrez les publier au format .qm (Qt Linguist permet de le faire).

### Construire un catalogue de traductions .ts

Pour commencer il va vous falloir extraire toutes les chaines de caractères à traduire des différents fichiers des sources de Kotidien:

```bash
$ cd DOSSIER_DES_SOURCES_DE_KOTIDIEN

# création du catalogue et extraction
# des chaines de caractères des fichiers
# présent à la racine des sources
$ lupdate * -ts fr_FR.ts -verbose

# complétion du catalogue avec les chaines
# extraites de l'interface graphique et de
# ses composants
$ pylupdate5 ./ui/*.py -ts fr_FR.ts -verbose

# certains accents sont mal encodés, on corrige cela
$ python3 lupdate_ts_repair.py fr_FR.ts
```

### Compiler le catalogue obtenu

Le catalogue désormais créé, le modifier avec votre éditeur préféré puis le compiler pour le rendre utilisable:

```bash
$ lrelease fr_FR.ts -qm fr_FR.qm -verbose
```

Et voila! Il ne reste plus qu'a copier coller le fichier .qm obtenu dans le dossier 'languages'.
Exécutez Kotidien, allez dans le menu **Aide** / **Langues** pour voir apparaître votre nouvelle traduction ;-)





