from django.urls import path
from django.conf import settings
from django.conf.urls.static import static 

from . import views  

urlpatterns = [
    path('home/' , views.home, name='home'),  
    path('Imge/' , views.Imge, name='Imge'), 
    path('Vdeo/' , views.Vdeo, name='Vdeo'), 
    path('Adio/' , views.Adio, name='Adio'),  
    path('map/' , views.map, name='map'),  
    path('charted/' , views.charted, name='charted'),   
    path('english/' , views.english, name='english'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
