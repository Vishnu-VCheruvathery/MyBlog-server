from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Blog, Image, SavedBlog

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'date_joined')

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email', 'password')
        
    def create(self, validated_data):
        user = User.objects.create_user(
            validated_data['username'],
            validated_data['email'],
            validated_data['password']
        )
        return user
    
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ('id', 'url', 'public_id')

class BlogSerializer(serializers.ModelSerializer):
    image = ImageSerializer()  # Nest the Image serializer here
    author = UserSerializer()
    class Meta:
        model = Blog
        fields = ('id', 'title', 'content', 'image', 'author')

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['username'] = user.username
        
        return token

class SavedBlogSerializer(serializers.ModelSerializer):
    blog = BlogSerializer()
    saved_by = User()
    class Meta:
        model = SavedBlog
        fields = ('id', 'blog', 'saved_by')
