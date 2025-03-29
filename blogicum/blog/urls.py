from django.urls import path
from django.urls import include

from . import views


app_name = 'blog'

post_urls = [
    path('<int:post_id>/', views.PostDetailView.as_view(),
         name='post_detail'),
    path('<int:post_id>/edit/', views.PostUpdateView.as_view(),
         name='edit_post'),
    path('<int:post_id>/delete/', views.PostDeleteView.as_view(),
         name='delete_post'),
    path('create/', views.PostCreateView.as_view(), name='create_post'),
    path('<int:post_id>/edit_comment/<int:comment_id>/',
         views.CommentUpdateView.as_view(), name='edit_comment'),
    path('<int:post_id>/delete_comment/<int:comment_id>/',
         views.CommentDeleteView.as_view(), name='delete_comment'),
    path('<int:post_id>/comment/', views.CommentCreateView.as_view(),
         name='add_comment'),
]

urlpatterns = [
    path('', views.PostListView.as_view(), name='index'),
    path('posts/', include(post_urls)),
    path('category/<slug:category_slug>/',
         views.CategoryPostListView.as_view(),
         name='category_posts'),
    path('edit_profile/', views.UserProfileEditView.as_view(),
         name='edit_profile'),
    path('change_password/', views.UserPasswordChangeView.as_view(),
         name='change_password'),
    path('profile/<str:username>/', views.UserProfileView.as_view(),
         name='profile'),
]
