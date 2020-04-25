import os
import stat

from contextlib import contextmanager
from typing import Iterator

import pytest

from grammarvalidation import (
    validate_grammar, inspect_xml_file, inspect_encoding
)
from grammarvalidation.validators import StopTaskExecution


def test_validate_positive_function(testdir):
    """ Checks: Positive result of the validation - no errors """
    assert validate_grammar(os.path.join(testdir, 'basic.grxml'))[0] is True


def test_validate_absolute_negative_function(testdir):
    """ Checks: Negative result of the validation - errors in log """
    res = inspect_xml_file(os.path.join(testdir, 'broken/droptest.grxml'))
    assert res[0] is False


def test_validate_tag_negative_function(testdir):
    """ Checks: Validation of grxml file with tag error inside """
    res = validate_grammar(os.path.join(testdir, 'broken/droptest2.grxml'))
    assert res[0] is False


def test_validate_pls_works_correctly(testdir):
    """ Checks: Validation of PLS schema is not implemented yet """
    res = validate_grammar(os.path.join(testdir, 'pls.grxml'))
    assert res[0] is True


def test_inspect_encoding_result_in_bad_encoding(testdir):
    grammar_path = os.path.join(testdir, 'broken/nonutf-8.grxml')
    res = inspect_encoding(grammar_path)
    assert res[0] is False


def test_unable_to_get_file_descriptor(testdir):
    """ Checks: Stop task with error if file descriptor is not gettable """
    locked_file = os.path.join(testdir, 'lock')
    with make_tmp_file(locked_file, stat.S_IWOTH), \
            pytest.raises(StopTaskExecution):
        inspect_xml_file(locked_file)


@contextmanager
def make_tmp_file(path, chmod):
    # type: (str, int) -> Iterator[None]
    """ Create test file in given directory """
    with open(path, 'w') as writer:
        writer.write('PEW')
    os.chmod(path, chmod)
    yield
    os.remove(path)
