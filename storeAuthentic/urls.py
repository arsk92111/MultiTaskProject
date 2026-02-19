from django.urls import path
from django.conf import settings
from django.conf.urls.static import static 

from . import views  

urlpatterns = [
    path('' , views.logIn, name='logIn'),  
    path('register/' , views.register, name='register'),   
    path('loggout/' , views.loggout, name='loggout'), 
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
