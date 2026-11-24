from functools import lru_cache
from datetime import date
from pathlib import Path
import json
import joblib
import pandas as pd
import sklearn
from .workflows import ROOT, DATA, MODELS, REPORTS, ACTIVITIES, CROWD_FEATURES, REC_FEATURES, calendar_features, rec_features

@lru_cache(maxsize=1)
def artifacts():
    manifest=json.loads((MODELS/'versions.json').read_text())
    if manifest['scikit_learn']!=sklearn.__version__:
        raise RuntimeError(f"Models require scikit-learn {manifest['scikit_learn']}. Run pip install -r requirements.txt or retrain using the notebooks.")
    return (joblib.load(MODELS/'crowd.joblib'),joblib.load(MODELS/'recommendation.joblib'),pd.read_csv(DATA/'demo_weather.csv'),pd.read_csv(DATA/'catalog.csv'))

def predict_destinations(destinations, travel_date, activities, crowd_preference='Any', area='All', limit=20):
    crowd_model,rec_model,weather,catalog=artifacts()
    day=date.fromisoformat(str(travel_date)); rows=[]
    known=set(catalog.destination_id)
    for item in destinations:
        if not item.get('is_active',True):continue
        if area!='All' and item['area']!=area:continue
        did=item['id'];selected=weather[(weather.destination_id==did)&(weather.month==day.month)]
        if selected.empty:
            area_ids=catalog[catalog.area==item['area']].destination_id
            selected=weather[(weather.destination_id.isin(area_ids))&(weather.month==day.month)]
        if selected.empty:selected=weather[weather.month==day.month]
        summary=selected[['temperature_mean_c','precipitation_mm_month','wind_speed_kmh_mean']].mean().to_dict()
        row={'destination_id':did,'destination_name':item['name'],'area':item['area'],'month':day.month,'popularity_score':float(item['popularity_score']),**summary,'customer_crowd_preference':crowd_preference}
        for a in ACTIVITIES:
            row[a]=int(a in item['activities']);row['customer_'+a]=int(a in activities)
        rows.append(row)
    if not rows:return {'results':[],'message':'No active destinations match this area.','synthetic':True}
    df=calendar_features(pd.DataFrame(rows));df['estimated_busyness']=crowd_model.predict(df[CROWD_FEATURES])
    crowd_probs=crowd_model.predict_proba(df[CROWD_FEATURES])
    df=rec_features(df);df['recommendation_score']=rec_model.predict_proba(df[REC_FEATURES])[:,1]
    result=[]
    for position,(_,r) in enumerate(df.iterrows()):
        if r.activity_match<=0:continue
        if crowd_preference!='Any' and r.estimated_busyness!=crowd_preference:continue
        matched=[a for a in activities if r[a]==1]
        result.append({'destination_id':r.destination_id,'name':r.destination_name,'area':r.area,'crowd':r.estimated_busyness,'crowd_model_probability':round(float(crowd_probs[position].max()),3),'recommendation_score':round(float(r.recommendation_score),4),'popularity_score':round(float(r.popularity_score),1),'popularity': 'High' if r.popularity_score>=70 else 'Medium' if r.popularity_score>=40 else 'Low','matched_activities':matched,'weather':{'temperature_c':round(float(r.temperature_mean_c),1),'rainfall_mm_month':round(float(r.precipitation_mm_month),1),'wind_kmh':round(float(r.wind_speed_kmh_mean),1),'kind':'Simulated monthly average; not a live forecast'},'synthetic':True,'new_destination':r.destination_id not in known,'estimate_note':'Unvalidated estimate for a new destination' if r.destination_id not in known else 'Demo estimate trained on simulated visitor histories'})
    result=sorted(result,key=lambda r:r['recommendation_score'],reverse=True)[:limit]
    return {'results':result,'travel_date':day.isoformat(),'month':day.month,'synthetic':True,'message':None if result else 'No destinations match your activities and crowd preference. Try Any crowd or another activity.','model_note':'Actual trained models using synthetic data. Scores are model outputs, not real-world confidence.'}

def model_reports():
    return {task:json.loads((REPORTS/f'{task}_test.json').read_text()) for task in ['crowd','recommendation']}
