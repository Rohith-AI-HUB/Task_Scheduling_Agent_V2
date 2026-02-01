# Task Scheduling Agent V2

> **AI-Enhanced Classroom Management System**

A production-ready intelligent classroom management platform that combines traditional task management with cutting-edge AI-powered features for scheduling, grouping, evaluation, and student support.

![Version](https://img.shields.io/badge/version-2.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![React](https://img.shields.io/badge/react-18+-blue.svg)
![License](https://img.shields.io/badge/license-Academic-orange.svg)

---

## 🎯 Overview

Task Scheduling Agent V2 is a comprehensive classroom management system designed for modern educational environments. It empowers teachers to efficiently manage coursework while providing students with AI-driven insights to optimize their learning journey.

### Key Highlights

- 🤖 **AI-Powered Scheduling** - Intelligent task prioritization based on deadlines, workload, and student patterns
- 💬 **Chat Assistant** - Task-focused AI chatbot with daily credit system (25 msgs/day for students, 50 for teachers)
- ⏰ **Extension Requests** - AI workload analysis for fair deadline extension decisions
- 👥 **Smart Grouping** - Automated fair group formation with balanced distribution
- 🔬 **Auto-Evaluation** - Sandboxed code execution and document analysis with AI feedback
- 📊 **Real-time Dashboards** - Comprehensive analytics for teachers and students
- 🌙 **Dark Mode** - Beautiful, accessible UI with dark mode support
- 📱 **PWA Ready** - Progressive Web App for mobile installation

---

## ✨ Features

### For Teachers

| Feature | Description |
|---------|-------------|
| **Multi-Subject Management** | Create and manage multiple classrooms with unique join codes |
| **Task Creation** | Code, document, and group tasks with flexible evaluation criteria |
| **Extension Review** | AI-assisted workload analysis for extension request decisions |
| **Auto-Evaluation** | Automatic code testing and document analysis with AI feedback |
| **Group Formation** | AI-powered fair grouping with random problem distribution |
| **Analytics Dashboard** | Real-time insights into student performance and engagement |
| **AI Chat Assistant** | 50 messages/day for task management support |

### For Students

| Feature | Description |
|---------|-------------|
| **AI Task Scheduler** | Personalized task prioritization with explanations |
| **Extension Requests** | Request deadline extensions with automatic workload analysis |
| **Code Submission** | Submit code with automatic testing and AI feedback |
| **Document Submission** | Upload documents with plagiarism detection and quality analysis |
| **Group Collaboration** | View group assignments and submit collaborative work |
| **AI Chat Assistant** | 25 messages/day for help with tasks and deadlines |
| **Calendar View** | Visualize all deadlines and upcoming tasks |

---

## 🏗️ Architecture

```
Task_Scheduling_Agent_V2/
├── backend/                    # FastAPI Backend (Python 3.11+)
│   ├── app/
│   │   ├── api/               # REST API endpoints
│   │   ├── models/            # Pydantic data models
│   │   ├── services/          # Business logic layer
│   │   ├── ai/                # AI engine (scheduler, evaluator, grouping)
│   │   ├── database/          # MongoDB connection & indexes
│   │   └── utils/             # Helper functions
│   ├── tests/                 # Unit and integration tests
│   ├── uploads/               # File upload storage
│   ├── Procfile               # Render deployment
│   ├── render.yaml            # Render config
│   └── requirements.txt       # Python dependencies
│
├── frontend-web/              # React + Vite Frontend (PWA)
│   ├── src/
│   │   ├── components/        # Reusable React components
│   │   ├── pages/             # Page-level components
│   │   ├── services/          # API client services
│   │   ├── context/           # React Context (Auth, Theme)
│   │   ├── hooks/             # Custom React hooks
│   │   └── utils/             # Utility functions
│   ├── public/
│   │   ├── manifest.json      # PWA manifest
│   │   └── sw.js              # Service worker
│   └── vercel.json            # Vercel deployment config
│
├── deployment/                # Deployment configurations
│   └── college-server/        # Non-container deployment scripts
│       ├── install.sh
│       ├── taskagent.service
│       └── nginx.conf
│
└── docs/                      # Documentation
    ├── API.md                 # Complete API reference
    ├── DATABASE.md            # Database schema
    └── DEPLOYMENT.md          # Deployment guide
```

---

## 🛠️ Tech Stack

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- **Database**: [MongoDB](https://www.mongodb.com/) - Document database (Atlas or local)
- **Authentication**: [Firebase Auth](https://firebase.google.com/docs/auth) - Secure user authentication
- **AI Engine**: [Groq API](https://groq.com/) - Fast AI inference with Llama 3.1
- **Code Sandbox**: Docker containers for secure code execution
- **Testing**: Pytest with coverage reporting

### Frontend
- **Framework**: [React 18](https://react.dev/) - Component-based UI
- **Build Tool**: [Vite](https://vitejs.dev/) - Lightning-fast dev server
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS
- **HTTP Client**: [Axios](https://axios-http.com/) - Promise-based HTTP client
- **State**: React Context API - Built-in state management
- **PWA**: Service Workers + Web Manifest

### Infrastructure
- **Backend Hosting**: [Render](https://render.com/) or College Server (systemd + nginx)
- **Frontend Hosting**: [Vercel](https://vercel.com/) - Edge network deployment
- **Database**: [MongoDB Atlas](https://www.mongodb.com/atlas) - Managed cloud database
- **Authentication**: Firebase Authentication

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- MongoDB (Atlas account or local installation)
- Firebase project with Authentication enabled
- Groq API key (optional, for AI features)

### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
Edit .env with your configuration:
  - MONGODB_URL
  - FIREBASE_CREDENTIALS (path to JSON file)
  - GROQ_API_KEY (optional)

Download Firebase credentials
1. Go to Firebase Console > Project Settings > Service Accounts
2. Generate new private key
3. Save as firebase-credentials.json in backend/

# Run the server
uvicorn app.main:app --reload
```

Backend runs at: **http://localhost:8000**
API docs at: **http://localhost:8000/docs**

### 2. Frontend Setup

```bash
# Navigate to frontend
cd frontend-web

# Install dependencies
npm install

Setup environment variables
Create .env file with:
VITE_API_BASE_URL=http://localhost:8000/api
VITE_FIREBASE_CONFIG={"apiKey":"...","authDomain":"..."}

# Run development server
npm run dev
```

Frontend runs at: **http://localhost:5173**

### 3. First-Time Setup

1. **Create a teacher account**: Register via the web app with a teacher email
2. **Update user role**: In MongoDB, set `role: "teacher"` in the users collection
3. **Create a classroom**: Use the teacher dashboard to create your first subject
4. **Get join code**: Share the generated join code with students
5. **Students join**: Students register and use the join code to enroll

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [API Documentation](./docs/API.md) | Complete REST API reference with examples |
| [Database Schema](./docs/DATABASE.md) | MongoDB collections and indexes |
| [Deployment Guide](./docs/DEPLOYMENT.md) | Step-by-step deployment instructions |

---

## 🎨 Features Deep Dive

### AI Task Scheduler

Intelligent task prioritization using a multi-factor algorithm:

- **Urgency Score**: Based on deadline proximity
- **Importance Score**: Based on point value
- **Balance Score**: Workload distribution across subjects
- **AI Explanations**: Groq-powered reasoning for each priority ranking

**Example Output:**
```
1. Data Structures Assignment (92% priority)
   → Urgent due to deadline in 2 days and high point value (100 pts)

2. Essay Draft (65% priority)
   → Moderate priority with 7 days remaining, balanced with workload
```

### Extension Request System

AI-powered deadline extension analysis:

1. **Student submits request** with reason
2. **System analyzes workload**:
   - Current pending tasks
   - Overdue assignments
   - Recent submission patterns
   - Total points at stake
3. **AI generates recommendation**:
   - Approve/Deny/Partial
   - Workload score (0-1)
   - Detailed reasoning
   - Suggested extension days
4. **Teacher reviews** with full context
5. **One-click approval** updates deadline automatically

### Code Evaluation

Secure, sandboxed code execution with comprehensive feedback:

- **Supported Languages**: Python, JavaScript, Java, C++, C
- **Test Cases**: Input/output validation with custom test cases
- **Security**: Docker containerization with resource limits
- **AI Feedback**: Groq-powered code quality analysis
- **Metrics**: Pass rate, execution time, security warnings

### Document Analysis

Multi-dimensional document evaluation:

- **Word Count & Keywords**: Requirement validation
- **Readability Metrics**: Flesch Reading Ease, Grade Level
- **Plagiarism Detection**: Similarity scoring with existing submissions
- **Structure Analysis**: Organization and flow assessment
- **AI Quality Review**: Groq-powered content analysis with improvement suggestions

### Chat Assistant

Task-focused AI chatbot with credit system:

- **Intent Classification**: Automatic categorization of queries
- **Context-Aware**: Accesses user's tasks, submissions, and schedule
- **Credit System**: 25/day (students), 50/day (teachers)
- **Rate Limited**: 10 messages/minute to prevent abuse
- **Fallback Handling**: Graceful degradation if AI unavailable

---

## 🔐 Security Features

- ✅ **Firebase Authentication** - Industry-standard OAuth 2.0
- ✅ **Role-Based Access Control** - Strict teacher/student permissions
- ✅ **Sandboxed Execution** - Docker containers for code evaluation
- ✅ **Input Validation** - Pydantic models with strict typing
- ✅ **Rate Limiting** - API abuse prevention
- ✅ **MongoDB Injection Prevention** - Parameterized queries
- ✅ **CORS Configuration** - Controlled origin access
- ✅ **Secure File Uploads** - Type and size validation

---

## 📊 API Rate Limits

| Feature | Limit | Window | Applies To |
|---------|-------|--------|------------|
| Chat Messages (Daily) | 25 (students) / 50 (teachers) | 24 hours | Per user |
| Chat Messages (Burst) | 10 | 1 minute | Per user |
| Code Evaluation | 20 | 1 hour | Per user |
| Document Analysis | 20 | 1 hour | Per user |
| Schedule Generation | 60 | 1 hour | Per user (cached) |
| Extension Analysis | 30 | 1 hour | System-wide |

---

## 🚢 Backend Deployment on Render (Step-by-Step)

### Prerequisites

Before deploying, ensure you have:
- A GitHub account with this repository
- A [Render](https://render.com) account (free tier works)
- A [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) account
- A [Firebase](https://console.firebase.google.com) project
- A [Groq API](https://console.groq.com) key (optional, for AI features)

---

### Step 1: Set Up MongoDB Atlas

1. **Create a MongoDB Atlas Account**
   - Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register)
   - Sign up for a free account

2. **Create a New Cluster**
   - Click "Build a Database"
   - Select **M0 FREE** tier
   - Choose a cloud provider and region (preferably close to your users)
   - Click "Create Cluster"

3. **Create Database User**
   - Go to **Database Access** in the left sidebar
   - Click "Add New Database User"
   - Choose **Password** authentication
   - Username: `taskagent` (or your choice)
   - Password: Generate a strong password and save it
   - Database User Privileges: **Read and write to any database**
   - Click "Add User"

4. **Configure Network Access**
   - Go to **Network Access** in the left sidebar
   - Click "Add IP Address"
   - Click "Allow Access from Anywhere" (for Render deployment)
   - This adds `0.0.0.0/0` to the whitelist
   - Click "Confirm"

5. **Get Connection String**
   - Go to **Database** in the left sidebar
   - Click "Connect" on your cluster
   - Choose "Connect your application"
   - Copy the connection string:
     ```
     mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority&appName=TaskScheduler
     ```
   - Replace `<username>` and `<password>` with your database user credentials
   - Save this for later use

---

### Step 2: Set Up Firebase Authentication

1. **Create Firebase Project**
   - Go to [Firebase Console](https://console.firebase.google.com)
   - Click "Add project"
   - Enter project name: `task-scheduling-agent` (or your choice)
   - Disable Google Analytics (optional)
   - Click "Create project"

2. **Enable Authentication**
   - In your Firebase project, go to **Authentication** in the left sidebar
   - Click "Get started"
   - Enable **Email/Password** sign-in method
   - Enable **Google** sign-in method (optional)

3. **Get Firebase Web Config** (for frontend later)
   - Go to **Project Settings** (gear icon) > "General"
   - Scroll to "Your apps"
   - Click the web icon `</>`
   - Register app name: `task-scheduling-web`
   - Copy the config object (you'll need this for frontend)

4. **Generate Service Account Key** (for backend)
   - In **Project Settings**, go to the "Service accounts" tab
   - Click "Generate new private key"
   - Click "Generate key"
   - Save the downloaded JSON file as `firebase-credentials.json`

5. **Encode Firebase Credentials for Render**

   **On Windows (PowerShell):**
   ```powershell
   $bytes = [System.IO.File]::ReadAllBytes("firebase-credentials.json")
   $base64 = [System.Convert]::ToBase64String($bytes)
   $base64 | Set-Clipboard
   ```

   **On Mac/Linux:**
   ```bash
   base64 -w 0 firebase-credentials.json | pbcopy  # Mac
   base64 -w 0 firebase-credentials.json | xclip -selection clipboard  # Linux
   ```

   The base64-encoded string is now in your clipboard. Save it in a text file for the next step.

---

### Step 3: Get Groq API Key (Optional - for AI Features)

1. **Create Groq Account**
   - Go to [Groq Console](https://console.groq.com)
   - Sign up for a free account

2. **Generate API Key**
   - Go to "API Keys" section
   - Click "Create API Key"
   - Name it: `task-scheduling-agent`
   - Copy and save the API key securely
   - **Note**: Free tier includes 30 requests/minute and 14,400 requests/day

---

### Step 4: Deploy Backend to Render

#### Option A: Deploy via Render Blueprint (Recommended)

1. **Push to GitHub**
   - Ensure your code is pushed to GitHub
   ```bash
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin main
   ```

2. **Create New Blueprint**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New" → "Blueprint"
   - Click "Connect a repository"
   - Authorize Render to access your GitHub account
   - Select your repository: `Task_Scheduling_Agent_V2`

3. **Configure Blueprint**
   - Render will auto-detect `backend/render.yaml`
   - Service name: `task-scheduling-agent-api`
   - Click "Apply"

4. **Set Environment Variables**

   Render will prompt you to fill in these required variables:

   | Variable | Value | Description |
   |----------|-------|-------------|
   | `MONGODB_URL` | `mongodb+srv://...` | Your MongoDB Atlas connection string from Step 1 |
   | `FIREBASE_CREDENTIALS_BASE64` | `eyJ0eXBlIjoi...` | Base64-encoded Firebase credentials from Step 2 |
   | `ALLOWED_ORIGINS` | `https://your-app.vercel.app` | Your frontend URL (update after frontend deployment) |
   | `GROQ_API_KEY` | `gsk_...` | Your Groq API key from Step 3 (optional) |

   **Note**: `SECRET_KEY` and `MONGODB_DB_NAME` are auto-configured in `render.yaml`

5. **Deploy**
   - Click "Apply" to start deployment
   - Render will:
     - Install Python dependencies
     - Start the Gunicorn server
     - Run health checks
   - Wait 3-5 minutes for deployment to complete

6. **Get Backend URL**
   - Once deployed, copy your backend URL:
     ```
     https://task-scheduling-agent-api.onrender.com
     ```
   - Save this for frontend configuration

---

#### Option B: Deploy via Render Dashboard (Manual)

1. **Create Web Service**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New" → "Web Service"
   - Connect your GitHub repository

2. **Configure Service**
   - **Name**: `task-scheduling-agent-api`
   - **Region**: Choose closest to your users (e.g., Oregon USA, Frankfurt EU)
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`

3. **Add Environment Variables**

   Click "Advanced" → "Add Environment Variable" and add each:

   | Key | Value |
   |-----|-------|
   | `PYTHON_VERSION` | `3.11.7` |
   | `MONGODB_URL` | Your MongoDB connection string |
   | `MONGODB_DB_NAME` | `task_scheduling_agent` |
   | `FIREBASE_CREDENTIALS_BASE64` | Your base64-encoded Firebase credentials |
   | `SECRET_KEY` | Generate using: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
   | `ALLOWED_ORIGINS` | `https://your-app.vercel.app` (update later) |
   | `DEBUG` | `False` |
   | `GROQ_API_KEY` | Your Groq API key (optional) |
   | `GROQ_ENABLE_ROUTING` | `true` |
   | `GROQ_ENABLE_GUARDS` | `true` |
   | `GROQ_ENABLE_CACHING` | `true` |

4. **Create Web Service**
   - Click "Create Web Service"
   - Wait for deployment (3-5 minutes)

---

### Step 5: Verify Deployment

1. **Check Health Endpoint**
   ```bash
   curl https://your-backend-url.onrender.com/health
   ```

   Expected response:
   ```json
   {"status": "ok"}
   ```

2. **Check API Documentation**
   - Open in browser: `https://your-backend-url.onrender.com/docs`
   - You should see the FastAPI interactive documentation (Swagger UI)

3. **Check Render Logs**
   - In Render Dashboard, go to your service
   - Click "Logs" tab
   - Look for:
     ```
     Application startup complete
     MongoDB connected successfully
     ```

---

### Step 6: Configure Auto-Deploy (Optional)

1. **Enable Auto-Deploy**
   - In Render Dashboard, go to your service
   - Go to "Settings" tab
   - Scroll to "Auto-Deploy"
   - Enable "Auto-Deploy: Yes"
   - Every push to `main` branch will trigger automatic deployment

---

### Step 7: Update CORS Settings

1. **After Frontend Deployment**
   - Once you deploy the frontend to Vercel (next step), you'll get a URL like:
     ```
     https://task-scheduling-agent.vercel.app
     ```

2. **Update ALLOWED_ORIGINS**
   - Go to Render Dashboard → Your service → "Environment"
   - Edit `ALLOWED_ORIGINS` variable:
     ```
     https://task-scheduling-agent.vercel.app,https://www.your-custom-domain.com
     ```
   - Save changes (service will auto-redeploy)

---

### Troubleshooting

**Issue: Deployment fails with "Module not found"**
- Solution: Ensure `requirements.txt` is in the `backend/` directory
- Check Render logs for the specific missing module

**Issue: "Firebase credentials not found"**
- Solution: Verify `FIREBASE_CREDENTIALS_BASE64` has no line breaks
- Re-encode the JSON file ensuring no newlines: `base64 -w 0 firebase-credentials.json`

**Issue: "MongoDB connection timeout"**
- Solution: Check Network Access in MongoDB Atlas
- Ensure `0.0.0.0/0` is in the IP whitelist

**Issue: "Health check failed"**
- Solution: Check Render logs for errors
- Verify MongoDB connection string is correct
- Ensure `/health` endpoint returns 200 status

**Issue: "CORS error when accessing from frontend"**
- Solution: Update `ALLOWED_ORIGINS` with your frontend URL
- Include both `http://` and `https://` if testing locally

---

### Next Steps

After successful backend deployment:

1. **Deploy Frontend to Vercel** - See [Frontend Deployment Guide](#frontend-deployment-on-vercel)
2. **Test Authentication** - Create a teacher account and verify login
3. **Update Documentation** - See complete [DEPLOYMENT.md](./docs/DEPLOYMENT.md) for advanced configuration

---

## Frontend Deployment on Vercel

**Coming soon** - Deploy the React frontend to Vercel with PWA support.

See [DEPLOYMENT.md](./docs/DEPLOYMENT.md) for complete frontend deployment instructions.

---

## Alternative Deployment Options

### College Server (No Containers)

For servers that don't allow containers:

```bash
# Run installation script
sudo ./deployment/college-server/install.sh

# Service automatically starts via systemd
sudo systemctl status taskagent
```

See [DEPLOYMENT.md](./docs/DEPLOYMENT.md) for detailed instructions.

---

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests (if configured)
cd frontend-web
npm test
```

---

## 🌟 Credits & Acknowledgments

### AI Services
- **Groq**: Fast AI inference with Llama 3.1 models
- **Firebase**: Authentication and user management

### Technologies
- **FastAPI**: Modern Python web framework
- **React**: Component-based UI library
- **MongoDB**: Flexible document database
- **Tailwind CSS**: Utility-first styling

---

## 📈 Project Status

**Status**: ✅ **Production Ready**

All core features implemented and tested:
- ✅ Authentication & Authorization
- ✅ Multi-subject classroom management
- ✅ Task creation & submission
- ✅ AI-powered evaluation
- ✅ Smart grouping
- ✅ Extension requests
- ✅ AI chat assistant
- ✅ Real-time dashboards
- ✅ PWA support
- ✅ Deployment configurations

---

## 📝 License

This project is developed for academic purposes.

---

## 👤 Author

**Rohith B**
Developer & Architect

---

## 🤝 Contributing

This is an academic project. For suggestions or issues, please contact the author.

---

**Version**: 2.0
**Last Updated**: February 2026

---

*Built with ❤️ for modern education*
