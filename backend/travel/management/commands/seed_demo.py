from pathlib import Path
import csv,json
from django.core.management.base import BaseCommand
from django.db import transaction
from travel.models import Destination,DestinationPhoto
from travel.serializers import ACTIVITIES
ROOT=Path(__file__).resolve().parents[4]
DESCRIPTIONS={
'YS001':'Explore the temple precinct and riverside setting of Pashupatinath. Respect worshippers, photography restrictions and access rules at this active religious site.',
'YS002':'Walk around the great stupa, notice the prayer flags and explore the surrounding streets. Boudhanath is a place for both cultural visits and respectful reflection.',
'YS003':'Follow the hilltop steps toward the stupa and look across the Kathmandu Valley. The walking approach combines a cultural visit with a short climb.',
'YS004':'Explore the courtyards, temples and historic architecture of Kathmandu Durbar Square on foot.',
'YS005':'Take a slower break among the gardens and historic buildings close to Thamel.',
'YS006':'Explore Patan’s historic square, courtyards and architectural details on a heritage walk.',
'YS007':'Spend time with the collections and courtyards of Patan Museum. Check current opening times before visiting.',
'YS008':'Visit the Golden Temple in Patan and observe local religious practices respectfully.',
'YS009':'Explore Bhaktapur’s historic square and nearby streets at a walking pace.',
'YS010':'See the landmark pagoda and surrounding square in Bhaktapur. Follow local rules for access.',
'YS011':'Spend time by Phewa Lake and explore boating opportunities around the lakeside. Check conditions and use suitable safety equipment.',
'YS012':'Plan a quieter lakeside visit at Begnas Lake, with boating subject to local availability and conditions.',
'YS013':'Explore the Sarangkot viewpoint and walking routes. Adventure activities depend on operators, conditions and current local permissions.',
'YS014':'Visit Pokhara’s hilltop peace pagoda, with views over the surrounding landscape and a walking approach.',
'YS015':'Explore the waterfall visitor area in Pokhara and follow the designated paths and barriers.',
'YS016':'Annapurna Base Camp is a mountain trekking destination. A map pin marks the destination, not a complete trekking route; plan permits, guides, acclimatisation and weather separately.',
'YS017':'Everest Base Camp is a high-altitude trekking destination. Allow time for acclimatisation and confirm access, permits and local conditions.',
'YS018':'Explore Namche Bazaar as part of a carefully planned mountain journey, with time to acclimatise and learn about the surrounding communities.',
'YS019':'Explore Langtang Valley through a planned mountain trek. The map shows an approximate visitor point within a larger region.',
'YS020':'Mardi Himal Base Camp is a mountain trekking destination. Confirm route conditions, access and altitude preparation with local guidance.'}
class Command(BaseCommand):
    help='Create missing demo destinations and photos without overwriting admin edits.'
    @transaction.atomic
    def handle(self,*args,**options):
        catalog=list(csv.DictReader((ROOT/'data/processed/catalog.csv').open(encoding='utf-8')))
        media=json.loads((ROOT/'data/raw/media_manifest.json').read_text(encoding='utf-8'))
        for row in catalog:
            m=media[row['destination_id']]
            defaults={'name':row['destination_name'],'area':row['area'],'destination_type':row['destination_type'],'description':DESCRIPTIONS[row['destination_id']],'latitude':m['latitude'],'longitude':m['longitude'],'coordinate_source':m['coordinate_source'],'popularity_score':float(row['popularity_score']),'specific_activities':row['specific_activities'],**{a:row[a]=='1' for a in ACTIVITIES}}
            dest,created=Destination.objects.get_or_create(id=row['destination_id'],defaults=defaults)
            if created:
                for i,p in enumerate(m['photos']):DestinationPhoto.objects.create(destination=dest,image=p['file'],caption=p['caption'][:300],credit=p['credit'][:400],license=p['license'][:150],source_url=p['source_url'],position=i)
        self.stdout.write(self.style.SUCCESS(f'{Destination.objects.count()} destinations ready. Existing admin edits preserved.'))
