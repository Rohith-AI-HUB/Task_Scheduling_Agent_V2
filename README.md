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
│   ├── Procfile               # Render deployment
│   ├── render.yaml            # Render config
│   └── requirements.txt       # Python dependencies
│
├── frontend-web/              # React + Vite Frontend
│   ├── src/
│   │   ├── components/        # Reusable React components
│   │   ├── pages/             # Page-level components
│   │   ├── services/          # API client services
│   │   └── context/           # React Context (Auth, Theme)
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
├── docs/                      # Documentation
│   ├── API.md                 # Complete API reference
│   ├── DATABASE.md            # Database schema
│   └── DEPLOYMENT.md          # Deployment guide
│
└── frontend-mobile/           # Flutter Mobile (Planned)
    └── lib/
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
# Edit .env with your configuration:
#   - MONGODB_URL
#   - FIREBASE_CREDENTIALS (path to JSON file)
#   - GROQ_API_KEY (optional)

# Download Firebase credentials
# 1. Go to Firebase Console > Project Settings > Service Accounts
# 2. Generate new private key
# 3. Save as firebase-credentials.json in backend/

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

# Setup environment variables
# Create .env file with:
#   VITE_API_BASE_URL=http://localhost:8000/api
#   VITE_FIREBASE_CONFIG={"apiKey":"...","authDomain":"..."}

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

## 🚢 Deployment

### Render (Backend)

```bash
# Automatic deployment via render.yaml
git push origin main
```

Configuration: `backend/render.yaml`

### Vercel (Frontend)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd frontend-web
vercel
```

Configuration: `frontend-web/vercel.json`

### College Server (No Containers)

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
**Last Updated**: January 2026

---

*Built with ❤️ for modern education*
