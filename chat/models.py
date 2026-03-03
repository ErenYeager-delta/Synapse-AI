"""
Models for Synapse Chat.
FIX: Removed all djongo references. Uses standard Django ORM with SQLite.
All AI chat data (sessions, messages) lives in MongoDB via mongo_store.py.
These models are used only by Django Admin UI.
"""
from django.db import models
from django.contrib.auth.models import User


class ChatSession(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    title      = models.CharField(max_length=200, default='New Chat')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active  = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        try:
            return f"{self.user.username if self.user else 'Unknown User'} — {self.title}"
        except Exception:
            return f"Session {self.id} — {self.title}"


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user',      'User'),
        ('assistant', 'Assistant'),
        ('system',    'System'),
    ]
    session   = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role      = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content   = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        try:
            prev = self.content[:50] if self.content else "No Content"
            return f"[{self.role}] {prev}..."
        except Exception:
            return f"Message {self.id}"
