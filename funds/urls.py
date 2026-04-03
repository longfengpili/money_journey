from django.urls import path
from funds.views import record_list, add_record, edit_record, upload_csv, download_csv_template, create_snapshot

app_name = 'funds'

urlpatterns = [
    path('', record_list, name='record_list'),
    path('add/', add_record, name='add_record'),
    path('<int:record_id>/edit/', edit_record, name='edit_record'),
    path('upload-csv/', upload_csv, name='upload_csv'),
    path('download-template/', download_csv_template, name='download_csv_template'),
    # 新增快照路由
    path('create-snapshot/', create_snapshot, name='create_snapshot'),
]