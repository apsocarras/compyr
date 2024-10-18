from __future__ import annotations
from ._types import * 
from typing import Union
from .funcs.run_profile_subprocess import run_profile_script_subprocess
from .funcs.utils import check_R_func_exists_in_Rscript, inject_logger, parse_csv_str, compare_dataframes, kwargs_dict_to_CLI_string
from .config import Config

import os
from scalene.scalene_json import ScaleneJSONSchema
from pydantic import BaseModel, Field, field_validator, model_validator, FilePath, ValidationError

import subprocess
import importlib
import logging

from polars.testing import assert_frame_equal
from inspect import get_annotations 

import json 


class SpecFile(BaseModel):
    path: FilePath
    _ext: str  # Private field that should not be set by users

    @model_validator(mode='before')
    @classmethod
    def ensure_valid_extension(cls, data: dict):
        try:
            # Extract file extension from the provided path
            file_ext = os.path.splitext(data['path'])[-1]
        except:
            raise ValueError(f"Failed to parse file extension for {data['path']} (type: {type(data['path'])})")

        # Ensure that the file extension matches the required extension
        if file_ext != cls._ext.default:
            raise ValueError(f'{data["path"]} does not have a valid {cls._ext.default} extension')
        return data

    @classmethod
    def factory(cls, file_ext: str) -> Type['SpecFile']:
        """
        Factory method to create a SpecFile subclass with a fixed private extension (`_ext`).

        #### Usage: 
        RFile = SpecFile.factory(".R")
        PyFile = SpecFile.factory(".py")

        r_file = RFile(path="example.R")
        py_file = PyFile(path='example.R')
        >>> ValidationError
        """
        # Define a new subclass of SpecFile with a fixed private extension
        class CustomSpecFile(cls):
            _ext: str = file_ext  # Fixed private extension
            class Config:
                # This prevents new attributes from being added by users (to protect `_ext`)
                extra = 'forbid'

        return CustomSpecFile

R_File: Type[SpecFile] = SpecFile.factory('.R')
Py_File: Type[SpecFile] = SpecFile.factory('.py')
JSON_File: Type[SpecFile] = SpecFile.factory('.py')

class TestCaseInput(BaseModel): 
    """
    Test case inputs and expected outputs. Omits function information (intended for use with compyr.scripts.compare())
    """
    args: Tuple[Any] | None = Field(None, "Positional arguments to pass into the profiled function.")
    kwargs: Mapping[str, Any] | None = Field(None, "Key:value arguments to pass into the profiled function.")
    expected_output: Any

    def run(self, 
            func_name: str,
            func_location: R_FileName | Py_ModuleName, 
            profiling_script: R_FileName | Py_FileName, 
            ) -> 'TestCaseOutput': 
        """Run the test case in a subprocess given some profiling script and function to profile"""

        test_output_process: subprocess.CompletedProcess = run_profile_script_subprocess(profiling_script, func_location, func_name, *self.args, **self.kwargs)

        # Parse the output result 
        test_output = TestCaseOutput.from_subprocess(test_output_process)
        
        return test_output

    def __str__(self) -> str:
        """(Abbreviated expected_output for sensible logging)""" 

        abbrev_output = str(self.expected_output)[:min(len(self.expected_output), 100)]

        return f"{self.__class__.__name__}(*({', '.join(self.args)}), **({kwargs_dict_to_CLI_string(sep=', ')}), expected_output={abbrev_output})"
    
    def __eq__(self, other: 'TestCaseInput') -> bool: 
        """Compare just the test data inputs of two test cases (e.g. if comparing a test case for a python function and an R function)"""
        return (self.args == other.args) and (self.kwargs == self.kwargs)
    

    def log(self, logger: logging.Logger) -> None: 
        """TODO: Log self info in a standard format."""
        return None 

