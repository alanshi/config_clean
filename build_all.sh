#!/usr/bin/env bash
set -e

echo "📦 Step 1: Cleaning old build..."
rm -rf dist build *.egg-info

echo "⚙️ Step 2: Building project wheel with uv..."
uv build

echo "⬇️ Step 3: Downloading all dependency wheels with pip..."
mkdir -p dist/dependencies
pip download -r requirements.txt -d dist/dependencies

echo "✅ Step 4: Build completed successfully!"
echo ""
echo "Generated files:"
ls dist
