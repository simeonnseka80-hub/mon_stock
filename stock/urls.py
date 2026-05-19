from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('mouvements/', views.mouvement_list, name='mouvement_list'),
    path('mouvements/ajouter/', views.mouvement_create, name='mouvement_create'),
    path('mouvements/<int:pk>/facture/', views.facture_pdf, name='facture_pdf'),
    path('export/excel/', views.export_excel, name='export_excel'),
    path('login/', auth_views.LoginView.as_view(template_name='stock/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
