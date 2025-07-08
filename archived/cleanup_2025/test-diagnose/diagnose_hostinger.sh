#!/bin/bash
# Hostinger PostgreSQL Diagnostic Script
# Run this on your Hostinger server via SSH

echo "🔍 PostgreSQL Diagnostic Report"
echo "================================"

echo ""
echo "1️⃣ Checking if PostgreSQL is installed and running..."
if command -v psql &> /dev/null; then
    echo "✅ PostgreSQL is installed"
    
    # Check if service is running
    if systemctl is-active --quiet postgresql; then
        echo "✅ PostgreSQL service is running"
    else
        echo "❌ PostgreSQL service is NOT running"
        echo "💡 Try: sudo systemctl start postgresql"
    fi
else
    echo "❌ PostgreSQL is NOT installed"
    echo "💡 Install with: sudo apt update && sudo apt install postgresql postgresql-contrib"
fi

echo ""
echo "2️⃣ Checking PostgreSQL processes..."
ps aux | grep postgres | grep -v grep
if [ $? -eq 0 ]; then
    echo "✅ PostgreSQL processes found"
else
    echo "❌ No PostgreSQL processes running"
fi

echo ""
echo "3️⃣ Checking what ports are listening..."
echo "All listening ports:"
netstat -tlnp | grep LISTEN
echo ""
echo "PostgreSQL specific ports:"
netstat -tlnp | grep postgres
if [ $? -ne 0 ]; then
    echo "❌ PostgreSQL is not listening on any ports"
fi

echo ""
echo "4️⃣ Checking PostgreSQL configuration..."
if [ -f /etc/postgresql/*/main/postgresql.conf ]; then
    echo "✅ PostgreSQL config found"
    echo "Current listen_addresses setting:"
    grep -n "listen_addresses" /etc/postgresql/*/main/postgresql.conf
    echo ""
    echo "Current port setting:"
    grep -n "^port" /etc/postgresql/*/main/postgresql.conf
else
    echo "❌ PostgreSQL config not found in standard location"
fi

echo ""
echo "5️⃣ Checking if PostgreSQL accepts connections..."
if command -v sudo &> /dev/null; then
    echo "Testing local connection as postgres user:"
    sudo -u postgres psql -c "SELECT version();" 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ Local PostgreSQL connection works"
        echo ""
        echo "Checking databases:"
        sudo -u postgres psql -c "\l"
        echo ""
        echo "Checking users:"
        sudo -u postgres psql -c "\du"
    else
        echo "❌ Local PostgreSQL connection failed"
    fi
fi

echo ""
echo "6️⃣ Checking firewall status..."
if command -v ufw &> /dev/null; then
    echo "UFW status:"
    ufw status
else
    echo "UFW not installed, checking iptables:"
    iptables -L INPUT | grep 5432
fi

echo ""
echo "7️⃣ System information..."
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME)"
echo "PostgreSQL version: $(psql --version 2>/dev/null || echo 'Not found')"

echo ""
echo "🔧 RECOMMENDED ACTIONS:"
echo "======================"

if ! systemctl is-active --quiet postgresql 2>/dev/null; then
    echo "1. Start PostgreSQL: sudo systemctl start postgresql"
    echo "2. Enable PostgreSQL: sudo systemctl enable postgresql"
fi

if ! netstat -tlnp | grep postgres | grep -q ":5432"; then
    echo "3. Configure PostgreSQL to listen on all addresses:"
    echo "   - Edit: sudo nano /etc/postgresql/*/main/postgresql.conf"
    echo "   - Change: listen_addresses = '*'"
    echo "   - Restart: sudo systemctl restart postgresql"
fi

echo "4. Configure authentication:"
echo "   - Edit: sudo nano /etc/postgresql/*/main/pg_hba.conf"
echo "   - Add: host all all 0.0.0.0/0 md5"
echo "   - Restart: sudo systemctl restart postgresql"

echo ""
echo "📋 Quick fix commands:"
echo "sudo systemctl start postgresql"
echo "sudo systemctl enable postgresql"
echo "sudo sed -i \"s/#listen_addresses = 'localhost'/listen_addresses = '*'/g\" /etc/postgresql/*/main/postgresql.conf"
echo "echo 'host all all 0.0.0.0/0 md5' | sudo tee -a /etc/postgresql/*/main/pg_hba.conf"
echo "sudo systemctl restart postgresql"