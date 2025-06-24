#!/bin/bash
# File Optimizer Agent Setup Script

set -e

echo "🔧 Setting up File Optimizer Background Agent..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python $PYTHON_VERSION detected"

# Install required packages
echo "📦 Installing required Python packages..."
pip3 install watchdog || {
    echo "🔄 Trying with --user flag..."
    pip3 install --user watchdog
}

# Make scripts executable
chmod +x file-optimizer-agent.py
chmod +x setup-optimizer.sh

# Create default configuration
if [ ! -f "optimizer-config.json" ]; then
    echo "⚙️ Creating default configuration..."
    cat > optimizer-config.json << 'EOF'
{
  "similarity_threshold": 0.7,
  "auto_merge": false,
  "backup_before_merge": true,
  "ignore_patterns": [
    ".git",
    "__pycache__",
    "*.pyc",
    "node_modules",
    ".vscode",
    "*.log"
  ],
  "file_types_to_monitor": [
    ".py",
    ".sh",
    ".js",
    ".ts",
    ".yml",
    ".yaml",
    ".json",
    ".md",
    ".txt",
    ".conf"
  ],
  "command_patterns": [
    "docker\\s+compose\\s+\\w+",
    "docker\\s+\\w+",
    "git\\s+\\w+",
    "npm\\s+\\w+",
    "pip\\s+install",
    "chmod\\s+\\+x",
    "systemctl\\s+\\w+",
    "service\\s+\\w+",
    "apt\\s+install",
    "yum\\s+install"
  ]
}
EOF
    echo "✅ Created optimizer-config.json"
fi

# Create systemd service for background operation (optional)
if command -v systemctl &> /dev/null && [ "$EUID" -eq 0 ]; then
    echo "🔧 Creating systemd service..."
    WORK_DIR=$(pwd)
    cat > /etc/systemd/system/file-optimizer.service << EOF
[Unit]
Description=File Optimizer Background Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$WORK_DIR
ExecStart=/usr/bin/python3 $WORK_DIR/file-optimizer-agent.py --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    echo "✅ Systemd service created. Enable with: systemctl enable file-optimizer"
fi

echo ""
echo "🎉 File Optimizer Agent setup complete!"
echo ""
echo "📖 Usage Examples:"
echo "  # One-time scan and report:"
echo "  ./file-optimizer-agent.py --report"
echo ""
echo "  # Create consolidated script:"
echo "  ./file-optimizer-agent.py --consolidate"
echo ""
echo "  # Run as background daemon:"
echo "  ./file-optimizer-agent.py --daemon"
echo ""
echo "  # Monitor specific directory:"
echo "  ./file-optimizer-agent.py --watch-dir /path/to/project --daemon"
echo ""
echo "📁 Files created:"
echo "  - file-optimizer-agent.py (main agent)"
echo "  - optimizer-config.json (configuration)"
echo "  - setup-optimizer.sh (this setup script)"
echo ""
echo "📊 Run './file-optimizer-agent.py --report' to get started!" 