# models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Post(models.Model):
    title = models.CharField(max_length=100, default='Default Title')  # Adicione 'default' temporariamente
    content = models.TextField()
    date_posted = models.DateTimeField(default=timezone.now)  # Adicione 'default' temporariamente
    author = models.ForeignKey(User, on_delete=models.CASCADE, default=1)  # Adicione 'default' temporariamente

    def __str__(self):
        return self.title

class PostImage(models.Model):
    post = models.ForeignKey(Post, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='generated_images/')

    def __str__(self):
        return f"Image for post {self.post.title}"
