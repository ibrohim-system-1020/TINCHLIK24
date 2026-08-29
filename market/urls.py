from django.urls import path
from . import views

app_name = 'market'

urlpatterns = [
    path('', views.listings, name='listings'),
    path('my/', views.my_listings, name='my_listings'),
    path('create/', views.create_listing, name='create_listing'),
    path('<int:pk>/', views.listing_detail, name='listing_detail'),
    path('<int:pk>/edit/', views.edit_listing, name='edit_listing'),
    path('<int:pk>/delete/', views.delete_listing, name='delete_listing'),
    path('<int:pk>/sold/', views.mark_sold, name='mark_sold'),
]
