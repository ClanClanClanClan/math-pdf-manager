#!/usr/bin/env python3
"""
Complete Grobid Setup and Integration Script

This script provides multiple options for setting up Grobid:
1. Docker-based setup (recommended)
2. Local JAR download and setup
3. Verify existing installation
4. Test integration with the academic PDF system
"""

import subprocess
import sys
import requests
import zipfile
import os
from pathlib import Path
import time
import shutil


def check_docker():
    """Check if Docker is available"""
    try:
        result = subprocess.run(['docker', '--version'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_java():
    """Check if Java is available"""
    try:
        result = subprocess.run(['java', '-version'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def setup_grobid_docker():
    """Setup Grobid using Docker"""
    print("🐳 Setting up Grobid with Docker...")
    
    if not check_docker():
        print("❌ Docker not available. Please install Docker first.")
        return False
    
    try:
        # Pull Grobid Docker image
        print("📦 Pulling Grobid Docker image...")
        subprocess.run([
            'docker', 'pull', 'lfoppiano/grobid:0.8.2'
        ], check=True)
        
        print("✅ Grobid Docker image ready!")
        print("🚀 To start Grobid server, run:")
        print("   docker run --rm -p 8070:8070 -p 8071:8071 lfoppiano/grobid:0.8.2")
        print("")
        print("Or use the included script:")
        print("   ./tools/grobid/start_grobid_docker.sh")
        
        # Create convenience script
        script_content = """#!/bin/bash
echo "🔬 Starting Grobid server with Docker..."
docker run --rm -p 8070:8070 -p 8071:8071 lfoppiano/grobid:0.8.2
"""
        script_path = Path(__file__).parent / "start_grobid_docker.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        script_path.chmod(0o755)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Docker setup failed: {e}")
        return False


def setup_grobid_local():
    """Setup Grobid locally with JAR download"""
    print("📦 Setting up Grobid locally...")
    
    if not check_java():
        print("❌ Java not available. Please install Java 8+ first.")
        return False
    
    grobid_dir = Path(__file__).parent / "grobid-local"
    grobid_dir.mkdir(exist_ok=True)
    
    try:
        # Download Grobid
        grobid_version = "0.8.2"
        download_url = f"https://github.com/kermitt2/grobid/releases/download/{grobid_version}/grobid-{grobid_version}.zip"
        zip_path = grobid_dir / f"grobid-{grobid_version}.zip"
        
        print(f"📥 Downloading Grobid {grobid_version}...")
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print("📂 Extracting Grobid...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(grobid_dir)
        
        # Make gradlew executable
        gradlew_path = grobid_dir / f"grobid-{grobid_version}" / "gradlew"
        if gradlew_path.exists():
            gradlew_path.chmod(0o755)
        
        # Copy custom config
        config_src = Path(__file__).parent.parent.parent / "config" / "grobid" / "grobid.yaml"
        config_dst = grobid_dir / f"grobid-{grobid_version}" / "grobid-service" / "config" / "grobid.yaml"
        
        if config_src.exists() and config_dst.parent.exists():
            shutil.copy2(config_src, config_dst)
            print("⚙️ Custom configuration installed")
        
        print("✅ Grobid local installation complete!")
        print("🚀 To start Grobid server, run:")
        print(f"   cd {grobid_dir / f'grobid-{grobid_version}'}")
        print("   ./gradlew run")
        
        # Clean up
        zip_path.unlink()
        
        return True
        
    except Exception as e:
        print(f"❌ Local setup failed: {e}")
        return False


def test_grobid_integration():
    """Test Grobid integration with the academic PDF system"""
    print("🧪 Testing Grobid integration...")
    
    # Add src to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
    
    try:
        from core.grobid_client import grobid_client
        
        # Test service availability
        is_available = grobid_client.is_available()
        
        if is_available:
            print("✅ Grobid service is available and responding")
            print(f"🔗 Server: {grobid_client.grobid_server}")
            
            # Test with sample PDF if available
            samples_dir = Path(__file__).parent.parent.parent / "samples" / "papers"
            if samples_dir.exists():
                pdf_files = list(samples_dir.glob("*.pdf"))
                if pdf_files:
                    print(f"📄 Testing with sample PDF: {pdf_files[0].name}")
                    result = grobid_client.process_pdf(pdf_files[0])
                    
                    if result:
                        print("✅ PDF processing successful!")
                        print(f"📝 Title: {result.get('title', 'N/A')[:60]}...")
                        print(f"🎯 Confidence: {result.get('confidence', 0):.2f}")
                    else:
                        print("⚠️ PDF processing returned no results")
        else:
            print("⚠️ Grobid service not available")
            print("💡 Start Grobid server first, then run this test again")
            
        return is_available
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


def main():
    """Main setup interface"""
    print("🔬 GROBID SETUP FOR ACADEMIC PDF MANAGEMENT SYSTEM")
    print("=" * 60)
    
    print("\nChoose setup method:")
    print("1. Docker setup (recommended)")
    print("2. Local JAR setup")
    print("3. Test existing installation")
    print("4. Exit")
    
    while True:
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            if setup_grobid_docker():
                print("\n🎉 Docker setup complete!")
                print("💡 Start the server and run option 3 to test integration")
            break
            
        elif choice == "2":
            if setup_grobid_local():
                print("\n🎉 Local setup complete!")
                print("💡 Start the server and run option 3 to test integration")
            break
            
        elif choice == "3":
            if test_grobid_integration():
                print("\n🎉 Grobid integration working perfectly!")
            else:
                print("\n💡 Setup Grobid first (options 1 or 2)")
            break
            
        elif choice == "4":
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid choice. Please enter 1-4.")


if __name__ == "__main__":
    main()