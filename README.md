# logview

GitHub action log archive viewer

Command line tool processes GitHub actions log archive .zip file.

- Consumes previously downloaded Log archives.
- Scans for specific strings like "warning" or "error" and
  summarizes findings at the end.
- Intended for use in a terminal either stand alone or one
  lauched by an IDE.
- Colorizes phrases.
- Override default configuration by providing a .toml file. 

Requires Python Package Index packages colorama and tomli.

[![](https://img.shields.io/pypi/l/phmdoctest.svg)](https://github.com/tmarktaylor/logview/blob/master/LICENSE.txt)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![CI Test](https://github.com/tmarktaylor/logview/actions/workflows/ci.yml/badge.svg)](https://github.com/tmarktaylor/logview/actions/workflows/ci.yml)
