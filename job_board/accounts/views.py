# job_board/accounts/views.py
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Message
from .forms import MessageForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.db.models import Q, Max, Count
from django.core.mail import send_mail
from django.conf import settings

class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2", "account_type")

def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(reverse("home"))
    else:
        form = SignupForm()
    return render(request, "accounts/signup.html", {"form": form})


class CustomLoginView(auth_views.LoginView):
    template_name = "registration/login.html"
    def get_success_url(self):
        user = self.request.user
        try:
            if user.is_recruiter():
                return reverse("jobs:my_jobs")
        except Exception:
            pass
        return reverse("profiles:my_profile")

@login_required
def inbox(request):
    received_messages = Message.objects.filter(recipient=request.user).order_by('-timestamp')
    sent_messages = Message.objects.filter(sender=request.user).order_by('-timestamp')
    return render(request, 'accounts/inbox.html', {
        'received_messages': received_messages,
        'sent_messages': sent_messages,
    })

@login_required
def send_message(request, recipient_id=None):
    if request.method == 'POST':
        form = MessageForm(request.POST, sender=request.user)   # ⬅️ pass sender
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user

            # defense-in-depth: block crafted POSTs
            if message.recipient_id == request.user.id:
                form.add_error('recipient', "You can’t send a message to yourself.")
                return render(request, 'accounts/send_message.html', {'form': form})

            message.save()
            django_messages.success(request, 'Message sent successfully!')
            return redirect('accounts:inbox')
    else:
        initial = {}
        if recipient_id:
            initial['recipient'] = User.objects.get(id=recipient_id)
            # Optional: block if trying to prefill yourself
            if recipient_id == request.user.id:
                django_messages.error(request, "You can’t message yourself.")
                return redirect('accounts:inbox')
        form = MessageForm(initial=initial, sender=request.user)  # ⬅️ pass sender
    return render(request, 'accounts/send_message.html', {'form': form})

@login_required
def send_email_message(request, recipient_id=None):
    if request.method == 'POST':
        recipient = User.objects.get(id=recipient_id)
        subject = request.POST.get('subject', 'Message from Recruiter')
        content = request.POST.get('content', '')
        recipient_email = recipient.email
        if recipient_email and content:
            send_mail(
                subject=subject,
                message=content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False,  # Show errors in console
            )
            django_messages.success(request, 'Email sent to candidate!')
            return redirect('accounts:inbox')
    else:
        recipient = User.objects.get(id=recipient_id)
    return render(request, 'accounts/send_email_message.html', {'recipient': recipient})

@login_required
def conversations(request, user_id=None):
    user = request.user
    # Find all users this user has messaged or received messages from
    convo_users = (
        User.objects.filter(
            Q(sent_messages__recipient=user) | Q(received_messages__sender=user)
        )
        .exclude(id=user.id)
        .distinct()
    )
    # Build conversation list with last message and unread count
    conversations = []
    for other_user in convo_users:
        last_msg = Message.objects.filter(
            Q(sender=user, recipient=other_user) | Q(sender=other_user, recipient=user)
        ).order_by('-timestamp').first()
        unread_count = Message.objects.filter(sender=other_user, recipient=user, is_read=False).count()
        conversations.append({
            'other_user': other_user,
            'last_message': last_msg.content if last_msg else '',
            'unread_count': unread_count,
        })
    # Sort by last message time
    conversations.sort(key=lambda c: Message.objects.filter(
        Q(sender=user, recipient=c['other_user']) | Q(sender=c['other_user'], recipient=user)
    ).aggregate(Max('timestamp'))['timestamp__max'] or '', reverse=True)

    messages_with_user = None
    message_form = None
    active_user_id = None
    if user_id:
        active_user = User.objects.get(id=user_id)
        active_user_id = active_user.id
        send_success = False
        if request.method == 'POST':
            message_form = MessageForm(request.POST)
            if message_form.is_valid():
                msg = message_form.save(commit=False)
                msg.sender = user
                msg.recipient = active_user
                msg.save()
                return redirect('accounts:conversation', user_id=active_user.id)
        else:
            message_form = MessageForm()
            message_form.fields['recipient'].initial = active_user.id
            message_form.fields['recipient'].widget = forms.HiddenInput()
        messages_with_user = Message.objects.filter(
            Q(sender=user, recipient=active_user) | Q(sender=active_user, recipient=user)
        ).order_by('timestamp')
        # Mark received messages as read
        Message.objects.filter(sender=active_user, recipient=user, is_read=False).update(is_read=True)
    else:
        send_success = False
    context = {
        'conversations': conversations,
        'messages_with_user': messages_with_user,
        'message_form': message_form,
        'active_user_id': active_user_id,
        'user': user,
        'send_success': send_success,
    }
    return render(request, 'accounts/conversations.html', context)
