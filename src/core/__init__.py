#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/__init__.py - Core Package
Simplified initialization without complex re-exports.
"""

# The core package is now just a namespace
# Individual modules should be imported directly as needed

# This avoids the import errors from trying to re-export 
# modules that may not exist or have been moved

__all__ = []