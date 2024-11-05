from django.db import models
from django.contrib.auth.models import User

class Image(models.Model):  # Inherit from models.Model
    url = models.URLField()
    public_id = models.CharField(max_length=100)

class Blog(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField(max_length=1000)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)

class SavedBlog(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE)  # Link to Blog instead of duplicating fields
    saved_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_blogs")  # User who saved the blog
    saved_at = models.DateTimeField(auto_now_add=True)  # Optional: Timestamp for when the blog was saved
