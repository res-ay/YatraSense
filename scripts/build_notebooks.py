from pathlib import Path
import nbformat as nbf
ROOT=Path(__file__).resolve().parents[1]
SETUP='''from pathlib import Path
import sys, json, inspect
import pandas as pd
from IPython.display import display
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "ml_service/workflows.py").exists())
sys.path.insert(0, str(ROOT))
from ml_service import workflows as w
print("Project:", ROOT)
print("Synthetic demonstration: real-world accuracy has not been measured.")'''
def notebook(path,title,explanation,cells):
    nb=nbf.v4.new_notebook()
    nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.12'}}
    nb.cells=[nbf.v4.new_markdown_cell(f'# {title}\n\n{explanation}\n\nRun every cell from top to bottom. Use the project `.venv` kernel in VS Code. No season field is used. Data and test scores are synthetic.'),nbf.v4.new_code_cell(SETUP)]
    for kind,text in cells:nb.cells.append(nbf.v4.new_code_cell(text) if kind=='code' else nbf.v4.new_markdown_cell(text))
    path.parent.mkdir(parents=True,exist_ok=True);nbf.write(nb,path)
for task in ['crowd','recommendation']:
    folder=ROOT/'notebooks'/task
    desc='Estimate relative monthly busyness without using current visitor counts as input.' if task=='crowd' else 'Predict simulated customer choice probabilities and rank destination candidates. Use crowd predictions, not actual crowd labels, as features.'
    notebook(folder/'01_ingestion.ipynb',f'{task.title()} / 01 — Ingestion',desc,[
      ('code','print(inspect.getsource(w.ingest))'),('code','audit = w.ingest()\ndisplay(pd.Series(audit))\ndf = pd.read_csv(w.DATA / "ingested.csv")\ndisplay(df.head())'),
      ('markdown','The input repeats each destination/month for six synthetic customer profiles. This repetition is intentional for recommendation examples; it must not inflate the crowd training dataset.')])
    func='preprocess_crowd' if task=='crowd' else 'preprocess_recommendation'
    notebook(folder/'02_preprocessing.ipynb',f'{task.title()} / 02 — Preprocessing', 'Run crowd notebooks first. Recommendation preprocessing needs the selected crowd model.' if task=='recommendation' else 'Deduplicate monthly observations, encode month cyclically and create a training-only weather snapshot.',[
      ('code',f'print(inspect.getsource(w.{func}))\nprint(inspect.getsource(w.preprocessing))'),
      ('code',f'summary = w.{func}()\nprint(summary)\ndf = pd.read_csv(w.DATA / "{task}.csv")\ndisplay(df.head())'),
      ('markdown','Numeric imputation and scaling, plus categorical imputation and one-hot encoding, are fitted inside each training pipeline. Validation and test records never fit those transforms. Recommendation crowd features are grouped out-of-fold predictions for training and frozen train-only predictions for later years. Those folds group whole years; they are cross-fitting, not a rolling historical backtest.')])
    notebook(folder/'03_train_validation_test_split.ipynb',f'{task.title()} / 03 — Chronological split','Preserve the CSV’s fixed chronological split. Never randomly distribute copies of a monthly observation or customer request across sets.',[
      ('code',f'df = pd.read_csv(w.DATA / "{task}.csv")\ntrain = df[df.dataset_split == "train"].copy()\nvalidation = df[df.dataset_split == "validation"].copy()\ntest = df[df.dataset_split == "test"].copy()\ndisplay(df.groupby("dataset_split").agg(rows=("year","size"), first_year=("year","min"), last_year=("year","max")))\nassert train.year.max() < validation.year.min() < test.year.min()\nkey = "destination_month_id" if "{task}" == "crowd" else "request_id"\nassert not set(train[key]) & set(validation[key])\nassert not set(train[key]) & set(test[key])\nassert not set(validation[key]) & set(test[key])\nprint("Chronological and grouping checks passed.")'),
      ('markdown','Train: 2016–2022. Validation: 2023. Test: 2024–2025. The test set is only used after selecting the winner. Busyness categories were generated using fixed simulator reference levels, not quantiles learned from test records.')])
    notebook(folder/'04_model_training.ipynb',f'{task.title()} / 04 — Train candidates','Compare four trained algorithms and a majority-class baseline. The training functions below use only the training partition.',[
      ('code','print(inspect.getsource(w.candidates))\nprint(inspect.getsource(w.train))'),
      ('code',f'names = w.train("{task}")\nprint("Trained:", names)'),
      ('markdown','Candidate pipelines include Logistic Regression, Random Forest, Extra Trees and Histogram Gradient Boosting. Candidate artifacts contain fitted preprocessing and estimators together. Only load trusted joblib files.')])
    notebook(folder/'05_model_evaluation.ipynb',f'{task.title()} / 05 — Validation evaluation','Evaluate all candidates on 2023. Accuracy alone can reward majority prediction, so report macro F1 and balanced accuracy too.',[
      ('code','print(inspect.getsource(w.evaluate_validation))'),
      ('code',f'comparison = w.evaluate_validation("{task}")\ndisplay(comparison)'),
      ('markdown','The recommendation table also includes ROC AUC, NDCG@5 and Precision@5. NDCG excludes requests with no positive choice labels and reports the number used. A score is not a guarantee of usefulness for real customers.')])
    notebook(folder/'06_model_selection.ipynb',f'{task.title()} / 06 — Select the winner','Select the trained algorithm with highest validation accuracy; macro F1 breaks ties. Do not pick a model from its test score.',[
      ('code','print(inspect.getsource(w.select))'),
      ('code',f'choice = w.select("{task}")\ndisplay(pd.Series(choice))\nprint("Saved fitted pipeline:", w.MODELS / "{task}.joblib")'),
      ('markdown','The selected pipeline remains fitted on the training set, preserving the evaluation/inference contract. An 80% target is not guaranteed; results are never rewritten to meet it.')])
    notebook(folder/'07_test_and_save.ipynb',f'{task.title()} / 07 — Final test & artifact manifest','Evaluate the frozen winner on untouched 2024–2025 records, then save metrics and dependency versions.',[
      ('code','print(inspect.getsource(w.final_test))'),
      ('code',f'report = w.final_test("{task}")\ndisplay(pd.Series(report["test"]))\ndisplay(pd.DataFrame(report["classification_report"]).T)\ndisplay(pd.DataFrame(report["confusion_matrix"], index=report["class_order"], columns=report["class_order"]))\nprint("Above 80%:", report["accuracy_above_80"])\nprint("Saved reports:", w.REPORTS)\nprint("Model versions:", (w.MODELS / "versions.json").read_text())'),
      ('markdown','The crowd target is relative busyness (Low/Medium/High), not a visitor-count forecast or occupancy measurement. The recommendation target is a noisy simulated binary choice. Neither task has been validated on real-world labels. New admin destinations are outside the trained catalog and are explicitly labelled unvalidated.')])
