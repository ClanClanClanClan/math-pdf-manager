#!/bin/bash
# Install Architectural Quality Pre-commit Hooks
# Phase 1, Week 1 Implementation

echo "🏗️  Installing Architectural Quality Pre-commit Hooks"
echo "=================================================="

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "❌ pre-commit is not installed. Please install it first:"
    echo "   pip install pre-commit"
    exit 1
fi

# Install pre-commit hooks
echo "📦 Installing pre-commit hooks..."
pre-commit install

# Run hooks on all files to establish baseline
echo "🔍 Running initial architectural analysis..."
echo "   (This may take a few minutes for the first run)"

# Run architectural lint to get baseline
if python automated_improvement_tooling.py --ci-mode; then
    echo "✅ Current architectural health check passed"
else
    echo "⚠️  Current codebase has architectural violations"
    echo "   These will need to be addressed over time"
fi

echo ""
echo "✅ Pre-commit hooks installed successfully!"
echo ""
echo "📋 Installed hooks:"
echo "   1. architectural-lint     - Prevents new architectural violations"
echo "   2. file-size-check       - Blocks files over 500 lines"
echo "   3. forbidden-patterns    - Catches hardcoded secrets, print statements"
echo "   4. single-responsibility - Ensures focused modules"
echo "   5. dependency-rules      - Enforces architectural boundaries"
echo "   6. secure-config-check   - Prevents insecure configuration"
echo ""
echo "🚀 Next steps:"
echo "   1. Hooks will run automatically on 'git commit'"
echo "   2. To run manually: pre-commit run --all-files"
echo "   3. To skip temporarily: git commit --no-verify"
echo ""
echo "📚 See IMPLEMENTATION_ROADMAP.md for the full transformation plan"