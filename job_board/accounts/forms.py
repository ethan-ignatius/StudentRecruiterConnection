# job_board/accounts/forms.py
from django import forms
from .models import Message, User   # ⬅️ import User too

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['recipient', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Type your message here...'}),
        }

    def __init__(self, *args, sender=None, **kwargs):
        """
        Pass the current user as `sender` so we can (a) hide them
        from the recipient dropdown, and (b) validate on POST.
        """
        super().__init__(*args, **kwargs)
        self.sender = sender
        if sender is not None:
            self.fields['recipient'].queryset = User.objects.exclude(id=sender.id)

    def clean_recipient(self):
        recipient = self.cleaned_data['recipient']
        if self.sender and recipient == self.sender:
            raise forms.ValidationError("You can’t send a message to yourself.")
        return recipient
