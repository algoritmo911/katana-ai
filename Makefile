install:
	pip install -r requirements.txt

test:
	python -m pytest

run:
	python katana/agent/main.py
