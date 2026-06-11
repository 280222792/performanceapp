#!/usr/bin/env python3
"""Production launcher for 绩效承诺书管理系统."""
import os
import sys

# Ensure we're in the app directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Add current dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from waitress import serve
from app import app, ensure_directories

ensure_directories()

print("=" * 50)
print("  绩效承诺书管理系统 已启动")
print("  http://localhost:8080")
print("=" * 50)

serve(app, host='0.0.0.0', port=8080, threads=4)
