#!/usr/bin/env bash
rm -rf build
mkdir build
sphinx-build docs build
cd build
python -m http.server
cd ../