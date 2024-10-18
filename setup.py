from setuptools import setup 
from setuptools import find_packages

setup(
    name='compyr', 
    version='0.1.0',
    packages=find_packages(where='src'),
    package_data={
        'compyr':['scripts/*.R']
    }
)