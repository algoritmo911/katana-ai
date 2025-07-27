#!/bin/bash
pip install -r requirements.txt
export PYTHONPATH=$PYTHONPATH:./
pytest
