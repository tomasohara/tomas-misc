#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Test(s) for ../spell.py
# ^ TODO: More?
#
# Notes:
# - For debugging the tested script, the ALLOW_SUBCOMMAND_TRACING environment
#   option shows tracing output normally suppressed by  unittest_wrapper.py.
# - This can be run as follows:
#   $ PYTHONPATH=".:$PYTHONPATH" python ./mezcla/tests/test_bing_search.py
# - Spellcheck requires nltk and hunspell for multi-language support
#   Language specific hunspell can be installed as hunspell-LANG_CODE (e.g. hunspell-ne -> Nepali)
#   $ apt-get install hunspell-ne 
#
# TODO1:
# - Rework tests following test_spell_EN
# - Carefully review tests/template.py.
# TODO3:
# - Create test helpers to cut down on all the redundant code.
#   ex: def check_spelling(self, lang, text, bad):
#       """Run spelling over TEXT in TEXT looking for BAD words""
#       output = self.run_script(env_options=f"SPELL_LANG={lang}", data_file=gh.create_temp_file(text))
#       assert(system.intersection(text.split(), bad.split()))
# TODO4:
# - Reword "This test can take some time or may have missing libraries" so that just
#   covers RUN_SLOW_TESTS; Check separately for missing libraries.
#

"""Tests for spell module"""
# Standard packages
## OLD: import re

# Installed packages
import pytest
# import unittest

# Local packages
from mezcla import debug
from mezcla import glue_helpers as gh
from mezcla import system
from mezcla.unittest_wrapper import TestWrapper
## TODO: from mezcla.unittest_wrapper import trap_exception

# Note: Two references are used for the module to be tested:
#    THE_MODULE:	    global module object
#    TestIt.script_module:              path to file
try:
    # note: requires enchant-2 library package under Ubuntu (besides pyenchant)
    import mezcla.spell as THE_MODULE
except:
    THE_MODULE = None
    system.print_exception_info("spell import")

# Since importing doesn't work properly, a temporary fix is specifying the path
# import mezcla.spell as THE_MODULE
# *** It works fine: please follow the example in test/template.py better! ***
## BAD
## PATH1 = f'$PWD/mezcla/spell.py'
## PATH2 = f'$PWD/spell.py'
## PATH3 = f'../spell.py'
## PWD_COMMAND = f'echo $PWD'
## echo_PWD = gh.run(PWD_COMMAND)
## if (echo_PWD.endswith('/mezcla/mezcla')):
##     SPELL_PATH = PATH2
## elif (echo_PWD.endswith('/mezcla')):
##     SPELL_PATH = PATH1
## else:
##     SPELL_PATH = PATH3
##
## NOTE: the following is a temporary workaround for the bad tests
## TODO1: use run_script as in the template (and in most other tests elsewhere)!
SPELL_PATH = gh.resolve_path("../spell.py")

## Environment Variables
RUN_SLOW_TESTS = system.getenv_bool(
    "RUN_SLOW_TESTS", 
    False,
    description="Run tests that can a while to run"
    )

# @pytest.mark.skipif(not THE_MODULE, reason="Problem loading spell.py: check requirements")

