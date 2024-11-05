"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path
from blog.views import (RegisterView, LoginView, BlogPost, GetBlogs,UpdatePost,DeletePost,SaveBlog,getSavedBlogs,deleteSaveBlog)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/register', RegisterView.as_view(), name='auth_register'),
    path('api/auth/login', LoginView.as_view(), name='auth_login'),
     path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/blogs/post', BlogPost.as_view(), name='blog_post'),
    path('api/blogs/', GetBlogs.as_view(), name='get_blogs'),
    path('api/blogs/edit', UpdatePost.as_view(), name='update_post'),
    path('api/blogs/delete/<int:id>/', DeletePost.as_view(), name='delete_post'),
    path('api/blogs/save/<int:blogID>/<int:userID>/', SaveBlog.as_view(), name='delete_post'),
    path('api/blogs/saved/<int:userID>/', getSavedBlogs.as_view(), name='get_saved_blogs'),
    path('api/blogs/saved/remove/<int:blogID>/', deleteSaveBlog.as_view(), name='remove_saved_blog'),
    
]

urlpatterns += staticfiles_urlpatterns()