notebook(ROOT/'notebooks/shared/08_integration.ipynb','Both models / 08 — FastAPI integration','Load the exact saved pipelines and exercise the FastAPI prediction endpoint without a running server.',[
 ('code','from fastapi.testclient import TestClient\nfrom ml_service.main import app\nfrom ml_service.inference import artifacts\nfrom ml_service.workflows import ACTIVITIES\nclient = TestClient(app)\nassert client.get("/health").status_code == 200\ncatalog = artifacts()[3]\ndestinations = [{"id": r.destination_id, "name": r.destination_name, "area": r.area, "activities": [a for a in ACTIVITIES if r[a] == 1], "popularity_score": r.popularity_score} for _,r in catalog.iterrows()]\npayload = {"travel_date": "2026-10-15", "activities": ["heritage_pilgrimage"], "crowd_preference": "Any", "area": "All", "destinations": destinations}\nresponse = client.post("/predict", json=payload)\nassert response.status_code == 200, response.text\nresult = response.json()\ndisplay(pd.DataFrame(result["results"])[["name","crowd","popularity","recommendation_score"]])'),
 ('code','payload["crowd_preference"] = "Low"\nquiet = client.post("/predict", json=payload).json()\nassert all(r["crowd"] == "Low" for r in quiet["results"])\npayload["activities"] = ["wildlife_birdwatching"]\nempty = client.post("/predict", json=payload).json()\nassert empty["results"] == []\nprint("Crowd filters and empty activity matches verified.")'),
 ('markdown','Website integration: React → Django `/api/plan/` → FastAPI `/predict` → saved crowd pipeline and recommendation pipeline. Django enriches results with SQLite destination records, photos and maps. Saved customer plans are stored in SQLite. Start the three services using the README. Offline photos are bundled; OpenStreetMap tiles require internet.')])
print('Generated',len(list((ROOT/'notebooks').rglob('*.ipynb'))),'notebooks')
