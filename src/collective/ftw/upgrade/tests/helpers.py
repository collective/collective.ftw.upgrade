from contextlib import contextmanager

import logging
import os
import sys


@contextmanager
def capture_streams(stdout=None, stderr=None):
    ori_stdout = sys.stdout
    ori_stderr = sys.stderr

    if stdout is not None:
        sys.stdout = stdout
    if stderr is not None:
        sys.stderr = stderr

    try:
        yield
    finally:
        if stdout is not None:
            sys.stdout = ori_stdout
        if stderr is not None:
            sys.stderr = ori_stderr


@contextmanager
def chdir(path):
    before = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(before)


@contextmanager
def no_logging_threads():
    """In testing, when a request is executed (e.g. from requests) to the ZSERVER
    layer and errors are logged, the logging module might write to the logging
    handler in a thread after the request is finished.
    Since the testrunner tracks left over threads the logging thread is detected
    as leftover thread. Since this thread is a dummy thread it cannot be joined,
    which results in a error in the threading module (python 2.7 bug).
    The result is that from this test on the test log is spammed with threading
    errors for each following test.
    In order to mitigate this issue this context manager temporarily disables
    threading of logging in general so that logs are processed synchronously and
    no left over threads are created.
    """
    original_log_threads = logging.logThreads
    logging.logThreads = 0
    try:
        yield
    finally:
        logging.logThreads = original_log_threads


def truncate_value(message, lines):
    truncated = []
    for line in lines:
        if message in line:
            line = f"{line[: line.index(message) + len(message)]} XXX"
        truncated.append(line)
    return truncated


def truncate_duration(lines):
    return truncate_value("Upgrade step duration:", lines)


def truncate_memory(lines):
    return truncate_value("Current memory usage in MB (RSS):", lines)


def truncate_memory_and_duration(lines):
    return truncate_duration(truncate_memory(lines))
