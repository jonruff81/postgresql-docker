#!/usr/bin/env python3
"""
Get your local public IP address for firewall configuration
"""

import requests
import socket

def get_public_ip():
    """Get public IP address using multiple services"""
    services = [
        'https://ifconfig.me/ip',
        'https://api.ipify.org',
        'https://ipecho.net/plain',
        'https://myexternalip.com/raw'
    ]
    
    for service in services:
        try:
            response = requests.get(service, timeout=5)
            if response.status_code == 200:
                ip = response.text.strip()
                print(f"✅ Your public IP address: {ip}")
                print(f"🔥 Firewall command: sudo ufw allow from {ip} to any port 5432")
                return ip
        except Exception as e:
            print(f"❌ Failed to get IP from {service}: {e}")
            continue
    
    print("❌ Could not determine public IP address")
    return None

def get_local_ip():
    """Get local network IP address"""
    try:
        # Connect to a remote address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        print(f"🏠 Your local network IP: {local_ip}")
        return local_ip
    except Exception as e:
        print(f"❌ Could not determine local IP: {e}")
        return None

def main():
    print("🌐 IP Address Information for Firewall Configuration")
    print("=" * 60)
    
    public_ip = get_public_ip()
    local_ip = get_local_ip()
    
    print("\n" + "=" * 60)
    print("📋 Firewall Configuration Commands:")
    
    if public_ip:
        print(f"\n🔥 For UFW (Ubuntu Firewall):")
        print(f"   sudo ufw allow from {public_ip} to any port 5432")
        
        print(f"\n🔥 For iptables:")
        print(f"   sudo iptables -A INPUT -p tcp -s {public_ip} --dport 5432 -j ACCEPT")
        
        print(f"\n📝 For pg_hba.conf:")
        print(f"   host    all    all    {public_ip}/32    md5")
    
    print(f"\n💡 Use the PUBLIC IP ({public_ip}) for firewall rules")
    print(f"   The local IP ({local_ip}) is only for your internal network")

if __name__ == "__main__":
    main()