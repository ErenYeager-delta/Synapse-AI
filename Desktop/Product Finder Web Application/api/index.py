import sys
import os

# Add the backend directory to sys.path so we can import 'app'
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import create_app

# Vercel looks for the 'app' variable
app = create_app()
