"""Views for Synapse Chat."""
import json
import logging
import re

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.serializers.json import DjangoJSONEncoder

from .mongo_store import mongo_store
from .ai_engine import get_ai_response, reset_agent
from .otp_service import otp_service

logger = logging.getLogger(__name__)

# TODO: Add rate limiting (e.g. django-ratelimit) to send_otp_view,
#       verify_signup_view, login_view, and ai_chat_endpoint to prevent
#       brute-force and abuse.  Placeholder for future implementation.


def landing_view(request):
    return render(request, 'chat/landing.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('chat')
    error = None
    if request.method == 'POST':
        user = authenticate(request,
                            username=request.POST.get('username', ''),
                            password=request.POST.get('password', ''))
        if user:
            login(request, user)
            return redirect('chat')
        error = 'Invalid username or password.'
    return render(request, 'chat/login.html', {'error': error})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('chat')
    from django.conf import settings as s
    return render(request, 'chat/signup.html', {
        'emailjs_service_id':  s.EMAILJS_SERVICE_ID  or '',
        'emailjs_template_id': s.EMAILJS_TEMPLATE_ID or '',
        'emailjs_public_key':  s.EMAILJS_PUBLIC_KEY  or '',
    })


@require_POST
def send_otp_view(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    email    = data.get('email', '').strip()
    username = data.get('username', '').strip()

    if not email or not username:
        return JsonResponse({'status': 'error', 'message': 'Email and Username are required.'})

    # Basic email validation
    if '@' not in email or not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return JsonResponse({'status': 'error', 'message': 'Invalid email address.'})

    from django.contrib.auth.models import User
    if User.objects.filter(username=username).exists():
        return JsonResponse({'status': 'error', 'message': 'Username already taken.'})
    if User.objects.filter(email=email).exists():
        return JsonResponse({'status': 'error', 'message': 'Email already registered.'})

    try:
        otp = otp_service.generate_otp()
        otp_service.store_otp(email, otp)
    except Exception:
        logger.error("Failed to generate/store OTP for email=%s", email, exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Failed to generate OTP. Please try again.'})

    # SECURITY: Never return the OTP value in the response.
    return JsonResponse({'status': 'success', 'message': 'OTP sent to your email.'})


@require_POST
def verify_signup_view(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    username = data.get('username', '').strip()
    email    = data.get('email', '').strip()
    password = data.get('password', '')
    otp      = data.get('otp', '').strip()

    if not all([username, email, password, otp]):
        return JsonResponse({'status': 'error', 'message': 'All fields are required.'})

    if not otp_service.verify_otp(email, otp):
        return JsonResponse({'status': 'error', 'message': 'Invalid or expired OTP.'})

    from django.contrib.auth.models import User
    from django.conf import settings
    if User.objects.count() >= settings.MAX_USERS:
        return JsonResponse({'status': 'error',
                             'message': f"Beta limit reached ({settings.MAX_USERS} users max)."})
    try:
        User.objects.create_user(username=username, password=password, email=email)
        return JsonResponse({'status': 'success', 'message': 'Account created!'})
    except Exception:
        logger.error("Failed to create user username=%s", username, exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Failed to create account. Please try again.'})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def chat_view(request):
    stats = mongo_store.get_user_chat_stats(str(request.user.id))
    return render(request, 'chat/index.html', {
        'sessions': mongo_store.get_sessions(request.user.id),
        'user':     request.user,
        'chat_stats': stats,
    })


@require_POST
@login_required
def new_session_view(request):
    reset_agent(request.user.id)
    session_id = mongo_store.create_session(request.user.id)
    return JsonResponse({'status': 'success', 'session_id': session_id, 'title': 'New Chat'})


@login_required
def session_messages_view(request, session_id):
    session = mongo_store.get_session(session_id, request.user.id)
    if not session:
        return JsonResponse({'status': 'error', 'message': 'Session not found.'}, status=404)
    return JsonResponse({'status': 'success',
                         'messages': mongo_store.get_messages(session_id),
                         'title':    session['title']},
                        encoder=DjangoJSONEncoder)


@require_POST
@login_required
def delete_session_view(request, session_id):
    if mongo_store.delete_session(session_id, request.user.id):
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Session not found.'}, status=404)


@require_POST
@login_required
def rename_session_view(request, session_id):
    """Rename an existing chat session."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    title = data.get('title', '').strip()
    if not title:
        return JsonResponse({'error': 'Title required'}, status=400)

    try:
        mongo_store.update_session_title(session_id, title)
        return JsonResponse({'status': 'success'})
    except Exception:
        logger.error("Failed to rename session=%s", session_id, exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Failed to rename session.'}, status=500)


@require_POST
@login_required
def clear_session_view(request, session_id):
    """Delete all messages in a session without deleting the session itself."""
    try:
        mongo_store.delete_session_messages(session_id)
        return JsonResponse({'status': 'success'})
    except Exception:
        logger.error("Failed to clear session=%s", session_id, exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Failed to clear session.'}, status=500)


@require_POST
@login_required
def delete_message_view(request, message_id):
    """Delete a specific message by its ID."""
    try:
        mongo_store.delete_message(message_id)
        return JsonResponse({'status': 'success'})
    except Exception:
        logger.error("Failed to delete message=%s", message_id, exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Failed to delete message.'}, status=500)


@login_required
def get_settings_view(request):
    s = mongo_store.get_user_settings(request.user.id)
    s.pop('_id', None)
    return JsonResponse({'status': 'success', 'settings': s}, encoder=DjangoJSONEncoder)


@require_POST
@login_required
def update_settings_view(request):
    try:
        data = json.loads(request.body)
        mongo_store.update_user_settings(
            request.user.id,
            data.get('preferred_language', 'Python'),
            data.get('personal_api_key', '').strip()
        )
        reset_agent(request.user.id)
        return JsonResponse({'status': 'success'})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception:
        logger.error("Failed to update settings for user=%s", request.user.id, exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Failed to update settings.'})


@require_POST
@login_required
async def ai_chat_endpoint(request):
    try:
        data    = json.loads(request.body)
        message = data.get('message', '').strip()
        if not message:
            return JsonResponse({'status': 'error', 'message': 'Empty message.'})
        response = await get_ai_response(request.user.id, message)
        return JsonResponse({'status': 'success', 'response': response},
                            encoder=DjangoJSONEncoder)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)
    except Exception:
        logger.error("AI chat error for user=%s", request.user.id, exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'An internal error occurred.'})


@login_required
def chat_stats_view(request):
    """Return the current user's daily chat usage stats for the live UI counter."""
    mongo_user = mongo_store.get_user_by_username(request.user.username)
    if not mongo_user:
        return JsonResponse({
            'status': 'success',
            'daily_count': 0,
            'daily_limit': 50,
            'total_chats': 0,
        })
    stats = mongo_store.get_user_chat_stats(mongo_user['id'])
    if not stats:
        return JsonResponse({
            'status': 'success',
            'daily_count': 0,
            'daily_limit': 50,
            'total_chats': 0,
        })
    return JsonResponse({
        'status': 'success',
        'daily_count': stats['daily_count'],
        'daily_limit': stats['daily_limit'],
        'total_chats': stats['total_chats'],
    })