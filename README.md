# CrimeMind AI

An AI-powered Investigation Copilot designed to assist law enforcement agencies (such as the Karnataka Police) in analyzing First Information Reports (FIRs), extracting crucial entity relationships, finding similar historical crime cases, and query parsing under secure guardrails.

---

## 🏛️ Project Architecture

CrimeMind AI consists of a decoupled frontend and backend:

* **Frontend**: Next.js (TypeScript) application providing a rich, dark-themed responsive dashboard for FIR document management, copilot chat, and investigation analysis.
* **Backend**: FastAPI (Python) service that manages database auditing, vector similarity indexing, and routes incoming traffic through security guardrails.

```
CrimeMind/
├── app/                  # Next.js Frontend pages, components and hooks
├── backend/              # FastAPI Python Backend
│   ├── app/              # FastAPI core services, APIs, and integrations
│   │   ├── integrations/ # External integrations (Enkrypt AI, Qdrant Cloud)
│   │   ├── mastra/       # Mastra workflow orchestrations
│   │   └── main.py       # API entry point
│   ├── docs/             # Technical architecture guides
│   ├── requirements.txt  # Python package dependencies
│   └── alembic/          # Database migration configurations
├── package.json          # Frontend dependencies
└── README.md             # Project documentation
```

---

## 🚀 Core AI Integrations

CrimeMind AI leverages three state-of-the-art AI systems to deliver secure, semantic-aware insights:

1. **Mastra**: Orchestrates workflow states for the copilot query engine (e.g., retrieving FIR text, parsing extracted entities, querying similar cases, and generating responses).
2. **Qdrant Cloud**: A high-performance vector database used to store and query dense semantic embeddings (using Google Gemini's `text-embedding-004` model) for finding similar criminal records.
3. **Enkrypt AI**: Real-time AI security guardrails protecting LLM endpoints against prompt injections, toxicity, data exfiltration, and custom safety policy violations.

For in-depth details about the AI integrations, refer to the [AI Integration Guide](backend/docs/ai_integration.md).

---

## 🛠️ Getting Started

### 1. Prerequisite Configuration

#### Backend Setup (.env)
Create a `.env` file under the `backend/` directory by copying `.env.example`:
```bash
cd backend/
cp .env.example .env
```
Ensure you configure the following variables:
* **Database**: `DATABASE_URL` (PostgreSQL connection string).
* **Gemini**: `GEMINI_API_KEY` (Gemini API token).
* **Qdrant Cloud**: `QDRANT_URL` and `QDRANT_API_KEY`.
* **Enkrypt AI**: `ENKRYPT_API_KEY` and `ENKRYPT_ENABLED=true`.

#### Frontend Setup (.env.local)
Create a `.env.local` file under the project root:
```bash
cp .env.example .env.local
```
Configure `NEXT_PUBLIC_API_URL` to point to the backend server (default: `http://localhost:8000`).

---

### 2. Backend Installation & Run
1. Create and activate a Python virtual environment:
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run database migrations:
   ```bash
   alembic upgrade head
   ```
4. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
The backend docs will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

### 3. Frontend Installation & Run
1. From the project root, install Node dependencies:
   ```bash
   npm install
   ```
2. Start the development server:
   ```bash
   npm run dev
   ```
Open [http://localhost:3000](http://localhost:3000) in your browser to view the application dashboard.

---

## 🔒 Security Audit Logs
Every user query sent to the AI Copilot is audited by the Enkrypt Guardrail system. Violations (e.g. prompt injection, jailbreaks, crime policy violations) are automatically blocked with a `400 Bad Request` before reaching the LLM and logged in the PostgreSQL `guardrail_logs` table for administrative review.
