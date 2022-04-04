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
- Locates newest .zip for a specific repository.
- See tests/configs and logview.py:default_config for
  example configuration files.

Requires Python Package Index packages colorama and tomli.

[![GitHub](https://img.shields.io/github/license/tmarktaylor/logview)](https://github.com/tmarktaylor/logview/blob/master/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![CI Test](https://github.com/tmarktaylor/logview/actions/workflows/ci.yml/badge.svg)](https://github.com/tmarktaylor/logview/actions/workflows/ci.yml)

## Installation

- Suggest installing in a Python virtual environment.
- Copy the file logview.py to a folder that is on PYTHONPATH.
- Install dependencies:
```shell
python -m pip install --upgrade pip
python -m pip install colorama
python -m pip install tomli
```

# Hints
- This project is unversioned and subject to future breaking changes.
- Text within archive members may change over time requiring
  updates to search patterns.
