# YatraSense Organic — new, separate project

Django + SQLite + FastAPI + React + Tailwind. Twenty destination pages, sixty
locally stored photographs, interactive maps, a trip planner, account profiles,
saved trips, and Django administration. This folder is independent of your old
YatraSense project. Extract it into a new folder; do not copy it over the old one.

## Windows quick start (Python 3.12 recommended)

Open PowerShell **inside `YatraSense_Organic`**, where this README lives.
Close your old servers first, since this project uses the same ports.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py seed_demo
.\.venv\Scripts\python.exe backend\manage.py createsuperuser
cd frontend
npm install
cd ..
```

If `python` cannot be found, use the working Python 3.12 executable on your
computer to create the venv. Do not use the previously broken `py` launcher
without checking it. The remaining commands always use the venv explicitly.

Start **three terminals**, all initially in `YatraSense_Organic`:

**Terminal 1 — Django / SQLite / admin**

```powershell
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

**Terminal 2 — trained ML / FastAPI**

```powershell
.\.venv\Scripts\python.exe -m uvicorn ml_service.main:app --host 127.0.0.1 --port 8001
```

**Terminal 3 — React / Tailwind**

```powershell
cd frontend
npm run dev
```

- Website: http://127.0.0.1:5173
- Django administration: http://127.0.0.1:8000/admin/
- FastAPI docs: http://127.0.0.1:8001/docs
- Backend health: http://127.0.0.1:8000/api/health/

There is no preset admin password. Use the superuser you create above. Customer
accounts are created using the website's Sign in → Create an account form.

The ZIP includes a seeded SQLite database with **no user accounts**. Running
`migrate` and `seed_demo` is still recommended. Seeding creates missing demo
places and preserves existing admin edits; it does not restore deleted photos
or overwrite destination descriptions. For a completely fresh database, move
`backend/db.sqlite3` aside, then migrate and seed again.

## Admin: add, edit, delete and upload

Open **Destinations** in Django administration. Select a destination to edit its
description, coordinates, area, popularity and activity tags. Add photos using
the **Destination photos** rows at the bottom. Three upload rows appear by
default; use “Add another Destination photo” for more. Add captions, credits,
licences and order. JPEG, PNG and WebP images up to 10 MB are supported.

A superuser has full standard Django permissions, including creation, editing
and deletion of destinations, photos, users and saved trips. Map coordinates
are mandatory. Refresh the website to see admin changes. A new place can be
recommended through the existing area encoding, but the UI labels its estimate
as unvalidated. Admin metadata edits do not automatically retrain the models.

## How the models work

The dataset is used as an ordinary structured ML dataset: validation checks,
chronological splits, fitted preprocessing pipelines, training, candidate
comparison, winner selection, held-out testing and persisted artifacts.

It remains **synthetic**. Counts, weather, popularity and customer choices are
simulated. Activity assignments are illustrative, not a researched activity
inventory. The app and notebooks state this; these are not real-world forecasts.

1. Crowd classifier: destination, area, month encoding and weather → Low,
   Medium or High **relative monthly busyness**. Current visitor counts and
   target labels are excluded from inputs. A monthly row is deduplicated before
   training. It does not predict exact daily attendance or actual capacity.
2. Recommendation classifier: activities requested and offered, weather,
   popularity and **predicted** busyness → probability of a simulated customer
   choice. That score ranks candidate destinations. Training uses grouped
   out-of-fold crowd predictions. Customer examples remain grouped by request
   across chronological splits.
3. Filtering: requested activity match is required. Low/Medium/High keeps only
   that predicted crowd level; Any allows all levels. An empty match produces a
   clear message. Filtering itself is not ML.

There is no season feature. Month is a calendar input, not a displayed season.
Weather at prediction time comes from **training-only simulated monthly
averages**, not a live weather API. Crowd model probabilities are not calibrated
real-world confidence. Popularity is an independent synthetic attribute; it
does not mean current crowding. Wildlife has no tagged places in this twenty
destination collection, so selecting only wildlife returns no matches.

