from django.urls import path,include
from rest_framework.routers import DefaultRouter
from . import views
router=DefaultRouter();router.register('destinations',views.DestinationViewSet)
urlpatterns=[path('',include(router.urls)),path('health/',views.health),path('metrics/',views.metrics),path('plan/',views.plan),path('auth/register/',views.register),path('auth/login/',views.login),path('auth/logout/',views.logout),path('profile/',views.profile),path('trips/<int:pk>/',views.delete_trip)]
