from django.conf import settings
from django.conf.urls.static import static 
from . import views  
from django.urls import path 
urlpatterns = [
    path('chatbot/' , views.chatbot, name='chatbot'),    
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)