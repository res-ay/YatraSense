from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Destination,DestinationPhoto,Trip
ACTIVITIES=['heritage_pilgrimage','trekking_hiking','wildlife_birdwatching','boating_water','adventure_sports']
class PhotoSerializer(serializers.ModelSerializer):
    class Meta:model=DestinationPhoto;fields=['id','image','caption','credit','license','source_url','position']
class DestinationSerializer(serializers.ModelSerializer):
    photos=PhotoSerializer(many=True,read_only=True)
    activities=serializers.SerializerMethodField()
    popularity=serializers.SerializerMethodField()
    model_coverage=serializers.SerializerMethodField()
    class Meta:model=Destination;fields='__all__'
    def get_activities(self,obj):return [a for a in ACTIVITIES if getattr(obj,a)]
    def get_popularity(self,obj):return 'High' if obj.popularity_score>=70 else 'Medium' if obj.popularity_score>=40 else 'Low'
    def get_model_coverage(self,obj):return 'synthetic_training_catalog' if obj.id.startswith('YS') else 'new_destination_unvalidated'
class PlanSerializer(serializers.Serializer):
    travel_date=serializers.DateField()
    activities=serializers.ListField(child=serializers.ChoiceField(choices=ACTIVITIES),min_length=1,max_length=5)
    crowd_preference=serializers.ChoiceField(choices=['Low','Medium','High','Any'],default='Any')
    area=serializers.ChoiceField(choices=['All','Kathmandu','Lalitpur','Bhaktapur','Pokhara','Mountain regions'],default='All')
    save=serializers.BooleanField(default=False)
class RegisterSerializer(serializers.ModelSerializer):
    password=serializers.CharField(write_only=True,min_length=8)
    class Meta:model=User;fields=['username','email','password']
    def validate_password(self,value):validate_password(value);return value
    def create(self,data):return User.objects.create_user(**data)
class TripSerializer(serializers.ModelSerializer):
    class Meta:model=Trip;exclude=['user']
