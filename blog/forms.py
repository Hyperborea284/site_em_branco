from django import forms
from .models import Post

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content']  # Inclua outros campos necessários
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control'}),
        }

class TextSubmissionForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea, label="Insira seu texto")
