# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/nedbat/coveragepy/blob/master/NOTICE.txt

"""
Pytest auto configuration.

This module is run automatically by pytest, to define and enable fixtures.
"""

import os
import sys
import warnings

import pytest

from coverage import env
from coverage.exceptions import StopEverything


# Pytest will rewrite assertions in test modules, but not elsewhere.
# This tells pytest to also rewrite assertions in coveragetest.py.
pytest.register_assert_rewrite("tests.coveragetest")
pytest.register_assert_rewrite("tests.helpers")

# Pytest can take additional options:
# $set_env.py: PYTEST_ADDOPTS - Extra arguments to pytest.

@pytest.fixture(autouse=True)
def set_warnings():
    """Configure warnings to show while running tests."""
    warnings.simplefilter("default")
    warnings.simplefilter("once", DeprecationWarning)

    # Warnings to suppress:
    # How come these warnings are successfully suppressed here, but not in setup.cfg??

    #   setuptools/py33compat.py:54: DeprecationWarning: The value of convert_charrefs will become
    #   True in 3.5. You are encouraged to set the value explicitly.
    #       unescape = getattr(html, 'unescape', html_parser.HTMLParser().unescape)
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=r"The value of convert_charrefs will become True in 3.5.",
        )

    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=r".* instead of inspect.getfullargspec",
        )

    # <frozen importlib._bootstrap>:681:
    # ImportWarning: VendorImporter.exec_module() not found; falling back to load_module()
    warnings.filterwarnings(
        "ignore",
        category=ImportWarning,
        message=r".*exec_module\(\) not found; falling back to load_module\(\)",
        )
    # <frozen importlib._bootstrap>:908:
    # ImportWarning: AssertionRewritingHook.find_spec() not found; falling back to find_module()
    # <frozen importlib._bootstrap>:908:
    # ImportWarning: _SixMetaPathImporter.find_spec() not found; falling back to find_module()
    # <frozen importlib._bootstrap>:908:
    # ImportWarning: VendorImporter.find_spec() not found; falling back to find_module()
    warnings.filterwarnings(
        "ignore",
        category=ImportWarning,
        message=r".*find_spec\(\) not found; falling back to find_module\(\)",
        )

    if env.PYPY:
        # pypy3 warns about unclosed files a lot.
        warnings.filterwarnings("ignore", r".*unclosed file", category=ResourceWarning)


@pytest.fixture(autouse=True)
def reset_sys_path():
    """Clean up sys.path changes around every test."""
    sys_path = list(sys.path)
    yield
    sys.path[:] = sys_path


@pytest.fixture(autouse=True)
def fix_xdist_sys_path():
    """Prevent xdist from polluting the Python path.

    We run tests that care a lot about the contents of sys.path.  Pytest-xdist
    changes sys.path, so running with xdist, vs without xdist, sets sys.path
    differently.  With xdist, sys.path[1] is an empty string, without xdist,
    it's the virtualenv bin directory.  We don't want the empty string, so
    clobber that entry.

    See: https://github.com/pytest-dev/pytest-xdist/issues/376

    """
    if os.environ.get('PYTEST_XDIST_WORKER', ''):       # pragma: part covered
        # We are running in an xdist worker.
        if sys.path[1] == '':
            # xdist has set sys.path[1] to ''.  Clobber it.
            del sys.path[1]
        # Also, don't let it sneak stuff in via PYTHONPATH.
        try:
            del os.environ['PYTHONPATH']
        except KeyError:
            pass


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    """Convert StopEverything into skipped tests."""
    outcome = yield
    if outcome.excinfo and issubclass(outcome.excinfo[0], StopEverything):
        pytest.skip(f"Skipping {item.nodeid} for StopEverything: {outcome.excinfo[1]}")
