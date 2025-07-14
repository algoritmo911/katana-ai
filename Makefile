install:
	pip install -r requirements.txt

test:
	python -m pytest

lint:
	flake8 .

run:
	python katana/agent/main.py
