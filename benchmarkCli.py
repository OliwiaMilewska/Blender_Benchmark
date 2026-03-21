#!/usr/bin/env python3
"""
CLI wrapper for blender_benchmark
Run with: python benchmarkCli.py --help
Or: python benchmarkCli.py --commands
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.blender_benchmark.cli import main

if __name__ == "__main__":
    main()
