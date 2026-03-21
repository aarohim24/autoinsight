# AutoInsight — Complete Setup Guide for VS Code
# From zero to running app, step by step.

===================================================
PART 1 — INSTALL THE PREREQUISITES (do this once)
===================================================

STEP 1: Install Python 3.12
─────────────────────────────
  → Go to https://www.python.org/downloads/
  → Download Python 3.12.x (the latest 3.12 version)
  → Run the installer
  → ✅ IMPORTANT: On the first screen, check the box that says
       "Add Python to PATH" before clicking Install Now

  Verify it worked — open a terminal and type:
    python --version
  You should see: Python 3.12.x


STEP 2: Install VS Code
─────────────────────────────
  → Go to https://code.visualstudio.com/
  → Download and install for your OS


STEP 3: Install VS Code Extensions
─────────────────────────────
  Open VS Code, press Ctrl+Shift+X (Extensions panel), search and install:
  
  → "Python"          (by Microsoft)  — required
  → "Pylance"         (by Microsoft)  — recommended
  → "Thunder Client"  (by Rangav)     — useful for testing API endpoints


STEP 4: Install Redis
─────────────────────────────
  Redis is used as the session store. Pick ONE option:

  OPTION A — Docker (easiest, recommended):
    → Install Docker Desktop from https://www.docker.com/products/docker-desktop/
    → Start Docker Desktop
    → You'll start Redis with one command later (Step 10)

  OPTION B — Windows (no Docker):
    → Download from https://github.com/microsoftproject/redis/releases
    → Run the .msi installer
    → Redis will run as a Windows service automatically

  OPTION C — Mac (no Docker):
    → Install Homebrew first: https://brew.sh
    → Then run:  brew install redis
    → Start it:  brew services start redis

  OPTION D — Skip Redis entirely (simplest):
    → AutoInsight works WITHOUT Redis — it falls back to in-memory storage
    → This means data is lost if the server restarts, and won't work with
       multiple workers — fine for local development and portfolio demos


===================================================
PART 2 — GET YOUR ANTHROPIC API KEY
===================================================

STEP 5: Create an Anthropic account and get your API key
─────────────────────────────
  → Go to https://console.anthropic.com/
  → Sign up / log in
  → Click "API Keys" in the left sidebar
  → Click "Create Key"
  → Copy the key — it starts with "sk-ant-..."
  → Save it somewhere safe — you only see it once

  ⚠️  Keep this key private. Never commit it to GitHub.


===================================================
PART 3 — SET UP THE PROJECT IN VS CODE
===================================================

STEP 6: Download the project files
─────────────────────────────
  You have two options:

  OPTION A — From Claude (you already have the files):
    → Download all the output files from this conversation
    → Create a folder called "autoinsight" on your computer
      e.g. C:\Users\YourName\Projects\autoinsight   (Windows)
           /Users/YourName/Projects/autoinsight      (Mac/Linux)
    → Place all the downloaded files inside, matching this structure:

        autoinsight/
        ├── backend/
        │   ├── __init__.py
        │   ├── main.py
        │   ├── modules/
        │   │   ├── __init__.py
        │   │   ├── cache.py
        │   │   ├── data_processor.py
        │   │   ├── llm_engine.py
        │   │   └── session_store.py
        │   └── routes/
        │       ├── __init__.py
        │       └── api.py
        ├── frontend/
        │   └── app.py
        ├── tests/
        │   ├── conftest.py
        │   ├── test_api_routes.py
        │   ├── test_cache.py
        │   ├── test_data_processor.py
        │   ├── test_llm_engine.py
        │   └── test_session_store.py
        ├── sample_data/
        │   └── sample_sales.csv
        ├── .env.example
        ├── .gitignore
        ├── docker-compose.yml
        ├── Dockerfile
        ├── pytest.ini
        └── requirements.txt

  OPTION B — From GitHub (if you pushed it):
    → Open a terminal, navigate to your Projects folder
    → Run: git clone https://github.com/YOUR_USERNAME/autoinsight.git


STEP 7: Open the project in VS Code
─────────────────────────────
  → Open VS Code
  → Click File → Open Folder
  → Select your "autoinsight" folder
  → Click "Select Folder" / "Open"

  You should see all the files in the Explorer panel on the left.


