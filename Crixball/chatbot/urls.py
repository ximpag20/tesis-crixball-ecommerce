from django.urls import path
from . import views

urlpatterns = [
    path('', views.Chatbot, name='Chatbot'),  # Página HTML del chatbot
    path('dialogflow/', views.dialogflow_chat, name='dialogflow_chat'),  # API del chatbot
    path('historial/', views.obtener_historial_chat, name='obtener_historial_chat'),

]
