# iliOS - REA Investment Platform

## Overview
This is a real estate asset investment management platform built with React and TypeScript frontend, and Python FastAPI backend. The application provides user authentication, asset management, due diligence, task management, and reporting features.

## Project Structure
- `frontend/rea-investment-fe/` - React/TypeScript frontend application
  - `src/` - Source code (components, modules, hooks, contexts)
  - `config/` - Webpack and development server configuration
  - `public/` - Static assets
  - `scripts/` - Build and development scripts
- `backend/ilios-server/` - Python FastAPI backend
  - `app/` - Main application code
  - `alembic/` - Database migrations
- `backend/ilios-DocAI/` - AI/ML document processing service
- `docai/` - Document AI processing components

## Development Workflows

### Frontend (Port 5000)
```bash
cd frontend/rea-investment-fe && PORT=5000 npm start
```

### Backend (Port 8000)
```bash
cd backend/ilios-server && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Environment Variables
- **REACT_APP_URL**: Backend API URL for frontend to connect to
- **db_host, db_user, db_password, db_name**: Database connection for development
- Production uses Replit's built-in PostgreSQL (PG* environment variables)

## Test Credentials
- Email: system@user.com
- Password: SystemUser123!

## Tech Stack

### Frontend
- React 18
- TypeScript
- Material UI (MUI)
- React Query (TanStack Query)
- React Router DOM
- AG Grid (tables)
- Chart.js
- Webpack 5

### Backend
- Python 3.11
- FastAPI
- SQLAlchemy
- Alembic (migrations)
- PostgreSQL

## Deployment
Configured as a static deployment for frontend:
1. Runs `npm run build` in the frontend directory
2. Serves the built static files from `frontend/rea-investment-fe/build`

## Notes
- Both frontend and backend are configured and running in this Replit environment
- Frontend connects to the backend API on port 8000

## Recent Features

### Asset Management Overview - Collapsible Drag-and-Drop Cards (Jan 2026)
- **Drag-and-drop reordering**: Cards can be reordered using @dnd-kit library with rectSortingStrategy for grid layouts
- **Collapsible cards**: Each card has a collapse/expand toggle in the header
- **Default state**: Top row (first 3 cards) open by default, others collapsed
- **Persistence**: Card order and collapsed state persist per site using localStorage (key: `overview_cards_{siteId}`)
- **Missing field indicators**: Warning icon (⚠️) appears in card header when required fields are missing
- **Components**: DraggableCardLayout.tsx, Overview.tsx with REQUIRED_FIELDS configuration

## Integration Status
- **Redis**: ✅ Working (Upstash with TLS) - Health check at `/api/internal/health`
- **PostgreSQL**: ✅ Working (Replit built-in)
- **PowerBI**: ✅ Working - Returns reports from workspace
- **Mailgun**: ✅ Configured (US region, domain: iliospower.com)
- **Rombus**: ✅ Configured - Camera/security integration
- **AG Grid**: ✅ Licensed - Enterprise license configured

## Tips
- **Upstash copy/paste**: Always paste URLs to a text editor first to verify completeness. The Upstash console copy function may truncate URLs.
