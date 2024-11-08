from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    post_list_view,
    post_detail_view,
    post_create_view,
    post_update_view,
    post_delete_view,
    choose_database_view,
    main_menu_view,
    insert_links_view,
    remove_data_view,
    update_data_view,
    generate_document_view,
    create_post_from_text,
)

urlpatterns = [
    path('', post_list_view, name='blog-home'),
    path('post/new/', post_create_view, name='post-create'),
    path('post/<int:pk>/', post_detail_view, name='post-detail'),
    path('post/<int:pk>/update/', post_update_view, name='post-update'),
    path('post/<int:pk>/delete/', post_delete_view, name='post-delete'),
    path('choose_database/', choose_database_view, name='choose_database'),
    path('main_menu/', main_menu_view, name='main_menu'),
    path('insert_links/', insert_links_view, name='insert_links'),
    path('remove_data/', remove_data_view, name='remove_data'),
    path('update_data/', update_data_view, name='update_data'),
    path('generate_document/', generate_document_view, name='generate_document'),
    path('post/create_from_text/', create_post_from_text, name='create_post_from_text'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)