from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('records/', views.record_list, name='record_list'),
    path('records/add/', views.add_record, name='add_record'),
    path('records/upload-csv/', views.upload_csv, name='upload_csv'),
    path('records/download-template/', views.download_csv_template, name='download_csv_template'),
    path('charts/', views.charts, name='charts'),
]