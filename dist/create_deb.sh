#! /bin/sh

echo "Création des répertoires..."
mkdir -p ./debian
mkdir -p ./Kotidien/DEBIAN
mkdir -p ./Kotidien/usr/local/bin
mkdir -p ./Kotidien/usr/local/Kotidien
mkdir -p ./Kotidien/usr/share/applications
mkdir -p ./Kotidien/usr/share/doc/Kotidien

echo "\nCopie des fichiers..."
cp ./Kotidien.linux/CHANGELOG.md ./debian/changelog
cp ./Kotidien.linux/Kotidien.debian_control ./debian/control
cp ./Kotidien.linux/README.md ./debian/README.Debian
cp ./Kotidien.linux/COPYRIGHT.txt ./debian/copyright
cp ./Kotidien.linux/LICENCE.txt ./debian/license
cp ./Kotidien.linux/Kotidien.desktop ./Kotidien/usr/share/applications/Kotidien.desktop
cp ./debian/control ./Kotidien/DEBIAN/control
cp ./debian/changelog ./Kotidien/usr/share/doc/Kotidien/changelog.gz
gzip -9 ./Kotidien/usr/share/doc/Kotidien/changelog.gz
cp -R ./Kotidien.linux/* ./Kotidien/usr/local/Kotidien

echo "\nCréation du lien symbolique..."
echo '#! /bin/sh

chmod +x /usr/local/Kotidien/Kotidien
ln -s /usr/local/Kotidien/Kotidien /usr/local/bin/Kotidien
' > ./Kotidien/DEBIAN/postinst
chmod 0775 ./Kotidien/DEBIAN/postinst

echo "\nCréation du paquet debian..."
dpkg-deb --build Kotidien

echo "\nSuppression du répertoire de travail..."
rm -rf ./debian
rm -rf ./Kotidien

echo "\nTerminé!"




