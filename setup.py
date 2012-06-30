# coding: utf-8

from distutils.core import setup
import os

import _meta


requirements = open('requirements.txt').readlines()

setup(
    name='tf2idle',
    version=_meta.__version__,
    author='Gregg Gajic',
    author_email='gregg.gajic@gmail.com',
    py_modules=['_meta'],
    install_requires=requirements,
    classifiers=['Programming Language :: Python',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.2',
                 'Natural Language :: English',
                 'Operating System :: Microsoft :: Windows',
                 'License :: OSI Approved :: MIT License',
                 'Development Status :: 3 - Alpha'],
    packages=['tf2idle'],
    scripts=['bin/tf2idlectl.py'],
    license=open('LICENSE').read(),
    description='Python library to idle in Team Fortress 2 using Sandboxie',
    long_description=open('README.rst').read(),
    url='https://github.com/gg/tf2idle',
)
