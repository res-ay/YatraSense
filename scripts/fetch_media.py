"""Build-time download of Wikimedia photos and location metadata.
Bundled snapshots let the website show real photos without runtime image APIs.
"""
from pathlib import Path
import requests, json, re, html, time
from concurrent.futures import ThreadPoolExecutor, as_completed
ROOT=Path(__file__).resolve().parents[1]
HEADERS={'User-Agent':'YatraSenseEducationalDemo/1.0 (noncommercial local tourism student project)'}
ENTRIES=[
('YS001','Pashupatinath Temple','Pashupatinath Temple'),('YS002','Boudha Stupa','Boudhanath'),
('YS003','Swayambhunath','Swayambhunath'),('YS004','Kathmandu Durbar Square','Kathmandu Durbar Square'),
('YS005','Garden of Dreams','Garden of Dreams Kathmandu'),('YS006','Patan Durbar Square','Patan Durbar Square'),
('YS007','Patan Museum','Patan Museum'),('YS008','Hiranya Varna Mahavihar','Golden Temple Patan'),
('YS009','Bhaktapur Durbar Square','Bhaktapur Durbar Square'),('YS010','Nyatapola Temple','Nyatapola'),
('YS011','Phewa Lake','Phewa Lake'),('YS012','Begnas Lake','Begnas Lake'),
('YS013','Sarangkot','Sarangkot'),('YS014','World Peace Pagoda, Pokhara','World Peace Pagoda Pokhara'),
('YS015',"Devi's Falls","Davis Falls Pokhara"),('YS016','Annapurna Sanctuary','Annapurna Base Camp'),
('YS017','Everest base camps','Everest Base Camp Nepal'),('YS018','Namche Bazaar','Namche Bazaar'),
('YS019','Langtang valley','Langtang Valley'),('YS020','Mardi Himal','Mardi Himal Base Camp')]
# Visitor map points for large regions/routes, not the location of every feature.
FALLBACK={
'YS001':(27.7105,85.3488),'YS002':(27.7214,85.3620),'YS003':(27.7148,85.2904),
'YS004':(27.7043,85.3066),'YS005':(27.7140,85.3145),'YS006':(27.6734,85.3250),
'YS007':(27.6736,85.3253),'YS008':(27.6766,85.3253),'YS009':(27.6722,85.4280),
'YS010':(27.6711,85.4294),'YS011':(28.2117,83.9488),'YS012':(28.1747,84.0960),
'YS013':(28.2437,83.9486),'YS014':(28.2015,83.9449),'YS015':(28.1901,83.9592),
'YS016':(28.5305,83.8780),'YS017':(28.0026,86.8528),'YS018':(27.8053,86.7105),
'YS019':(28.2110,85.5670),'YS020':(28.4770,83.9300)}
def clean(s):return html.unescape(re.sub('<[^>]+>','',s or '')).strip()
def get(url,**kw):
    for attempt in range(4):
        r=requests.get(url,headers=HEADERS,timeout=35,**kw)
        if r.status_code==429:
            time.sleep(3*(attempt+1));continue
        r.raise_for_status();return r
    r.raise_for_status()
def one(entry):
    did,title,search=entry;coords=FALLBACK[did];coordinate_source='Approximate visitor map point; review before navigating'
    source='https://en.wikipedia.org/wiki/'+title.replace(' ','_')
    try:
        summary=get('https://en.wikipedia.org/api/rest_v1/page/summary/'+requests.utils.quote(title,safe='')).json()
        if 'coordinates' in summary and did not in ['YS016','YS017','YS019','YS020']:
            coords=(summary['coordinates']['lat'],summary['coordinates']['lon']);coordinate_source=source
    except Exception as exc:print(did,'summary',str(exc)[:70],flush=True)
    params={'action':'query','format':'json','generator':'search','gsrsearch':search+' filetype:bitmap','gsrnamespace':6,'gsrlimit':12,'prop':'imageinfo','iiprop':'url|extmetadata','iiurlwidth':1100}
    result=get('https://commons.wikimedia.org/w/api.php',params=params).json()
    pages=sorted(result.get('query',{}).get('pages',{}).values(),key=lambda p:p.get('index',999))
    photos=[]
    for page in pages:
        name=page['title']
        if any(x in name.lower() for x in ['map','logo','flag','locator','diagram','collage']):continue
        info=page.get('imageinfo',[{}])[0];url=info.get('thumburl',info.get('url'))
        if not url:continue
        meta=info.get('extmetadata',{})
        license=clean(meta.get('LicenseShortName',{}).get('value'))
        if not any(x in license.lower() for x in ['cc','public domain','pd','attribution']):continue
        try:
            r=get(url)
            if not r.headers.get('Content-Type','').startswith('image/'):continue
            suffix='.png' if 'png' in r.headers['Content-Type'] else '.jpg'
            rel=f'destinations/{did}_{len(photos)+1}{suffix}'
            (ROOT/'backend/media'/rel).write_bytes(r.content)
            photos.append({'file':rel,'caption':clean(name.removeprefix('File:')).rsplit('.',1)[0],'credit':clean(meta.get('Artist',{}).get('value'))[:300] or 'Wikimedia Commons contributor','license':license,'source_url':info.get('descriptionurl','https://commons.wikimedia.org/wiki/'+name.replace(' ','_'))})
            if len(photos)==3:break
        except Exception as exc:print(did,'image',str(exc)[:80],flush=True)
    return did,{'latitude':coords[0],'longitude':coords[1],'coordinate_source':coordinate_source,'photos':photos}
if __name__=='__main__':
    manifest=ROOT/'data/raw/media_manifest.json'
    result=json.loads(manifest.read_text()) if manifest.exists() else {}
    pending=[e for e in ENTRIES if e[0] not in result or len(result[e[0]]['photos'])<3]
    with ThreadPoolExecutor(max_workers=1) as pool:
        for future in as_completed([pool.submit(one,e) for e in pending]):
            try:
                did,item=future.result();result[did]=item;print(did,len(item['photos']),flush=True)
            except Exception as exc:print('FAILED',exc,flush=True)
    (ROOT/'data/raw/media_manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('TOTAL',len(result),sum(len(v['photos']) for v in result.values()),flush=True)
