#!/bin/bash

# Backup current streamlit_app.py
cp streamlit_app.py streamlit_app.py.bak
echo "Backed up streamlit_app.py to streamlit_app.py.bak"

# Overwrite streamlit_app.py with the template
cp streamlit_app.py.template streamlit_app.py
echo "Restored streamlit_app.py from template."

# Validate syntax
python -m py_compile streamlit_app.py
if [ $? -eq 0 ]; then
  echo "Syntax validation successful."
  # Run streamlit app
  streamlit run streamlit_app.py
else
  echo "Syntax validation failed. Please check streamlit_app.py."
  exit 1
fi
