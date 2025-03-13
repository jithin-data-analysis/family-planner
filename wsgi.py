import sys
import os

# Add the project root directory to the Python path
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.append(path)

# Import your Streamlit app
from src.app import app 