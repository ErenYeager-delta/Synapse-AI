"""URL routing for Synapse chat app."""
from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # Pages
    path('',        views.landing_view, name='landing'),
    path('chat/',   views.chat_view,    name='chat'),
    path('login/',  views.login_view,   name='login'),
    path('signup/', views.signup_view,  name='signup'),
    path('logout/', views.logout_view,  name='logout'),

    # Auth API
    path('api/auth/send-otp/',      views.send_otp_view,      name='send_otp'),
    path('api/auth/verify-signup/', views.verify_signup_view, name='verify-signup'),

    # AI Chat
    path('api/chat/', views.ai_chat_endpoint, name='ai_chat'),

    # Settings
    path('api/settings/',        views.get_settings_view,    name='get-settings'),
    path('api/settings/update/', views.update_settings_view, name='update-settings'),

    # Usage
    path('api/usage/', views.get_usage_view, name='get-usage'),

    # Sessions — FIX: <str:session_id> was missing, caused 404 on every chat load
    path('api/sessions/new/',                          views.new_session_view,      name='new_session'),
    path('api/sessions/<str:session_id>/messages/',    views.session_messages_view, name='session_messages'),
    path('api/sessions/<str:session_id>/delete/',      views.delete_session_view,   name='delete_session'),
    path('manifest.json',                              views.manifest_view,         name='manifest'),
    
    # Root-level Favicon Support (Visual Excellence)
    path('favicon.ico', RedirectView.as_view(url='/static/chat/images/favicon.ico', permanent=True)),
]
