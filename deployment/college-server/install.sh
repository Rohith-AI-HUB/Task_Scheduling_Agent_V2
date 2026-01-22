#!/bin/bash
# Task Scheduling Agent V2 - College Server Installation Script
# This script sets up the backend on a college server without containers

set -e

echo "=========================================="
echo "Task Scheduling Agent V2 - Installation"
echo "=========================================="

# Configuration
APP_DIR="/opt/taskagent"
APP_USER="taskagent"
PYTHON_VERSION="3.11"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Check Python version
if ! command -v python$PYTHON_VERSION &> /dev/null; then
    echo "Python $PYTHON_VERSION is required but not installed."
    echo "Please install Python $PYTHON_VERSION first."
    exit 1
fi

echo "[1/7] Creating application user..."
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -s /bin/false $APP_USER
    echo "Created user: $APP_USER"
else
    echo "User $APP_USER already exists"
fi

echo "[2/7] Creating application directory..."
mkdir -p $APP_DIR
chown $APP_USER:$APP_USER $APP_DIR

echo "[3/7] Copying application files..."
# Assuming script is run from repository root
cp -r backend/* $APP_DIR/
chown -R $APP_USER:$APP_USER $APP_DIR

echo "[4/7] Creating virtual environment..."
cd $APP_DIR
python$PYTHON_VERSION -m venv venv
source venv/bin/activate

echo "[5/7] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[6/7] Setting up environment file..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp .env.example .env 2>/dev/null || cat > .env << 'EOF'
# MongoDB
MONGODB_URL=mongodb+srv://your-connection-string
MONGODB_DB_NAME=task_scheduling_agent

# Firebase (base64 encoded credentials)
FIREBASE_CREDENTIALS_BASE64=your-base64-encoded-credentials

# App Settings
APP_NAME=Task Scheduling Agent V2
DEBUG=False
SECRET_KEY=generate-a-64-char-random-string-here

# Server
HOST=0.0.0.0
PORT=8000

# CORS - Add your frontend domains
ALLOWED_ORIGINS=https://your-app.vercel.app

# Groq AI
GROQ_API_KEY=your-groq-api-key
GROQ_ENABLE_ROUTING=true
GROQ_ENABLE_GUARDS=true
GROQ_ENABLE_CACHING=true
EOF
    echo "Created .env file - PLEASE EDIT WITH YOUR CREDENTIALS"
else
    echo ".env file already exists"
fi

echo "[7/7] Creating uploads directory..."
mkdir -p $APP_DIR/uploads
chown -R $APP_USER:$APP_USER $APP_DIR/uploads
chmod 755 $APP_DIR/uploads

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit the .env file with your credentials:"
echo "   sudo nano $APP_DIR/.env"
echo ""
echo "2. Copy the systemd service file:"
echo "   sudo cp deployment/college-server/taskagent.service /etc/systemd/system/"
echo ""
echo "3. Reload systemd and start the service:"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable taskagent"
echo "   sudo systemctl start taskagent"
echo ""
echo "4. Configure nginx (optional but recommended):"
echo "   sudo cp deployment/college-server/nginx.conf /etc/nginx/sites-available/taskagent"
echo "   sudo ln -s /etc/nginx/sites-available/taskagent /etc/nginx/sites-enabled/"
echo "   sudo nginx -t && sudo systemctl reload nginx"
echo ""
echo "5. Check service status:"
echo "   sudo systemctl status taskagent"
echo "   sudo journalctl -u taskagent -f"
echo ""
