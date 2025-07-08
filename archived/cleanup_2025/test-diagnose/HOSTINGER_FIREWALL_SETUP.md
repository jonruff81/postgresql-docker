# Hostinger Firewall Configuration for PostgreSQL Access

## 🔥 Firewall Setup Steps

### Step 1: SSH into Your Hostinger Server
```bash
ssh root@31.137.137.221
```

### Step 2: Check Current Firewall Status
```bash
# Check if UFW (Ubuntu Firewall) is active
sudo ufw status

# Check if iptables is being used
sudo iptables -L

# Check what's listening on PostgreSQL port
sudo netstat -tlnp | grep 5432
```

### Step 3: Configure UFW Firewall (Most Common)

**Option A: Allow PostgreSQL from Your Specific IP (Recommended)**
```bash
# Get your local IP address first
curl ifconfig.me

# Allow PostgreSQL from your specific IP (replace YOUR_IP with actual IP)
sudo ufw allow from YOUR_IP to any port 5432

# Example: sudo ufw allow from 123.456.789.012 to any port 5432
```

**Option B: Allow PostgreSQL from Any IP (Less Secure)**
```bash
# Allow PostgreSQL from anywhere (use with caution)
sudo ufw allow 5432
```

**Enable UFW if not already enabled:**
```bash
sudo ufw enable
```

**Check UFW status:**
```bash
sudo ufw status verbose
```

### Step 4: Configure iptables (Alternative Method)

If your server uses iptables instead of UFW:

```bash
# Allow PostgreSQL from your specific IP
sudo iptables -A INPUT -p tcp -s YOUR_IP --dport 5432 -j ACCEPT

# Save iptables rules (Ubuntu/Debian)
sudo iptables-save > /etc/iptables/rules.v4

# Or for CentOS/RHEL
sudo service iptables save
```

### Step 5: Configure PostgreSQL to Accept External Connections

**Edit PostgreSQL configuration:**
```bash
# Find PostgreSQL version and config location
sudo -u postgres psql -c "SHOW config_file;"

# Edit postgresql.conf (replace XX with your PostgreSQL version)
sudo nano /etc/postgresql/XX/main/postgresql.conf

# Find and change this line:
# FROM: #listen_addresses = 'localhost'
# TO:   listen_addresses = '*'
```

**Edit PostgreSQL host-based authentication:**
```bash
# Edit pg_hba.conf
sudo nano /etc/postgresql/XX/main/pg_hba.conf

# Add this line at the end (replace YOUR_IP with your actual IP):
host    all             all             YOUR_IP/32              md5

# Or to allow from any IP (less secure):
host    all             all             0.0.0.0/0               md5
```

**Restart PostgreSQL:**
```bash
sudo systemctl restart postgresql
```

### Step 6: Test the Connection

From your local machine, test the connection:
```bash
python test_connection.py
```

## 🛡️ Security Best Practices

### 1. Use Specific IP Restrictions
Always restrict access to your specific IP address rather than allowing all IPs:
```bash
# Good - specific IP
sudo ufw allow from 123.456.789.012 to any port 5432

# Bad - any IP
sudo ufw allow 5432
```

### 2. Use Strong Database Passwords
```bash
# Connect to PostgreSQL and change password
sudo -u postgres psql
ALTER USER Jon WITH PASSWORD 'your_very_strong_password_here';
```

### 3. Create a Dedicated Database User
```bash
# Create a user specifically for your application
sudo -u postgres psql
CREATE USER takeoff_app WITH PASSWORD 'strong_password';
GRANT ALL PRIVILEGES ON DATABASE takeoff_pricing_db TO takeoff_app;
```

### 4. Consider SSH Tunnel (Most Secure Option)
Instead of opening PostgreSQL port, use SSH tunnel:

**On your local machine:**
```bash
# Create SSH tunnel (keeps PostgreSQL port closed)
ssh -L 5433:localhost:5432 root@31.137.137.221 -N
```

**Update your config.py for SSH tunnel:**
```python
HOSTINGER_SSH_TUNNEL_CONFIG = DatabaseConfig(
    host='localhost',  # Connect through tunnel
    port=5433,         # Local tunnel port
    database='takeoff_pricing_db',
    user='Jon',
    password='Transplant4real'
)
```

## 🔍 Troubleshooting Commands

### Check if PostgreSQL is Running
```bash
sudo systemctl status postgresql
sudo systemctl start postgresql  # if not running
```

### Check PostgreSQL Logs
```bash
sudo tail -f /var/log/postgresql/postgresql-XX-main.log
```

### Test Local PostgreSQL Connection
```bash
# Test from the server itself
sudo -u postgres psql -h localhost -p 5432 -d takeoff_pricing_db -U Jon
```

### Check Open Ports
```bash
# See what ports are open
sudo netstat -tlnp
sudo ss -tlnp
```

### Verify Firewall Rules
```bash
# UFW status
sudo ufw status numbered

# iptables rules
sudo iptables -L -n --line-numbers
```

## 🚨 Common Issues and Solutions

### Issue 1: Connection Timeout
**Cause:** Firewall blocking the connection
**Solution:** Follow firewall configuration steps above

### Issue 2: Connection Refused
**Cause:** PostgreSQL not configured for external connections
**Solution:** Edit postgresql.conf and pg_hba.conf as shown above

### Issue 3: Authentication Failed
**Cause:** Wrong username/password or pg_hba.conf misconfiguration
**Solution:** Check credentials and pg_hba.conf settings

### Issue 4: Database Not Found
**Cause:** Database doesn't exist or wrong name
**Solution:** 
```bash
sudo -u postgres psql
\l  # List all databases
```

## 📋 Quick Setup Checklist

- [ ] SSH into Hostinger server
- [ ] Check current firewall status
- [ ] Allow PostgreSQL port (5432) from your IP
- [ ] Edit postgresql.conf (listen_addresses = '*')
- [ ] Edit pg_hba.conf (add your IP)
- [ ] Restart PostgreSQL service
- [ ] Test connection from local machine
- [ ] Update config.py with correct credentials

## 🔄 Alternative: Hostinger Control Panel

Some Hostinger plans have a web-based firewall control:
1. Log into Hostinger control panel
2. Go to **VPS Management** or **Server Settings**
3. Look for **Firewall** or **Security** section
4. Add rule: Allow TCP port 5432 from your IP address

Run these commands and let me know the output - I can help you configure the specific firewall setup for your server!