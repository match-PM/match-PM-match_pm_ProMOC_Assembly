from setuptools import find_packages
from setuptools import setup

setup(
    name='promoc_assembly_interfaces',
    version='0.0.0',
    packages=find_packages(
        include=('promoc_assembly_interfaces', 'promoc_assembly_interfaces.*')),
)
