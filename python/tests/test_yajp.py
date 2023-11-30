import pytest
import os
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from yajp import parse, JSONParserError


def lmao():
    print(1)


basedir = os.path.abspath(os.path.dirname(__file__))
testdir = os.path.join(basedir, "../../JSONTestSuite/test_parsing")

test_cases = []

for test in os.listdir(testdir):
    try:
        content = open(os.path.join(testdir, test)).read()
        if test.startswith("y_"):
            test_cases.append((content, True))
        elif test.startswith("n_"):
            test_cases.append((content, False))
        else:
            continue
    except UnicodeDecodeError:
        continue


@pytest.mark.parametrize("input,expected_output", test_cases)
def test_function(input, expected_output):
    try:
        result = parse(input)
    except Exception as e:
        if expected_output:
            raise
        return
    if expected_output:
        assert result == json.loads(input)
    else:
        raise