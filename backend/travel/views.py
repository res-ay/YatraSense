import requests
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import viewsets
from .models import Destination,Trip
from .serializers import DestinationSerializer,PlanSerializer,RegisterSerializer,TripSerializer

class DestinationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=DestinationSerializer
    queryset=Destination.objects.filter(is_active=True).prefetch_related('photos')
    def get_queryset(self):
        q=super().get_queryset();area=self.request.query_params.get('area');search=self.request.query_params.get('search')
        if area and area!='All':q=q.filter(area=area)
        if search:q=q.filter(name__icontains=search)
        return q
@api_view(['GET'])
def health(request):
    try:
        r=requests.get(settings.ML_SERVICE_URL+'/health',timeout=3);r.raise_for_status();ml=r.json()
    except requests.RequestException:ml={'status':'unavailable'}
    return Response({'database':'sqlite','destinations':Destination.objects.filter(is_active=True).count(),'ml':ml,'synthetic':True})
@api_view(['GET'])
def metrics(request):
    try:
        r=requests.get(settings.ML_SERVICE_URL+'/metrics',timeout=5);r.raise_for_status();return Response(r.json())
    except (requests.RequestException,ValueError):return Response({'detail':'Start the FastAPI service to view model reports.'},status=503)
@api_view(['POST'])
def plan(request):
    serializer=PlanSerializer(data=request.data);serializer.is_valid(raise_exception=True);data=serializer.validated_data
    if data['save'] and not request.user.is_authenticated:return Response({'detail':'Sign in to save this trip.'},status=401)
    destinations=DestinationSerializer(Destination.objects.filter(is_active=True),many=True).data
    payload={'travel_date':data['travel_date'].isoformat(),'activities':data['activities'],'crowd_preference':data['crowd_preference'],'area':data['area'],'destinations':[{'id':d['id'],'name':d['name'],'area':d['area'],'activities':d['activities'],'popularity_score':d['popularity_score'],'is_active':d['is_active']} for d in destinations]}
    if not destinations:return Response({'results':[],'message':'No destinations are available. Ask an administrator to add places.','synthetic':True})
    try:
        r=requests.post(settings.ML_SERVICE_URL+'/predict',json=payload,timeout=30);r.raise_for_status();result=r.json()
    except (requests.RequestException,ValueError):return Response({'detail':'Prediction service is unavailable. Start FastAPI on port 8001 and try again.'},status=503)
    byid={d['id']:d for d in DestinationSerializer(Destination.objects.filter(is_active=True).prefetch_related('photos'),many=True,context={'request':request}).data}
    for item in result['results']:item['destination']=byid.get(item['destination_id'])
    if data['save']:
        trip=Trip.objects.create(user=request.user,travel_date=data['travel_date'],area=data['area'],activities=data['activities'],crowd_preference=data['crowd_preference'],results=result['results'])
        result['saved_trip_id']=trip.id
    return Response(result)
@api_view(['POST'])
def register(request):
    s=RegisterSerializer(data=request.data);s.is_valid(raise_exception=True);user=s.save();token,_=Token.objects.get_or_create(user=user)
    return Response({'token':token.key,'username':user.username},status=201)
@api_view(['POST'])
def login(request):
    user=authenticate(username=request.data.get('username',''),password=request.data.get('password',''))
    if not user:return Response({'detail':'Username or password is incorrect.'},status=400)
    token,_=Token.objects.get_or_create(user=user);return Response({'token':token.key,'username':user.username})
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete();return Response({'detail':'Signed out.'})
@api_view(['GET','PATCH'])
@permission_classes([IsAuthenticated])
def profile(request):
    if request.method=='PATCH':
        email=request.data.get('email',request.user.email)
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            if email:validate_email(email)
        except ValidationError:return Response({'detail':'Enter a valid email address.'},status=400)
        request.user.email=email;request.user.save(update_fields=['email'])
    return Response({'username':request.user.username,'email':request.user.email,'date_joined':request.user.date_joined,'is_staff':request.user.is_staff,'trip_count':request.user.trips.count(),'trips':TripSerializer(request.user.trips.all(),many=True).data})
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_trip(request,pk):
    deleted,_=Trip.objects.filter(pk=pk,user=request.user).delete()
    return Response(status=204) if deleted else Response({'detail':'Trip not found.'},status=404)