STEP 8: Open the integrated terminal
─────────────────────────────
  → Press Ctrl+` (backtick) to open the terminal inside VS Code
  → OR go to Terminal → New Terminal from the menu bar

  Make sure you're in the right folder. You should see something like:
    C:\Users\YourName\Projects\autoinsight>    (Windows)
    /Users/YourName/Projects/autoinsight $     (Mac/Linux)

  If not, type:  cd path/to/your/autoinsight


STEP 9: Create a virtual environment
─────────────────────────────
  A virtual environment keeps this project's packages separate from other projects.

  In the VS Code terminal, run:

    Windows:
      python -m venv venv
      venv\Scripts\activate

    Mac/Linux:
      python3 -m venv venv
      source venv/bin/activate

  ✅ You'll know it's active when you see "(venv)" at the start of your terminal line:
    (venv) C:\Users\YourName\Projects\autoinsight>

  VS Code may show a popup asking "Do you want to use this environment?" — click Yes.


STEP 10: Install all dependencies
─────────────────────────────
  With your venv active, run:

    pip install -r requirements.txt

  This installs everything — FastAPI, Streamlit, pandas, Redis, etc.
  It will take 1-2 minutes. You'll see packages downloading.

  ✅ When finished, you should see "Successfully installed ..."


===================================================
PART 4 — CONFIGURE ENVIRONMENT VARIABLES
===================================================

STEP 11: Create your .env file
─────────────────────────────
  → In VS Code, find ".env.example" in the file explorer
  → Right-click it → click "Copy"
  → Right-click the root folder → Paste
  → Rename the copy from ".env.example" to ".env"

  OR in the terminal:
    Windows:  copy .env.example .env
    Mac/Linux: cp .env.example .env

  → Now open ".env" in VS Code
  → Replace the placeholder with your real Anthropic API key:

    BEFORE:  ANTHROPIC_API_KEY=sk-ant-your-key-here
    AFTER:   ANTHROPIC_API_KEY=sk-ant-api03-abc123...  ← your real key

  → Save the file (Ctrl+S)

  ⚠️  The .gitignore already excludes .env — it will NOT be uploaded to GitHub.


===================================================
PART 5 — RUN THE APP
===================================================

You need THREE terminal windows running simultaneously:
  Terminal 1 → Redis (skip if not installed)
  Terminal 2 → FastAPI backend
  Terminal 3 → Streamlit frontend

─────────────────────────────
TERMINAL 1: Start Redis
─────────────────────────────
  In VS Code, open a new terminal (click the + icon in the terminal panel).

  If using Docker:
    docker run -d -p 6379:6379 --name autoinsight-redis redis:7-alpine

  If using Homebrew (Mac):
    brew services start redis

  If skipping Redis: nothing to do — the app uses memory automatically.

─────────────────────────────
TERMINAL 2: Start the FastAPI backend
─────────────────────────────
  Open another new terminal (click + again). Make sure venv is active.
  
  Windows (load .env and start server):
    set ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

  Mac/Linux:
    export $(cat .env | grep -v '#' | xargs)
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

  ✅ You should see:
    {"event": "startup_complete", ...}
    INFO:     Uvicorn running on http://0.0.0.0:8000

  → Open your browser and go to: http://localhost:8000/docs
    You'll see the interactive API documentation. This confirms the backend works.

─────────────────────────────
TERMINAL 3: Start the Streamlit frontend
─────────────────────────────
  Open a THIRD new terminal (click + again). Make sure venv is active.

  Windows:
    streamlit run frontend/app.py

  Mac/Linux:
    streamlit run frontend/app.py

  ✅ You should see:
    You can now view your Streamlit app in your browser.
    Local URL: http://localhost:8501

  → Your browser should open automatically, or go to: http://localhost:8501


===================================================
PART 6 — USE THE APP
===================================================

STEP 12: Try it with the sample dataset
─────────────────────────────
  1. In the browser at http://localhost:8501
  2. In the left sidebar, click "Browse files"
  3. Navigate to your project folder → sample_data → select "sample_sales.csv"
  4. Click "⚡ Load & Analyze"
  5. You'll see the KPI row populate and 4 tabs appear
  6. Explore the tabs:
     - 📋 Preview  → see the raw data table
     - 📈 Visualize → interactive charts (histogram, scatter, heatmap)
     - 🔬 Statistics → numeric summary, correlations, trends
     - 💬 Ask a Question → type any question about the data
  7. In the sidebar, click "🔮 Generate Insights"
     → Wait ~10 seconds for Claude to analyse and return insights
     → You'll see 3 columns: Key Insights, Possible Reasons, Actionable Suggestions


===================================================
PART 7 — RUN THE TESTS
===================================================

STEP 13: Run the test suite
─────────────────────────────
  In any terminal (venv active), from the project root:

  Run all tests:
    pytest

  Run with verbose output (see each test name):
    pytest -v

  Run with coverage report:
    pytest --cov=backend --cov-report=term-missing

  Run a specific test file:
    pytest tests/test_data_processor.py -v

  ✅ You should see: 62 passed


===================================================
PART 8 — PUSH TO GITHUB (for your portfolio)
===================================================

STEP 14: Create a GitHub repo and push
─────────────────────────────
  1. Go to https://github.com → click "New repository"
  2. Name it "autoinsight"
  3. Set to Public (so recruiters can see it)
  4. DO NOT add README or .gitignore — you already have them
  5. Click "Create repository"

  In your VS Code terminal:
    git init
    git add .
    git commit -m "Initial commit: AutoInsight production-grade data analysis tool"
    git branch -M main
    git remote add origin https://github.com/YOUR_USERNAME/autoinsight.git
    git push -u origin main

  6. After pushing, go to your repo on GitHub
  7. Click "Actions" tab — you'll see the CI pipeline running automatically
  8. ✅ It should go green within 2-3 minutes

  IMPORTANT: Update the badge URLs in README.md
  → Open README.md
  → Replace "YOUR_USERNAME" with your actual GitHub username in the badge URLs
  → Save, commit, push:
      git add README.md
      git commit -m "Update badge URLs"
      git push


===================================================
PART 9 — TROUBLESHOOTING
===================================================

❌ "ModuleNotFoundError: No module named 'backend'"
  → You're not running from the project root directory
  → Make sure your terminal is IN the autoinsight/ folder
  → Run: cd path/to/autoinsight

❌ "ANTHROPIC_API_KEY environment variable is not set"
  → Your .env file isn't being loaded, or the key is wrong
  → Windows: manually run: set ANTHROPIC_API_KEY=sk-ant-your-key
  → Mac/Linux: run: export ANTHROPIC_API_KEY=sk-ant-your-key
  → Check the key has no extra spaces

❌ "Connection refused" on port 8000
  → The FastAPI backend isn't running
  → Start it in Terminal 2 (Step 10)

❌ "Address already in use" on port 8000 or 8501
  → Something else is using that port
  → Find and kill it:
      Windows: netstat -ano | findstr :8000  → taskkill /PID <number> /F
      Mac/Linux: lsof -i :8000 → kill -9 <PID>

❌ Redis connection warning in the logs
  → This is fine — the app falls back to in-memory automatically
  → You'll see a yellow warning but the app still works

❌ "venv is not activated" — pip installs to wrong place
  → Windows: run venv\Scripts\activate
  → Mac/Linux: run source venv/bin/activate
  → You must see "(venv)" in your terminal prompt

❌ Streamlit page is blank / not loading
  → Hard refresh: Ctrl+Shift+R
  → Check Terminal 3 for error messages
  → Make sure the backend (Terminal 2) is running first


===================================================
QUICK REFERENCE — DAILY WORKFLOW
===================================================

Every time you want to work on the project:

  1. Open VS Code → Open Folder → autoinsight
  2. Open terminal (Ctrl+`)
  3. Activate venv:
       Windows:   venv\Scripts\activate
       Mac/Linux: source venv/bin/activate
  4. Terminal 1: docker run -d -p 6379:6379 redis:7-alpine  (or skip)
  5. Terminal 2: uvicorn backend.main:app --reload --port 8000
  6. Terminal 3: streamlit run frontend/app.py
  7. Open http://localhost:8501

To stop everything: Ctrl+C in each terminal.
