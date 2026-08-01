from django.urls import path
from django.contrib.auth import views as auth_views
from .views import dashboard_redirect_view, register_view

app_name = 'accounts'

urlpatterns = [
    path('register/', register_view, name='register'),
    path('', dashboard_redirect_view, name='dashboard_redirect'), # Root URL redirects based on role
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]