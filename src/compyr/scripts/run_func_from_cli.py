import importlib
import click
import json
import time
from pathlib import Path 
from..funcs.utils import parse_kwargs_CLI_strings
from typing import Sequence, Mapping, Any 

@click.command()
@click.argument('function_module', type=str)
@click.argument('func_name', type=str)
@click.argument('args', nargs=-1)
@click.option('--kwargs', type=str, multiple=True, help="Keyword arguments in the format key=value")
def run_function(function_module: str, func_name: str, args: Sequence[Any], kwargs: Mapping | Sequence[str]) -> Any:
    """
    CLI Wrapper to execute any function from a Python module with given positional and keyword arguments. 

    Args: 
        function_module (str): Name of python module containing function 
        func_name (str): Name of function to import from module 
        args (Sequence[Any]): Positional arguments to provide the python function 
        kwargs (Mapping | Sequence[str]): Keyword arguments to pass to function (either as dict or "key=value" strings)
    
    Returns: 
        result (Any): Result of the executed function.  

    Usage:
    -----
    ## math_funcs.py 
    def circumference(radius):
        from math import pi
        from time import sleep
        sleep(2)
        return 2 * pi * radius

    python3 -m src.compyr.scripts.run_func_from_cli math_funcs circumference 5
    >>> Result: 31.41592653589793

    python3 -m src.compyr.scripts.run_func_from_cli math_funcs circumference --kwargs "radius=5"
    >>> Result: 31.41592653589793

    # With scalene 
    python3 -m scalene --json src/compyr/scripts/run_func_from_cli.py math_funcs circumference 5
    """

    # Import the module and function
    module = importlib.import_module(function_module)
    func = getattr(module, func_name)
    
    # Process arguments
    args = [eval(arg) for arg in args]  # Convert string args to appropriate types    
    kwargs_dict = parse_kwargs_CLI_strings(kwargs)

    # Execute
    try: 
        result = func(*args, **kwargs_dict)
    except TypeError as e: 
        e.add_note(json.dumps([{"args":args}] + [{"kwargs":kwargs_dict}]))
        raise e    
    
    # Print the result of the function
    click.echo(f"Result: {result}")

    return result 

if __name__ == '__main__':
    run_function()
