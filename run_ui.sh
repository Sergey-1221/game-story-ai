#!/bin/bash

echo "Starting AI Game Story Generator UI..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Check if streamlit is installed
python -c "import streamlit" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing Streamlit..."
    pip install streamlit streamlit-option-menu streamlit-aggrid streamlit-extras plotly
fi

# Run the Streamlit app
echo "Launching UI at http://localhost:8501"
streamlit run streamlit_app.py --server.port 8501 --server.address localhost