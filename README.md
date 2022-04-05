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

## Usage
<!--phmdoctest-label usage-->
```shell
usage: logview.py [-h] [--auto-locate-logfile] FILE [FILE ...]

positional arguments:
  FILE                  One or more .toml or .zip files.

optional arguments:
  -h, --help            show this help message and exit
  --auto-locate-logfile
                        Locate logfile specified by criteria in the .toml
                        file.
```
## Default Configuration

<!--phmdoctest-label default-configuration-->
```toml
[tool.logview]
# Provide direction to --auto-locate-logfile
log_file_directory = ""
archives = "logs*.zip"
repository = ""    # <GitHub user login name>/project
contains_member = "*.txt"  # archive member (wildcards allowed)

do_not_scan = ["*",]
do_not_show = []
show_at_end = []
keep_timetags = false

# Do not print log lines containing any of these patterns.
do_not_print = [
    " remote: Counting objects: ",
    " remote: Compressing objects: ",
    " Receiving objects: ",
    " Resolving deltas: ",
]

summary_title = "errors"
summary_color = "RED"
# Entire line containing the string is added to summary. Any case matches.
summary_patterns = [
    "warning",
     "error",
     "Process completed with exit code 1",
]

# Line containing the exact string is exempt from summary checking above.
summary_exemptions = [
    "Evaluating continue on error",
    "hint: of your new repositories, which will suppress this warning, call:",
    "fail_ci_if_error: false",
]

# Colorize these phrases in a log line. The color must be a name
# defined by colorama.Fore.
[tool.logview.phrases]
    " OK" = "GREEN"
    "PASSED" = "GREEN"
    "FAILED" = "RED"
    "SKIPPED" = "LIGHTYELLOW_EX"
    "hint:" =  "GREEN"

```
## Coverage Report
<!--phmdoctest-label coverage-report-->
```shell
Name         Stmts   Miss Branch BrPart  Cover
----------------------------------------------
logview.py     228     49     91     10    77%
----------------------------------------------
TOTAL          228     49     91     10    77%
```

## Hints
- This project is unversioned and subject to future breaking changes.
- Text within archive members may change over time requiring
  updates to search patterns.
