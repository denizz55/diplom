from django.urls import path
from . import views
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from .views import logout_view
from .views import profile_view, cancel_booking

urlpatterns = [
    path('', views.concert_list, name='concert_list'),
    path('<int:id>/', views.concert_detail, name='concert_detail'),
    path('book/<int:seat_id>/', views.book_seat, name='book_seat'),  # Этот маршрут для бронирования
    path('booking/<int:seat_id>/', views.seat_selection, name='seat_selection'),  # Новый маршрут для формы бронирования
    path('payment/<int:seat_id>/', views.payment_view, name='payment'),  # Маршрут для страницы оплаты
    path('payment/success/<str:payment_id>/', views.payment_success, name='payment_success'),  # Страница успешной оплаты
    path('cancel_booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('register/', views.register, name='register'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('about/', views.about_us, name='about_us'),
    path('contacts/', views.contacts, name='contacts'),  # Новый маршрут для страницы "Контакты"
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),  # Новый маршрут для страницы "Политика конфиденциальности"
    
    # Review URLs
    path('<int:concert_id>/review/add/', views.add_review, name='add_review'),
    path('review/<int:review_id>/edit/', views.edit_review, name='edit_review'),
    path('review/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    
    # API для поиска концертов
    path('api/search-concerts/', views.search_concerts_api, name='search_concerts_api'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('concert/<int:concert_id>/delete/', views.delete_concert, name='delete_concert'),
    path('concert/<int:concert_id>/edit/', views.edit_concert, name='edit_concert'),
]
