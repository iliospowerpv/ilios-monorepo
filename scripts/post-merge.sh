#!/bin/bash
set -e

cd backend/ilios-server && alembic upgrade head

cd /home/runner/workspace/frontend/rea-investment-fe && npm install --legacy-peer-deps
