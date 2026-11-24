"""Reproducible training stages used by the notebooks and command-line runner.

Synthetic demonstration only. IDs and labels are never silently treated as
observations. Test years never select candidate models or thresholds.
"""
from pathlib import Path
import json
import hashlib
import platform
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.metrics import accuracy_score, f1_score, balanced_accuracy_score, classification_report, confusion_matrix, roc_auc_score, ndcg_score

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/YatraSense_20_destinations_synthetic.csv'
DATA = ROOT / 'data/processed'
MODELS = ROOT / 'models'
REPORTS = ROOT / 'reports'
ACTIVITIES = ['heritage_pilgrimage','trekking_hiking','wildlife_birdwatching','boating_water','adventure_sports']
CROWD_FEATURES = ['destination_id','area','month_sin','month_cos','temperature_mean_c','precipitation_mm_month','wind_speed_kmh_mean']
REC_FEATURES = ['destination_id','area','popularity_score','temperature_mean_c','precipitation_mm_month','wind_speed_kmh_mean','month_sin','month_cos'] + ACTIVITIES + ['customer_'+x for x in ACTIVITIES] + ['activity_match','weather_comfort','customer_crowd_preference','estimated_busyness','crowd_match']
TARGETS = {'crowd':'busyness_label','recommendation':'customer_chose_destination'}
SEED = 42

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding='utf-8')

def ingest():
    for p in [DATA,MODELS,REPORTS]: p.mkdir(parents=True,exist_ok=True)
    df=pd.read_csv(RAW, keep_default_na=False)
    assert len(df)==14400 and df.destination_id.nunique()==20
    assert df.row_id.is_unique and (df.is_synthetic==1).all()
    assert not any('season' in c for c in df.columns)
    assert set(df.busyness_label)=={'Low','Medium','High'}
    assert set(df.customer_crowd_preference)=={'Low','Medium','High','Any'}
    for a in ACTIVITIES+['customer_'+x for x in ACTIVITIES]: assert df[a].isin([0,1]).all()
    assert (df.visitor_count>=0).all() and df.month.between(1,12).all()
    assert df.temperature_mean_c.between(-50,60).all()
    assert df.precipitation_mm_month.between(0,2000).all()
    pd.to_datetime(df.travel_date, errors='raise')
    # Repeated monthly facts must agree across every customer example.
    facts=['visitor_count','busyness_label','temperature_mean_c','precipitation_mm_month','wind_speed_kmh_mean','popularity_score']
    assert (df.groupby('destination_month_id')[facts].nunique()==1).all().all()
    assert (df.groupby('request_id').dataset_split.nunique()==1).all()
    df.to_csv(DATA/'ingested.csv', index=False)
    audit={'rows':len(df),'destinations':20,'unique_monthly_observations':df.destination_month_id.nunique(),'sha256':hashlib.sha256(RAW.read_bytes()).hexdigest(),'synthetic':True,'duplicate_months_expected':True,'splits':df.dataset_split.value_counts().to_dict(),'unsupported_activity':'wildlife_birdwatching: no tagged destination in this catalog'}
    write_json(REPORTS/'ingestion.json',audit)
    return audit

def calendar_features(df):
    df=df.copy()
    df['month_sin']=np.sin(2*np.pi*df.month/12)
    df['month_cos']=np.cos(2*np.pi*df.month/12)
    return df

def preprocess_crowd():
    df=pd.read_csv(DATA/'ingested.csv')
    # All customer-related columns are discarded; one example per place/month.
    fields=['destination_month_id','destination_id','destination_name','area','year','month','temperature_mean_c','precipitation_mm_month','wind_speed_kmh_mean','visitor_count','busyness_label','dataset_split']
    df=calendar_features(df[fields].drop_duplicates('destination_month_id'))
    assert len(df)==2400 and df.destination_month_id.is_unique
    assert df.groupby('dataset_split').year.agg(['min','max']).to_dict()=={'min':{'test':2024,'train':2016,'validation':2023},'max':{'test':2025,'train':2022,'validation':2023}}
    df.to_csv(DATA/'crowd.csv',index=False)
    train=df[df.dataset_split=='train']
    # This is a synthetic climatology for demo inference, never a live forecast.
    weather=train.groupby(['destination_id','month'])[['temperature_mean_c','precipitation_mm_month','wind_speed_kmh_mean']].mean().round(2).reset_index()
    weather.to_csv(DATA/'demo_weather.csv',index=False)
    meta=['destination_id','destination_name','area','destination_type']+ACTIVITIES+['specific_activities']
    original=pd.read_csv(DATA/'ingested.csv')
    catalog=original[meta].drop_duplicates('destination_id').set_index('destination_id')
    catalog['popularity_score']=original[original.dataset_split=='train'].groupby('destination_id').popularity_score.mean().round(1)
    catalog.reset_index().to_csv(DATA/'catalog.csv',index=False)
    return df.groupby('dataset_split').size().to_dict()

