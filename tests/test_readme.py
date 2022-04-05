"""pytest test cases for examples in fenced code blocks in README.md."""

import difflib
from itertools import zip_longest
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
    got = Path("help.txt").read_text(encoding="utf-8").rstrip()
    checker(want, got)


def test_default_configuration(checker):
    """README default configuration is the same as code's default value."""
    want = labeled.contents(label="default-configuration").rstrip()
    got = logview.default_config
    checker(want, got)


def test_coverage_report(checker):
    """README coverage report is the same as the file written by CI action."""
    want = labeled.contents(label="coverage-report").rstrip()
    got = Path("coverage_report.txt").read_text(encoding="utf-8").rstrip()
    checker(want, got)
