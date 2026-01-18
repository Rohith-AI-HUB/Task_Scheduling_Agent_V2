# Task Scheduling Agent - Frontend Web Application

React + Vite frontend for the Task Scheduling Agent V2 classroom management system.

## Features

- 🔐 Firebase Authentication (Email/Password + Google Sign-In)
- 🎨 Modern UI with Tailwind CSS
- 🌙 Dark mode support
- 📱 Responsive design
- 🔄 Role-based routing (Teacher/Student)
- ⚡ Fast development with Vite

## Tech Stack

- **Framework**: React 18
- **Build Tool**: Vite 7
- **Styling**: Tailwind CSS 3
- **Routing**: React Router DOM 6
- **Authentication**: Firebase 11
- **HTTP Client**: Axios
- **Icons**: Material Symbols

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Firebase project (for authentication)
- Backend API running (default: http://localhost:8000)

### Installation

1. Navigate to the frontend directory:
```bash
cd frontend-web
```

2. Install dependencies:
```bash
npm install
```

3. Create environment file:
```bash
cp .env.example .env
```

4. Configure Firebase:
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create a new project or select existing one
   - Go to Project Settings > Your apps
   - Select Web app and copy the configuration
   - Update `.env` with your Firebase credentials

5. Update `.env` file:
```env
VITE_FIREBASE_API_KEY=your-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
VITE_FIREBASE_APP_ID=your-app-id
VITE_API_BASE_URL=http://localhost:8000/api
```

### Development

Run the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

Preview production build:
```bash
npm run preview
```

## Project Structure

```
frontend-web/
├── src/
│   ├── components/        # Reusable React components
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── tasks/
│   │   ├── submissions/
│   │   └── ai-assistant/
│   │
│   ├── pages/            # Page components
│   │   ├── Login.jsx
│   │   ├── Register.jsx
│   │   ├── TeacherDashboard.jsx
│   │   ├── StudentDashboard.jsx
│   │   ├── SubjectView.jsx
│   │   └── TaskView.jsx
│   │
│   ├── services/         # API and auth services
│   │   ├── api.js
│   │   ├── authService.js
│   │   ├── taskService.js
│   │   └── aiService.js
│   │
│   ├── context/          # React Context providers
│   │   └── AuthContext.jsx
│   │
│   ├── config/           # Configuration files
│   │   └── firebase.js
│   │
│   ├── hooks/            # Custom React hooks
│   ├── utils/            # Utility functions
│   ├── App.jsx           # Main app component
│   ├── main.jsx          # Entry point
│   └── index.css         # Global styles
│
├── public/               # Static assets
├── index.html           # HTML template
├── vite.config.js       # Vite configuration
├── tailwind.config.js   # Tailwind configuration
└── package.json         # Dependencies
```

## Authentication Flow

1. **Login**:
   - Email/Password authentication via Firebase
   - Google Sign-In via Firebase popup
   - Backend token verification
   - Role-based dashboard routing

2. **Registration**:
   - Create Firebase user
   - Store user data in backend
   - Automatic role assignment
   - Redirect to appropriate dashboard

3. **Auth State Management**:
   - `AuthContext` provides global auth state
   - Automatic token refresh
   - Auth state persistence

## API Integration

The app uses Axios with interceptors for API calls:

- **Base URL**: Configured via `VITE_API_BASE_URL`
- **Authentication**: Auto-attached Firebase ID token
- **Error Handling**: Global error interceptor

### Example API Call:
```javascript
import api from './services/api';

// GET request (token auto-attached)
const response = await api.get('/tasks');

// POST request
const response = await api.post('/tasks', taskData);
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_FIREBASE_API_KEY` | Firebase API key | `AIzaSy...` |
| `VITE_FIREBASE_AUTH_DOMAIN` | Firebase auth domain | `project.firebaseapp.com` |
| `VITE_FIREBASE_PROJECT_ID` | Firebase project ID | `my-project` |
| `VITE_FIREBASE_STORAGE_BUCKET` | Firebase storage bucket | `project.appspot.com` |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | Firebase messaging sender ID | `1234567890` |
| `VITE_FIREBASE_APP_ID` | Firebase app ID | `1:123:web:abc` |
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:8000/api` |

## Troubleshooting

### Firebase Authentication Errors

**Problem**: "Firebase not initialized"
- **Solution**: Check that `.env` file exists and has correct Firebase config

**Problem**: "Google Sign-In popup blocked"
- **Solution**: Allow popups in browser settings

### API Connection Issues

**Problem**: "Network Error"
- **Solution**: Ensure backend is running and `VITE_API_BASE_URL` is correct

**Problem**: "CORS Error"
- **Solution**: Check backend CORS configuration allows frontend origin

### Build Issues

**Problem**: Tailwind styles not working
- **Solution**: Run `npm install` again to ensure PostCSS and Tailwind are installed

## Firebase Setup Guide

1. Create Firebase project
2. Enable Authentication:
   - Email/Password provider
   - Google provider
3. Add authorized domains in Firebase Console
4. Copy web app configuration to `.env`

## Contributing

1. Create feature branch
2. Make changes
3. Test thoroughly
4. Submit pull request

## License

Academic project - See main README for details
