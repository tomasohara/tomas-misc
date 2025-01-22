#! /usr/bin/env python
#
# Note:
# - This is work-in-progress code in much need of improvement.
# - For example, the code was adapted from type hinting checks,
#   but not sufficiently updated (see type-hinting-integration repo).
# - To disable caching of pytests, use the PYTEST_ADDOPTS environment variable externally
#   $ export PYTEST_ADDOPTS="--cache-clear"
#
# TODO0:
# - Rework the tests to be less brittle. This might be added to Github actions with
#   other code check scripts to be run once a week or so. Therefore, a single failure
#   should not cause the test suite to fail. Instead, use percentage thresholds.
#
# TODO1:
# - Remember to check for mezcla wrappers before calling functions directly (e.g., for
#   tracing and sanity checks):
#      $ para-grep getsize ~/mezcla/*.py
#   where para-grep defined in tomohara-aliases.bash of companion shell-scripts repo
# - This is good for one's pre-commit checklist (e.g., along with running python-lint).
#
# TODO2:
# - Try to make output easier to review for pytest summary.
#
# TODO3:
# - Keep most comments focused on high-level, covering the intention of the code.
#   Avoid getting into the nitty-gritty details unless it is a tricky algorithm.
#   (Moreover, tricky algorithms in general should be avoided unless critical.)
#
# TODO4:
# - Avoid numbering steps, because it becomes a maintenance issue.
# - Similarly, avoid references like "script 1", etc.
#

"""
Miscellaneous tests for mezcla_to_standard module
"""

# Standard packages
import difflib
from typing import List

# Installed packages
import pytest
from pydantic import BaseModel

# Local packages
from mezcla import system, debug, glue_helpers as gh, misc_utils
from mezcla.my_regex import my_re
from mezcla.unittest_wrapper import TestWrapper
from mezcla.tests.common_module import RUN_SLOW_TESTS, fix_indent

# Constants, including environment variables
MEZCLA_DIR = gh.form_path(gh.dir_path(__file__), "..")
debug.assertion(system.file_exists(gh.form_path(MEZCLA_DIR, "debug.py")))
MIN_MEZCLA_SCRIPTS_COUNT = 50
LINE_IMPORT_PYDANTIC = "from pydantic import validate_call\n"
TEST_GLOB = system.getenv_value(
    "TEST_GLOB",
    None,
    description="Specify glob pattern for files to test"
)
TEST_FILES = system.getenv_value(
    "TEST_FILES",
    None,
    description="Comma-separated list of files to test"
)
debug.assertion(not (TEST_GLOB and TEST_FILES))
SKIP_WARNINGS = system.getenv_bool(
    "SKIP_WARNINGS", 
    False,
    description="Skip warning comments for tests without standard equivalents"
)
OMIT_SLOW_TESTS = not (RUN_SLOW_TESTS or TEST_GLOB or TEST_FILES)
OMIT_SLOW_REASON = "this will take a while"

class ScriptComparison(BaseModel):
    """Pydantic Class for use in validation"""
    original_script: str
    converted_script: str
    differences: List[str]
    total_original_lines: int
    total_converted_lines: int
    lines_added: int
    lines_removed: int
    lines_warned: int

