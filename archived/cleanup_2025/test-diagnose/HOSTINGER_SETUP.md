# Hostinger PostgreSQL Connection Setup

This guide will help you connect your local Flask application to your Hostinger-hosted PostgreSQL database.

## 🎯 What You Need to Configure

### 1. Hostinger Database Information
You'll need to gather these details from your Hostinger control panel:

- **Database Host/IP**: `31.137.137.221` (from your screenshot)
- **Database Port**: Usually `5432`, but may be different
- **Database Name**: Your actual database name on Hostinger
- **Username**: Your PostgreSQL username
- **Password**: Your PostgreSQL password

### 2. Update Configuration
Edit the `config.py` file and update the `HOSTINGER_DB_CONFIG` section:

```python
HOSTINGER_DB_CONFIG = DatabaseConfig(
    host='31.137.137.221',  # Your Hostinger server IP
    port=5432,  # Check your actual port in Hostinger panel
    database='your_actual_db_name',  # Replace with actual database name
    user='your_db_username',  # Replace with actual username
    password='your_db_password'  # Replace with actual password
)
```

## 🔧 Setup Steps

### Step 1: Find Your Database Details
1. Log into your Hostinger control panel
2. Go to **Databases** section
3. Find your PostgreSQL database
4. Note down:
   - Database name
   - Username
   - Host/Server address
   - Port number

### Step 2: Configure Firewall (if needed)
Your Hostinger server may need to allow connections from your local IP:
1. Check if PostgreSQL port is open for external connections
2. Add your local IP to allowed connections if required

### Step 3: Test Connection
Run the connection test:
```bash
python test_connection.py
```

### Step 4: Run Your Application
Once connection is successful, you can run your Flask app with Hostinger database:

**Option A: Using batch file**
```bash
run_hostinger.bat
```

**Option B: Using command line**
```bash
set DB_ENV=hostinger
python web_ui/app.py
```

**Option C: Using PowerShell**
```powershell
$env:DB_ENV="hostinger"
python web_ui/app.py
```

## 🚀 Benefits of This Setup

✅ **Live Data**: Your local development uses real production data
✅ **Easy Switching**: Switch between local and remote databases instantly
✅ **Team Collaboration**: Multiple developers can share the same database
✅ **Backup Safety**: Data is safely stored on Hostinger servers
✅ **Performance Testing**: Test with real data volumes

## 🔄 Switching Between Databases

### Use Local Docker Database:
```bash
run_local.bat
# or
set DB_ENV=local
python web_ui/app.py
```

### Use Hostinger Database:
```bash
run_hostinger.bat
# or
set DB_ENV=hostinger
python web_ui/app.py
```

## 🛠️ Troubleshooting

### Connection Timeout
- Check if Hostinger firewall allows your IP
- Verify the port number (may not be 5432)
- Ensure PostgreSQL service is running on Hostinger

### Authentication Failed
- Double-check username and password
- Verify database name is correct
- Check if user has proper permissions

### Database Not Found
- Confirm database name in Hostinger panel
- Ensure database exists and is accessible

### Network Issues
- Try connecting via SSH tunnel if direct connection fails
- Check your local firewall settings
- Verify internet connection

## 📊 Data Management

### Loading Data to Hostinger
Once connected, you can load your data using:
```bash
# Set environment to use Hostinger
set DB_ENV=hostinger

# Run your data loader
python scripts/new_data_loader.py
```

### Backup Considerations
- Hostinger handles server backups
- Consider periodic data exports for additional safety
- Test restore procedures

## 🔐 Security Notes

- Keep database credentials secure
- Use environment variables for production
- Consider VPN for additional security
- Regularly update passwords
- Monitor database access logs

## 📝 Next Steps

1. Update `config.py` with your actual Hostinger database details
2. Run `python test_connection.py` to verify connection
3. Use `run_hostinger.bat` to start your Flask app with live data
4. Load your data using the data loader scripts
5. Enjoy developing with live data!