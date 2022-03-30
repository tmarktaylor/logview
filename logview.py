"""Display parts of GitHub Action log zip files.

Copyright (c) 2022 Mark Taylor

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import argparse
from dataclasses import dataclass
from enum import Enum
import fnmatch
from pathlib import Path
import re
from typing import Any
from typing import List
from typing import Optional
from typing import Tuple
from zipfile import ZipFile

from colorama import Fore  # type: ignore

try:
    import tomllib  # type: ignore
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore


@dataclass
class Highlighter:
    """A string and terminal color code start sequence."""

    text: str
    effect: str

    def __post_init__(self) -> None:
        self._code_sequence = self.effect + self.text + str(Fore.RESET)

    def highlighted(self) -> str:
        return self._code_sequence


def colorize_line(line: str, phrases: List[Highlighter]) -> str:
    # Colorize all phrases in the line.
    if chr(27) + "[" not in line:  # ANSI start sequence
        for phrase in phrases:
            line = line.replace(phrase.text, phrase.highlighted())
    return line


class ColorName(Enum):
    """Lookup table to convert the Fore color name string to the ansi sequence."""

    NONE = ""
    BLACK = Fore.BLACK
    BLUE = Fore.BLUE
    CYAN = Fore.CYAN
    GREEN = Fore.GREEN
    LIGHTBLACK_EX = Fore.LIGHTBLACK_EX
    LIGHTBLUE_EX = Fore.LIGHTBLUE_EX
    LIGHTCYAN_EX = Fore.LIGHTCYAN_EX
    LIGHTGREEN_EX = Fore.LIGHTGREEN_EX
    LIGHTMAGENTA_EX = Fore.LIGHTMAGENTA_EX
    LIGHTRED_EX = Fore.LIGHTRED_EX
    LIGHTWHITE_EX = Fore.LIGHTWHITE_EX
    LIGHTYELLOW_EX = Fore.LIGHTYELLOW_EX
    RED = Fore.RED
    RESET = Fore.RESET
    WHITE = Fore.WHITE
    YELLOW = Fore.YELLOW


default_config = """
[tool.logview]
log_file_directory = ""
archives = "logs*.zip"
contains_member = "*.txt"
do_not_scan = ["*",]
do_not_show = []
show_at_end = []
keep_timetags = false

# Exclude log lines containing any of these patterns.
excludes = [
    " remote: Counting objects: ",
    " remote: Compressing objects: ",
    " Receiving objects: ",
    " Resolving deltas: ",
]

# Entire line containing the string treated as error. Any case matches.
errors = [
    "warning",
     "error",
     "Process completed with exit code 1",
]

