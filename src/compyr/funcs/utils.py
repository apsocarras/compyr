from .._types import R_FileName, Py_FileName, Bash_FileName, Py_ModuleName, DF, DataFrameComparison
from typing import Mapping, TypedDict, Literal, Sequence, Any
from ..config import Config
import polars as pl
import io
import subprocess 
import os 
import importlib.resources as resources
import logging 
from polars.testing import assert_series_equal
from collections import defaultdict

def inject_logger(logger: logging.Logger | None,/) -> logging.Logger: 
    """
    Use on 'logger' parameter set in a function default to return a logger with a null handler if no logger is provided. 

    E.g. 

    def my_func(logger): 
        inject_logger(logger)
        logger.debug("Testing")
        print('Ran without error')

    my_func(None)
    >>> Ran without error. 

    Returns: 
        logger: Either the original logger or a null logger. 

    https://stackoverflow.com/questions/56709525/python-library-default-nullhandler-causing-error-when-unit-testing 
        - note to *call* NullHandler()
    """
    if not isinstance(logger, logging.Logger): 
        logger = logging.getLogger('dummy')
        logger.addHandler(logging.NullHandler()) 
        logger.propagate = False
        logger.setLevel(logging.NOTSET)

    return logger 
    
def kwargs_dict_to_CLI_string(sep=" ", wrap_in_quotes: bool = False, **kwargs) -> str:
    """   
    Parse a dictionary of key:value arguments to a string of key=value pairs.
    """
    return sep.join([f'{k}={v}' if not wrap_in_quotes else f'"{k}={v}"' 
                     for k,v in kwargs.items()]).rstrip(sep)

def parse_kwargs_CLI_strings(kwarg_strs: Sequence[str]) -> dict[str, Any]: 
    """
    Evaluates the string values using eval()
    """
    kwargs_dict = {}
    for k in kwarg_strs: 
        key, value = k.split('=')
        kwargs_dict[key] = eval(value)
    return kwargs_dict


def parse_csv_str(csv_string: str, /, 
                  prefix: str = "csv:", 
                  lazy: bool = True, 
                  schema: Mapping[str, pl.DataType] | None = None) -> str | DF: 
    """
    Attempt to read a string into a Polars LazyFrame or DataFrame. 
    Removes any prefix designating a CSV string. 
    """
    if csv_string.startswith(prefix):
        csv_string = csv_string[len(prefix):]
    
    csv_bytes = io.BytesIO(csv_string.encode('utf-8'))
    return pl.scan_csv(csv_bytes, schema=schema) if lazy else pl.read_csv(csv_bytes, schema=schema)

def check_R_func_exists_in_Rscript(r_file_name: R_FileName, r_func_name: str, 
                                   logger: logging.Logger | None = None) -> bool: 
    """
    Check that an R function exists in a given R file. 
    Runs packaged .R script 'check_file_func.R'
    """
    logger = inject_logger(logger)
    r_script_path = resources.files('compyr') / os.path.join('scripts', 'Rscripts', 'check_file_func.R')

    cmd = ['Rscript', r_script_path, r_file_name, r_func_name]
    try: 
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0: 
            logger.debug('R script executed successfully.')
            try: 
                output = result.stdout.strip()
            except AttributeError as e: 
                output = result.stdout
            match output: 
                case 'TRUE': 
                    return True 
                case 'False': 
                    return False 
                case _: 
                    raise ValueError(f"Unexpected output from R script: {output}")
    except FileNotFoundError as e:
        e.add_note('Rscript not found; ensure R is installed and accessible in your PATH variable.')
        raise e 

def compare_dataframes(a: DF, b: DF,
                       check_row_order: bool = False, 
                       ) -> DataFrameComparison: 
    """
    Compare two polars DataFrames/LazyFrames for schema, column order, row order, and column values.  
    Collects LazyFrames in order to compare row values. 
    NOTE: Use polars.testing.assert_frame_equal if you just want to know if they are different and don't need the full list of differences. 

    (Separate methods for each of these checks exist in polars.testing.asserts but they are private methods).
    """
    
    diff = {}

    # Schema 
    a_schema, b_schema = a.collect_schema(), b.collect_schema()
    if a_schema == b_schema: 
        diff['schema'] = {}
    else: 
        schema_diffs = {}
        
        a_schema_set, b_schema_set = set(a_schema), set(b_schema)
        schema_diffs['a_not_in_b'] = b_schema_set.difference(a_schema_set)
        schema_diffs['b_not_in_a'] = a_schema_set.difference(b_schema_set)
        schema_diffs['diff_types'] = {k:{'a':a_schema[k], 'b':b_schema[k]}
                                      for k in a_schema_set.intersection(b_schema_set) 
                                      if type(a_schema[k]) != type(b_schema[k])}
        diff['schema'] = schema_diffs

    # Column order
    a_columns, b_columns = list(a_schema), list(b_schema)
    if a_columns == b_columns: 
        diff['col_order'] = {}
    else: 
        diff['col_order'] = {'a':a_columns, 'b':b_columns}

    # Collect for row order, row values, and n_rows 
    if isinstance(a, pl.LazyFrame): 
        a = a.collect()
    if isinstance(b, pl.LazyFrame): 
        b = b.collect()    

    if not check_row_order: 
        # Sort both by a's columns
        a = a.sort(by=a.columns)
        b = b.sort(by=a.columns)
    
    # n_rows
    diff['n_rows'] = {}
    if a.height != b.height: 
        diff['n_rows'] = {'a': a.height, 'b': b.height}

    # Values 
    diff['col_values'] = {}
    for col in a.columns: 
        col_a, col_b = a.get_column(col), b.get_column(col)
        try: 
            assert_series_equal(col_a, col_b)
        except AssertionError as e: 
            diff['col_values'][col] = str(e)
    
    return diff 