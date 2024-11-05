from django.shortcuts import render
from rest_framework import generics
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny,IsAuthenticated
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, BlogSerializer, CustomTokenObtainPairSerializer, SavedBlogSerializer
from .models import Blog, Image,SavedBlog
import base64
from uuid import uuid4
import boto3
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
# Create your views here.

s3 = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = (AllowAny,)
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            token_serializer = CustomTokenObtainPairSerializer()
            refresh = token_serializer.get_token(user)
            user_serializer = UserSerializer(user)  
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': user_serializer.data                
            }, status=200)
        else:
            return Response({'detail': 'Invalid credentials'}, status=401)

class BlogPost(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        title = request.data.get('title')
        content = request.data.get('content')
        image_base64 = request.data.get('image')
        user_id = request.data.get('userID')  # Follow Python convention for variable names

        # Decode base64 image
        try:
            format, imgstr = image_base64.split(';base64,')
            ext = format.split('/')[-1]
            img_data = base64.b64decode(imgstr)
        except (ValueError, AttributeError):
            return Response({"error": "Invalid image data"}, status=400)

        # Generate a unique filename
        filename = f"{uuid4()}.{ext}"

        # Upload to S3
        s3.put_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=f"media/blog_images/{filename}",
            Body=img_data,
            ContentType=f"image/{ext}",
        )

        # Construct the S3 image URL
        image_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/media/blog_images/{filename}"

        # Create the Image object
        blog_image = Image.objects.create(
            url=image_url,
            public_id=filename
        )

        # Get the User object for the specified user_id
        try:
            author = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        # Create the Blog object
        new_post = Blog.objects.create(
            title=title,
            content=content,
            image=blog_image,
            author=author
        )

        return Response({"message": "Blog posted successfully!", "post_id": new_post.id}, status=201)

class GetBlogs(APIView):
    permission_classes = (AllowAny,)
    
    def get(self, request, *args, **kwargs):
        blogs = Blog.objects.all()
        serializer = BlogSerializer(blogs, many=True)
       
        
        return Response(serializer.data)

class UpdatePost(APIView):
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        title = request.data.get('title')
        content = request.data.get('content')
        image_base64 = request.data.get('image')
        blog_id = request.data.get('id')
        logger.info(f"Updating blog post with ID: {blog_id}")

        try:
            blog_post = Blog.objects.get(id=blog_id, author=request.user)
            blog_image = blog_post.image
        except Blog.DoesNotExist:
            return Response({"error": "Blog post not found or you do not have permission to edit it."}, status=404)
        except Image.DoesNotExist:
            return Response({"error": "Image not found."}, status=404)

        blog_post.title = title
        blog_post.content = content

        if image_base64:
            try:
                format, imgstr = image_base64.split(';base64,')
                ext = format.split('/')[-1]
                img_data = base64.b64decode(imgstr)
                logger.info("Image decoded successfully")
            except (ValueError, AttributeError) as e:
                logger.error("Image decoding failed")
                return Response({"error": "Invalid image data"}, status=400)

            filename = blog_image.public_id
            try:
                s3.put_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Key=f"media/blog_images/{filename}",
                    Body=img_data,
                    ContentType=f"image/{ext}",
                )
                logger.info("Image uploaded successfully to S3")
            except Exception as e:
                logger.error("S3 upload failed: %s", str(e))
                return Response({"error": "Image upload failed"}, status=500)

            image_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/media/blog_images/{filename}"
            blog_image.url = image_url
            blog_image.save()
            logger.info(f"Image URL updated in database: {image_url}")

        blog_post.save()
        logger.info(f"Blog post with ID {blog_id} updated successfully")

        return Response({"message": "Blog post updated successfully!", "post_id": blog_post.id}, status=200)

class DeletePost(APIView):
    permission_classes = (IsAuthenticated,)

    def delete(self, request, *args, **kwargs):
        blog_id = self.kwargs.get('id')
       
        try:
            # Retrieve the blog post
            blog = Blog.objects.get(pk=blog_id, author=request.user)
            image = blog.image  # Access the related Image instance
            
            # Delete the image from S3
            try:
                s3.delete_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Key=f"media/blog_images/{image.public_id}"
                )
                logger.info(f"Deleted image {image.public_id} from S3.")
                
                # Delete the image record from the database
                image.delete()
            except Exception as e:
                logger.error(f"Failed to delete image from S3: {e}")
                return Response({"error": "Failed to delete image from S3"}, status=500)
            
            # Delete the blog post
            blog.delete()
            logger.info(f"Deleted blog post with ID {blog_id}.")
            return Response({"message": "Blog post deleted successfully!"}, status=204)
        
        except Blog.DoesNotExist:
            return Response({"error": "Blog post not found or you do not have permission to delete it."}, status=404)
        except Image.DoesNotExist:
            return Response({"error": "Image not found."}, status=404)
        
class SaveBlog(APIView):
    permission_classes = (AllowAny,)
    def put(self, request, *args, **kwargs):
        blogID = self.kwargs.get('blogID')
        userID = self.kwargs.get('userID')
        
        try:
            blog = Blog.objects.get(pk=blogID)
            user = User.objects.get(pk=userID)
            blog_saved = SavedBlog.objects.create(
                blog = blog,
                saved_by = user
            )
            
            return Response({"message": "Blog post saved successfully!", "post_id": blog_saved.id}, status=200)
        except Blog.DoesNotExist:
            return Response({"error": "Blog post not found or you do not have permission to delete it."}, status=404)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=404)

class getSavedBlogs(APIView):
    permission_classes = (AllowAny,)
    def get(self, request, *args, **kwargs):
        userID = self.kwargs.get('userID')
        blogs = SavedBlog.objects.filter(saved_by_id=userID)
        serializer = SavedBlogSerializer(blogs, many=True)
       
        
        return Response(serializer.data)

class deleteSaveBlog(APIView):
    permission_classes = (IsAuthenticated,)
    
    def delete(self, request, *args, **kwargs):
        blogID = self.kwargs.get('blogID')
        
        blog = SavedBlog.objects.get(pk = blogID)
        
        blog.delete()
        
        return Response({"message": "Blog removed from saved!", "post_id": blog.id}, status=200)
        
        