class ComparisonData(BaseModel): 
    """
    Schema for JSON file containing test cases to be input into the comparison function.

    NOTE: .py and .R functions will be associated together based on their sort order. 
    The number of test cases should therefore be the same for each. 

    NOTE: Does not screen for duplicate test cases.

    """
    py_cases: Sequence[TestCaseInput]
    R_cases: Sequence[TestCaseInput]
    both: Sequence[TestCaseInput]

    @model_validator(mode='before')
    @classmethod
    def ensure_same_number(cls, data: dict):
        """Ensure number of test cases provided for the python and R functions are the same"""
        try: 
            assert len(data.get('py',[])) == len(data.get('R',[]))
        except AssertionError: 
            raise ValueError(f"Number of python test cases must match number of R test cases.")
        return data 

    @classmethod
    def json_file_schema(cls) -> str:
        """
        Return expected JSON file schema when reading in test cases from a .json file.
        Use when printing to CLI.
        
        Returns: 
            json_file_schema: 
                - .py: Test cases to run on python functions only 
                - .R: Test cases to run on R functions only 
                - both: Test cases to run on both python and R functions. 

        NOTE: .py and .R functions will be associated together based on their sort order. 
        The number of test cases should therefore be the same for each. 
        """ 
        return  json.dumps({

            'py_cases':"["+json.dumps(get_annotations(cls)) + "..." + "]",
            'R_cases':"["+json.dumps(get_annotations(cls)) + "..." + "]",
            'both':"["+json.dumps(get_annotations(cls)) + "..." + "]",

            }, indent=2)
    
    @classmethod
    def from_json(cls, fp) -> 'ComparisonData':
        
        JSON_File(path=fp) # Ensure file exists and has .json extension 
        
        with open(fp, 'r') as file: 
            data = json.load(file)
        
        try: 
            return ComparisonData(py=data.get('py'),
                                      R=data.get('R'), 
                                      both=data.get('both'))
        except ValidationError as e: 
            
            data_str = json.dumps(data, indent=2)
            data_head = data_str[:min(100, len(data_str))] + "\n..."

            val_e = ValueError(f'Failed to parse {fp} according to {cls.__name__}: {e}')
            val_e.add_note("Given:\n\n" + data_head)

            raise val_e

class TestCaseOutput(TestCaseInput):
    """
    Model for the output of a profiling script given a single test case and function.
    """  
    func_tested: 'FuncInfo'   
    output: CsvString | Any  = Field(..., "Output of the function.")
    time: int = Field(..., "System time in seconds.")
    memory: int = Field(..., "Memory usage in bytes of the function profiled.")
    cpu: 'UsageCPU' | None = Field(None, description="TODO: Enable cpu usage monitoring of parallel processing tasks in R and Python.")

    # Additional fields present in the detailed output from ScaleneJSONSchema
    scalene_data: ScaleneJSONSchema | None = Field(None, 'More detailed profiling output from the scalene python package.')
 
    _schema: Mapping[str, pl.DataType] | None = Field(None, '(Optional) Set a default schema for the output field when reading a CSV string in the output to a DataFrame')

    def parse_csv_str(self, schema: Mapping[str, pl.DataType] | None = None) -> pl.LazyFrame: 
        """
        Parse self.output into a polars Lazyframe relative to a specified schema (defaults to self._schema)
        """
        schema = schema or self._schema 
        return parse_csv_str(self.output, schema=schema)

    def compare(self, other: 'TestCaseOutput',/, full: bool = True) -> 'TestCaseOutputComparison': 
        """
        Compare self vs the performance & output of another profiled function.  

        Args: 
            other: Another ProfileOutput to compare against. 
            full: Whether to conduct a full comparison between self.output and other.output (relevant if DataFrames)

        NOTE: Compared functions can have equivalent expected outputs or distinct expected outputs. 
        NOTE: Could technically compare two Python functions or two R functions.
        """        
    
        # Performance 
        time_diff = self.time - other.time 
        memory_diff = self.memory - other.memory
        cpu_diff = self.cpu.compare(other.cpu)

        # Behavior 
        output_comparison = None
        match self.output: 
            case str(): # attempt to parse csv string to DataFrame 
                self_df = parse_csv_str(self.output)
                other_df = parse_csv_str(other.output)
                
                if isinstance(self_df, pl.LazyFrame) and isinstance(other_df, pl.LazyFrame):  
                    if full: 
                        # Conduct full comparison of DataFrames
                        output_comparison = compare_dataframes(a=self_df, b=other_df)
                    else:  
                        try: 
                            assert_frame_equal(self_df, other_df)
                        except AssertionError as e: 
                            output_comparison = str(e)
            case _: # just compare the two values
                output_comparison = (self.output == other.output)
        
        return TestCaseOutputComparison()
    
    @classmethod
    def from_subprocess(cls, input: subprocess.CompletedProcess, /,):
        """
        TODO: Create TestCaseOutput parsed from the output of a profiling script (subprocess.CompletedProcess)
        """
        return None 
    
