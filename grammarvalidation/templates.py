""" Formatting render shortcuts and utils """
from typing import Dict, Any, Text

from .utils import get_file_name


def error(file_path, message):  # type: (Text, Text) -> Dict[Text, Any]
    """ Shortcut for error report """
    return {
        get_file_name(file_path): {
            u'error': message
        }
    }


def success(file_path, hook_name):  # type: (Text, Text) -> Dict[Text, Any]
    """ Shortcut for success report """
    return {
        get_file_name(file_path): {
            hook_name: u'Successfully passed'
        }
    }
