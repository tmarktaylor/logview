"""Display parts of GitHub Action log zip files.

https://github.com/tmarktaylor/logview

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


@dataclass
class Highlighter:
    """Colorizes text using terminal color code sequence."""

    text: str
    color_enum: ColorName

    def __post_init__(self) -> None:
        if self.color_enum == ColorName.NONE:
            self.highlighted = self.text
        else:
            self.highlighted = self.color_enum.value + self.text + str(Fore.RESET)


def colorize_line(line: str, phrases: List[Highlighter]) -> str:
    # Colorize all phrases in the line.
    if chr(27) + "[" not in line:  # ANSI start sequence
        for phrase in phrases:
            line = line.replace(phrase.text, phrase.highlighted)
    return line


# todo- additional summaries
# todo- prob want a toml vector? of multiple summary sections
# todo- docstring like documentation for the config file

default_config = """
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
"""


class Config:
    """Process TOML configuration file parts into object attributes."""

    def __init__(self, config_file_path: Optional[Path]):
        """Decode .toml configuration file."""
        self.config_file_path = config_file_path
        # Use default values if filename is an empty string.
        if config_file_path is None:
            text = default_config
        else:
            text = config_file_path.read_text(encoding="utf-8")
        config = tomllib.loads(text)
        self._my_config = config["tool"]["logview"]
        self.phrases: List[Highlighter] = []
        for text, color in self._my_config["phrases"].items():
            try:
                _ = ColorName[color]
            except KeyError:
                msg = "Unknown color name {} in config file [tool.logview.phrases]"
                print(msg.format(color))
                raise
            phrase = Highlighter(text=text, color_enum=ColorName[color])
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
                        fnmatch.fnmatch(f, p)
                        for f, p in zip(filename_parts, pattern_parts)
                    ):
                        matches.append("/".join(filename_parts))
        return matches


def identify_repository(matcher: MemberFilter, zip: ZipFile) -> Optional[str]:
    """Look for repository line in the top level files. Return first one.

    Assumes the action script only checked out one repository.
    """
    for member in matcher.select(["*.txt"]):
        text = zip.read(member).decode(encoding="utf-8")
        lines = text.splitlines()
        for line in lines:
            m = re.search(pattern=r"^.*  repository: (.*)$", string=line)
            if m:
                return m.group(1)
    return None


def show_action_log(logfile_path: Path, config: Config) -> None:
    """Display selected logs from GH Actions zip log file.  Colorize parts."""
    print(logfile_path)
    summary: List[str] = []
    with ZipFile(logfile_path) as zip:
        matcher = MemberFilter(zip)
        repository = identify_repository(matcher, zip)
        if repository:
            print("repository: ", repository)
        print()
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
            summary.extend(e)

        print()
        print()
        if summary:
            title = config.get("summary_title")
            color = config.get("summary_color")
            print(title.join([" ------------------- ", " ------------------- "]))
            error_phrases = [
                Highlighter(text=s, color_enum=ColorName[color])
                for s in config.get("summary_patterns")
            ]
            for line in summary:
                line = colorize_line(line=line, phrases=error_phrases)
                print(line)
        else:
            print("Nothing found for summary.")

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
        print(logfile_path, matcher.timestamp)


def check_one_file(
    config: Config, filename: str, text: str, is_printed: bool
) -> List[str]:
    """Colorize phrases in text and check for error phrases."""
    summary = []
    lowered_errors = [
        e.lower() for e in config.get("summary_patterns")
    ]  # assure case insensitive
    lines = text.splitlines()
    for num, line in enumerate(lines, start=1):
        # Discard the line if it has any from do_not_print key as a substring.
        if any(True for pattern in config.get("do_not_print") if pattern in line):
            continue

        if not config.get("keep_timetags"):
            # Chop off the start of the line which is assumed to start
            # with a time tag like this: 2021-11-14T02:31:28.6752380Z
            line = line[TIMETAG_SIZE:]
        # Highlight and save for error summary if flagging a line.
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
                True for exempt in config.get("summary_exemptions") if exempt in line
            )
        ):
            # Save to summary without colorizing.
            summary.append("{: 3d} {} {}".format(num, filename, line))
            if is_printed:
                # Print entire colorized line identified for the summary.
                color = config.get("summary_color")
                line = colorize_line(
                    line=line,
                    phrases=[Highlighter(text=line, color_enum=ColorName[color])],
                )
                print(format(num, " 3d"), line)
        else:
            if is_printed:
                # Colorize all phrases in the line.
                line = colorize_line(line=line, phrases=config.phrases)
                print(format(num, " 3d"), line)
    return summary


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
            repository = identify_repository(matcher, zip)
            if repository == config.get("repository"):
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
    config = Config(None)  # This is the default config
    if args.auto_locate_logfile:
        # Use config to locate a log file.
        if args.files:
            # The first file must be the config file, all other files are ignored.
            config = Config(Path(args.files[0]))
            print("read config from", config.config_file_path)
        log_file = locate_log_file(config)
        log_file_directory = Path(config.get("log_file_directory"))
        if not log_file:
            print("Could not find a logfile meeting criteria:")
            print("  log file directory=", log_file_directory)
            print("  archives=", config.get("archives"))
            print("  repository=", config.get("repository"))
            print("  contains_member=", config.get("contains_member"))
        else:
            print("log file directory=", log_file_directory)
            show_action_log(log_file, config=config)
    else:
        for file in args.files:
            path = Path(file)
            if path.suffix == ".toml":
                config = Config(path)
                print("read config from", file)
                continue
            print("+=" * 50)
            show_action_log(path, config=config)


if __name__ == "__main__":
    main()
