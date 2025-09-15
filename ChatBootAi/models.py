import django
from django.db import models

class Conversation(models.Model):
    user_email = models.EmailField(max_length=225)
    user_input = models.TextField(max_length=100000)
    bot_response = models.TextField(max_length=100000)
    created_at = models.DateTimeField(default = django.utils.timezone.now)
    def __str__(self):
        return self.user_input
