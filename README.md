# SplitEase — Shared Expenses App
Built for Spreetail Software Engineering Intern Assignment

## Live URL
https://spreetail-task.onrender.com

## Tech Stack
- Backend: Django + Django REST Framework
- Frontend: React (Vite)
- Database: PostgreSQL (Supabase)
- Auth: JWT (SimpleJWT)

## Local Setup

### Backend
git clone https://github.com/3456789rashmi/Spreetail_task
cd spreetail-expenses
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        ← fill in your DB credentials
python manage.py migrate
python manage.py runserver

### Frontend
cd frontend
npm install
npm run dev

## AI Tools Used
- GitHub Copilot (code generation)
- Claude by Anthropic (architecture decisions, anomaly analysis)
