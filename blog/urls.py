from django.urls import path
from .views import get_blogs,register_user,login_user,post_blog,update_blog,delete_blog,save_blog, delete_save_blog,get_saved_blogs

urlpatterns = [
     path('blogs/', get_blogs, name='get_blogs'),
     path('login/', login_user, name='login_user'),
     path('register/', register_user, name='register_user'),
     path('post/', post_blog, name='post_blog'),
     path('edit/<str:id>', update_blog, name='update_blog'),
     path('delete/<str:id>', delete_blog, name='delete_blog'),
     path('savedBlogs/<str:id>/<str:userid>', save_blog, name='save_blog'),
     path('savedBlogs/remove/<str:userid>/<str:blogid>', delete_save_blog, name='delete_save_blog'),
     path('savedBlogs/<str:userID>', get_saved_blogs, name='get_saved_blogs')
]
