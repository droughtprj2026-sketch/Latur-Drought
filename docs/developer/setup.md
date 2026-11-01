# Development Environment Setup & Testing

This guide explains how to set up the development environment, execute the automated test suite, and compile the frontend.

---

## 1. Prerequisites

- **Python:** 3.10, 3.11, or 3.12 (standard CPython).
- **Node.js:** 18+ LTS or 20+ LTS with `npm`.
- **Git:** Git 2.30+.

---

## 2. Python Environment Setup

Clone the repository and install required Python packages:

```bash
# Clone the repository
git clone https://github.com/Shivaji-University/Drought-Monitoring-Latur.git
cd Drought-Monitoring-Latur

# Create and activate virtual environment
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install pipeline and testing dependencies
pip install -r scripts/requirements-realtime.txt pytest mkdocs-material
```

---

## 3. Frontend Web App Setup

```bash
cd frontend
npm install
```

---

## 4. Mandatory Verification Suite ("Done" Definition)

Before committing any code or deploying to production, **all** of the following commands must execute cleanly:

### 4.1 Run Automated Pytest Suite
```bash
python -m pytest scripts/tests -q
```
*Expected Result:* 43 passed tests verifying classification parity, CDI formulas, data integrity, and pipeline helpers.

### 4.2 TypeScript Type-Check & Next.js Build
```bash
cd frontend
npx tsc --noEmit
npm run build
```
*Expected Result:* Zero TypeScript errors; all 11 static/dynamic pages compiled successfully.

### 4.3 Documentation Website Build
```bash
mkdocs build --strict
```
*Expected Result:* Zero warnings; production HTML site compiled to `site/`.

