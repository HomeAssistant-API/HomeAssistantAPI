#!/bin/bash

# Run pytest with coverage
pytest tests --cov --cov-report=html:htmlcov

# Open the coverage report in the default browser
if command -v open > /dev/null; then
    open htmlcov/index.html
else
    echo "Coverage report generated at: htmlcov/index.html"
fi