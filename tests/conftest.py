import os

import pytest

ROOT = os.path.join(os.path.dirname(__file__), os.pardir)


@pytest.fixture(scope='session', autouse=True)
def testdir():
    """ Fixture to return testdir in the current ENV """
    return os.path.join(ROOT, 'test-examples')


@pytest.fixture(scope='session', autouse=True)
def command():
    """ Fixture to return srgsvalidation command path in the current ENV """
    return os.path.join(ROOT, 'bin/srgsvalidation')


@pytest.fixture(autouse=True)
def root_dir():
    """ Change dir to root (to get coverage results) """
    os.chdir(ROOT)
    yield
