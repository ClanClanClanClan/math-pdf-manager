#!/usr/bin/env python3
"""
SETUP AUTO VPN
==============

One-time setup to enable automatic ETH VPN connection.
After this setup, everything will be fully automated.
"""

import subprocess
import time
import sys
from pathlib import Path

def check_cisco_client():
    """Check if Cisco client is available"""
    cisco_path = "/opt/cisco/secureclient/bin/vpn"
    
    if not Path(cisco_path).exists():
        print("❌ Cisco Secure Client not found")
        print("💡 Please install Cisco Secure Client first")
        return False
    
    print("✅ Cisco Secure Client found")
    return True

def test_vpn_status():
    """Test current VPN status"""
    cisco_path = "/opt/cisco/secureclient/bin/vpn"
    
    try:
        result = subprocess.run([cisco_path, "status"], 
                              capture_output=True, text=True, timeout=10)
        
        print("🔍 Current VPN Status:")
        print(result.stdout)
        
        if "state: Connected" in result.stdout:
            print("✅ VPN already connected!")
            return True
        else:
            print("❌ VPN not connected")
            return False
            
    except Exception as e:
        print(f"❌ VPN status check failed: {e}")
        return False

def setup_vpn_profile():
    """Guide user through VPN profile setup"""
    cisco_path = "/opt/cisco/secureclient/bin/vpn"
    
    print("\n🔧 VPN PROFILE SETUP")
    print("=" * 40)
    print("I'll help you set up the VPN profile for automatic connection.")
    print("This requires your ETH credentials and 2FA - you'll only do this ONCE.")
    
    input("\nPress Enter when ready to proceed...")
    
    try:
        print("\n🔄 Connecting to ETH VPN...")
        print("Please complete the following when prompted:")
        print("1. Enter your ETH username")
        print("2. Enter your ETH password") 
        print("3. Complete 2FA authentication")
        print("4. When asked about saving/remembering - choose YES")
        
        # Run interactive connection
        result = subprocess.run([cisco_path, "connect", "vpn.ethz.ch"], 
                              timeout=120)
        
        if result.returncode == 0:
            print("✅ VPN connection attempt completed")
        else:
            print("⚠️ VPN connection may need manual completion")
        
        # Wait a moment then check status
        time.sleep(5)
        
        if test_vpn_status():
            print("🎉 VPN CONNECTION SUCCESSFUL!")
            print("✅ Profile should now be saved for automatic connection")
            return True
        else:
            print("❌ VPN connection failed")
            print("💡 Please try connecting manually through Cisco Secure Client GUI")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Connection timed out")
        print("💡 Please complete the connection manually if still in progress")
        return test_vpn_status()
    except Exception as e:
        print(f"❌ VPN setup failed: {e}")
        return False

def test_auto_reconnection():
    """Test if VPN can reconnect automatically"""
    cisco_path = "/opt/cisco/secureclient/bin/vpn"
    
    print("\n🧪 TESTING AUTO-RECONNECTION")
    print("=" * 40)
    
    try:
        # Disconnect
        print("1. Disconnecting VPN...")
        subprocess.run([cisco_path, "disconnect"], 
                      capture_output=True, timeout=10)
        time.sleep(3)
        
        # Reconnect
        print("2. Attempting automatic reconnection...")
        result = subprocess.run([cisco_path, "connect", "vpn.ethz.ch"], 
                              capture_output=True, text=True, timeout=30)
        
        time.sleep(5)
        
        if test_vpn_status():
            print("🎉 AUTO-RECONNECTION WORKS!")
            print("✅ VPN can now connect automatically")
            return True
        else:
            print("❌ Auto-reconnection failed")
            print("💡 May need to save credentials in Cisco client settings")
            return False
            
    except Exception as e:
        print(f"❌ Auto-reconnection test failed: {e}")
        return False

def create_auto_vpn_manager():
    """Create the automatic VPN manager"""
    
    manager_code = '''#!/usr/bin/env python3
"""
AUTO VPN MANAGER
================

Automatically manages ETH VPN connection for Wiley downloads.
"""

import subprocess
import time
import asyncio

class AutoVPNManager:
    """Automatic VPN connection manager"""
    
    def __init__(self):
        self.cisco_path = "/opt/cisco/secureclient/bin/vpn"
        self.connected = False
    
    def check_connection(self):
        """Check if VPN is connected"""
        try:
            result = subprocess.run([self.cisco_path, "status"], 
                                  capture_output=True, text=True, timeout=10)
            
            if "state: Connected" in result.stdout:
                self.connected = True
                return True
            else:
                self.connected = False
                return False
        except:
            self.connected = False
            return False
    
    def ensure_connection(self):
        """Ensure VPN is connected"""
        if self.check_connection():
            print("✅ VPN already connected")
            return True
        
        print("🔄 Connecting VPN...")
        try:
            result = subprocess.run([self.cisco_path, "connect", "vpn.ethz.ch"], 
                                  capture_output=True, text=True, timeout=30)
            
            # Wait for connection
            for i in range(10):
                time.sleep(2)
                if self.check_connection():
                    print("✅ VPN connected successfully")
                    return True
            
            print("❌ VPN connection failed")
            return False
            
        except Exception as e:
            print(f"❌ VPN connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect VPN"""
        try:
            subprocess.run([self.cisco_path, "disconnect"], 
                          capture_output=True, timeout=10)
            self.connected = False
            print("✅ VPN disconnected")
        except:
            pass

# Global VPN manager instance
vpn_manager = AutoVPNManager()
'''
    
    manager_path = Path("auto_vpn_manager.py")
    with open(manager_path, 'w') as f:
        f.write(manager_code)
    
    print(f"✅ Created automatic VPN manager: {manager_path}")

def main():
    """Main setup function"""
    
    print("🔧 ETH VPN AUTO-CONNECTION SETUP")
    print("=" * 60)
    print("This will set up automatic VPN connection for Wiley downloads.")
    print("You'll need to enter credentials ONCE, then everything is automated.")
    print("=" * 60)
    
    # Check prerequisites
    if not check_cisco_client():
        return False
    
    # Check current status
    if test_vpn_status():
        print("✅ VPN already connected - testing auto-reconnection...")
        if test_auto_reconnection():
            print("🎉 SETUP COMPLETE - VPN auto-connection ready!")
            create_auto_vpn_manager()
            return True
    
    # Set up VPN profile
    if setup_vpn_profile():
        print("✅ VPN profile set up successfully")
        
        # Test auto-reconnection
        if test_auto_reconnection():
            print("🎉 SETUP COMPLETE!")
            print("✅ VPN will now connect automatically for downloads")
            create_auto_vpn_manager()
            return True
        else:
            print("⚠️ Manual connection works, but auto-reconnection needs work")
            print("💡 Downloads will work but may need manual VPN connection")
            create_auto_vpn_manager()
            return True
    else:
        print("❌ VPN setup failed")
        print("💡 Please set up VPN connection manually in Cisco Secure Client")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print(f"\n🎯 READY FOR AUTOMATIC WILEY DOWNLOADS!")
        print(f"Run the main download script - VPN will connect automatically")
    else:
        print(f"\n💥 Setup incomplete - manual VPN connection may be needed")