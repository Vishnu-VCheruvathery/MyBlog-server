from rest_framework.decorators import api_view, permission_classes  # Import permission_classes here
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.contrib.auth.hashers import make_password, check_password  # Import check_password
from rest_framework_simplejwt.tokens import AccessToken
from db_connection import blog_collection, user_collection
import base64
import boto3
from django.conf import settings
from uuid import uuid4
from bson.objectid import ObjectId

# Initialize S3 client
# Initialize S3 client using credentials from settings.py
s3 = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)

def serialize_blog(blog):
    """
    Convert MongoDB's ObjectId fields to strings so they can be serialized into JSON.
    """
    blog['_id'] = str(blog['_id'])  # Convert the _id to a string
    if 'Author' in blog:
        blog['Author'] = str(blog['Author'])  # Convert the Author ObjectId to a string
    if 'image' in blog and 'public_id' in blog['image']:
        blog['image']['public_id'] = str(blog['image']['public_id'])  # Ensure image public_id is a string
    return blog

# Create your views here.
@api_view(['GET'])
@permission_classes([AllowAny])
def get_blogs(request):
    try:
        blogs_cursor = blog_collection.find()
        blogs = list(blogs_cursor)  # Convert cursor to list

        # Fetch authors for the blogs
        author_ids = [blog['Author'] for blog in blogs if 'Author' in blog]
        authors = user_collection.find({'_id': {'$in': author_ids}})  # Fetch all authors at once
        authors_dict = {str(author['_id']): author['username'] for author in authors}  # Create a mapping

        # Populate the Author field in each blog
        for blog in blogs:
            # Convert Author ObjectId to a dictionary with id and username
            author_id_str = str(blog['Author'])  # Convert ObjectId to string
            blog['Author'] = {
                'id': author_id_str,  # Include author ID as a string
                'username': authors_dict.get(author_id_str, 'Unknown Author')  # Get username or default
            }
            
            # Convert blog fields to string if they are ObjectId or other non-serializable types
            blog['_id'] = str(blog['_id'])  # Convert blog ID to string
            if 'image' in blog:
                blog['image']['public_id'] = str(blog['image'].get('public_id', ''))  # Ensure public_id is a string
                blog['image']['url'] = str(blog['image'].get('url', ''))  # Ensure url is a string

        # Move the return statement outside of the loop
        return JsonResponse(blogs, safe=False)  # Return populated blogs

    except Exception as e:
        print("An error occurred:", str(e))
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    try:
        username = request.data.get('username')
        password = request.data.get('password')

        existing_user = user_collection.find_one({'username': username})
        if existing_user:
            return JsonResponse({'error': 'User already exists!'})

        hashed_password = make_password(password)  # Hash the password using Django's hashers
        user = {
            'username': username,
            'password': hashed_password,
            'savedBlogs': []
        }
        
        user_collection.insert_one(user)  # Insert new user into MongoDB
        return JsonResponse({'message': 'Registration successful!'}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        
        user_data = user_collection.find_one({'username': username})
        
        if not user_data:
            return JsonResponse({'error': 'No user found'})

        # Use Django's check_password to verify the password
        if not check_password(password, user_data['password']):
            return JsonResponse({'error': "Passwords don't match"})

        # Generate JWT token with a custom payload
        token = AccessToken()
        token['id'] = str(user_data['_id'])  # Include the user ID as a string
        token['username'] = user_data['username']  # Include the username

        return JsonResponse({'token': str(token)}, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(["POST"])
@permission_classes([AllowAny])
def post_blog(request):
    try:
        
        title = request.data.get('title')
        content = request.data.get('content')
        image_base64 = request.data.get('image')  # Image as base64 string
        user = request.data.get('userID');
        if not title or not content or not image_base64:
            return Response({'error': 'Title, content, and image are required'}, status=status.HTTP_400_BAD_REQUEST)

        # Decode base64 image
        format, imgstr = image_base64.split(';base64,')  # Separate the format and the image data
        ext = format.split('/')[-1]  # Extract the image extension (e.g., jpg, png)
        
        img_data = base64.b64decode(imgstr)  # Decode the base64 string

        # Generate a unique filename
        filename = f"{uuid4()}.{ext}"

        existing_user = user_collection.find_one({'_': user})

        # Upload to S3
        s3.put_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,  # Get bucket name from settings
            Key=f"media/blog_images/{filename}",  # Path in the bucket
            Body=img_data,
            ContentType=f"image/{ext}",  # Set the correct content type
        )

        # Construct the S3 image URL
        image_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/media/blog_images/{filename}"

        # Create blog entry
        blog = {
            'title': title,
            'content': content,
            'image': {
                'url': image_url,
                'public_id': filename
            },
            'Author': ObjectId(user)
        }

        # Insert blog into MongoDB
        blog_collection.insert_one(blog)

        return JsonResponse({'message': 'Blog added successfully!'}, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(["PUT"])
@permission_classes([AllowAny])
def update_blog(request, id):
    try:
        # Find the existing blog
        blog = blog_collection.find_one({'_id': ObjectId(id)})
        if not blog:
            return JsonResponse({'error': 'Blog not found'}, status=404)

        # Get updated fields from the request
        title = request.data.get('title')
        content = request.data.get('content')
        image_base64 = request.data.get('image')  # Image as base64 string

        # Decode base64 image if provided
        if image_base64:
            format, imgstr = image_base64.split(';base64,')  # Separate format and image data
            ext = format.split('/')[-1]  # Extract image extension (e.g., jpg, png)
            img_data = base64.b64decode(imgstr)  # Decode the base64 string
            
            filename = blog["image"]["public_id"].split('.')[0]  # Keep original filename without extension
            
            # Generate new filename
            new_filename = f"{filename}.{ext}"
            
            # Upload the new image to S3
            s3.put_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=f"media/blog_images/{new_filename}",
                Body=img_data,
                ContentType=f"image/{ext}",
            )
            
            # Generate the new image URL
            image_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/media/blog_images/{new_filename}"
            
            # Update image details
            image_data = {
                'url': image_url,
                'public_id': new_filename
            }
        else:
            image_data = blog.get('image')  # Keep the original image data if no new image is provided

        # Prepare the updated blog document
        new_blog_data = {
            'title': title,
            'content': content,
            'image': image_data,  # Use either new or original image data
            'Author': blog["Author"],  # Keep original author
        }

        # Update the blog using $set to modify specific fields
        blog_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": new_blog_data}
        )
        
        return JsonResponse({'message': 'Blog updated successfully!'}, status=200)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(["DELETE"])
