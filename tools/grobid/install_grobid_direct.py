#!/usr/bin/env python3
"""
Direct Grobid Installation Script

Uses the most reliable method: cloning the repository and building locally.
"""

import subprocess
import sys
import os
from pathlib import Path
import shutil


def run_command(cmd, cwd=None, timeout=300):
    """Run a command with proper error handling"""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, 
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            print(f"❌ Command failed: {cmd}")
            print(f"Error: {result.stderr}")
            return False
        print(result.stdout)
        return True
    except subprocess.TimeoutExpired:
        print(f"❌ Command timed out: {cmd}")
        return False
    except Exception as e:
        print(f"❌ Command error: {e}")
        return False


def check_java():
    """Check Java availability"""
    return run_command("java -version")


def check_git():
    """Check Git availability"""
    return run_command("git --version")


def install_grobid():
    """Install Grobid by cloning and building"""
    print("🔬 Installing Grobid from source...")
    
    # Check prerequisites
    if not check_java():
        print("❌ Java not available. Please install Java 8+ first.")
        return False
        
    if not check_git():
        print("❌ Git not available. Please install Git first.")
        return False
    
    # Set correct JAVA_HOME for macOS Homebrew OpenJDK
    java_home = "/opt/homebrew/Cellar/openjdk@17/17.0.16/libexec/openjdk.jdk/Contents/Home"
    if os.path.exists(java_home):
        os.environ['JAVA_HOME'] = java_home
        print(f"✅ Set JAVA_HOME to: {java_home}")
    else:
        # Try to find the correct Java installation
        try:
            result = subprocess.run(
                ["/usr/libexec/java_home", "-v", "17"], 
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                java_home = result.stdout.strip()
                os.environ['JAVA_HOME'] = java_home
                print(f"✅ Auto-detected JAVA_HOME: {java_home}")
            else:
                print("⚠️ Could not auto-detect JAVA_HOME, using system default")
        except Exception as e:
            print(f"⚠️ Could not set JAVA_HOME: {e}")
    
    # Create installation directory
    install_dir = Path(__file__).parent / "grobid-installation"
    if install_dir.exists():
        print("🗑️ Removing existing installation...")
        shutil.rmtree(install_dir)
    
    install_dir.mkdir(exist_ok=True)
    
    print("📥 Cloning Grobid repository...")
    if not run_command(
        "git clone https://github.com/kermitt2/grobid.git", 
        cwd=install_dir
    ):
        return False
    
    grobid_dir = install_dir / "grobid"
    
    print("🔧 Building Grobid...")
    print("⏳ This may take several minutes...")
    
    # Build Grobid
    if not run_command("./gradlew clean build", cwd=grobid_dir, timeout=600):
        print("❌ Build failed. Trying alternative build...")
        if not run_command("./gradlew assemble", cwd=grobid_dir, timeout=600):
            return False
    
    print("✅ Grobid built successfully!")
    
    # Copy our configuration
    config_src = Path(__file__).parent.parent.parent / "config" / "grobid" / "grobid.yaml"
    config_dst = grobid_dir / "grobid-service" / "config" / "grobid.yaml"
    
    if config_src.exists() and config_dst.parent.exists():
        shutil.copy2(config_src, config_dst)
        print("⚙️ Custom configuration installed")
    
    # Create startup script
    startup_script = Path(__file__).parent / "start_grobid.sh"
    script_content = f"""#!/bin/bash
echo "🔬 Starting Grobid server..."
cd "{grobid_dir}"
./gradlew run
"""
    
    with open(startup_script, 'w') as f:
        f.write(script_content)
    startup_script.chmod(0o755)
    
    print("🎉 Grobid installation complete!")
    print(f"📁 Installed in: {grobid_dir}")
    print("🚀 To start Grobid server:")
    print(f"   cd {grobid_dir}")
    print("   ./gradlew run")
    print("")
    print("Or use the convenience script:")
    print(f"   {startup_script}")
    print("")
    print("🔗 Server will be available at: http://localhost:8070")
    print("📊 Admin interface: http://localhost:8071")
    
    return True


def test_grobid():
    """Test if Grobid is running"""
    import requests
    try:
        response = requests.get("http://localhost:8070/api/isalive", timeout=5)
        if response.status_code == 200:
            print("✅ Grobid server is running!")
            return True
        else:
            print(f"⚠️ Grobid server responded with status: {response.status_code}")
            return False
    except requests.RequestException:
        print("❌ Grobid server is not running")
        print("💡 Start it with: ./gradlew run (in the grobid directory)")
        return False


if __name__ == "__main__":
    print("🔬 GROBID DIRECT INSTALLATION")
    print("=" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_grobid()
    else:
        install_grobid()