# iliOS - REA Investment Platform

## Overview
This is a real estate asset investment management platform frontend built with React and TypeScript. The application provides user authentication, asset management, due diligence, task management, and reporting features.

## Project Structure
- `frontend/rea-investment-fe/` - React/TypeScript frontend application
  - `src/` - Source code (components, modules, hooks, contexts)
  - `config/` - Webpack and development server configuration
  - `public/` - Static assets
  - `scripts/` - Build and development scripts
- `backend/` - Backend services (not configured in Replit)
  - `ilios-server/` - Python FastAPI backend with Alembic migrations
  - `ilios-DocAI/` - AI/ML document processing service
- `docai/` - Document AI processing components

## Development
The frontend runs on port 5000 using webpack-dev-server. Start with:
```bash
cd frontend/rea-investment-fe && PORT=5000 npm start
```

## Deployment
Configured as a static deployment. The build process:
1. Runs `npm run build` in the frontend directory
2. Serves the built static files from `frontend/rea-investment-fe/build`

## Tech Stack
- React 18
- TypeScript
- Material UI (MUI)
- React Query (TanStack Query)
- React Router DOM
- AG Grid (tables)
- Chart.js
- Webpack 5

## Notes
- The backend (ilios-server) is a separate Python FastAPI application not currently set up in this Replit environment
- The frontend connects to an external API backend for data