@permission_classes([AllowAny])
def delete_blog(request, id):
    try:
        
        blog = blog_collection.find_one({'_id': ObjectId(id)})
        if not blog:
            return JsonResponse({'error': 'Blog not found'}, status=404)
        file_key = f"media/blog_images/{blog['image']['public_id']}"
        s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=file_key)
        blog_collection.find_one_and_delete({'_id': ObjectId(id)})
        return JsonResponse({'message': 'Blog deleted successfully'}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(["PUT"])
@permission_classes([AllowAny])
def save_blog(request, id, userid):
    try:
        # Assuming you have user_collection defined correctly
        blog = blog_collection.find_one({'_id': ObjectId(id)})
        if not blog:
            return JsonResponse({'error': 'Blog not found'}, status=404)
        
        user_collection.update_one(
            {"_id": ObjectId(userid)},  # Locate the user by their ID
            {"$push": {"savedBlogs": ObjectId(id)}}  # Push the blog ID to the savedBlogs array
        )
        return JsonResponse({'message': 'Blog saved successfully'}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@api_view(["GET"])
@permission_classes([AllowAny])
def get_saved_blogs(request, userID):
    try:
        # Validate if the userID is a valid ObjectId
        if not ObjectId.is_valid(userID):
           
            return JsonResponse({'error': 'Invalid userID format'}, status=400)

        # Find the user by userID
        user = user_collection.find_one({"_id": ObjectId(userID)})
        if not user:    
            return JsonResponse({'error': 'User not found'}, status=404)
        savedBlogs = []

        # Iterate over saved blog IDs and fetch the corresponding blogs
        for blog_id in user.get("savedBlogs", []):
         
            if ObjectId.is_valid(blog_id):  # Check if blog_id is valid
                blog = blog_collection.find_one({"_id": ObjectId(blog_id)})
                if blog:
                   
                    # Convert ObjectIds in the blog to strings
                    serialized_blog = serialize_blog(blog)
                    savedBlogs.append(serialized_blog)  # Append the serialized blog
                else:
                    print("Blog not found for blog_id:", blog_id)
            else:
                print("Invalid blog_id:", blog_id)
        

        return JsonResponse(savedBlogs, safe=False)  # Return the list of blogs

    except Exception as e:
        print("An error occurred:", str(e))
        return JsonResponse({'error': str(e)}, status=500)
        

@api_view(["DELETE"])
@permission_classes([AllowAny])
def delete_save_blog(request, userid, blogid):
    try:
            # Assuming you have user_collection defined correctly
        blog = blog_collection.find_one({'_id': ObjectId(blogid)})
        if not blog:
            return JsonResponse({'error': 'Blog not found'}, status=404)
        # Assuming you have user_collection defined correctly
        user_collection.update_one(
            {"_id": ObjectId(userid)},  # Locate the user by their ID
            {"$pull": {"savedBlogs": ObjectId(blogid)}}  # Push the blog ID to the savedBlogs array
        )
        return JsonResponse({'message': 'Blog removed from saved!'}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    