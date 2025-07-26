#!/usr/bin/env python3
"""
CLI VPN CONNECT
===============

Use Cisco's command line interface instead of GUI automation
"""

import subprocess
import time
import getpass
import sys

def connect_vpn_cli():
    """Connect using Cisco CLI directly"""
    
    print("🔐 CLI VPN CONNECTION")
    print("=" * 40)
    
    # Check if already connected
    try:
        result = subprocess.run(
            ["/opt/cisco/secureclient/bin/vpn", "status"],
            capture_output=True, text=True, timeout=5
        )
        if "state: Connected" in result.stdout:
            print("✅ Already connected!")
            return True
    except:
        pass
    
    print("\n1️⃣ Using Cisco CLI to connect...")
    
    # Try to connect using command line
    try:
        # Connect to ETH VPN
        connect_result = subprocess.run(
            ["/opt/cisco/secureclient/bin/vpn", "connect", "sslvpn.ethz.ch/staff-net"],
            input="\n",  # Send enter for any prompts
            text=True,
            capture_output=True,
            timeout=30
        )
        
        print(f"Connect command output:")
        print(connect_result.stdout)
        if connect_result.stderr:
            print(f"Errors: {connect_result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("⏳ Connection command timed out (this might be normal)")
    except Exception as e:
        print(f"❌ CLI connect error: {e}")
    
    print("\n2️⃣ Monitoring connection status...")
    
    # Monitor for connection
    for i in range(120):
        try:
            status_result = subprocess.run(
                ["/opt/cisco/secureclient/bin/vpn", "status"],
                capture_output=True, text=True, timeout=3
            )
            
            status_output = status_result.stdout
            
            if "state: Connected" in status_output:
                print(f"\n🎉 VPN CONNECTED via CLI!")
                return True
            elif "state: Connecting" in status_output:
                if i % 10 == 0:
                    print(f"   Connecting... {120-i}s remaining")
            elif "Please enter your username and password" in status_output:
                print("🔑 Credentials required - please enter manually")
            
        except Exception as e:
            if i % 20 == 0:
                print(f"   Monitoring... {120-i}s remaining")
        
        time.sleep(1)
    
    print("\n⏸️ CLI connection timeout")
    return False

def fallback_gui_simple():
    """Simple GUI fallback if CLI doesn't work"""
    
    print("\n🖱️ FALLBACK: Simple GUI method")
    print("=" * 40)
    
    # Launch GUI
    print("1️⃣ Opening Cisco GUI...")
    subprocess.run(["open", "-a", "Cisco Secure Client"])
    time.sleep(3)
    
    print("2️⃣ Please manually:")
    print("   - Click Connect in the Cisco window")
    print("   - Enter your credentials")
    print("   - Complete 2FA")
    
    # Monitor for manual connection
    print("\n3️⃣ Waiting for manual connection...")
    
    for i in range(180):  # 3 minutes
        try:
            result = subprocess.run(
                ["/opt/cisco/secureclient/bin/vpn", "status"],
                capture_output=True, text=True, timeout=3
            )
            
            if "state: Connected" in result.stdout:
                print(f"\n✅ VPN Connected manually!")
                return True
                
        except:
            pass
        
        if i % 30 == 0:
            print(f"   Waiting for manual connection... {180-i}s remaining")
        
        time.sleep(1)
    
    return False

def test_vpn_access():
    """Test if VPN access is working"""
    
    print("\n🧪 TESTING VPN ACCESS")
    print("=" * 40)
    
    # Try accessing a Wiley paper that requires institutional access
    test_url = "https://onlinelibrary.wiley.com/doi/10.3982/ECTA20404"
    
    try:
        import requests
        
        response = requests.get(test_url, timeout=10)
        
        if "Full Access" in response.text or "Institution:" in response.text:
            print("✅ VPN access confirmed - can access subscription content!")
            return True
        else:
            print("⚠️ VPN access unclear - may need manual verification")
            return False
            
    except Exception as e:
        print(f"❌ Could not test VPN access: {e}")
        return False

def main():
    """Main robust VPN connection"""
    
    print("🚀 ROBUST VPN CONNECTION")
    print("=" * 60)
    print("Method 1: CLI automation")
    print("Method 2: GUI fallback with manual assistance")
    print("=" * 60)
    
    # Method 1: Try CLI
    print("\n🔧 ATTEMPTING CLI CONNECTION...")
    cli_success = connect_vpn_cli()
    
    if cli_success:
        print("✅ CLI method worked!")
        # Test access
        test_vpn_access()
        return True
    
    # Method 2: GUI fallback
    print("\n🖱️ CLI failed, trying GUI fallback...")
    gui_success = fallback_gui_simple()
    
    if gui_success:
        print("✅ GUI method worked!")
        test_vpn_access()
        return True
    
    print("\n❌ Both methods failed")
    print("💡 Try connecting manually and then run PDF download scripts")
    return False

if __name__ == "__main__":
    main()