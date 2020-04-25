""" SRGS grammar validator storage module """
import logging
import os
import re

import cchardet as chardet

from typing import Text, BinaryIO, Dict, Tuple, Any

from lxml import etree, objectify

from .templates import error, success
from .utils import parse_exception, get_file_name

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
XSD_SCHEMA = os.path.join(CUR_DIR, 'schema.xsd')


class StopTaskExecution(Exception):
    """ Specific cause to prevent abusing further script execution """


def _get_file_descriptor(fp):
    # type: (Text) -> BinaryIO
    """ Return file descriptor for file system """
    try:
        return open(fp, 'rb')
    except (OSError, IOError):
        raise StopTaskExecution()


def inspect_encoding(file_path):
    # type: (Text) -> Tuple[bool, Dict[Text, Any]]
    """ Check file on correct encoding """
    filename = get_file_name(file_path)
    logging.info(u'Checking if %s has UTF-8 encoding' % filename)
    grammar_file = _get_file_descriptor(file_path)
    text = grammar_file.read()
    result = chardet.detect(text)
    encoding = result['encoding']
    if encoding.upper() == 'UTF-8' and result['confidence'] > 0.5:
        return True, success(file_path, "File is UTF-8 encoded")
    return False, error(file_path, 'Current file encoding is %s' % encoding)


def inspect_xml_file(file_path):
    # type: (Text) -> Tuple[bool, Dict[Text, Any]]
    """ Check file on xml errors """
    # MyPy magic below (python2 typeshed btw)
    filename = get_file_name(file_path)
    logging.info(u'Check if %s is valid XML file' % filename)
    xml_file = _get_file_descriptor(file_path)
    try:
        etree.parse(xml_file)
    except etree.XMLSyntaxError as ioerr:
        exception = parse_exception(ioerr)
        msg = u'XML "{}" is not well-formed: {}'.format(
            filename,
            exception
        )
        logging.error(msg)
        return False, error(file_path, msg)
    except IOError as file_err:
        msg = (
            u'Cannot open [%s]. System error [%s]'
            % (file_path, parse_exception(file_err))
        )
        logging.error(msg)
        return False, error(file_path, msg)
    return True, success(file_path, u'XML format inspection')


def validate_grammar(file_path):
    # type: (Text) -> Tuple[bool, Dict[Text, Any]]
    """ Validate a single SRGS file with XSD SCHEMA

    Args:
        file_path: path to .grxml (SRGS valid) grammar

    Returns:
        True if any errors.
        False if no errors.

    Notes:
        A little bit clumsy and shadowed with True/False on the output,
        but it works well with if statements (err = validate_grammar())
    """
    logging.info(
        'Execute W3C SRGS validation for %s', get_file_name(file_path)
    )
    srgs_file = _get_file_descriptor(file_path)
    doc = etree.parse(srgs_file)
    xml_schema_io = etree.parse(open(u'%s' % XSD_SCHEMA))
    schema = etree.XMLSchema(xml_schema_io)
    try:
        schema.assert_(doc)
    except AssertionError:
        errors = schema.error_log.copy()
        errors_msg = []
        for exception in errors:
            if re.search(
                    r'({(http|ftp|https)://([\w_-]+(?:(?:\.[\w_-]+)+))'
                    r'([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?}lexicon)',
                    str(exception)
            ):
                logging.info('\n%s', exception)
            else:
                errors_msg.append(
                    u'Line number {}: {:^100}'.format(
                        exception.line,
                        exception.message
                    )
                )
                logging.error('\n%s', exception)
        if errors_msg:
            return False, error(file_path, u'\n'.join(errors_msg))
    #
    return True, success(file_path, u'W3C SRGS grammar validator')


def validate_rules(file_path):  # type: (Text) -> Tuple[bool, Dict[Text, Any]]
    """ Validate that all stated rules are included in grammar root rule """
    logging.info(
        'Assure all rules are included into root rule for %s',
        get_file_name(file_path)
    )
    srgs_file_content = _get_file_descriptor(file_path).read()
    root = objectify.fromstring(srgs_file_content)
    core_rule = root.attrib['root']
    rule_array = [tag.attrib['id'] for tag in root.rule]
    if len(rule_array) == 1:
        logging.info(
            u'SRGS grammar contain only root rule. Nothing to inspect'
        )
        return True, success(file_path, u'Root Rule validator')

    if core_rule not in rule_array:
        msg = u'Core rule %s was not included in SRGS file!' % core_rule
        logging.error(msg)
        return False, error(file_path, msg)

    core_rule_object = [
        rule for rule in root.rule if rule.attrib['id'] == core_rule
    ][0]
    allowed_rules = set([
        item.ruleref.attrib['uri'][1:]
        for one_of in core_rule_object.iterchildren(
            tag='{http://www.w3.org/2001/06/grammar}one-of'
        )
        for item in one_of.item
    ])
    if not allowed_rules:
        allowed_rules = {core_rule_object.item.ruleref.attrib['uri'][1:]}
        if not allowed_rules:
            msg = u'No rulerefs provided in [%s] root rule' % core_rule
            logging.error(msg)
            return False, error(file_path, msg)

    rule_array.remove(core_rule)
    if not allowed_rules.issuperset(rule_array):
        missing_rules = [
            rule for rule in rule_array if rule not in allowed_rules
        ]
        msg = (
            u'Several rules [%s] were not included in %s tag'
            % (u' '.join(missing_rules).rstrip(), core_rule)
        )
        logging.error(msg)
        return False, error(file_path, msg)
    return True, success(file_path, u'Root rule validator')
