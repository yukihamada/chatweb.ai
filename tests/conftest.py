"""Shared test fixtures."""
import os

# Set test environment variables before importing main
os.environ.setdefault("DB_PATH", "/tmp/test_chatweb.db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")
