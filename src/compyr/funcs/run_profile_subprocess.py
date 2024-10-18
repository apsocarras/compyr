from .._types import *
from ..config import *
import subprocess
import os 
from .utils import kwargs_dict_to_CLI_string
import importlib

def run_profile_script_subprocess(
                       func_name: str, 
                       func_location: Union[R_FileName, Py_ModuleName],
                       profiling_script: Union[R_FileName, Py_FileName, Bash_FileName] | None = None, 
                       *args,
                       **kwargs
                      ) -> subprocess.CompletedProcess: 
    """
    Run a profiling script on either a Python function or an R function in a Python subprocess.
    
    Designed to be used with the default profiling scripts included in this package but you can use your own. 
        - TODO: Can set defaults in compyr.config.Config 
    
    The profiling script must accept either an R script and an R function name or a Python module and a function name.
        
    Args: 
        func_name: Name of the R or Python function.
        func_location: name of an .R file containing the R function or the name of a python module containing the python function.
        profiling_script: path to a script to profile the function.
            - For python functions: 
                - Script must be executable with 'python3 -m scalene --json <path/to/script>.py' (default is run_func_from_cli.py, i.e. no custom scalene logic)
                - "<my_var>=<my_value>" kwarg strings entered after "--kwargs" flag
            - For R functions: 
                - Set default in `Config.defaults.scripts.profile_R_func`
        *args: Positional args to pass to the function to be profiled.
        **kwargs: Key word arguments to be passed to the profiled function.
    """

    # Determine if function to be profiled is in R or Python 
    func_type: str = None 
    try: 
        file_ext = os.path.splitext(func_location)[-1]
        assert file_ext in set('.R', '')
        if file_ext == '': 
            try: 
                module = importlib.import_module(func_location)
                imported_func = getattr(module, func_name)
            except ImportError as e: 
                raise e # TODO: in case you want to handle something 
            except AttributeError as e: 
                e.add_note(f'Function {func_name} not imported from module {module}')
                raise e 
            func_type = '.py'
        else: 
            func_type = '.R'
    except AssertionError: 
        e = ValueError(f"Invalid file extension for `func_location`={func_location}.")
        e.add_note("Must provide .R script for an R function or a module name for a python function.")
        raise e 
    except TypeError as e: 
        e.add_note(f'"func_location" must be str (given: {func_location})')
        raise e

    # Set profiling_script based on func_type
    if profiling_script is not None: 
        try: 
            file_ext = os.path.splitext(profiling_script)[-1]
            assert profiling_script in set('.R', '.py')
            assert profiling_script == func_type
        except AssertionError: 
            raise ValueError(f"`profiling_script` must match the function type (`func_name`: {func_name}, `func_location`:{func_location}, `profiling_script`: {profiling_script}, `func_type`: {func_type})")
    else: 
        profiling_script = Config._scripts.profile_py_func if func_type == '.py' else Config._scripts.profile_R_func 

    # Run subprocess 
    exec_command = ['python3', '-m', 'scalene', '--json'] if func_type == '.py' else ['Rscript']
    cl_args = [args] if args else []
    cl_kwargs = [kwargs_dict_to_CLI_string(wrap_in_quotes=True, **kwargs)] if kwargs else []

    result: subprocess.CompletedProcess = subprocess.run(
        exec_command + [profiling_script, func_location, func_name] + cl_args + cl_kwargs, 
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, # capture outputs 

    )

    return result