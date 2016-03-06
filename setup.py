""" Simple `setup.py` to distribute the `make_ssl` module """
from setuptools import setup

setup(
    name='make-ssl',
    version='0.1.0',
    py_modules=['make_ssl'],
    entry_points='''
      [console_scripts]
      make_ssl=make_ssl:cli
    '''
)
