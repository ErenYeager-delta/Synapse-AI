"""Views for Synapse Chat."""
import json, asyncio, logging
logger = logging.getLogger(__name__)
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .mongo_store import mongo_store
from .ai_engine import get_ai_response, reset_agent, get_remaining_chats
from .otp_service import otp_service


@login_required
def get_usage_view(request):
    remaining, total, key_stats = get_remaining_chats()
    return JsonResponse({
        'status': 'success', 
        'remaining': remaining, 
        'total': total,
        'key_stats': key_stats
    })


def manifest_view(request):
    return render(request, 'chat/manifest.json', content_type='application/json')


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


@ensure_csrf_cookie
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
        data     = json.loads(request.body)
        email    = data.get('email')
        username = data.get('username')

        if not email or not username:
            return JsonResponse({'status': 'error', 'message': 'Email and Username are required.'})

        if mongo_store.get_mongo_user(username):
            return JsonResponse({'status': 'error', 'message': 'Username already taken.'})
        
        # Simple email check in MongoDB (not index-optimized but sufficient for beta)
        if mongo_store.users.find_one({"email": email}):
            return JsonResponse({'status': 'error', 'message': 'Email already registered.'})

        otp = otp_service.generate_otp()
        otp_service.store_otp(email, otp)
        # OTP returned so the frontend EmailJS SDK can fill the template
        return JsonResponse({'status': 'success', 'otp': otp, 'message': 'OTP generated.'})
    except Exception as e:
        logger.error(f"OTP Generation Error: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'An internal error occurred while generating OTP.'}, status=500)


@require_POST
def verify_signup_view(request):
    data     = json.loads(request.body)
    username = data.get('username')
    email    = data.get('email')
    password = data.get('password')
    otp      = data.get('otp')

    if not otp_service.verify_otp(email, otp):
        return JsonResponse({'status': 'error', 'message': 'Invalid or expired OTP.'})

    from django.conf import settings
    # For MongoDB, we can count documents
    if mongo_store.users.count_documents({}) >= settings.MAX_USERS:
        return JsonResponse({'status': 'error',
                             'message': f"Beta limit reached ({settings.MAX_USERS} users max)."})
    try:
        mongo_store.create_mongo_user(username=username, email=email, password=password)
        return JsonResponse({'status': 'success', 'message': 'Account created!'})
    except Exception as e:
        logger.error(f"User Creation Error: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": "Could not create account."}, status=500)


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def chat_view(request):
    return render(request, 'chat/index.html', {
        'sessions': mongo_store.get_sessions(request.user.username),
        'user':     request.user,
    })


@login_required
def new_session_view(request):
    reset_agent(request.user.username)
    session_id = mongo_store.create_session(request.user.username)
    return JsonResponse({'status': 'success', 'session_id': session_id, 'title': 'New Chat'})


@login_required
def session_messages_view(request, session_id):
    session = mongo_store.get_session(session_id, request.user.username)
    if not session:
        return JsonResponse({'status': 'error', 'message': 'Session not found.'}, status=404)
    return JsonResponse({'status': 'success',
                         'messages': mongo_store.get_messages(session_id),
                         'title':    session['title']})


@login_required
def delete_session_view(request, session_id):
    if mongo_store.delete_session(session_id, request.user.username):
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Session not found.'}, status=404)


@login_required
def get_settings_view(request):
    s = mongo_store.get_user_settings(request.user.username)
    s.pop('_id', None)
    
    data = {'status': 'success', 'settings': s}
    
    # Add admin stats if authorized
    if request.user.is_staff:
        data['admin_stats'] = {
            'total_users': mongo_store.users.count_documents({}),
            'active_sessions': mongo_store.sessions.count_documents({})
        }
        
    return JsonResponse(data)


@require_POST
@login_required
def update_settings_view(request):
    try:
        data = json.loads(request.body)
        mongo_store.update_user_settings(
            request.user.username,
            data.get('preferred_language', 'Python'),
            data.get('personal_api_key', '').strip()
        )
        reset_agent(request.user.username)
        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.error(f"Settings Update Error: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": "Failed to update settings."}, status=500)


@csrf_exempt
@login_required
@require_POST
async def ai_chat_endpoint(request):
    try:
        data    = json.loads(request.body)
        message = data.get('message', '').strip()
        if not message:
            return JsonResponse({'status': 'error', 'message': 'Empty message.'})
        response = await get_ai_response(request.user.username, message)
        return JsonResponse({'status': 'success', 'response': response})
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'})
    except Exception as e:
        logger.error(f"AI Chat Error: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": "The AI engine encountered an error."}, status=500)
