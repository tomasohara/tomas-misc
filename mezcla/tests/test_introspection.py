#! /usr/bin/env python
#
# Test(s) for ../<module>.py
#
# Notes:
# - This can be run as follows (e.g., from root of repo):
#   $ pytest ./mezcla/tests/test_<module>.py
#

"""Tests for introspection module"""

# Standard modules
## TODO: from collections import defaultdict

# Installed modules
import pytest

# Local modules
from mezcla.unittest_wrapper import TestWrapper, invoke_tests
from mezcla import debug
from mezcla.my_regex import my_re
from mezcla import system

# Note: Two references are used for the module to be tested:
#    THE_MODULE:                        global module object
#    TestIt.script_module:              path to file
THE_MODULE = None
try:
    import mezcla.introspection as THE_MODULE
except:
    system.print_exception_info("introspection import") 
## 
## TODO: make sure import above syntactically valid
#
# Note: sanity test for customization (TODO: remove if desired)
if not my_re.search(__file__, r"\btemplate.py$"):
    debug.assertion("mezcla.template" not in str(THE_MODULE))

#------------------------------------------------------------------------

class TestIt(TestWrapper):
    """Class for command-line based testcase definition"""
    # note: script_module used in argument parsing sanity check (e.g., --help)
    script_module = TestWrapper.get_testing_module_name(__file__, THE_MODULE)

    @pytest.mark.xfail                   # TODO: remove xfail
    def test_01_simple_introspection(self):
        """Test for simple introspection"""
        debug.trace(4, f"TestIt.test_01_simple_introspection(); self={self}")
        fubar = 123.321
        fubar_expr = THE_MODULE.intro.format(fubar)
        self.do_assert(my_re.search("fubar.*123.321", fubar_expr))
        return

    @pytest.mark.xfail                   # TODO: remove xfail
    def test_02_multiline_introspection(self):
        """Test for multi-line introspection"""
        debug.trace(4, f"TestIt.test_02_multiline_introspection(); self={self}")
        multiline_value_expr = THE_MODULE.intro.format(
            2
            +
            2
            ==
            5)
        self.do_assert(my_re.search(r"2.*\+.*2.*==.*5", multiline_value_expr))
        return

#------------------------------------------------------------------------

if __name__ == '__main__':
    debug.trace_current_context()
    invoke_tests(__file__)
