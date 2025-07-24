#!/bin/bash

# Script to run code quality checks using ruff and pyright

echo "Running ruff check..."
ruff check .

echo "Running ruff format check..."
ruff format --check .

echo "Running pyright type checking..."
pyright

echo "All checks completed!"