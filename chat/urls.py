"""URL routing for Synapse chat app."""
from django.urls import path
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

    # Sessions — FIX: <str:session_id> was missing, caused 404 on every chat load
    path('api/sessions/new/',                          views.new_session_view,      name='new_session'),
    path('api/sessions/<str:session_id>/messages/',    views.session_messages_view, name='session_messages'),
    path('api/sessions/<str:session_id>/delete/',      views.delete_session_view,   name='delete_session'),
    path('api/sessions/<str:session_id>/rename/',      views.rename_session_view,   name='rename_session'),
    path('api/sessions/<str:session_id>/clear/',       views.clear_session_view,    name='clear_session'),

    # Messages
    path('api/messages/<str:message_id>/delete/',      views.delete_message_view,   name='delete_message'),

    # Chat stats (live limit counter)
    path('api/chat/stats/',  views.chat_stats_view,  name='chat_stats'),
]
