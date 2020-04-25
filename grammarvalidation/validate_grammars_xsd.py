# coding: utf-8
""" Option parser and main script for SRGS validation processes """
import logging
import os
import time

from functools import partial
from multiprocessing import cpu_count
from multiprocessing.pool import ApplyResult, ThreadPool  # type: ignore
from typing import Text, Optional, Iterable, Callable, Dict, List, Any, Tuple

import click

from six import iteritems, text_type
from six.moves import filter

from .templates import error
from .validators import (
    validate_grammar,
    validate_rules,
    inspect_xml_file,
    inspect_encoding,
    StopTaskExecution
)


logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

logging.addLevelName(
    logging.ERROR,
    "\033[1;31m%s\033[1;0m" % logging.getLevelName(logging.ERROR)
)
logging.addLevelName(
    logging.INFO,
    "\033[1;36m%s\033[1;0m" % logging.getLevelName(logging.INFO)
)

VALIDATORS = Iterable[Callable[[Text], Tuple[bool, Dict[Text, Any]]]]
LINE_SPLIT = partial(
    click.secho,
    u'----------------------------------',
    bold=True,
    fg='yellow'
)


@click.command()  # type: ignore
@click.option(
    '--suppress',
    '-s',
    default=False,
    is_flag=True,
    help=(
        'Suppress logger output about ongoing processes.'
    )
)
@click.option(
    '--grammar-dir',
    '-d',
    default=os.getcwd(),
    type=click.Path(exists=True, path_type=text_type),
    help='Path to grammars directory'
)
@click.option(
    '--check-empty',
    '-ce',
    is_flag=True,
    default=False,
    help=(
        'Check if directory contains empty files. '
        'Default value is False. '
        'Note that, you will get one more line in report (flag)'
    )
)
@click.option(
    '--check-rules',
    is_flag=True,
    default=False,
    help=(
        'Validate that each of the grammars root rule contains minor rules. '
        'Minor rules are included within <ruleref uri="#rule_id" /> tag '
    )
)
@click.option(
    '--grammar-file',
    '-f',
    'file_',
    type=click.Path(exists=True, path_type=text_type),
    help=(
        'Path to grammar file. '
        'Has higher priority than -d flag. '
    )
)
def validate_srgs_xml_file(
        suppress,  # type: bool
        grammar_dir,  # type: Text
        check_empty,  # type: bool
        check_rules,  # type: bool,
        file_  # type: Optional[Text]
):
    # type: (...) -> int
    """ Validate .grxml with W3C xsd schema

    Args:
        suppress: Bool flag. Suppressing redundant output. Default = False
        grammar_dir: str directory path.
        check_empty: Bool flag. Suppressing empty files. Default = True
        check_rules: Boolean flag. Verify user intention to check rules
        file_: str single grammar path
    """
    if suppress:
        logging.disable(logging.CRITICAL)
    #
    validators = _prepare_validators(check_rules)

    def execute_single_task(path_):  # type: (Text) -> int
        result_ = validation_task(path_, validators)
        report_ = _make_report(result_, check_empty)
        return exit_(report_)

    if file_ is not None:
        return execute_single_task(file_)

    grxml_files_p = [val for val in filter(
        lambda path: os.path.getsize(path) > 0
        if not check_empty
        else lambda x: x,
        [
            os.path.join(grammar_dir, dir_file_name)
            for dir_file_name in os.listdir(grammar_dir)
            if os.path.isfile(os.path.join(grammar_dir, dir_file_name))
            if os.path.splitext(dir_file_name)[-1] == '.grxml'
        ]
    )]
    if not grxml_files_p:
        logging.error('Directory does not contain .grxml files')
        return 1
    if len(grxml_files_p) == 1:
        return execute_single_task(grxml_files_p[0])

    pool = ThreadPool(
        processes=cpu_count() * 5
    )
    base_thread_pool = []  # type: List[ApplyResult]
    with click.progressbar(
            length=len(grxml_files_p),
            show_percent=True,
            show_pos=True
    ) as progress_bar:
        for index, file_path in enumerate(grxml_files_p):
            promise = pool.apply_async(
                validation_task,
                args=(file_path, validators)
            )
            base_thread_pool.append(promise)
            progress_bar.update(index + 1)
    result = _merge_dicts(
        *[thread.get(timeout=1) for thread in base_thread_pool]
    )
    report = _make_report(result, check_empty)
    return exit_(report)


def validation_task(path, validators):
    # type: (Text, VALIDATORS) -> Dict[Text, Any]
    """ Task content (linear validation, cause validators are used in chain)

    Args:
        path: FP to the grammar
        validators: Predefined hooks for validating data

    Returns:
        Raw report for parsing

    """
    report = {}  # type: Dict[Text, Any]
    for validator in validators:
        try:
            result = validator(path)
        except StopTaskExecution:
            result = error(
                path,
                u'Unable to get file descriptor for this grammar. '
                u'Hint - chmod 777 %path%'
            )
        report = _dict_update(report, result[1])
        if result[0] is False:
            break
    return report