def preprocessing(features):
    categorical=[c for c in features if c in ['destination_id','area','customer_crowd_preference','estimated_busyness']]
    numeric=[c for c in features if c not in categorical]
    return ColumnTransformer([
      ('numeric',Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler())]),numeric),
      ('category',Pipeline([('impute',SimpleImputer(strategy='most_frequent')),('one_hot',OneHotEncoder(handle_unknown='ignore',sparse_output=False))]),categorical)
    ])

def candidates(task):
    features=CROWD_FEATURES if task=='crowd' else REC_FEATURES
    algorithms={
      'LogisticRegression':LogisticRegression(max_iter=1500,random_state=SEED),
      'RandomForest':RandomForestClassifier(n_estimators=180,min_samples_leaf=5,max_depth=14,random_state=SEED,n_jobs=-1),
      'ExtraTrees':ExtraTreesClassifier(n_estimators=180,min_samples_leaf=4,max_depth=18,random_state=SEED,n_jobs=-1),
      'GradientBoosting':HistGradientBoostingClassifier(max_iter=140,max_leaf_nodes=15,l2_regularization=4,random_state=SEED),
      'MajorityBaseline':DummyClassifier(strategy='most_frequent')
    }
    return {name:Pipeline([('preprocess',preprocessing(features)),('classifier',model)]) for name,model in algorithms.items()}

def train(task):
    df=pd.read_csv(DATA/f'{task}.csv'); tr=df[df.dataset_split=='train']
    features=CROWD_FEATURES if task=='crowd' else REC_FEATURES
    trained={}
    for name,pipe in candidates(task).items():
        pipe.fit(tr[features],tr[TARGETS[task]])
        trained[name]=pipe
    joblib.dump(trained,MODELS/f'{task}_candidates.joblib')
    return list(trained)

def metrics(y,pred):
    return {'accuracy':float(accuracy_score(y,pred)),'macro_f1':float(f1_score(y,pred,average='macro',zero_division=0)),'balanced_accuracy':float(balanced_accuracy_score(y,pred))}

def ranking_metrics(frame,probs):
    results=[]; precision=[]
    scored=frame[['request_id','customer_chose_destination']].copy();scored['score']=probs
    for _,group in scored.groupby('request_id'):
        y=group.customer_chose_destination.to_numpy()
        if y.sum()>0:
            results.append(float(ndcg_score([y],[group.score.to_numpy()],k=5)))
        precision.append(float(group.nlargest(5,'score').customer_chose_destination.mean()))
    return {'ndcg_at_5':float(np.mean(results)) if results else 0.,'precision_at_5':float(np.mean(precision)),'requests':int(scored.request_id.nunique()),'ndcg_requests_with_positive':len(results)}

def evaluate_validation(task):
    df=pd.read_csv(DATA/f'{task}.csv'); va=df[df.dataset_split=='validation']
    features=CROWD_FEATURES if task=='crowd' else REC_FEATURES
    models=joblib.load(MODELS/f'{task}_candidates.joblib'); rows=[]
    for name,model in models.items():
        pred=model.predict(va[features]); result={'model':name,**metrics(va[TARGETS[task]],pred)}
        if task=='recommendation':
            prob=model.predict_proba(va[features])[:,1]
            result.update(ranking_metrics(va,prob));result['roc_auc']=float(roc_auc_score(va[TARGETS[task]],prob))
        rows.append(result)
    table=pd.DataFrame(rows).sort_values(['accuracy','macro_f1'],ascending=False)
    table.to_csv(REPORTS/f'{task}_validation.csv',index=False)
    return table