class SpellFiles(TestWrapper):
    """Class for testcase definition"""
    script_module = TestWrapper.get_testing_module_name(__file__, THE_MODULE)
    use_temp_base_dir = True    # treat TEMP_BASE as directory
         
    # NOTE 1: For test_phrase, song lyrics are used
    # NOTE 2: The content in test_phase error MUST be all lowercase
    # NOTE 3: Standard assertion case: assert (output in test_phrase_error and len(output) != 0)
    # TODO 1: Find a method to not create any external filess when test_spell_query_LL functions used
    # TODO 2: A function for test_run_command replacement (optional)

    # Function A: Helper Function reduces the amount of code to be written
    # @pytest.mark.skip
    def helper_spell(
        self, 
        lang_code:str="en_EN", 
        phrase:str="Hello World", 
        batch_file_path:str="-",
        ):
        """Helper function for test_spell.py"""
        debug.trace(4, f"\nhelper_spell(); self={self}")
        
        data_file = gh.create_temp_file(contents=phrase) if batch_file_path == "-" else batch_file_path
        output = self.run_script(
            env_options=f"SPELL_LANG={lang_code}",
            data_file=data_file,
        )

        debug.trace_expr(5, output, lang_code, phrase, batch_file_path)      
        return output

        ## OLD    
        # if batch_file_path == "-" and query_like == False:
        #     command = f'echo "{phrase}" | SPELL_LANG={lang_code} {SPELL_PATH} {batch_file_path}'
        # elif query_like:
        #     temp_file = gh.create_temp_file(contents=phrase) if query_like else batch_file_path
        #     command = f'SPELL_LANG={lang_code} {SPELL_PATH} {temp_file}'
        # else:
        #     command = f'SPELL_LANG={lang_code} {SPELL_PATH} {batch_file_path}'
        
        # output = gh.run(command)
    
    ## OLD: Merged to helper_spell()
    # # Function B: Helper Function for query-like tests (skipped by default)
    # # @pytest.mark.skip
    # def helper_spell_tempfile(
    #     self,
    #     lang_code:str="en_EN",
    #     phrase:str="Hello World"
    #     ):
    #     """Helper function using tempfile"""
    #     debug.trace(4, f"\nhelper_spell_tempfile(); self={self}")

    #     ## OLD: 
    #     # temp_phrase = f"{self.temp_file}.phrase"
    #     # test_run_command_1 = f'echo "{phrase}" > {temp_phrase}'
    #     # test_run_command_2 = f'SPELL_LANG={lang_code} {SPELL_PATH} {temp_phrase} > {self.temp_file}'
        
    #     # gh.issue(test_run_command_1)
    #     # output = gh.run(test_run_command_2)
    #     # output = self.run_script(self.temp_file)
        
    #     temp_file = gh.create_temp_file(contents=phrase)
    #     command = f'SPELL_LANG={lang_code} {SPELL_PATH} {temp_file}'
    #     output = gh.run(command)
    #     debug.trace_expr(5, output, lang_code, phrase)
    #     return output
    
    # @pytest.mark.skip
    @pytest.mark.xfail                   # TODO: remove xfail
    def test_spell_default(self):
        """Ensure test_spell_default [English] works as expected"""
        debug.trace(4, f"\ntest_spell_default(); self={self}")
        
        test_phrase = "One kiss is all it tajkes"
        test_phrase_error = "tajkes"
        output = self.helper_spell(phrase=test_phrase)

        debug.trace_expr(5, output, test_phrase_error)
        assert (output == test_phrase_error and len(output) != 0)

    @pytest.mark.xfail                   # TODO: remove xfail
    # @trap_exception                      # TODO: remove when debugged
    # @pytest.mark.xfail                   # TODO: remove xfail
    def test_spell_EN(self):
        """Ensure test_spell_EN [English] works as expected"""
        debug.trace(4, f"\ntest_spell_EN(); self={self}")
        
        test_lang = "en_EN"
        test_phrase = "You givc me that feeling"
        test_phrase_error = "givc"

        ## TODO: maldito vs code so awkward to use!
        output = self.helper_spell(test_lang, test_phrase)
        debug.trace_expr(5, output, test_phrase_error)
        assert (output in test_phrase_error and len(output) != 0)
        return

    @pytest.mark.skipif(not RUN_SLOW_TESTS, reason="This test can take some time or may have missing libraries")               
    @pytest.mark.xfail                   # TODO: remove xfail
    def test_spell_ES(self):
        """Ensure test_spell_ES [Spanish] works as expected"""
        debug.trace(4, f"\ntest_spell_ES(); self={self}")
        
        test_lang = "es_ES"
        test_phrase = "Yo te miro y se me corta la respiraciónqq"
        test_phrase_error = "respiraciónqq"
        output = self.helper_spell(test_lang, test_phrase)
        
        debug.trace_expr(5, output, test_phrase_error)
        assert (output in test_phrase and len(output) != 0)
        return

    @pytest.mark.skipif(not RUN_SLOW_TESTS, reason="This test can take some time or may have missing libraries")               
    @pytest.mark.xfail                   # TODO: remove xfail
    def test_spell_NE(self):
        """Ensure test_spell_NE y[Nepali] works as expected"""
        debug.trace(4, f"\ntest_spell_NE(); self={self}")
        
        test_lang = "ne_NE"
        test_phrase = "थाहा छैन तिमीर को हो मेरो"
        test_phrase_error = "तिमीर"
        output = self.helper_spell(lang_code=test_lang, phrase=test_phrase)
        
        debug.trace_expr(5, output, test_phrase_error)
        assert (output in test_phrase and len(output) != 0)
        return

    @pytest.mark.skipif(not RUN_SLOW_TESTS, reason="This test can take some time or may have missing libraries")
    @pytest.mark.xfail                   # TODO: remove xfail
    def test_spell_AR(self):
        """Ensure test_spell_AR [Arabic] works as expected"""
        debug.trace(4, f"test_spell_AR(); self={self}")

        test_lang = "ar_AR"
        test_phrase = "سعلينا الهوى وغنّا"
        output = self.helper_spell(test_lang, test_phrase)
        
        debug.trace_expr(5, output, test_phrase)
        assert (output in test_phrase and len(output)!=0)
        return
    
    @pytest.mark.skipif(not RUN_SLOW_TESTS, reason="This test can take some time or may have missing libraries")
    @pytest.mark.xfail                   # TODO: remove xfail
    def test_spell_RU(self):
        """Ensure test_spell_RU [Russian] works as expected"""
        debug.trace(4, f"test_spell_RU(); self={self}")
        
        test_lang = "ru_RU"
        test_phrase = "Поплыли туманыны над рекой"
        output = self.helper_spell(test_lang, test_phrase)
        
        debug.trace_expr(5, output, test_phrase)
        assert (output in test_phrase and len(output) != 0)
        return
    
    @pytest.mark.skipif(not RUN_SLOW_TESTS, reason="This test can take some time or may have missing libraries")
    def test_spell_query_EN(self):
        """Ensure test_spell_query_EN works as expected"""
        debug.trace(4, f"test_spell_query_EN(); self={self}")

        test_lang = "en_EN"
        test_phrase = "Because I am lostr in the way you move"
        test_phrase_error = "lostr"
        output = self.helper_spell(test_lang, test_phrase)

        debug.trace_expr(5, output, test_phrase_error)
        assert (output == test_phrase_error and len(output) != 0)
        return

    @pytest.mark.skipif(not RUN_SLOW_TESTS, reason="This test can take some time or may have missing libraries")
    def test_spell_query_ES(self):
        """Ensure test_spell_query_ES works as expected"""
        debug.trace(4, f"test_spell_query_ES(); self={self}")

        
        test_lang = "es_ES"
        test_phrase = "Me dijeron que te estás casandoi"
        test_phrase_error = "casandoi"
        output = self.helper_spell(test_lang, test_phrase)
        
        debug.trace_expr(5, output, test_phrase_error)
        assert (output == test_phrase_error and len(output) != 0)
        return

    @pytest.mark.skipif(not RUN_SLOW_TESTS, reason="This test can take some time or may have missing libraries")
    def test_spell_query_NE(self):
        """Ensure test_spell_query_NE works as expected"""
        debug.trace(4, f"test_spell_query_NE(); self={self}")

        test_lang = "ne_NE"
        test_phrase = "तिमी नै अबप मेरो झुल्केको बिहानी"
        test_phrase_error = "अबप"
        output = self.helper_spell(test_lang, test_phrase)

        debug.trace_expr(5, output, test_phrase_error)
        assert (output in test_phrase and len(output) != 0)
        return

    @pytest.mark.skipif(not RUN_SLOW_TESTS, reason="This test can take some time or may have missing libraries")
    @pytest.mark.xfail                   # TODO: remove xfail
    def test_spell_default_batch(self):
        """Ensure test_spell_default_batch [English] works as expected"""
        debug.trace(4, f"test_spell_default_branch(); self={self}")
        
        testfile_path = gh.resolve_path("./resources/spell-py-en.list")
        output = (self.helper_spell(batch_file_path=testfile_path)).split("\n")
        
        debug.trace_expr(5, output)
        assert (output != [] and len(output) > 5)
        return
    
    @pytest.mark.skipif(not RUN_SLOW_TESTS, reason="This test can take some time or may have missing libraries")
    @pytest.mark.xfail                   # TODO: remove xfail
    def test_spell_ES_batch(self):
        """Ensure test_spell_ES_batch [Spanish] works as expected"""
        debug.trace(4, f"test_spell_ES_batch(); self={self}")
        
        test_lang = "es_ES"
        testfile_path = gh.resolve_path("./resources/spell-py-es.list")
        output = (self.helper_spell(lang_code=test_lang, batch_file_path=testfile_path)).split("\n")
        
        debug.trace_expr(5, output)
        assert (output != [] and len(output) > 3)
        return
    
    @pytest.mark.skipif(not RUN_SLOW_TESTS, reason="This test can take some time or may have missing libraries")
    @pytest.mark.xfail                   # TODO: remove xfail
    def test_spell_RU_batch(self):
        """Ensure test_spell_RU_batch [Russian] works as expected"""
        debug.trace(4, f"test_spell_RU_batch(); self={self}")
        
        test_lang = "ru_RU"
        testfile_path = gh.resolve_path("./resources/spell-py-ru.list")
        output = (self.helper_spell(lang_code=test_lang, batch_file_path=testfile_path)).split("\n")
        
        debug.trace_expr(5, output)
        assert (output != [] and len(output) > 3)
        return
    
    @pytest.mark.skipif(not RUN_SLOW_TESTS, reason="This test can take some time or may have missing libraries")
    @pytest.mark.xfail                   # TODO: remove xfail
    def test_spell_AR_batch(self):
        """Ensure test_spell_AR_batch [Arabic] works as expected"""
        debug.trace(4, f"test_spell_AR_batch(); self={self}")
        
        test_lang = "ar_AR"
        testfile_path = gh.resolve_path("./resources/spell-py-ar.list")
        output = (self.helper_spell(lang_code=test_lang, batch_file_path=testfile_path)).split("\n")
        
        debug.trace_expr(5, output)
        assert (output != "" and len(output)>5)
        return

    @pytest.mark.xfail                   # TODO: remove xfail
    def test_spell_LANG_suggest(self):
        """Ensure test_spell_LANG_suggest works as expected"""
        debug.trace(4, f"test_suggest_LANG(); self={self}")
        self.do_assert(False, "TODO: code test")

if __name__ == '__main__':
    debug.trace_current_context()
    pytest.main([__file__])
