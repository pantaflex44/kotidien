#! /bin/sh

pyinstaller --clean --onefile --windowed --distpath ../dist/Kotidien.linux --workpath ../build/linux -y Kotidien.spec
