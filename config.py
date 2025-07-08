"""
Database configuration for takeoff pricing application
Connects to Hostinger PostgreSQL database only
"""

import os
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class DatabaseConfig:
    """Database configuration class"""
    host: str
    port: int
    database: str
    user: str
    password: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for psycopg2"""
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password
        }
    
    def to_url(self) -> str:
        """Convert to PostgreSQL URL format"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

# Hostinger PostgreSQL Configuration
DB_CONFIG = DatabaseConfig(
    host='31.97.137.221',  # Hostinger server IP
    port=5432,  # PostgreSQL port
    database='takeoff_pricing_db',  # Database name on Hostinger
    user='Jon',  # PostgreSQL username on Hostinger
    password=os.getenv('DB_PASSWORD', 'Transplant4real')  # Use environment variable for password
)

print("🌐 Using Hostinger PostgreSQL database")

# Export for backward compatibility
DB_CONFIG_DICT = DB_CONFIG.to_dict()
