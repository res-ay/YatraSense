from pathlib import Path
from io import BytesIO
from unittest.mock import patch
import tempfile
from PIL import Image
from django.test import TestCase,override_settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from fastapi.testclient import TestClient
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from ml_service.main import app
from .models import Destination,DestinationPhoto,Trip

class ServiceResponse:
    def __init__(self,response):self.response=response
    def raise_for_status(self):self.response.raise_for_status()
    def json(self):return self.response.json()

class IntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command
        call_command('seed_demo',verbosity=0)
        cls.user=User.objects.create_user('traveller',password='a-strong-test-password')
        cls.other=User.objects.create_user('other',password='another-strong-password')
        cls.admin=User.objects.create_superuser('admin-test',email='admin@example.com',password='admin-test-password')
    def setUp(self):self.client=APIClient();self.fast=TestClient(app)
    def bridge(self,url,json,timeout):
        self.assertTrue(url.endswith('/predict'))
        return ServiceResponse(self.fast.post('/predict',json=json))
    def test_catalog_photos_coordinates_and_files(self):
        response=self.client.get('/api/destinations/')
        self.assertEqual(response.status_code,200);self.assertEqual(len(response.data),20)
        for d in response.data:
            self.assertEqual(len(d['photos']),3)
            self.assertTrue(26<d['latitude']<31);self.assertTrue(80<d['longitude']<89)
        for p in DestinationPhoto.objects.all():self.assertTrue(Path(p.image.path).is_file())
        self.assertEqual(self.client.get('/api/destinations/YS002/').data['name'],'Boudhanath')
    def test_model_contract_and_invalid_input(self):
        self.assertEqual(self.fast.get('/health').status_code,200)
        self.assertEqual(self.client.post('/api/plan/',{'travel_date':'bad','activities':[]},format='json').status_code,400)
        self.assertEqual(self.client.post('/api/plan/',{'travel_date':'2026-10-15','activities':['invalid']},format='json').status_code,400)
    @patch('travel.views.requests.post')
    def test_real_models_through_django_and_crowd_filter(self,post):
        post.side_effect=self.bridge
        payload={'travel_date':'2026-10-15','activities':['heritage_pilgrimage'],'crowd_preference':'Any','area':'All'}
        response=self.client.post('/api/plan/',payload,format='json')
        self.assertEqual(response.status_code,200)
        self.assertGreater(len(response.data['results']),0)
        scores=[r['recommendation_score'] for r in response.data['results']]
        self.assertEqual(scores,sorted(scores,reverse=True))
        for item in response.data['results']:
            self.assertIn('heritage_pilgrimage',item['matched_activities'])
            self.assertEqual(len(item['destination']['photos']),3)
            self.assertIn(item['crowd'],['Low','Medium','High'])
        payload['crowd_preference']='Low'
        payload['travel_date']='2026-01-15'
        quiet=self.client.post('/api/plan/',payload,format='json')
        self.assertGreater(len(quiet.data['results']),0)
        self.assertTrue(all(r['crowd']=='Low' for r in quiet.data['results']))
        payload['activities']=['wildlife_birdwatching']
        empty=self.client.post('/api/plan/',payload,format='json')
        self.assertEqual(empty.data['results'],[]);self.assertTrue(empty.data['message'])
    @patch('travel.views.requests.post')
    def test_accounts_saved_trip_ownership(self,post):
        post.side_effect=self.bridge
        payload={'travel_date':'2026-11-15','activities':['boating_water'],'save':True}
        self.assertEqual(self.client.post('/api/plan/',payload,format='json').status_code,401)
        login=self.client.post('/api/auth/login/',{'username':'traveller','password':'a-strong-test-password'},format='json')
        self.assertEqual(login.status_code,200)
        self.client.credentials(HTTP_AUTHORIZATION='Token '+login.data['token'])
        response=self.client.post('/api/plan/',payload,format='json');self.assertEqual(response.status_code,200)
        tid=response.data['saved_trip_id'];self.assertTrue(Trip.objects.filter(id=tid,user=self.user).exists())
        self.assertEqual(self.client.get('/api/profile/').data['trip_count'],1)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.delete(f'/api/trips/{tid}/').status_code,404)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.delete(f'/api/trips/{tid}/').status_code,204)
    def test_admin_destination_crud_and_photo_upload(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/admin/travel/destination/').status_code,200)
        self.assertEqual(self.client.get('/admin/travel/destination/YS002/change/').status_code,200)
        place=Destination.objects.create(name='Admin-added place',area='Kathmandu',latitude=27.7,longitude=85.3,heritage_pilgrimage=True)
        place.description='An edited description';place.save();place.refresh_from_db()
        self.assertEqual(place.description,'An edited description')
        buffer=BytesIO();Image.new('RGB',(20,20),'green').save(buffer,'PNG')
        with tempfile.TemporaryDirectory() as directory,override_settings(MEDIA_ROOT=directory):
            photo=DestinationPhoto(destination=place,image=SimpleUploadedFile('uploaded.png',buffer.getvalue(),content_type='image/png'))
            photo.full_clean();photo.save();self.assertTrue(Path(photo.image.path).exists())
            place.delete();self.assertFalse(DestinationPhoto.objects.filter(pk=photo.pk).exists())
    @patch('travel.views.requests.post')
    def test_new_admin_place_gets_explicit_unvalidated_estimate(self,post):
        post.side_effect=self.bridge
        place=Destination.objects.create(name='New heritage place',area='Kathmandu',latitude=27.7,longitude=85.3,heritage_pilgrimage=True,popularity_score=90)
        response=self.client.post('/api/plan/',{'travel_date':'2026-10-15','activities':['heritage_pilgrimage']},format='json')
        item=next(r for r in response.data['results'] if r['destination_id']==place.id)
        self.assertTrue(item['new_destination']);self.assertIn('Unvalidated',item['estimate_note'])
    @patch('travel.views.requests.post')
    def test_ml_outage_returns_clear_error(self,post):
        import requests
        post.side_effect=requests.ConnectionError('offline')
        response=self.client.post('/api/plan/',{'travel_date':'2026-10-15','activities':['heritage_pilgrimage']},format='json')
        self.assertEqual(response.status_code,503);self.assertIn('FastAPI',response.data['detail'])