Train: 2016–2022. Validation: 2023. Test: 2024–2025. Four candidate algorithms and
a majority-class baseline are evaluated. Highest validation accuracy selects
the trained winner, with macro F1 breaking ties. Test records do not select it.

| Task | Selected model | Validation accuracy | Test accuracy |
|---|---|---:|---:|
| Crowd estimation | Random Forest | 77.08% | 72.50% |
| Recommendation | Random Forest | 77.85% | 75.90% |

These scores did **not** exceed 80%. Recommendation test macro F1 is 0.648,
ROC AUC is 0.759, and NDCG@5 is 0.491. Accuracy is not ranking quality. Complete
reports and class confusion matrices are in `reports/`; reports are also visible
at `/models` in the website. The packaged pipelines remain fitted on training
data, matching the stated evaluations.

## Fifteen executed notebooks

The notebooks include explanatory markdown, the workflow function source,
actual executed cells and output tables. No output is hand-written. This build
used in-process IPython because its environment blocked Jupyter kernel sockets;
the same notebook cells run in a normal VS Code/Jupyter kernel on your laptop.

Open the project in VS Code, install its Python and Jupyter extensions, open a
notebook and select **`.venv\Scripts\python.exe`** as the kernel. Run all cells.
Use this order:

1. `notebooks/crowd/01_ingestion.ipynb`
2. `notebooks/crowd/02_preprocessing.ipynb`
3. `notebooks/crowd/03_train_validation_test_split.ipynb`
4. `notebooks/crowd/04_model_training.ipynb`
5. `notebooks/crowd/05_model_evaluation.ipynb`
6. `notebooks/crowd/06_model_selection.ipynb`
7. `notebooks/crowd/07_test_and_save.ipynb`
8. Run those same seven stages in `notebooks/recommendation/`.
9. `notebooks/shared/08_integration.ipynb` checks both saved models through FastAPI.

Or execute all notebooks:

```powershell
.\.venv\Scripts\python.exe scripts\run_notebooks.py
```

Or retrain without notebook output capture:

```powershell
.\.venv\Scripts\python.exe scripts\train_models.py
```

Restart FastAPI after retraining. The service checks the packaged scikit-learn
version before loading artifacts to avoid your previous pickle-version error.
Requirements pin the evaluated versions. If you intentionally change those
versions, retrain locally instead of loading old artifacts.

## Maps and photos

Every destination has a map point and three bundled photographs. Map tiles
need internet; photos do not need an external image server. Credits and source
links appear under each gallery image. `data/raw/media_manifest.json` preserves
all photo provenance and coordinate sources. Some locations use clearly labelled
approximate visitor points, especially large mountain regions. Pins are not
trekking routes or navigation advice. Verify approximate coordinates before
using them for navigation. No API key is required for the development map.

If online tiles fail, the app shows a bundled country outline and destination
points with an explicit notice. The outline is public-domain Natural Earth
1:110m country geometry from
https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson.
It supplies geographic context, not street details.

## Checks and troubleshooting

```powershell
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py test travel
cd frontend
npm run build
```

- Backend unavailable: start Django and verify port 8000.
- Prediction unavailable: start FastAPI **from the project root**, not `backend`.
- Admin missing tables: run `migrate`.
- No destinations: run `seed_demo`.
- Map blank: check internet access and OpenStreetMap tile availability; the
external OpenStreetMap link and coordinates are also provided.
- Port already used: stop the old YatraSense servers before starting this one.
- Model version error: install the pinned requirements or retrain in your venv.

This is a local development package. Production hosting requires a secret key,
restricted hosts/origins, HTTPS, production media/static serving and disabling
debug; Vite and Django development servers are not production servers.
#   Y a t r a S e n s e  
 