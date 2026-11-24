from django.contrib import admin
from django.utils.html import format_html
from .models import Destination,DestinationPhoto,Trip
class PhotoInline(admin.TabularInline):
    model=DestinationPhoto
    extra=3
    fields=['image','preview','caption','credit','license','source_url','position']
    readonly_fields=['preview']
    def preview(self,obj):
        return format_html('<img src="{}" width="100" style="max-height:70px;object-fit:cover"/>',obj.image.url) if obj.image else 'Upload a photo'
@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display=['name','area','destination_type','popularity_score','photo_count','is_active']
    list_filter=['area','is_active','destination_type']
    search_fields=['name','description']
    inlines=[PhotoInline]
    fieldsets=[('Place',{'fields':['name','area','destination_type','description','is_active']}),('Map',{'fields':['latitude','longitude','coordinate_source']}),('Recommendation features',{'fields':['popularity_score','heritage_pilgrimage','trekking_hiking','wildlife_birdwatching','boating_water','adventure_sports','specific_activities']})]
    def photo_count(self,obj):return obj.photos.count()
@admin.register(DestinationPhoto)
class PhotoAdmin(admin.ModelAdmin):
    list_display=['destination','caption','position','license']
    list_filter=['destination__area']
    search_fields=['destination__name','caption']
@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display=['user','travel_date','area','crowd_preference','created_at']
    list_filter=['area','crowd_preference']
admin.site.site_header='YatraSense Administration'
admin.site.site_title='YatraSense Admin'
admin.site.index_title='Destinations, photos & customer trips'
