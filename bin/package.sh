#!/bin/sh

rm -Rf build dist onering.egg-info
python setup.py sdist
python setup.py bdist_wheel --universal
rm -Rf onering.egg-info
