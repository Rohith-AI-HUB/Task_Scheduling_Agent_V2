# Task Scheduling Agent V2

> AI-Enhanced Classroom Management System

An intelligent classroom management platform that combines traditional task management with AI-powered features for scheduling, grouping, and evaluation.

## Features

- **Multi-Subject Support**: Teachers manage multiple subjects, students view all tasks in one place
- **AI Task Scheduler**: Intelligent prioritization based on deadlines, workload, and student patterns
- **Smart Grouping**: AI-assisted fair group formation with random problem distribution
- **Auto-Evaluation**: Sandboxed code execution and document analysis
- **Extension System**: Deadline extension requests with AI workload analysis
- **AI Assistant**: Rule-based conversational helper for task management

## Project Structure

```
task-scheduling-agent/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── models/      # Pydantic models
│   │   ├── database/    # MongoDB connection
│   │   ├── ai/          # AI engine components
│   │   ├── services/    # Business logic
│   │   └── utils/       # Helpers
│   └── tests/           # Unit tests
│
├── frontend-web/        # React + Vite web app
│   └── src/
│       ├── components/  # React components
│       ├── pages/       # Page components
│       └── services/    # API calls
│
├── frontend-mobile/     # Flutter mobile app (future)
│   └── lib/
│
└── docs/               # Documentation
    ├── API.md
    ├── DATABASE.md
    └── DEPLOYMENT.md
```

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: MongoDB (Atlas or Local)
- **Authentication**: Firebase Auth
- **Testing**: Pytest

### Frontend
- **Web**: React + Vite
- **Mobile**: Flutter (planned)
- **State Management**: React Context / Provider
- **HTTP Client**: Axios / HTTP package

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB (local or Atlas)
- Firebase project (for authentication)

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Add Firebase credentials:
- Download `firebase-credentials.json` from Firebase Console
- Place it in the backend directory

6. Run the server:
```bash
uvicorn app.main:app --reload
```

Backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend-web
```

2. Install dependencies:
```bash
npm install
```

3. Run development server:
```bash
npm run dev
```

Frontend will be available at `http://localhost:5173`

## Development Phases

- [x] Project setup and folder structure
- [ ] Phase 1: Foundation & Authentication (Weeks 1-2)
- [ ] Phase 2: Core Classroom (Weeks 3-4)
- [ ] Phase 3: AI Task Scheduler (Week 5)
- [ ] Phase 4: Group Tasks & AI Grouping (Week 6)
- [ ] Phase 5: AI Evaluation Engine (Week 7)
- [ ] Phase 6: Extension System (Week 8)
- [ ] Phase 7: AI Assistant (Week 9)
- [ ] Phase 8: Polish & Testing (Week 10)

## Documentation

- [API Documentation](./docs/API.md)
- [Database Schema](./docs/DATABASE.md)
- [Deployment Guide](./docs/DEPLOYMENT.md)
- [Complete Implementation Plan](./Task_Scheduling_Agent_V2.md)

## Key Design Decisions

### Why No External LLMs?
- **Transparency**: All AI logic is explainable through deterministic rules
- **Compliance**: No dependency on external paid services
- **Control**: Full control over data and decision-making process

### Why MongoDB?
- Flexible schema for evolving features
- Easy handling of nested data structures
- Simple migration path

### Why Firebase Auth?
- Industry-standard security
- No custom authentication vulnerabilities
- Easy role-based access control

## License

This project is developed as part of an academic curriculum.

## Contributors

- Rohit (Developer)

---

*Version: 2.0*
*Last Updated: 2026-01-18*