class TestCaseOutputComparison(BaseModel):
    R_TestCaseOutput: TestCaseOutput
    Py_TestCaseOutput: TestCaseOutput
    time_diff: float 
    memory_diff: float 
    cpu_diff: float 
    output_comparison: bool | DataFrameComparison


class FuncInfo(BaseModel, arbitrary_types_allowed=True): 
    """
    Model for data needed to identify, execute, and profile a function in R or Python.

    Can optionally attach test cases.
    """
    func_type: Literal['.R', '.py']
    func_location: str # 'R_FileName' | 'Py_ModuleName'
    func_name: str # 'FuncName'
    func: FunctionType | None = None # only python function, obviously
    profiling_script: str | None = None#  'R_FileName' | 'Py_FileName' | 'Bash_FileName'
    test_cases: Sequence['TestCaseInput'] | None = None 

    _logger: logging.Logger | None = None

    @model_validator(mode='before')
    @classmethod
    def ensure_func_location(cls, data: dict): 

        logger = inject_logger(cls._logger)

        match file := data.get('func_type', None): 
            case ".R": 
                # Check valid existing R file 
                R_File(path=data['func_location'])

                # Check that the function exists in the R file 
                if not check_R_func_exists_in_Rscript(
                                               r_file_name=data.get('func_location'), 
                                               r_func_name=data.get('func_name'),
                                               logger=logger): 
                    raise ImportError(f'Function "{data.get("func_name")}" not found in .R file "{data.get("func_location")}".')
            case ".py": 
                try: 
                    module_name = data.get('func_location')
                    func_name = data.get('func_name')

                    # Attempt to import the python module 
                    module = importlib.import_module(module_name)
                    logger.debug(f"Successfully imported module {module_name}")

                    # Attempt to import the function from the python module
                    func = getattr(module, func_name)
                    logger.debug(f'Successfully imported function "{func_name}" from module "{module_name}"')

                except ModuleNotFoundError as e: 
                    raise e 
                except AttributeError as e: 
                    e.add_note(f'Failed to import function "{func_name}" from module "{module_name}"')
                    raise e  
            case _: 
                raise ValueError(f'File {file} has an unsupported extension (must be .R or .py)')
            
        return data 
    
    def func_string(self, 
                    py_format_str: str = Config.defaults.decorators.py_func_name_format,   
                    R_format_str: str = Config.defaults.decorators.R_func_tag_format):
        """Format the func_name and func_location to a unified string based on self.func_type"""
        match self.func_type: 
            case ".R": 
                return R_format_str.format(**{'R_script':self.func_location, 'R_func':self.func_name})
            case ".py": 
                return py_format_str.format(**{'py_module':self.func_location, 'py_func':self.func_name})
    @classmethod       
    def from_func_string(self, s: str, **kwargs): 
        """Create instance from str (use **kwargs to initialize with other accepted fields)"""
        if '.R:' in s: 
            func_type = '.R'
            func_location, func_name = s.split('.R:')
        else: 
            func_type = '.py'
            func_location, func_name = s.split('.')
        return FuncInfo(func_type=func_type, func_location=func_location, func_name=func_name)
        
class UsageCPU(BaseModel):
    """
    TODO: Schema summarizing CPU usage for a multi-threaded process. 
    """
    def compare(self, other: 'UsageCPU', /,): 
        """
        TODO: Custom comparison method. 
        """
        return None     