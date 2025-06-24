# PostgreSQL 15 Docker Setup for Ubuntu 24.04 VPS

Production-grade PostgreSQL 15 container deployment for takeoff pricing database.

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/jonruff81/postgresql-docker.git
cd postgresql-docker

# Make scripts executable
chmod +x start.sh backup.sh

# Start PostgreSQL container
./start.sh
```

## 📋 Features

- **PostgreSQL 15 Alpine** - Lightweight and secure
- **Production Optimized** - Memory limits, connection pooling, performance tuning
- **Security Focused** - Localhost binding only, read-only mounts
- **Auto-Schema Setup** - Database initialization on first run
- **Health Monitoring** - Built-in health checks
- **Logging** - Structured logging with rotation
- **Backup Tools** - Automated backup scripts

## 🐘 Database Configuration

| Setting | Value |
|---------|-------|
| **Image** | `postgres:15-alpine` |
| **Database** | `takeoff_pricing_db` |
| **Username** | `Jon` |
| **Password** | `Transplant4real` |
| **Port** | `5432` (localhost only) |
| **Container** | `takeoff_postgres` |

## 🗂️ Project Structure

```
postgresql-docker/
├── docker-compose.yml      # Main container configuration
├── start.sh               # Bootstrap script
├── backup.sh              # Database backup utility
├── init/
│   └── schema.sql         # Database schema initialization
├── logs/                  # PostgreSQL logs (created on startup)
├── backups/               # Database backups (created when backing up)
└── README.md              # This file
```

## 🛠️ Management Commands

### Start Database
```bash
./start.sh
```

### Connect to Database
```bash
# Via Docker
docker exec -it takeoff_postgres psql -U Jon -d takeoff_pricing_db

# Via psql (if installed locally)
psql -h 127.0.0.1 -p 5432 -U Jon -d takeoff_pricing_db
```

### View Logs
```bash
# Container logs
docker-compose logs -f

# PostgreSQL logs
tail -f logs/postgresql-$(date +%Y-%m-%d).log
```

### Backup Database
```bash
./backup.sh
```

### Stop Database
```bash
docker-compose down
```

### Complete Cleanup (⚠️ Destroys data)
```bash
docker-compose down -v
docker system prune -f
```

## 🗄️ Database Schema

The database includes these main components:

### Schemas
- `pricing` - Main business logic tables
- `audit` - Change tracking and logging

### Tables
- `pricing.products` - Product catalog
- `pricing.price_rules` - Pricing logic and rules
- `pricing.takeoff_calculations` - Calculation results
- `audit.activity_log` - Change audit trail

### Users
- `Jon` - Database owner (admin access)
- `app_user` - Application user (limited access)

## 🔒 Security Features

- **Network Isolation** - Custom bridge network
- **Port Binding** - Localhost only (127.0.0.1:5432)
- **Resource Limits** - Memory and CPU constraints
- **Read-only Mounts** - Init scripts mounted read-only
- **User Separation** - Dedicated application user

## 📊 Monitoring & Health Checks

- **Health Check** - Every 30 seconds
- **Performance Monitoring** - pg_stat_statements enabled
- **Log Rotation** - Daily rotation, 100MB size limit
- **Resource Monitoring** - Docker stats available

## 🚨 Troubleshooting

### Container Won't Start
```bash
# Check Docker status
docker info

# View container logs
docker-compose logs

# Check system resources
docker system df
```

### Connection Issues
```bash
# Verify container is running
docker ps | grep takeoff_postgres

# Test connection
docker exec takeoff_postgres pg_isready -U Jon -d takeoff_pricing_db

# Check port binding
netstat -tulpn | grep :5432
```

### Performance Issues
```bash
# Check resource usage
docker stats takeoff_postgres

# View slow queries
docker exec -it takeoff_postgres psql -U Jon -d takeoff_pricing_db -c "SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

## 🔧 Customization

### Environment Variables
Copy `.env.example` to `.env` and modify as needed:
```bash
cp .env.example .env
nano .env
```

### Performance Tuning
Modify `docker-compose.yml` command section for your VPS specs:
- `shared_buffers` - 25% of RAM
- `effective_cache_size` - 75% of RAM
- `max_connections` - Based on your application needs

### Schema Changes
Edit `init/schema.sql` and restart container:
```bash
docker-compose down -v  # ⚠️ This destroys data
./start.sh
```

## 📝 Production Deployment Notes

### For Ubuntu 24.04 VPS:
1. Ensure Docker and Docker Compose are installed
2. Configure firewall (UFW) to block external PostgreSQL access
3. Set up automated backups via cron
4. Monitor disk space for logs and backups
5. Consider setting up SSL certificates for remote connections

### Recommended VPS Specs:
- **Minimum:** 2 CPU cores, 4GB RAM, 20GB SSD
- **Recommended:** 4 CPU cores, 8GB RAM, 50GB SSD

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review container logs: `docker-compose logs`
3. Create an issue in this repository

---

**Made for Ubuntu 24.04 Hostinger VPS** 🐧
