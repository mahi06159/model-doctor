# ModelDoctor - Developer Setup & Contribution Guidelines

This document outlines the guidelines for setting up the local development environment, running quality checks, and extending the ModelDoctor diagnostic engines.

---

## 1. Local Development Setup

Ensure you have [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed.

### Step 1: Clone and Configure Environment
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```

### Step 2: Spin Up Containers
Build and run the stack:
```bash
docker compose up --build -d
```

### Step 3: Run Database Migrations
Verify the database schema is up-to-date:
```bash
docker compose exec backend python manage.py migrate
```

### Step 4: Create a Superuser
Create credentials to log in to the live audit flow:
```bash
docker compose exec backend python manage.py createsuperuser
```

---

## 2. Codebase Organization

- `backend/analysis/`: Diagnostic engine calculators (e.g. leakage, calibration, overfitting, fairness, drift). Keep these functions pure (accepting NumPy arrays, Pandas DataFrames, or scikit-learn models, returning JSON-serializable dictionaries).
- `backend/audits/`: Django models, serializers, views, and Celery tasks orchestration.
- `frontend/src/pages/`: React views. `Dashboard.jsx` handles aggregate stats, gauge chart, and job summaries. `JobStatus.jsx` handles detailed metric reports and charts.

---

## 3. Running the Test Suite

ModelDoctor utilizes `pytest` for backend testing. Make sure to run tests inside the container environment to ensure correct Python libraries are used:

### Run All Tests
```bash
docker compose exec backend pytest tests/ -v
```

### Run Coverage Reports
```bash
docker compose exec backend pytest --cov=analysis --cov=audits tests/
```

---

## 4. Writing a New Diagnostic Module

To add an additional diagnostic checks module (e.g., Phase 7 or post-hoc auditing):

1. **Implement Core Logic**: Create a new python file in `backend/analysis/` (e.g. `backend/analysis/robustness.py`). Ensure the function returns `{"supported": True, ...}` or `{"supported": False, "message": "Reason"}` on graceful failures.
2. **Add Celery Execution Stage**: Import your function into `backend/audits/tasks.py` and call it in `run_leakage_audit`. Use `_update_progress` to update the user on the progress of the run.
3. **Merge Results**: Merge your results dictionary into the `job.results` JSON field.
4. **Update Health Score**: Adjust `backend/analysis/health_score.py` to add appropriate weights/penalties for the new module.
5. **Add Frontend Panel**: Add a corresponding tab button and result visualization dashboard panel inside `JobStatus.jsx`.