# Line containing the exact string is exempt from errors checking above.
error_exemptions = [
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
"""


class Config:
    """Process TOML configuration file parts into object attributes."""

    def __init__(self, filename: str):
        """Decode .toml configuration file."""
        self.filename = filename
        # Use default values if filename is an empty string.
        if not filename:
            config = tomllib.loads(default_config)
        else:
            path = Path(filename)
            if path.exists():
                text = path.read_text(encoding="utf-8")
                config = tomllib.loads(text)
            else:
                raise FileNotFoundError(path)

        self._my_config = config["tool"]["logview"]
        self.phrases: List[Highlighter] = []
        for text, color in self._my_config["phrases"].items():
            try:
                ansi_sequence = ColorName[color].value
            except KeyError:
                msg = "Unknown color name {} in config file [tool.logview.phrases]"
                print(msg.format(color))
                raise
            phrase = Highlighter(text=text, effect=ansi_sequence)
            self.phrases.append(phrase)

    def get(self, name: str) -> Any:
        """Get value of a key from the configuration file."""
        if name not in self._my_config:
            msg = "Error- Unknown key {} in config file [tool.logview]. Spelling?."
            print(msg.format(name))
        return self._my_config[name]


TIMETAG_SIZE = 28  # time tag at start of each line


def name_key_function(name: str) -> str:
    """Order files that start with digits in numeric order so 2 is before 11.

    Replace a run of digit characters at the start of the filename with a
    5 character string padded out with leading zeros.
    Also replace the same if immediately after a slash.
    """
    leading_digits = r"^([0-9]+)[^0-9]*"
    match1 = re.search(pattern=leading_digits, string=name)
    if match1 is not None:
        digits1 = match1.group(1)
        prefix1 = format(int(digits1), "05d")
        name = name.replace(digits1, prefix1)

    slash_leading_digits = r"/([0-9]+)[^0-9]*"
    match2 = re.search(pattern=slash_leading_digits, string=name)
    if match2 is not None:
        digits2 = match2.group(1)
        prefix2 = format(int(digits2), "05d")
        name = name.replace(digits2, prefix2)
    return name


class MemberFilter:
    """Sensible ordering, glob and fnmatch like selection of filenames from ZipFile."""

    def __init__(self, zip: ZipFile):
        """Sensibly order the archive member filenames, retrieve timestamp."""
        filenames = [f.filename for f in zip.infolist() if not f.is_dir()]
        self.ordered_filenames = sorted(filenames, key=name_key_function)
        self._parts = [Path(file).parts for file in self.ordered_filenames]
        # We assume every line in every archive member file starts with a timestamp.
        # Get from the first line of the first of the sensibly ordered members.
        text = zip.read(self.ordered_filenames[0]).decode(encoding="utf-8")
        self.timestamp = text[:TIMETAG_SIZE]

    def select(self, patterns: List[str]) -> List[str]:
        """Select from files those that match any of the patterns.

        A filename is compared to a pattern part by part as described by
        pathlib.Path().parts. The individual part is compared using
        fnmatch.fnmatch style wild cards.
        Slashes "/" are significant to separate the parts. To match
        files in directory dir use something like "dir/*".
        A pattern like "*.txt" will only match filenames that don't
        contain a "/".
        """
        matches = []
        for pattern in patterns:
            pattern_parts = Path(pattern).parts
            for filename_parts in self._parts:
                if len(filename_parts) == len(pattern_parts):
                    if all(
                        fnmatch.fnmatch(f, p) for f, p in zip(filename_parts, pattern_parts)
                    ):
                        matches.append("/".join(filename_parts))
        return matches


def show_action_log(logfile_name: Path, config: Config) -> None:
    """Display selected logs from GH Actions zip log file.  Colorize parts."""
    print(logfile_name)
    errors: List[str] = []
    with ZipFile(logfile_name) as zip:
        print()
        matcher = MemberFilter(zip)
        not_scanned = set(matcher.select(config.get("do_not_scan")))
        not_printed = set(matcher.select(config.get("do_not_show")))
        for filename1 in matcher.ordered_filenames:
            if filename1 in not_scanned:
                continue
            is_printed = filename1 not in not_printed
            if is_printed:
                print()
                print("=" * 80)
                print("name:", filename1)
                print()
            # Check all files for errors even if they are not printed.
            text = zip.read(filename1).decode(encoding="utf-8")
            e = check_one_file(config, filename1, text, is_printed=is_printed)
            errors.extend(e)

        print()
        print()
        if errors:
            print("------------------- errors -------------------")
            error_phrases = [Highlighter(s, Fore.RED) for s in config.get("errors")]
            for line in errors:
                line = colorize_line(line, error_phrases)
                print(line)
        else:
            print("No errors or warnings found.")

        # Repeat a few specific archive members at the very end.
        # Not subject to the do_not_show configuration.
        show_members_again = matcher.select(config.get("show_at_end"))
        if show_members_again:
            print()
            print()
            print("Displaying archive members selected by 'show_at_end':")
            print()
            for filename2 in matcher.select(config.get("show_at_end")):
                print("=" * 80)
                print("name:", filename2)
                text2 = zip.read(filename2).decode(encoding="utf-8")
                _ = check_one_file(config, filename2, text2, is_printed=True)
                print()

        print()
        print(logfile_name, matcher.timestamp)


def check_one_file(
    config: Config, filename: str, text: str, is_printed: bool
) -> List[str]:
    """Colorize phrases in text and check for error phrases."""
    errors = []
    lowered_errors = [
        e.lower() for e in config.get("errors")
    ]  # assure case insensitive
    lines = text.splitlines()
    for num, line in enumerate(lines, start=1):
        # Discard the line if it has any of _excludes as a substring.
        if any(True for pattern in config.get("excludes") if pattern in line):
            continue

        if not config.get("keep_timetags"):
            # Chop off the start of the line which is assumed to start
            # with a time tag like this: 2021-11-14T02:31:28.6752380Z
            line = line[TIMETAG_SIZE:]
        # Highlight and save for error summary if flagging an error.
        # Flag if line contains a string from _errors and line does not
        # contain a string from config error_exemptions.
        # config errors strings are case-insensitive.
        # config error_exemptions strings match exact case only.
        lowered_line = line.lower()
        if any(
            True
            for error in lowered_errors
            if error in lowered_line
            and not any(
                True for exempt in config.get("error_exemptions") if exempt in line
            )
        ):
            # Always print errors
            line = colorize_line(line, [Highlighter(line, Fore.MAGENTA)])
            errors.append("{: 3d} {} {}".format(num, filename, line))
            print(format(num, " 3d"), line)
        else:
            if is_printed:
                # Colorize all phrases in the line.
                line = colorize_line(line, config.phrases)
                print(format(num, " 3d"), line)
    return errors


def logfile_timestamp_keyfunc(m: MemberFilter) -> str:
    """Sort key function."""
    return m.timestamp


def locate_log_file(config) -> Optional[Path]:
    """Path to newest log archive meeting criteria."""
    files: List[Path] = []
    log_file_directory = Path(config.get("log_file_directory"))
    archive_glob = config.get("archives")
    files.extend(log_file_directory.glob(archive_glob))
    timestamps: List[Tuple[str, Path]] = []
    for file in files:
        with ZipFile(file) as zip:
            matcher = MemberFilter(zip)
            # Check for presence of members that match the pattern.
            members = matcher.select([config.get("contains_member")])
            if members:
                timestamps.append((matcher.timestamp, file))
    if timestamps:
        newest_order = sorted(timestamps, reverse=True)
        return newest_order[0][1]  # Path with newest timestamp
    else:
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--auto-locate-logfile",
        help="Locate logfile specified by criteria in the .toml file.",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "files",
        help="One or more .toml or .zip files.",
        metavar="FILE",
        type=str,
        nargs="+",
    )
    args = parser.parse_args()
    config = Config("")  # This is the default config
    if args.auto_locate_logfile:
        # Use config to locate a log file.
        if args.files:
            # The first file must be the config file, all other files are ignored.
            config = Config(args.files[0])
            print("read config from", config.filename)
        log_file = locate_log_file(config)
        log_file_directory = Path(config.get("log_file_directory"))
        if not log_file:
            print("Could not find a logfile meeting criteria:")
            print("  log file directory=", log_file_directory)
            print("  archives=", config.get("archives"))
            print("  contains_member=", config.get("contains_member"))
        else:
            print("log file directory=", log_file_directory)
            show_action_log(log_file, config=config)
    else:
        for file in args.files:
            path = Path(file)
            if not path.exists():
                raise FileNotFoundError(path)
            if file.endswith(".toml"):
                config = Config(file)
                print("read config from", file)
                continue
            print("+=" * 50)
            show_action_log(Path(file), config=config)


if __name__ == "__main__":
    main()
