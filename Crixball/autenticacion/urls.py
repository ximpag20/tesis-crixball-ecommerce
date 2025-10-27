from django.urls import path
from . import views

#urlpatterns = [
 #   path('', views.index),
  #  path('about/', views.about),
   # path('hello/<str:username>', views.TituloPrincipal)
#]

urlpatterns = [
    path ('', views.Autenticacion, name='Autenticacion'),
]