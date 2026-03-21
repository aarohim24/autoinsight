"""pytest configuration and shared fixtures."""
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Set test env vars before any imports
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-placeholder")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:8501")
os.environ.setdefault("LOG_LEVEL", "WARNING")