def select(task):
    table=pd.read_csv(REPORTS/f'{task}_validation.csv')
    # Respect requested highest validation accuracy; macro F1 breaks ties.
    table=table[table.model!='MajorityBaseline'].sort_values(['accuracy','macro_f1'],ascending=False)
    winner=table.iloc[0].model
    model=joblib.load(MODELS/f'{task}_candidates.joblib')[winner]
    joblib.dump(model,MODELS/f'{task}.joblib')
    choice={'model':winner,'criterion':'highest validation accuracy; macro F1 tie-break','validation':table.iloc[0].to_dict(),'test_used_for_selection':False,'synthetic':True}
    write_json(REPORTS/f'{task}_selection.json',choice)
    return choice

def rec_features(df):
    df=calendar_features(df)
    requested=df[['customer_'+x for x in ACTIVITIES]].to_numpy()
    offered=df[ACTIVITIES].to_numpy()
    df['activity_match']=(requested*offered).sum(axis=1)/np.maximum(requested.sum(axis=1),1)
    df['weather_comfort']=np.clip(1-df.precipitation_mm_month/650-np.maximum(0,5-df.temperature_mean_c)/25-df.wind_speed_kmh_mean/70,0,1)
    df['crowd_match']=((df.customer_crowd_preference=='Any')|(df.customer_crowd_preference==df.estimated_busyness)).astype(int)
    return df

def preprocess_recommendation():
    original=pd.read_csv(DATA/'ingested.csv')
    crowd=pd.read_csv(DATA/'crowd.csv'); train_frame=crowd[crowd.dataset_split=='train'].copy()
    crowd_model=joblib.load(MODELS/'crowd.joblib')
    # Grouped out-of-fold predictions prevent feeding memorized crowd labels
    # into the recommendation training examples. Group entire years.
    oof=cross_val_predict(clone(crowd_model),train_frame[CROWD_FEATURES],train_frame.busyness_label,cv=GroupKFold(n_splits=4),groups=train_frame.year,n_jobs=1)
    predictions=dict(zip(train_frame.destination_month_id,oof))
    held=crowd[crowd.dataset_split!='train']
    predictions.update(dict(zip(held.destination_month_id,crowd_model.predict(held[CROWD_FEATURES]))))
    original['estimated_busyness']=original.destination_month_id.map(predictions)
    df=rec_features(original)
    assert df.estimated_busyness.notna().all()
    df.to_csv(DATA/'recommendation.csv',index=False)
    return {'rows':len(df),'crowd_features':'grouped out-of-fold for train; frozen train-only model for validation/test','features':REC_FEATURES}

def final_test(task):
    df=pd.read_csv(DATA/f'{task}.csv'); te=df[df.dataset_split=='test']
    features=CROWD_FEATURES if task=='crowd' else REC_FEATURES
    model=joblib.load(MODELS/f'{task}.joblib'); pred=model.predict(te[features])
    labels=['Low','Medium','High'] if task=='crowd' else [0,1]
    report={'synthetic':True,'test_years':[2024,2025],'training_years':[2016,2022],'selection':json.loads((REPORTS/f'{task}_selection.json').read_text()),'test':metrics(te[TARGETS[task]],pred),'classification_report':classification_report(te[TARGETS[task]],pred,output_dict=True,zero_division=0),'confusion_matrix':confusion_matrix(te[TARGETS[task]],pred,labels=labels).tolist(),'class_order':labels,'features':features,'excluded_features':['visitor_count','busyness_label (target only)','row_id','request_id','dataset_split','customer_chose_destination (target only)'],'accuracy_above_80':bool(accuracy_score(te[TARGETS[task]],pred)>.8),'limitations':['Synthetic generator performance; not real crowd or customer validation.','Monthly estimates, not exact daily occupancy.','New admin destinations use area-level model encoding; unvalidated on unseen places.','Demo weather uses training-only monthly averages, not a live forecast.']}
    if task=='recommendation':
        probs=model.predict_proba(te[features])[:,1];report['test'].update(ranking_metrics(te,probs));report['test']['roc_auc']=float(roc_auc_score(te[TARGETS[task]],probs))
    write_json(REPORTS/f'{task}_test.json',report)
    pd.DataFrame({'actual':te[TARGETS[task]],'prediction':pred}).to_csv(REPORTS/f'{task}_test_predictions.csv',index=False)
    versions={'python':platform.python_version(),'scikit_learn':sklearn.__version__,'numpy':np.__version__,'pandas':pd.__version__,'joblib':joblib.__version__,'data_sha256':hashlib.sha256(RAW.read_bytes()).hexdigest(),'synthetic':True}
    write_json(MODELS/'versions.json',versions)
    return report
