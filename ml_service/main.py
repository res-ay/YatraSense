from datetime import date
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .inference import artifacts,predict_destinations,model_reports
from .workflows import ACTIVITIES

app=FastAPI(title='YatraSense ML',description='Trained crowd and recommendation models. Synthetic demonstration.',version='1.0.0')
class DestinationInput(BaseModel):
    id:str=Field(min_length=1,max_length=40)
    name:str=Field(min_length=1,max_length=160)
    area:str=Field(min_length=1,max_length=50)
    activities:list[str]
    popularity_score:float=Field(ge=0,le=100)
    is_active:bool=True
class PlanInput(BaseModel):
    travel_date:date
    activities:list[str]=Field(min_length=1,max_length=5)
    crowd_preference:Literal['Low','Medium','High','Any']='Any'
    area:str='All'
    limit:int=Field(default=20,ge=1,le=100)
    destinations:list[DestinationInput]=Field(min_length=1,max_length=500)
@app.get('/health')
def health():
    try:artifacts()
    except Exception as exc:raise HTTPException(503,str(exc))
    return {'status':'ok','synthetic':True,'models':['crowd','recommendation']}
@app.get('/metrics')
def metrics():return model_reports()
@app.post('/predict')
def predict(payload:PlanInput):
    if any(a not in ACTIVITIES for a in payload.activities):raise HTTPException(422,'Unknown activity')
    try:return predict_destinations([d.model_dump() for d in payload.destinations],payload.travel_date.isoformat(),payload.activities,payload.crowd_preference,payload.area,payload.limit)
    except Exception as exc:raise HTTPException(503,f'Model unavailable: {exc}')
