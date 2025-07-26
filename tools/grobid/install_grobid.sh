#!/bin/bash
# Grobid Installation Script for Academic PDF Management System

set -e

GROBID_VERSION="0.8.2"
GROBID_DIR="$(pwd)/tools/grobid"
GROBID_ZIP="${GROBID_DIR}/grobid-${GROBID_VERSION}.zip"
GROBID_EXTRACTED="${GROBID_DIR}/grobid-${GROBID_VERSION}"

echo "🔬 Installing Grobid ${GROBID_VERSION}..."

# Create directory
mkdir -p "${GROBID_DIR}"
cd "${GROBID_DIR}"

# Download Grobid
echo "📦 Downloading Grobid ${GROBID_VERSION}..."
curl -L "https://github.com/kermitt2/grobid/releases/download/${GROBID_VERSION}/grobid-${GROBID_VERSION}.zip" \
     -o "${GROBID_ZIP}"

# Extract
echo "📂 Extracting Grobid..."
unzip -q "${GROBID_ZIP}"

# Make gradlew executable
chmod +x "${GROBID_EXTRACTED}/gradlew"

# Copy our configuration
echo "⚙️ Installing custom configuration..."
cp ../../config/grobid/grobid.yaml "${GROBID_EXTRACTED}/grobid-service/config/"

echo "✅ Grobid installation complete!"
echo ""
echo "🚀 To start Grobid server:"
echo "   cd ${GROBID_EXTRACTED}"
echo "   ./gradlew run"
echo ""
echo "🔗 Server will be available at: http://localhost:8070"
echo "📊 Admin interface: http://localhost:8071"