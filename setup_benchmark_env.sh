#!/bin/bash
# Setup script for benchmark environment

set -e

echo "Setting up benchmark environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "benchmark_venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv benchmark_venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source benchmark_venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r benchmark_requirements.txt

echo ""
echo "✓ Setup complete!"
echo ""
echo "To use the benchmark scripts, activate the virtual environment:"
echo "  source benchmark_venv/bin/activate"
echo ""
echo "Then run your benchmarks:"
echo "  python benchmark_performance.py --config-name my_config --container-name flyimg"

