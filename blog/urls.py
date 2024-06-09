from django.urls import path
from . import views
from .views import PostListView, PostDetailView, PostCreateView

urlpatterns = [
    path('', PostListView.as_view(), name='blog-home'),
    path('post/<int:pk>/', PostDetailView.as_view(), name='post_detail'),
    path('post/new/', PostCreateView.as_view(), name='post-create'),
    path('choose_database/', views.choose_database_view, name='choose_database'),
    path('main_menu/', views.main_menu_view, name='main_menu'),
    path('insert_links/', views.insert_links_view, name='insert_links'),
    path('remove_data/', views.remove_data_view, name='remove_data'),
    path('update_data/', views.update_data_view, name='update_data'),
    path('generate_document/', views.generate_document_view, name='generate_document'),
]