def _make_report(raw_report, check_empty):
    # type: (Dict[Text, Any], bool) -> Dict[Text, Any]
    """ Create printable report from raw data """
    logging.info('BUILDING REPORT FOR %s GRAMMARS', len(raw_report))
    empty = 0
    report = {
        u'Valid files': 0,
        u'Checked in total': len(raw_report),
        u'Errors': {}
    }  # type: Dict[Text, Any]
    valid_counter = len(raw_report)
    for key in raw_report:
        if isinstance(raw_report[key], list):
            success_list = []
            list_errors = []
            for item in raw_report[key]:
                if u'error' in item:
                    list_errors.append(item[u'error'])
                else:
                    sub_key, sub_value = next(iteritems(item))
                    success_list.append(
                        u"{:<25}{:^30}".format(sub_key, sub_value)
                    )
            report[key] = u'\n'.join(success_list)
            if list_errors:
                report[u'Errors'].update({
                    key: u'\n'.join(list_errors)
                })
                valid_counter += -1

        elif u'error' in raw_report[key]:
            if u'Document is empty' in raw_report[key][u'error']:
                if check_empty:
                    empty += 1
                else:
                    report[u'Errors'].update({
                        key: raw_report[key][u'error']
                    })
            else:
                report[u'Errors'].update({
                    key: raw_report[key][u'error']
                })
            valid_counter += -1
        else:
            report[key] = raw_report[key]
    report[u'Valid files'] = valid_counter
    if check_empty:
        report[u'Empty files'] = empty
    return report


def exit_(report):  # type: (Dict[Text, Any]) -> int
    """ Perform report printing and end this validation session """
    # Small hack to prevent printing BEFORE logging emission
    time.sleep(0.01)
    if report[u'Errors']:
        _print_report(report, error=True)
        return 1
    _print_report(report)
    return 0


def _dict_update(master, slave):
    # type: (Dict[Text, Any], Dict[Text, Any]) -> Dict[Text, Any]
    """ Update report parts according to merge policy """
    for key in slave:
        if key in master:
            if isinstance(master[key], list):
                master[key].append(slave[key])
            else:
                master[key] = [master[key]] + [slave[key]]
        else:
            master[key] = slave[key]
    return master


def _print_report(report, error=False):
    # type: (Dict[Text, Any], bool) -> None
    """ Print report to STDOUT (make it look fancy) """
    errors = report.pop(u'Errors')
    LINE_SPLIT()
    click.secho('REPORT', bold=True, fg='yellow')  # type: ignore
    LINE_SPLIT()

    def _split_report(dictionary, filter_):
        # type: (Dict[Text, Any], Callable) -> Dict[Text, Any]
        """ Divide parts of the dictionary according to the filter """
        return {
            key_: value_
            for key_, value_ in iteritems(dictionary)
            if filter_(key_)
        }
    grammars_report = _split_report(report, lambda x: x.endswith(u'.grxml'))
    stats_report = _split_report(report, lambda x: not x.endswith(u'grxml'))
    if not error:
        for key, value in iteritems(grammars_report):
            click.secho(  # type: ignore
                'Grammar {:<30}'.format(key), fg='green', bold=True
            )
            for line in value.split(u'\n'):
                msg = '{:>{align}}'.format(line, align=len(line) + 10)
                click.secho(msg, fg='green')  # type: ignore
            LINE_SPLIT()

    else:
        for key, value in iteritems(errors):
            click.secho(  # type: ignore
                'Grammar {:<30}'.format(key), fg='red', bold=True
            )
            for line in value.split(u'\n'):
                msg = '{:>{align}}'.format(line, align=len(line) + 10)
                click.secho(msg, fg='red')  # type: ignore
            LINE_SPLIT()

    if error:
        click.secho(
            'Whoops....... Not a perfect run :(',
            fg='red',
            underline=True,
            bold=True
        )
    else:
        click.secho(
            'Congratz on being the best out of the best!',
            fg='green',
            underline=True,
            bold=True
        )
    for key, value in iteritems(stats_report):
        click.secho(
            '{:<20}{:^40}'.format(key, value), fg='yellow'
        )
    if error:
        click.secho(
            '{:<20}{:^40}'.format(u'Errors', len(errors)), fg='red'
        )


def _merge_dicts(*dicts):
    # type: (List[Dict[Text, Any]]) -> Dict[Text, Any]
    """ Concat dicts into one """
    result = {}  # type: Dict[Text, Any]
    for dictionary in dicts:
        result.update(dictionary)  # type: ignore
    return result


def _prepare_validators(rules_included):
    # type: (bool) -> VALIDATORS
    """ Use basic validators and append

    Args:
        rules_included: Flag indicating that rules should be checked as well

    Returns:
        Array of grammar validators

    Notes:
        ToDo: Should be updated within each flag or apply pattern matching
    """
    base = [inspect_encoding, inspect_xml_file, validate_grammar]
    if rules_included:
        base.append(validate_rules)
    return base
