"""pytest test cases for examples in fenced code blocks in README.md."""

import difflib
from itertools import zip_longest
import re
from pathlib import Path

import phmdoctest.tool
import pytest

import logview


@pytest.fixture()
def checker():
    """Return Callable(str, str) that runs difflib.ndiff. Multi-line str's ok."""

    def a_and_b_are_the_same(a, b):
        """Compare function with assert and line by line ndiff stdout."""
        a_lines = a.splitlines()
        b_lines = b.splitlines()
        for a_line, b_line in zip_longest(a_lines, b_lines):
            if a_line != b_line:
                diffs = difflib.ndiff(a_lines, b_lines)
                print()  # needed for IDE output window
                for line in diffs:
                    print(line)
                assert False

    return a_and_b_are_the_same


# Fenced code blocks that have the phmdoctest-label directive.
labeled = phmdoctest.tool.FCBChooser("README.md")


def test_usage(checker):
    """README default configuration is the same as code's default value."""
    want = labeled.contents(label="usage").rstrip()
    # Remove sections of the help text that vary between Python version/OS.
    want1 = re.sub(r"option.*:", "", string=want)
    want2 = re.sub(r"optional_arguments.*:", "", string=want1)
    got = Path("help.txt").read_text(encoding="utf-8").rstrip()
    got1 = re.sub(r"option.*:", "", string=got)
    got2 = re.sub(r"optional_arguments.*:", "", string=got1)
    checker(want2, got2)


def test_default_configuration(checker):
    """README default configuration is the same as code's default value."""
    want = labeled.contents(label="default-configuration").rstrip()
    got = logview.default_config
    checker(want, got)
