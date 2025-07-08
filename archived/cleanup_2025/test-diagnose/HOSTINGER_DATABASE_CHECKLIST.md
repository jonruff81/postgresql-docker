# Hostinger Database Connection Checklist

## 🔍 What We Discovered
The connection test failed with a timeout, which typically means:
- PostgreSQL port 5432 is not accessible from outside
- Hostinger may use a different port
- Firewall is blocking the connection

## 📋 Action Items for Hostinger Setup

### 1. Find Your Database Connection Details
In your Hostinger control panel, look for:

**Database Section → PostgreSQL → Connection Details**
- **Host**: May be different from server IP (could be `localhost` or internal hostname)
- **Port**: Likely NOT 5432 (common alternatives: 5433, 25432, or custom port)
- **Database Name**: Exact name as created in Hostinger
- **Username**: Database user (may be different from system user)
- **Password**: Database password

### 2. Check These Common Hostinger Configurations

**Option A: Internal Access Only**
- Host: `localhost` or `127.0.0.1`
- Requires SSH tunnel to access externally

**Option B: Custom Port**
- Host: `31.137.137.221` (your server IP)
- Port: Something other than 5432 (check Hostinger panel)

**Option C: Different Hostname**
- Host: `vps865895.hstgr.cloud` (your hostname from screenshot)
- Port: 5432 or custom port

### 3. SSH Tunnel Method (Most Likely Solution)
If PostgreSQL only accepts local connections, you'll need an SSH tunnel:

```bash
# Create SSH tunnel (run this in a separate terminal)
ssh -L 5433:localhost:5432 root@31.137.137.221

# Then connect to localhost:5433 instead of the remote server
```

## 🛠️ Next Steps

### Step 1: SSH into Your Hostinger Server
```bash
ssh root@31.137.137.221
```

### Step 2: Check PostgreSQL Status
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check what port PostgreSQL is using
sudo netstat -tlnp | grep postgres

# Check PostgreSQL configuration
sudo -u postgres psql -c "SHOW port;"
```

### Step 3: Check Database and User
```bash
# Connect to PostgreSQL as postgres user
sudo -u postgres psql

# List databases
\l

# List users
\du

# Check if your database exists
\c takeoff_pricing_db
```

### Step 4: Configure PostgreSQL for External Access (if needed)
```bash
# Edit PostgreSQL config to allow external connections
sudo nano /etc/postgresql/*/main/postgresql.conf
# Change: listen_addresses = 'localhost' to listen_addresses = '*'

# Edit pg_hba.conf to allow your IP
sudo nano /etc/postgresql/*/main/pg_hba.conf
# Add: host all all YOUR_LOCAL_IP/32 md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

## 🔧 Update Your Local Configuration

Once you find the correct connection details, update `config.py`:

```python
HOSTINGER_DB_CONFIG = DatabaseConfig(
    host='31.137.137.221',  # or vps865895.hstgr.cloud
    port=5432,  # or the actual port you find
    database='actual_database_name',  # from \l command
    user='actual_username',  # from \du command
    password='actual_password'  # your database password
)
```

## 🚀 Alternative: SSH Tunnel Configuration

If you prefer SSH tunnel (more secure), create this configuration:

```python
# SSH Tunnel Configuration
HOSTINGER_SSH_TUNNEL_CONFIG = DatabaseConfig(
    host='localhost',  # Connect to local tunnel
    port=5433,  # Local tunnel port
    database='takeoff_pricing_db',
    user='your_db_user',
    password='your_db_password'
)
```

Then create the tunnel:
```bash
ssh -L 5433:localhost:5432 root@31.137.137.221 -N
```

## 📞 Need Help?
1. SSH into your server and run the diagnostic commands above
2. Share the output of the PostgreSQL status and port checks
3. We can then update your configuration with the correct details