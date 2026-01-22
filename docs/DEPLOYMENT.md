# Task Scheduling Agent V2 - Deployment Guide

This guide covers deploying the application to:
- **Backend**: Render.com (primary) or College Server (alternative)
- **Frontend**: Vercel with PWA support
- **Database**: MongoDB Atlas (cloud)

## Prerequisites

- Node.js 18+ (for frontend build)
- Python 3.11+ (for backend)
- MongoDB Atlas account
- Firebase project with Authentication enabled
- Groq API key (for AI features)

---

## 1. Database Setup (MongoDB Atlas)

1. Go to [MongoDB Atlas](https://cloud.mongodb.com)
2. Create a new cluster (free tier works)
3. Create a database user with read/write access
4. Whitelist IP addresses:
   - `0.0.0.0/0` for Render (or specific IPs)
   - Your college server IP
5. Get your connection string:
   ```
   mongodb+srv://username:password@cluster.mongodb.net/?appName=TaskScheduler
   ```

---

## 2. Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Create a new project (or use existing)
3. Enable Authentication:
   - Email/Password provider
   - Google Sign-In provider
4. Get your web app config (for frontend)
5. Generate service account key (for backend):
   - Go to Project Settings > Service Accounts
   - Click "Generate new private key"
   - Save as `firebase-credentials.json`
6. For production, encode the credentials:
   ```bash
   # Linux/Mac
   base64 -w 0 firebase-credentials.json

   # Windows PowerShell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("firebase-credentials.json"))
   ```

---

## 3. Backend Deployment (Render.com)

### Option A: Deploy via Dashboard

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New" > "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: task-scheduling-agent-api
   - **Region**: Choose closest to your users
   - **Branch**: main
   - **Root Directory**: backend
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`

5. Add Environment Variables:
   | Key | Value |
   |-----|-------|
   | `MONGODB_URL` | Your MongoDB Atlas connection string |
   | `MONGODB_DB_NAME` | `task_scheduling_agent` |
   | `FIREBASE_CREDENTIALS_BASE64` | Base64 encoded credentials |
   | `SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
   | `ALLOWED_ORIGINS` | `https://your-app.vercel.app` |
   | `DEBUG` | `False` |
   | `GROQ_API_KEY` | Your Groq API key |

6. Click "Create Web Service"

### Option B: Deploy via render.yaml

The repository includes a `render.yaml` file for automated deployment:

1. Go to Render Dashboard
2. Click "New" > "Blueprint"
3. Connect your repository
4. Render will auto-detect `render.yaml`
5. Fill in the environment variables marked as `sync: false`

### Verify Deployment

```bash
curl https://your-backend.onrender.com/health
```

Expected response: `{"status": "ok"}`

---

## 4. Backend Deployment (College Server)

For servers that don't allow containers:

### Quick Install

```bash
# Clone repository
git clone https://github.com/your-repo/Task_Scheduling_Agent_V2.git
cd Task_Scheduling_Agent_V2

# Run installation script
sudo bash deployment/college-server/install.sh
```

### Manual Install

1. **Install dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3.11 python3.11-venv nginx
   ```

2. **Create application directory**:
   ```bash
   sudo mkdir -p /opt/taskagent
   sudo cp -r backend/* /opt/taskagent/
   ```

3. **Set up virtual environment**:
   ```bash
   cd /opt/taskagent
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   sudo cp deployment/college-server/.env.production /opt/taskagent/.env
   sudo nano /opt/taskagent/.env  # Edit with your values
   ```

5. **Set up systemd service**:
   ```bash
   sudo cp deployment/college-server/taskagent.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable taskagent
   sudo systemctl start taskagent
   ```

6. **Configure nginx** (optional but recommended):
   ```bash
   sudo cp deployment/college-server/nginx.conf /etc/nginx/sites-available/taskagent
   sudo ln -s /etc/nginx/sites-available/taskagent /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

### Check Status

```bash
sudo systemctl status taskagent
sudo journalctl -u taskagent -f  # View logs
```

---

## 5. Frontend Deployment (Vercel)

### Deploy via Vercel Dashboard

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click "Add New" > "Project"
3. Import your GitHub repository
4. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: frontend-web
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

5. Add Environment Variables:
   | Key | Value |
   |-----|-------|
   | `VITE_FIREBASE_API_KEY` | Your Firebase API key |
   | `VITE_FIREBASE_AUTH_DOMAIN` | `your-project.firebaseapp.com` |
   | `VITE_FIREBASE_PROJECT_ID` | Your project ID |
   | `VITE_FIREBASE_STORAGE_BUCKET` | `your-project.appspot.com` |
   | `VITE_FIREBASE_MESSAGING_SENDER_ID` | Your sender ID |
   | `VITE_FIREBASE_APP_ID` | Your app ID |
   | `VITE_API_BASE_URL` | `https://your-backend.onrender.com/api` |

6. Click "Deploy"

### Deploy via CLI

```bash
cd frontend-web
npm install -g vercel
vercel login
vercel --prod
```

---

## 6. PWA Configuration

The frontend is configured as a Progressive Web App (PWA):

### Features
- Installable on mobile devices
- Offline support for static assets
- App-like experience

### Required Files (already included)
- `public/manifest.json` - PWA manifest
- `public/sw.js` - Service worker
- `src/registerSW.js` - Service worker registration

### PWA Icons
You need to add these icon files to `frontend-web/public/`:
- `icon-192x192.png` (192x192 pixels)
- `icon-512x512.png` (512x512 pixels)

Generate icons from your logo using [PWA Asset Generator](https://www.pwabuilder.com/imageGenerator).

---

## 7. Post-Deployment Checklist

### Security
- [ ] Rotate all credentials (MongoDB password, SECRET_KEY, API keys)
- [ ] Remove `.env` files from git tracking
- [ ] Configure Firebase security rules
- [ ] Set up HTTPS (Render and Vercel handle this automatically)

### CORS
- [ ] Update `ALLOWED_ORIGINS` with production domains
- [ ] Remove `localhost` entries for production

### Testing
- [ ] Test login/register flow
- [ ] Test task creation and submission
- [ ] Test code evaluation
- [ ] Test PWA installation on mobile

### Monitoring
- [ ] Set up Render health checks
- [ ] Configure error logging
- [ ] Monitor MongoDB Atlas metrics

---

## 8. Environment Variables Reference

### Backend

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGODB_URL` | Yes | MongoDB connection string |
| `MONGODB_DB_NAME` | Yes | Database name |
| `FIREBASE_CREDENTIALS_BASE64` | Yes* | Base64 encoded Firebase credentials |
| `FIREBASE_CREDENTIALS_PATH` | Yes* | Path to Firebase credentials file |
| `SECRET_KEY` | Yes | Application secret key (64+ chars) |
| `ALLOWED_ORIGINS` | Yes | Comma-separated list of allowed origins |
| `DEBUG` | No | Enable debug mode (default: False) |
| `HOST` | No | Server host (default: 0.0.0.0) |
| `PORT` | No | Server port (default: 8000) |
| `GROQ_API_KEY` | Yes | Groq API key for AI features |
| `GROQ_ENABLE_*` | No | Feature flags for Groq |

*Either `FIREBASE_CREDENTIALS_BASE64` or `FIREBASE_CREDENTIALS_PATH` is required.

### Frontend

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_FIREBASE_API_KEY` | Yes | Firebase API key |
| `VITE_FIREBASE_AUTH_DOMAIN` | Yes | Firebase auth domain |
| `VITE_FIREBASE_PROJECT_ID` | Yes | Firebase project ID |
| `VITE_FIREBASE_STORAGE_BUCKET` | Yes | Firebase storage bucket |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | Yes | Firebase sender ID |
| `VITE_FIREBASE_APP_ID` | Yes | Firebase app ID |
| `VITE_API_BASE_URL` | Yes | Backend API URL |

---

## 9. Troubleshooting

### Backend Issues

**"Firebase credentials not found"**
- Ensure `FIREBASE_CREDENTIALS_BASE64` is set correctly
- Check the base64 encoding doesn't have line breaks

**"MongoDB connection failed"**
- Verify MongoDB Atlas IP whitelist includes your server
- Check connection string format

**"CORS error"**
- Add your frontend domain to `ALLOWED_ORIGINS`
- Include both `http://` and `https://` variants if needed

### Frontend Issues

**"API request failed"**
- Check `VITE_API_BASE_URL` points to correct backend
- Verify backend is running and accessible

**"Firebase auth error"**
- Verify Firebase config values are correct
- Check Firebase console for enabled auth providers

### PWA Issues

**"Service worker registration failed"**
- Ensure `sw.js` is in the `public` folder
- Check browser console for errors
- HTTPS is required for service workers (except localhost)

---

## 10. Useful Commands

### Backend

```bash
# Local development
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload

# Run tests
pytest

# Generate secret key
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Frontend

```bash
# Local development
cd frontend-web
npm install
npm run dev

# Production build
npm run build
npm run preview  # Preview production build

# Lint
npm run lint
```

### College Server

```bash
# View logs
sudo journalctl -u taskagent -f

# Restart service
sudo systemctl restart taskagent

# Check nginx config
sudo nginx -t

# View nginx logs
sudo tail -f /var/log/nginx/error.log
```
