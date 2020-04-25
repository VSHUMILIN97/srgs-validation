""" Bunch of utilities shared between modules """
import os

from lxml.etree import XMLSyntaxError
from typing import Text, Union

from six import ensure_text


def parse_exception(exc):  # type: (Union[Exception, XMLSyntaxError]) -> Text
    """ Return first line of the exception as the appropriate message """
    return ensure_text(str(exc)).splitlines()[0]


def get_file_name(fp):
    # type: (Text) -> Text
    """ Get name for file from path """
    return os.path.basename(fp)