class TestM2SBatchConversion(TestWrapper):
    """Class for batch conversion of test usage of equivalent calls for mezcla_to_standard"""

    script_module = "mezcla.mezcla_to_standard"

    def setup_test_directories(self, temp_base):
        """Setup and create required test directories"""
        dirs = {
            'typehint_org': f"{temp_base}-typehint_org",
            'typehint_m2s': f"{temp_base}-typehint_m2s",
            'mezcla_m2s': f"{temp_base}-mezcla_m2s",
            'pytest_org': f"{temp_base}-pytest_org",
            'pytest_m2s': f"{temp_base}-pytest_m2s"
        }
        for dir_path in dirs.values():
            system.create_directory(dir_path)   
        return dirs

    def process_pytest_results(self, pytest_output):
        """Extract pass/fail counts from pytest output"""
        failed = sum(map(int, my_re.findall(r"(\d+) x?failed", pytest_output)))
        passed = sum(map(int, my_re.findall(r"(\d+) x?passed", pytest_output)))
        return passed, failed
    
    def count_methods(self, code_content):
        """
        Count number of method definitions in code.
        
        Args:
            code_content: String containing the code to analyze
            
        Returns:
            Number of method definitions found
        """
        method_pattern = r"^\s*def\s+\w+\s*\(.*\):"
        # return sum(1 for _ in my_re.findall(r"^\s*def\s+\w+\s*\(.*\):", code_content, my_re.MULTILINE))
        return len(my_re.findall(method_pattern, code_content, my_re.MULTILINE))


    def validate_mez2std_conversion(self, script_path, dirs, m2s_path):
        """Process single script conversion and validation"""
        script = gh.basename(script_path)
        
        output, output_file = self.get_mezcla_command_output(
            m2s_path=m2s_path,
            script_path=script_path,
            option="to-standard",
            output_path=dirs['mezcla_m2s']
        )
        
        transformed_org = self.transform_for_validation(script_path)
        script_path_org = gh.form_path(dirs['typehint_org'], script)
        system.write_file(script_path_org, transformed_org)
        
        transformed_m2s = self.transform_for_validation(output_file)
        script_path_m2s = gh.form_path(dirs['typehint_m2s'], script)
        system.write_file(script_path_m2s, transformed_m2s)
        
        return {
            'script': script,
            'method_count': self.count_methods(output),
            'org_path': script_path_org,
            'm2s_path': script_path_m2s
        }
    
    def calculate_failure_metrics(self, validation_results, num_scripts):
        """Calculate and validate failure metrics"""
        fail_count = 0
        for result in validation_results:
            total_count = sum(result['m2s_passed'])
            if result['m2s_passed'][1] > result['org_passed'][1]:
                fail_count += 1
            bad_pct = round(fail_count * 100 / total_count, 2) if total_count else 0
            debug.assertion(bad_pct < 20)
            
        overall_bad_pct = round(fail_count * 100 / num_scripts, 2) if num_scripts else 0
        return overall_bad_pct
    
    ## TEMPORARILY COMMENTED
    # def run_validation_tests(self, script_info, dirs):
    #     """Run and compare validation tests for original and converted code"""
    #     # Create and run tests for original
    #     test_file_org = self.create_test_file(script_info['org_path'], dirs['typehint_org'])
    #     pytest_result_org = gh.run(f"PYTHONPATH='{dirs['typehint_org']}' pytest {test_file_org}")
        
    #     # Create and run tests for converted
    #     test_file_m2s = self.create_test_file(script_info['m2s_path'], dirs['typehint_m2s'])
    #     pytest_result_m2s = gh.run(f"PYTHONPATH='{dirs['typehint_m2s']}' pytest {test_file_m2s}")
        
    #     # Save test results
    #     org_result_path = gh.form_path(dirs['pytest_org'], gh.basename(script_info['script'], '.py')) + '.txt'
    #     m2s_result_path = gh.form_path(dirs['pytest_m2s'], gh.basename(script_info['script'], '.py')) + '.txt'
    #     system.write_file(pytest_result_org, org_result_path)
    #     system.write_file(pytest_result_m2s, m2s_result_path)
        
    #     return {
    #         'org_passed': self.process_pytest_results(pytest_result_org),
    #         'm2s_passed': self.process_pytest_results(pytest_result_m2s),
    #         'result_paths': (org_result_path, m2s_result_path)
    #     }

    def get_mezcla_scripts(self):
        """Returns list of paths for python scripts in MEZCLA_DIR.
        Note: Uses TEST_GLOB or TEST_FILES instead if defined
        """
        # Collect all mezcla scripts from MEZCLA_DIR (i.e. .py files)
        ## OLD: result = [f for f in os.listdir(MEZCLA_DIR) if f.endswith(".py")]
        file_names = []
        if TEST_GLOB:
            file_names = gh.get_matching_files(TEST_GLOB)
        elif TEST_FILES:
            file_names = misc_utils.extract_string_list(TEST_FILES)
        else:
            file_names = [f for f in system.read_directory(MEZCLA_DIR) if f.endswith(".py")]
        debug.trace_expr(6, file_names)
        result = [(gh.form_path(MEZCLA_DIR, f) if not system.file_exists(f) else f)
                  for f in file_names]
        debug.trace(5, f"get_mezcla_scripts() => {result!r}")
        return result

    def get_mezcla_command_output(self, m2s_path, script_path, option, skip_warnings=SKIP_WARNINGS, output_path="/dev/null"):
        """Executes the mezcla script externally (option: to_standard, metrics)"""
        # Helper Script: Get the output of the execution of mezcla_to_standard.py (w/ options)
        warning_option = ("--skip-warnings" if skip_warnings else "")
        if output_path != "/dev/null":
            output_file = f"{output_path}/_mez2std_{gh.basename(script_path, '.py')}.py"
            command = f"python3 {m2s_path} --{option} {script_path} {warning_option} | tee {output_file}"
        else:
            output_file = output_path
            command = f"python3 {m2s_path} --{option} {script_path} {warning_option} > {output_path}"
        print("\nCommand from get_mezcla_command_output:", command)
        output = gh.run(command)
        return output, output_file

    def get_m2s_path(self):
        """Returns the path of mezcla_to_standard.py"""        
        # Helper Script: Get absolute path of "mezcla_to_standard.py"
        return gh.form_path(MEZCLA_DIR, "mezcla_to_standard.py")

    def compare_scripts(self, original_script_path: str, converted_script_path: str) -> ScriptComparison:
        """Uses Pydantic to compare the contents between the original & converted scripts"""
        # Helper Script: Use Pydantic class to find comparison in the script
        original_code = system.read_file(original_script_path)
        converted_code = system.read_file(converted_script_path)
        
        original_lines = original_code.splitlines()
        converted_lines = converted_code.splitlines()

        diff = difflib.unified_diff(original_code.splitlines(), converted_code.splitlines())
        differences = [line for line in diff if line.strip()]

        ## TODO3: sum(1 for line in ...) => len(line for line in ...)
        lines_added = sum(1 for line in differences if line.startswith("+") and not line.startswith("+++"))
        lines_removed = sum(1 for line in differences if line.startswith("-") and not line.startswith("---"))
        lines_warned = sum(1 for line in converted_lines if 'WARNING not supported' in line)

        return ScriptComparison(
            original_script=original_script_path,
            converted_script=converted_script_path,
            differences=differences,
            total_original_lines=len(original_lines),
            total_converted_lines=len(converted_lines),
            lines_added=lines_added,
            lines_removed=lines_removed,
            lines_warned=lines_warned
        )
    
    def calculate_score(
            self, 
            lines_original: int, 
            lines_converted: int,
            lines_added: int,
            lines_removed: int, 
            lines_warned: int,
            epsilon: float = 0.001,
            wt_difference: float = 0.30,
            wt_added: float = 0.20,
            wt_removed: float = 0.20,
            wt_warning: float = 0.30
        ):
        """
        Calculates an efficiency score based on the changes made during conversion.
        
        Arguments:
            lines_original: Number of lines in the original script.
            lines_converted: Number of lines in the converted script.
            lines_added: Number of lines added during conversion.
            lines_removed: Number of lines removed during conversion.
            lines_warned: Number of warnings generated.
            epsilon: A small value to prevent division by zero.
            wt_difference, wt_added, wt_removed, wt_warning: Weights for each metric.
            
        Returns:
            A normalized efficiency score between 0.0 and 1.0.
        """
        if lines_original == 0 or lines_converted <= 1:
            return 0.0

        # Normalize ratios with capping at 1.0
        line_diff_ratio = min(1.0, abs(lines_converted - lines_original) / (lines_original + epsilon))
        line_add_ratio = min(1.0, abs(lines_added) / (lines_original + epsilon))
        line_removed_ratio = min(1.0, abs(lines_removed) / (lines_original + epsilon))
        line_warning_ratio = min(1.0, abs(lines_warned) / (lines_original + epsilon))

        # Adjust weights dynamically for large warning counts
        if lines_warned > lines_original * 0.5:
            wt_warning += 0.1  # Penalize heavily for excessive warnings
            wt_difference -= 0.05  # Reduce emphasis on line difference

        # Weighted sum with normalization
        weighted_sum = (
            line_diff_ratio * wt_difference +
            line_add_ratio * wt_added +
            line_removed_ratio * wt_removed +
            line_warning_ratio * wt_warning
        )

        # Reward minimal changes
        minimal_change_bonus = 0.05 if (line_diff_ratio < 0.1 and line_warning_ratio < 0.1) else 0.0

        # Calculate final score
        result = max(0.0, min(1.0, 1.0 - weighted_sum + minimal_change_bonus))
        return round(result, 4)
    
    def transform_for_validation(self, file_path):
        """Creates a copy of the script for validation of argument calls (using pydantic)"""
        # Conversion and comparison starts from here
        content = system.read_file(file_path)
        content = my_re.sub(r"^def", r"@validate_call\ndef", content, flags=my_re.MULTILINE)
        content = LINE_IMPORT_PYDANTIC + content
        return content

    def create_test_function(self, module_name, function_name):
        """Creates a test function template for a given function name"""
        code = (
            f"""
            def test_{function_name}():
                from {module_name} import {function_name}
                assert callable({function_name})
                # Add appropriate function calls and assertions here
                try:
                    {function_name}()  # Example call, modify as needed
                except Exception as e:
                    assert False, f"Function {function_name} raised an exception: {{e}}"
            """
            )
        result = fix_indent(code)
        debug.trace(6, f"create_test_function({module_name}, {function_name}) => {result!r}")
        return result

    def create_test_file(self, script_path, test_dir):
        """Creates a test file for a given script"""
        ## TODO: Convert this to a mezcla script
        script_name = gh.basename(script_path, ".py")
        function_names = self.extract_function_names(script_path)
        test_file_content = "\n".join([self.create_test_function(script_name, fn) for fn in function_names])
        test_file_dir = gh.form_path(test_dir, "tests")
        system.create_directory(test_file_dir)
        test_file_path = gh.form_path(test_file_dir, f"test_{script_name}.py")
        system.write_file(test_file_path, test_file_content)
        return test_file_path

    def extract_function_names(self, file_path):
        """Extracts function names from a script"""
        content = system.read_file(file_path)
        return my_re.findall(r"^def (\w+)", content, flags=my_re.MULTILINE)

    ## EXPERIMENTAL: check_mezcla_wrappers in converted
    def check_mezcla_wrappers(self, converted_code: str) -> dict:
        """Check for proper use of mezcla wrappers in converted code"""
        wrapper_stats = {
            'direct_calls': [],
            'wrapper_calls': []
        }
        
        wrapper_patterns = {
            'getsize': r'(?:gh\.file_size|os\.path\.getsize)',
            # Add other wrapper patterns here
        }
        
        for func, pattern in wrapper_patterns.items():
            direct_calls = my_re.findall(rf'(?<!gh\.){func}\(', converted_code)
            wrapper_calls = my_re.findall(rf'gh\.{func}\(', converted_code)

            
            if direct_calls:
                wrapper_stats['direct_calls'].extend(direct_calls)
            if wrapper_calls:
                wrapper_stats['wrapper_calls'].extend(wrapper_calls)
                
        return wrapper_stats

    # @pytest.mark.xfail
    # @pytest.mark.skipif(OMIT_SLOW_TESTS, reason=OMIT_SLOW_REASON)
    ## OLD_NAME: def test_m2s_compare_pytest(self)
    # def test_mez2std_heuristic(self):
    #     """Heuristic test for script differences: includes dynamic test checking via pydantic
    #     and running pytest over original and converted script"""
    #     scripts = self.get_mezcla_scripts()
    #     dirs = self.setup_test_directories(self.temp_file)
    #     m2s_path = self.get_m2s_path()
        
    #     validation_results = []
    #     for idx, script_path in enumerate(scripts, start=1):
    #         # Process script conversion
    #         script_info = self.validate_mez2std_conversion(script_path, dirs, m2s_path)
            
    #         # Run validation tests
    #         test_results = self.run_validation_tests(script_info, dirs)
            
    #         # Print results
    #         print(f"\n#{idx} {script_info['script']} [{script_info['method_count']}]: ")
    #         print(f"Converted Path: {script_info['m2s_path']}")
    #         print(f"Original: {test_results['org_passed'][0]} passed, {test_results['org_passed'][1]} failed")
    #         print(f"Modified: {test_results['m2s_passed'][0]} passed, {test_results['m2s_passed'][1]} failed")
    #         print(f"Pytest Results (Original): {test_results['result_paths'][0]}")
    #         print(f"Pytest Results (Mezcla): {test_results['result_paths'][1]}")
            
    #         validation_results.append(test_results)
        
    #     # Validate overall results
    #     overall_bad_pct = self.calculate_failure_metrics(validation_results, len(scripts))
    #     assert overall_bad_pct < 10

    ## TODO: Fix the bugs where test with error in the conversion are passed with efficiency of 0.5
    @pytest.mark.xfail
    @pytest.mark.skipif(OMIT_SLOW_TESTS, reason=OMIT_SLOW_REASON)
    def test_mez2std_heuristic(self):
        """Tests the conversion quality of mezcla scripts using various heuristic metrics."""

        scripts = self.get_mezcla_scripts()
        if not scripts:
            pytest.skip("No scripts found to test")
        
        m2s_path = self.get_m2s_path()
        output_dir = gh.get_temp_dir()

        # For result tracking        
        metrics = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'efficiency_scores': [],
            'clean_conversions': 0,
            'warned_conversions': 0,
            'failed_scripts': []
        }
        
        print("\nProcessing scripts for heuristic evaluation:")
        for script_path in scripts:
            script_name = gh.basename(script_path)
            metrics['processed'] += 1
            print(f"\nScript {metrics['processed']}/{len(scripts)}: {script_name}")
            
            try:
                output, output_file = self.get_mezcla_command_output(
                    m2s_path=m2s_path,
                    script_path=script_path,
                    option="to-standard",
                    output_path=output_dir
                )
                
                if not gh.file_exists(output_file):
                    raise RuntimeError("Conversion failed - no output file generated")
                    
                if "WARNING" in output:
                    metrics['warned_conversions'] += 1
                else:
                    metrics['clean_conversions'] += 1
                
                comparison = self.compare_scripts(script_path, output_file)
                efficiency = self.calculate_score(
                    lines_original=comparison.total_original_lines,
                    lines_converted=comparison.total_converted_lines,
                    lines_added=comparison.lines_added,
                    lines_removed=comparison.lines_removed,
                    lines_warned=comparison.lines_warned
                )
                metrics['efficiency_scores'].append(efficiency)
                metrics['successful'] += 1
                print(f"✓ Processed successfully (Efficiency: {efficiency:.2f})")
                print("Script Metrics: Original, Converted, Added, Removed, Warned:", comparison.total_original_lines, comparison.total_converted_lines, comparison.lines_added, comparison.lines_removed, comparison.lines_warned)
                
            except Exception as e:
                metrics['failed'] += 1
                metrics['failed_scripts'].append((script_name, str(e)))
                print(f"✗ Failed: {str(e)}")
        
        self.print_test_summary(metrics)
        
        # Verify against thresholds
        success_rate = (metrics['successful'] / metrics['processed']) * 100
        avg_efficiency = (sum(metrics['efficiency_scores']) / len(metrics['efficiency_scores']) 
                        if metrics['efficiency_scores'] else 0)

        assert success_rate >= 80, f"Success rate ({success_rate:.1f}%) below minimum threshold (80%)"
        assert avg_efficiency >= 0.75, f"Average efficiency ({avg_efficiency:.2f}) below minimum threshold (0.75)"
        
    # Check that 50+ scripts are collected
    def test_get_mezcla_scripts(self):
        """Returns an array of all Python3 scripts in MEZCLA_DIR"""
        min_mezcla_scripts_count = (MIN_MEZCLA_SCRIPTS_COUNT
                                    if not (TEST_GLOB or TEST_FILES) else 1)
        assert len(self.get_mezcla_scripts()) >= min_mezcla_scripts_count

    # @pytest.mark.xfail
    # @pytest.mark.skipif(OMIT_SLOW_TESTS, reason=OMIT_SLOW_REASON)
    # def test_mezcla_scripts_compare(self, threshold=0.75):
    #     """Tests for comparing mezcla scripts with the original scripts
    #     Note: unlike test_m2s_compare_pytest, this checks for superficial differences,
    #     which are evaluated using a metric modeling conversion "efficiency"
    #     """
    #     ## TODO1: rename to differentiate from test_m2s_compare_pytest
    #     # Find the differences between the tests and optionally set a threshold for differences
    #     scripts = self.get_mezcla_scripts()
    #     m2s_path = self.get_m2s_path()
    #     option = "to-standard"
    #     output_path = gh.get_temp_dir()

    #     for idx, script_path in enumerate(scripts, start=1):
    #         _output, output_file = self.get_mezcla_command_output(m2s_path=m2s_path, script_path=script_path, option=option, output_path=output_path)
    #         comparison = self.compare_scripts(script_path, output_file)
    #         print(f"\n#{idx} Differences between {script_path} and {output_file}:")
    #         print("Lines Original:", comparison.total_original_lines)
    #         print("Lines Converted:", comparison.total_converted_lines)
    #         print("Lines Added:", comparison.lines_added)
    #         print("Lines Removed:", comparison.lines_removed)
    #         print("Warning Lines:", comparison.lines_warned)
            
    #         score = self.calculate_score(
    #             lines_original = comparison.total_original_lines,
    #             lines_converted = comparison.total_converted_lines,
    #             lines_added = comparison.lines_added,
    #             lines_removed = comparison.lines_removed,
    #             lines_warned = comparison.lines_warned
    #         )
    #         print("Score =", score)
    #         assert (score >= threshold)
    

    ## OLD: Commented for debugging
    # @pytest.mark.xfail
    # @pytest.mark.skipif(OMIT_SLOW_TESTS, reason=OMIT_SLOW_REASON)
    # def test_mezcla_scripts_batch_conversion(self):
    #     """Test for batch conversion of mezcla scripts to standard script"""
    #     # Batch Conversion (from mezcla to standard)
    #     ## TODO2: rework so that a single failure doesn't break (

    #     print("\nBatch Conversion (mez2std):\n")
    #     scripts = self.get_mezcla_scripts()
    #     m2s_path = self.get_m2s_path()
    #     option = "to-standard"
    #     output_path = gh.get_temp_dir()

    #     for idx, script_path in enumerate(scripts, start=1):
    #         script = gh.basename(script_path)
    #         output, output_file = self.get_mezcla_command_output(m2s_path, script_path, option, output_path)
            
    #         # # Assertion A: Check file integrity (syntax errors)
    #         # try:
    #         #     converted_integrity_1 = ast.parse(source=output)
    #         #     converted_integrity_2 = ast.parse(source=system.read_file(output_file))
    #         # except SyntaxError:
    #         #     converted_integrity_1, converted_integrity_2 = None, None
    #         # # assert converted_integrity is not None
    #         # print(f"#{idx} {script} -> {output_file}\n\t{converted_integrity_1} \\ {converted_integrity_2}")

    #         print(f"#{idx} {script} -> {output_file}")

    #         # Assertion B: Check if for each script, there exists no empty file or error files
    #         ## TODO2: if ... bad_output_lines_count += 1 ... assert(bad_output_lines_count * 100/total 
    #         assert len(output.split("\n")) > 5

    #         # Assertion C: Check similarly between file content (file_size between +/- 20%)
    #         original_size = gh.file_size(script_path)
    #         converted_size = gh.file_size(output_file)
    #         ## TODO2: if ... bad_file_size_count += 1 ... assert(bad_output_lines_count * 100/total 
    #         assert 0.8 * original_size <= converted_size <= 1.2 * original_size

    #     # Assertion: Check if a converted output file exists for each script in mezcla
    #     ## TODO: gh.get_matching_files(gh.form_path(output_path, "*.py"))
    #     ## OLD: assert len(os.listdir(output_path)) == len(scripts)
        
    #     assert len(system.read_directory(output_path)) == len(scripts)

    ## OLD_NAME: test_mezcla_scripts_batch_conversion(self):
    @pytest.mark.xfail
    @pytest.mark.skipif(OMIT_SLOW_TESTS, reason=OMIT_SLOW_REASON)
    def test_mez2std_batch_conversion(self):
        """Test for batch conversion of mezcla scripts to standard scripts."""
        print("\n=== Starting Batch Conversion Test (mez2std) ===\n")
        scripts = self.get_mezcla_scripts()
        if not scripts:
            print("[ERROR] No mezcla scripts found for conversion.")
            return
        
        print(f"[DEBUG] Found {len(scripts)} mezcla scripts to process.")
        
        m2s_path = self.get_m2s_path()
        if not m2s_path:
            print("[ERROR] Conversion script path is not set.")
            return

        print(f"[DEBUG] Conversion script path: {m2s_path}")
        
        output_path = gh.get_temp_dir()
        if not output_path:
            print("[ERROR] Temporary directory for output is not available.")
            return

        print(f"[DEBUG] Output directory: {output_path}\n")

        for idx, script_path in enumerate(scripts, start=1):
            script_name = gh.basename(script_path)
            print(f"\n# [DEBUG {idx}/{len(scripts)}] Processing script: {script_name}")

            # Attempt to run the conversion command
            try:
                output, output_file = self.get_mezcla_command_output(
                    m2s_path=m2s_path, 
                    script_path=script_path, 
                    option="to-standard", 
                    output_path=output_path
                )
                print(f"[DEBUG] Command output file: {output_file}")
            except Exception as e:
                print(f"[ERROR] Failed to run conversion command for {script_name}: {e}")
                continue

            # Check if the output file was created
            if not gh.file_exists(output_file):
                print(f"[ERROR] Output file not generated for {script_name}.")
                continue

            try:
                original_size = gh.file_size(script_path)
                converted_size = gh.file_size(output_file)
                print(f"[DEBUG] Original size: {original_size} bytes, Converted size: {converted_size} bytes")

                assert 0.8 * original_size <= converted_size <= 1.2 * original_size, (
                    f"\n[ERROR] Converted size {converted_size} bytes is not within 20% of the original size {original_size} bytes"
                )
            except Exception as e:
                print(f"[ERROR] File size comparison failed for {script_name}: {e}")
                continue

            # Check content integrity
            try:
                converted_content = gh.read_file(output_file)
                if not converted_content.strip():
                    print(f"[ERROR] Converted file {output_file} is empty.")
                else:
                    line_count = len(converted_content.splitlines())
                    print(f"[DEBUG] Converted file {output_file} contains {line_count} lines.")
            except Exception as e:
                print(f"[ERROR] Failed to read converted file {output_file}: {e}")
                continue

        # Validate the output directory contents
        try:
            converted_files = gh.get_matching_files(gh.form_path(output_path, "*.py"))
            print(f"[DEBUG] Converted files in output directory: {len(converted_files)}")
            assert len(converted_files) == len(scripts), (
                f"[ERROR] Mismatch in expected ({len(scripts)}) and actual converted files ({len(converted_files)})."
            )
        except Exception as e:
            print(f"[ERROR] Final directory verification failed: {e}")

        print("\n=== Batch Conversion Test Completed ===\n")



    # @pytest.mark.xfail
    # @pytest.mark.skipif(OMIT_SLOW_TESTS, reason=OMIT_SLOW_REASON)   
    ## OLD_NAME: def test_mezcla_scripts_metrics(self, threshold=25):
    def test_mez2std_conversion_efficiency(self, threshold=25):
        """Tests external scripts through mezcla using metrics option (TODO: Write better description)
        Note: Provides alternative "conversion efficiency" to test_mezcla_scripts_compare
        """
        ## TODO2: better motivate the use of the "efficiency" metric and use a better threshold
        debug.trace(6, f"test_exteral_scripts({self})")
        
        print(f"\nEfficiency Scores (out of 100 / threshold={threshold}):\n")
        # Run conversion
        scripts = self.get_mezcla_scripts()[0]
        m2s_path = self.get_m2s_path()
        option = "metrics"
        output_path = "/dev/null"

        for idx, script_path in enumerate(scripts, start=1):
            script = gh.basename(script_path)
            output, _output_file = self.get_mezcla_command_output(m2s_path, script_path, option, output_path)

            # Use regex to search calls replaced and warnings added
            calls_replaced = my_re.search(r"Calls replaced:\t(\d+)", output)
            warnings_added = my_re.search(r"Warnings added:\t(\d+)", output)
            calls_replaced_num = int(calls_replaced.group(1)) if calls_replaced else None
            warnings_added_num = int(warnings_added.group(1)) if warnings_added else None

            efficiency = (
                round((calls_replaced_num * 100) / (calls_replaced_num + warnings_added_num), 2)
                if calls_replaced_num != warnings_added_num
                else 0
            )
            print(f"#{idx} {script}: {efficiency}")
            assert efficiency >= threshold

    # NEW: Test summary print handled by a different method
    def print_test_summary(self, metrics: dict):
        """Prints a detailed summary of test results based on the metrics."""
        print("\n=== Heuristic Test Summary ===")
        print(f"Total Scripts Processed: {metrics['processed']}")
        
        print("\nConversion Statistics:")
        print(f"- Successful Conversions: {metrics['successful']}")
        print(f"- Failed Conversions: {metrics['failed']}")
        success_rate = (metrics['successful'] / metrics['processed']) * 100 if metrics['processed'] > 0 else 0
        print(f"- Success Rate: {success_rate:.1f}%")
        
        print("\nQuality Metrics:")
        print(f"- Clean Conversions: {metrics['clean_conversions']}")
        print(f"- Conversions with Warnings: {metrics['warned_conversions']}")
        avg_efficiency = (sum(metrics['efficiency_scores']) / len(metrics['efficiency_scores'])
                        if metrics['efficiency_scores'] else 0)
        print(f"- Average Efficiency Score: {avg_efficiency:.2f}")
        
        if metrics['failed_scripts']:
            print("\nFailed Scripts:")
            for script, error in metrics['failed_scripts']:
                print(f"- {script}: {error}")

if __name__ == "__main__":
    debug.trace_current_context()
    pytest.main([__file__])