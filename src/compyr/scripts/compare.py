import click
import inspect
from .._types import *
from ..models import *
from ..config import *
import json
from pydantic import FilePath

from ..funcs.run_profile_subprocess import run_profile_script_subprocess
from ..funcs.utils import parse_csv_str, inject_logger

# TODO: Update logging config to https://www.youtube.com/watch?v=9L77QExPmI0 and write demo template in a package
from . import logging_config
import logging 

import importlib
from inspect import get_annotations

import concurrent.futures
import subprocess


def _run_test_case(t: TestCaseInput, /,func_name: str, func_location: str, profiling_script: str) -> TestCaseOutput:
    """Wrapper to enable running Python or R TestCaseInput method within a separate executor"""
    return t.run(func_name, func_location, profiling_script)


@click.argument('R_Func', help=f'''The name of an R function and the .Rscript containing it ({Config.defaults.decorators.R_func_tag_format})''')
@click.argument('Py_Func', help=f'''The name of a Python function and the python module containing it (<module_name>.<function_name>)''')
@click.option('--test_json', 
              default=None,
              type=click.Path(exists=True),
              help=f'''.json file of test cases to pass to the functions: \n\n{ComparisonData.json_file_schema()}''')
@click.option('--test_cases', 
              help=f'''JSON str of test cases to pass to the functions (same schema as .json file): "\n\n{ComparisonData.json_file_schema()}"''')
@click.option('--R_prof', 
              default=Config._scripts.profile_R_func,  
              type=click.Path(exists=True),
              help=f'''Path to an .R script to profile the R function. Defaults to {Config.defaults.scripts.profile_R_func}''')
@click.option('--Py_prof', '--py',
              default=Config._scripts.profile_R_func,  
              type=click.Path(exists=True),
              help=f'''Path to a .py script to profile the python function. Defaults to {Config.defaults.scripts.profile_py_func}''')
@click.option('--out_json', 
              default=None, 
              help=f'''.json file path to write the results of this comparison script''')
@click.option('--run_concurrent', 
              type=click.BOOL,
              default=True, 
              help=f'''Run each pair of R and Python test cases in parallel using concurrent.futures''')
@click.option()
def compare(
    R_Func:  str,
    Py_Func: str,
    R_prof: R_FileName  = Config.defaults.scripts.profile_R_func, 
    Py_prof: Py_FileName = Config.defaults.scripts.profile_py_func,
    test_json: FilePath | None = None,
    test_cases: str | None = None,
    out_json: str | None = None,
    run_concurrent: bool = Config.defaults.comparisons.run_concurrent,
    logger: logging.Logger | None = None 
    ) -> tuple[TestCaseOutputComparison]:
    """
    Compare the performance and behavior of a Python and R Function given some test case(s).
    
    Args:  
        R_Func: The R function to test with associated profiling script and test cases
        Py_Func: The python function to test with associated profiling script and test cases, or a single test case with an attached python function. 
        
        R_prof: Profiling script for R function (set default in compyr.config)
        Py_prof: Profiling script for R function (set default in compyr.config)
        
        test_json: Path to JSON file containing test cases (see '--help' for schema)
        test_cases: JSON str of test cases to run (see '--help' for schema)
        
        out_json: Path to JSON file to write results. 

        logger: Optional logger to pass (automatically provided through CLI)
            - TODO: Enable logger options through flags 

    Returns: 
        test_case_comparisons: Tuple of TestCaseOutputComparison objects comparing the results for each test case in Python and R.   
            - NOTE: Test cases between R and Python are associated together based on sort. 
            I.e. different inputs to each function can be considered and compared as the same test case. 
            
    Usage:  
    -----
    
    ## bash 
    python3 -m compyr.compare my_R_script.R::my_R_func my_py_module.my_py_func --test_json 

    """
    logger = inject_logger(logger)

    ### Validate inputs

    ## profiling scripts
    R_File(path=R_prof)
    Py_File(path=Py_prof)

    ## test cases and test json 
    try: 
        assert not (test_json and test_cases)
        assert any((test_json, test_cases))
    except AssertionError: 
        e = ValueError(f"Provide exactly one of `test_json` or `test_cases`")
        e.add_note(f"(Given: `test_json`={test_json}, `test_cases`={test_cases})") 
        raise e 
    if test_json: 
        parsed_test_json = ComparisonData.from_json(test_json)
    else: 
        parsed_test_json = ComparisonData.from_json(json.loads(test_cases))    

    # output json 
    if os.path.splitext(out_json)[-1] != '.json': 
        raise ValueError(f'`out_json` must be a path to a .json file.')

    # R_Func and Py_Func: Create FuncInfo objects from function names and other passed parameters 
    R_FuncInfo = FuncInfo.from_func_string(R_Func, 
                                           **{'profiling_script':R_prof,
                                              'test_cases':[parsed_test_json.R_cases] + [parsed_test_json.both]})
    Py_FuncInfo = FuncInfo.from_func_string(Py_Func, **{'profiling_script':Py_prof, 
                                                        'test_cases':[parsed_test_json.py_cases] + [parsed_test_json.both]})

    ### Run Python and R test cases in parallel: 
    for r_test_case, py_test_case in zip(R_FuncInfo.test_cases, Py_FuncInfo.test_cases): 

        # log the Python test data info and R test info  
        r_test_case.log(logger=logger)
        py_test_case.log(logger=logger)
        
        if run_concurrent: 
            with concurrent.futures.ThreadPoolExecutor() as executor: 
                future_py = executor.submit(_run_test_case, py_test_case)
                future_R = executor.submit(_run_test_case, r_test_case)

                concurrent.futures.wait([future_py, future_R])

                # run comparison
                py_result: TestCaseOutput = future_py.result()
                r_result: TestCaseOutput = future_R.result()

                comparison: TestCaseOutputComparison = py_result.compare(r_result)
                
        else: 
            





if __name__ == '__main__': 
    logger = logging.getLogger(__name__)
    compare(logger=logger)


# match input, R_Func, Py_Func: 
#     case _, _, _ if input is not None and any(R_Func, Py_Func):
#         raise ValueError('Cannot provide both "input" and "R_Func" or "Py_Func"')
#     case _, _, _ if input is None and not all(R_Func, Py_Func): 
#         raise ValueError('Must provide both "R_Func" and "Py_Func" or "input"')





