# LinguaVoice — AI-Powered Language Learning + SQL Lecture Assistant

A monorepo containing two integrated applications:

## 📁 Repository Structure

```
lingua-voice/
├── lms/          # Flask-based Language Learning LMS
│   ├── app.py                 # Main Flask application (52+ routes)
│   ├── templates/             # 24 HTML templates
│   ├── static/                # CSS, JS, images
│   ├── dictionaries/          # Hindi & Spanish dictionaries
│   ├── requirements.txt
│   └── Dockerfile
│
├── rag/          # FastAPI-based RAG system for SQL lectures
│   ├── app/                   # Modular FastAPI package
│   ├── main.py                # Standalone entry point
│   ├── frontend/              # Next.js 15 TypeScript UI
│   ├── requirements.txt
│   ├── docker-compose.yml
│   └── deploy/                # AWS/Azure deployment scripts
│
├── .gitignore
└── README.md
```

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (Port 3000/8001)              │
│  ┌─────────────────┐    ┌────────────────────────────┐  │
│  │  Flask LMS       │    │  Next.js Frontend (RAG)   │  │
│  │  (Port 8001)     │    │  (Port 3000)              │  │
│  └────────┬────────┘    └─────────────┬──────────────┘  │
│           │                           │                  │
│           ▼                           ▼                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │             FastAPI RAG Backend                   │   │
│  │             (Port 8000)                           │   │
│  │  POST /ask    → RAG + Ollama                      │   │
│  │  POST /speak  → Edge-TTS                          │   │
│  │  GET  /health → Status                            │   │
│  └──────────────────────┬───────────────────────────┘   │
│                          │                               │
│       ┌──────────────────┼──────────────────┐           │
│       ▼                  ▼                  ▼           │
│  ┌─────────┐     ┌──────────────┐     ┌──────────┐     │
│  │ Qdrant  │     │ Ollama       │     │ Edge-TTS │     │
│  │ VectorDB│     │ LLM (qwen2.5)│     │ TTS      │     │
│  └─────────┘     └──────────────┘     └──────────┘     │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Setup Instructions

### Prerequisites

- Python 3.12+
- Node.js 20+ (for RAG frontend)
- Docker (optional, for Qdrant + Ollama)

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/lingua-voice.git
cd lingua-voice
```

### 2. Start the LMS (Flask)

```bash
cd lms
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
python run_app.py
# → http://localhost:8001
```

### 3. Start the RAG Backend (FastAPI)

```bash
cd rag
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
copy .env.example .env    # Configure environment
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# → http://localhost:8000
```

### 4. Start Ollama (Required for RAG)

```bash
# Download and install Ollama from https://ollama.ai
ollama pull qwen2.5:0.5b
ollama serve
```

### 5. Start the RAG Frontend (Optional)

```bash
cd rag/frontend
npm install
npm run dev
# → http://localhost:3000
```

### 6. Populate Qdrant (First-time setup)

```bash
cd rag
python qdrant_setup.py
```

## 🧪 Running SQL Training

1. Ensure both Flask (8001) and FastAPI (8000) are running
2. Open http://localhost:8001 in Chrome/Edge
3. Log in or sign up
4. Navigate to **SQL Training** from the sidebar
5. Tap the microphone or type a SQL question
6. Click **Ask SQL Assistant** — answer appears with sources
7. Audio answer plays automatically via Edge-TTS

## 🐳 Docker Deployment

```bash
cd rag
docker-compose up -d
```

## 📡 API Reference

### FastAPI Endpoints (Port 8000)

| Method | Route       | Description              |
|--------|-------------|--------------------------|
| GET    | `/`         | App info                 |
| GET    | `/health`   | Health check + status    |
| POST   | `/ask`      | Ask a SQL question       |
| POST   | `/speak`    | Text-to-speech playback  |
| GET    | `/docs`     | Swagger UI               |

### Flask Routes (Port 8001)

Full LMS with authentication, transcription, AI tutor, vocabulary, quizzes, analytics, and SQL training.

## 🤝 Contributing

### Branch Strategy

```
main          → Production-ready code
├── develop   → Integration branch
│   ├── feature/sql-training     → SQL training improvements
│   ├── feature/rag-improvements → RAG pipeline enhancements
│   └── feature/lms-ui           → LMS frontend updates
```

### Workflow

1. Create a feature branch from `develop`
2. Make changes and test locally
3. Submit a pull request to `develop`
4. After review, merge to `main` for release

## 📝 Team Onboarding

1. **Clone repo** — `git clone https://github.com/YOUR_USERNAME/lingua-voice.git`
2. **Install LMS** — `cd lms && pip install -r requirements.txt`
3. **Install RAG** — `cd rag && pip install -r requirements.txt`
4. **Install Ollama** — https://ollama.ai — pull `qwen2.5:0.5b`
5. **Start servers** — Flask on 8001, FastAPI on 8000
6. **Test** — Visit http://localhost:8001 → SQL Training → ask a question
