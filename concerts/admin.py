from django.contrib import admin
from .models import Concert, Seat, Review

admin.site.register(Concert)
admin.site.register(Seat)
admin.site.register(Review)
