import importlib.resources
from ._types import *
from functag.registry import registry
import os
import pydantic as pyd

from . import logging_config
import logging

import importlib
from importlib.resources.abc import Traversable

from pathlib import Path 

CUR_DIR = Path(__file__).resolve().parent

class Config: 
    """
    Package defaults and configuration settings.
    Use setter methods to modify exposed attributes.  
    Do not modify "_"-protected attributes. 
    """
    class _scripts: # included scripts in the package
        """
        Paths to scripts included in package which can be executed from the command line.
        """
        script_dir = os.path.join(CUR_DIR, 'scripts')
        profile_R_func: Traversable = importlib.resources.files('compyr.scripts').joinpath('profile_R_func.R')
        profile_py_func: Path = Path(os.path.join('compyr','scripts','run_func_from_cli.py')) 
        
    class _decorators: 
        R_func_tag_name: str = "compare_to_R"
        R_func_tag_format: str = "{R_script}.R::{R_func}"
        py_func_name_format: str = "{py_module}.{py_func}"
        ensure_abs_path: bool = False 

    class defaults: 

        class scripts: 
            profile_R_func: Traversable = importlib.resources.files('compyr.scripts').joinpath('profile_R_func.R')
            profile_py_func: Path = Path(os.path.join('compyr','scripts','run_func_from_cli.py')) 

        class decorators: 
            R_func_tag_name: str = "compare_to_R"
            R_func_tag_format: str = "{R_script}.R::{R_func}"
            py_func_name_format: str = "{py_module}.{py_func}"
            ensure_abs_path: bool = False 

        class comparisons:
            run_concurrent: bool = True  
    
    