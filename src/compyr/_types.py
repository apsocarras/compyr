from types import FunctionType

from typing import TypeAlias, TypedDict, Generator, TypeVar, Literal, Any, Mapping, Sequence, Tuple, Union

from types import FunctionType
from typing import TypeAlias, TypedDict, Generator, TypeVar, Literal, Any, Type

import polars as pl 

CsvString: TypeAlias = str

DF = TypeVar('DF', pl.DataFrame, pl.LazyFrame)

ProfileDetailLevel: TypeAlias = Literal['simple', 'detailed']
ParseLevel: TypeAlias = Literal['all', 'df_only', 'none', 'csv:'] # 'csv:' prefixed string

DfEngine: TypeAlias = Literal['polars-lazy', 'polars-eager', 'pandas'] # for now only polars-lazy is supported 

FuncName: TypeAlias = str

Py_ModuleName: TypeAlias = str
Py_FileName: TypeAlias = str
R_FileName: TypeAlias = str

Bash_FileName: TypeAlias = str

ColumnName: TypeAlias = str  
ColumnDiffErrorMsg: TypeAlias = str # string representation of AssertionError 

class SchemaComparison(TypedDict): 
    a_not_in_b: set 
    b_not_in_a: set 
    diff_types: dict[str, type]

class DataFrameComparison(TypedDict): 
    schema: SchemaComparison
    col_order: dict[Literal['a','b'], list]
    n_rows: dict[Literal['a','b'], int]
    col_values: dict[ColumnName, ColumnDiffErrorMsg]