import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator,MaxValueValidator,FileExtensionValidator
from django.core.exceptions import ValidationError
def destination_id():return 'CUSTOM-'+uuid.uuid4().hex[:12]
def validate_image_size(value):
    if value.size>10*1024*1024:raise ValidationError('Each photo must be 10 MB or smaller.')
class Destination(models.Model):
    id=models.CharField(primary_key=True,max_length=40,default=destination_id,editable=False)
    name=models.CharField(max_length=160)
    area=models.CharField(max_length=50,choices=[('Kathmandu','Kathmandu'),('Lalitpur','Lalitpur'),('Bhaktapur','Bhaktapur'),('Pokhara','Pokhara'),('Mountain regions','Mountain regions')])
    destination_type=models.CharField(max_length=60,default='Attraction')
    description=models.TextField(blank=True)
    latitude=models.FloatField(validators=[MinValueValidator(-90),MaxValueValidator(90)])
    longitude=models.FloatField(validators=[MinValueValidator(-180),MaxValueValidator(180)])
    coordinate_source=models.CharField(max_length=400,blank=True)
    popularity_score=models.FloatField(default=50,validators=[MinValueValidator(0),MaxValueValidator(100)])
    heritage_pilgrimage=models.BooleanField(default=False)
    trekking_hiking=models.BooleanField(default=False)
    wildlife_birdwatching=models.BooleanField(default=False)
    boating_water=models.BooleanField(default=False)
    adventure_sports=models.BooleanField(default=False)
    specific_activities=models.CharField(max_length=400,blank=True)
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:ordering=['area','name']
    def __str__(self):return f'{self.name} · {self.area}'
class DestinationPhoto(models.Model):
    destination=models.ForeignKey(Destination,on_delete=models.CASCADE,related_name='photos')
    image=models.ImageField(upload_to='destinations/',validators=[validate_image_size,FileExtensionValidator(['jpg','jpeg','png','webp'])])
    caption=models.CharField(max_length=300,blank=True)
    credit=models.CharField(max_length=400,blank=True)
    license=models.CharField(max_length=150,blank=True)
    source_url=models.URLField(max_length=1000,blank=True)
    position=models.PositiveIntegerField(default=0)
    class Meta:ordering=['position','id']
    def __str__(self):return f'{self.destination.name}: {self.caption[:40]}'
class Trip(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='trips')
    travel_date=models.DateField()
    area=models.CharField(max_length=50,default='All')
    activities=models.JSONField(default=list)
    crowd_preference=models.CharField(max_length=10,default='Any')
    results=models.JSONField(default=list)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:ordering=['-created_at']
    def __str__(self):return f'{self.user.username} · {self.travel_date}'
