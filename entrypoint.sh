. .venv/bin/activate
echo "Waiting $DELAY seconds for Home Assistant to start..."
python -c "import time; time.sleep($DELAY)"
echo "Finished waiting $DELAY seconds. Starting tests..."
pytest tests --disable-warnings --cov --cov-report xml:coverage/coverage.xml
