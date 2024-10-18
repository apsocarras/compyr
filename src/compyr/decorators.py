from typing import Sequence, Mapping, Callable, Any, TypedDict, Generator
from ._types import R_FileName
from .models import R_File, ComparisonData
from .config import Config
from .funcs.utils import check

from functag.annotate import annotate



def compare_to_R(R_script: R_FileName, 
                R_func: str, 
                ensure_abs_path: bool = Config.defaults.decorators.ensure_abs_path, 
                R_tag_name: str = Config.defaults.decorators.R_func_tag_name,
                tag_format_str: str = Config.defaults.decorators.R_func_tag_format,
                test_data: Sequence[ComparisonData] | None = None, 
                add_to_registry: Callable | None = None
                ): 
    """
    Annotate to which R script/function a Python function corresponds.
    - Adds a str attribute indicating its R counterpart's location
    - Adds the function to a registry of Python functions with R counterparts.
    - (Optional) Add test cases to use when automatically generating comparison tests for pytest. 
    
    Args: 
        R_script (str): Name of an .R file. 
        R_func (str): Name of a function in the R file.
        ensure_abs_path (bool): Whether to check that the .R file exists - also checks that R function is importable from the R script. 
        R_tag_name (str): Name of the attribute designating the R function.
        tag_format_str (str): Format string for the attribute.        
        test_data (Sequence[ComparisonData]): (Optional) Sequence of test cases to use for generating comparison tests in pytest. 
        add_to_registry (Callable): (Optional) Registry of functions to which to add the function.
    
    Usage:
    ------

    ## calcCircumference.R
    circumference <- function(r) {
        2*pi*r
    }   

    ## math_funcs.py 
    from compyr.funcs.decorators import compare_to_R
    from math import pi

    @compare_to_R('calcCircumference.R', 'circumference', 
                test_data=ComparisonData(p={'radius':2}, R={'r':2}))
    def circumference(radius: int): 
        return 2*pi*radius 
    
    print(circumference.compare_to_R)
    >>> calcCircumference.R::circumference
    """
    
    # Validate extension 
    R_File.ensure_valid_extension({'path':R_script})

    # Validate file exists 
    if ensure_abs_path: 
        R_File(path=R_script)

    # Create annotations 
    R_tag_formatted = tag_format_str.format(**{'R_script':R_script, 'R_func':R_func})

    test_data_dict = {'test_data': test_data} if test_data is not None else {}
    annotated_func = annotate({**{tag_name:}, **test_data_dict})
    
    # Register annotated function 
    if add_to_registry is not None: 
        try: 
            assert annotated_func is not None 
        except AssertionError as e: 
            e.add_note('Sending None to a Generator causes it to stop awaiting new values -- this would terminate a Generator-based registry on accident.')
            e.add_note(f'Directly call {add_to_registry.__name__}(None) if you intend to send None to your registry.')
            raise e
        add_to_registry(annotated_func)
        
        if registries := getattr(annotated_func, 'registries', False): 
            if isinstance(registries, list): 
                registries.append(add_to_registry)
            else: 
                annotated_func.registries = [add_to_registry] 

    return annotated_func

    




