#!/bin/bash
echo "🔬 Starting Grobid server..."
cd "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts/tools/grobid/grobid-installation/grobid"
export JAVA_HOME="/opt/homebrew/Cellar/openjdk@17/17.0.16/libexec/openjdk.jdk/Contents/Home"
./gradlew run