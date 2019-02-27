from captcha.fields import CaptchaField
from django import forms
from django.utils.datastructures import MultiValueDict

from .models import *
from .templatetags.postmarkup import find_all_replies

__all__ = ['PostForm', 'ThreadForm', 'CaptchaForm']


class CaptchaForm(forms.Form):
    captcha = CaptchaField()


class AbstractPostForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('comment') and not cleaned_data.get('attachments_'):
            raise forms.ValidationError("Post is empty")

        if len(MultiValueDict(self.files).getlist('attachments_')) > 2:
            raise forms.ValidationError("Too many attachments_")

    def save(self):
        post = super().save()
        # post.save()

        Attachment.objects.bulk_create(
            [Attachment(post=post, file=file, mime=file.content_type) for file in self.files.getlist('attachments_')])

        return post


class PostForm(AbstractPostForm):
    attachments_ = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}), required=False)

    class Meta:
        model = Post

        fields = ['name', 'thread', 'subject', 'comment', 'thread', 'attachments_']
        widgets = {'thread': forms.HiddenInput(), 'comment': forms.Textarea()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self):
        post = super().save()
        post.replies_to.add(*Post.objects.filter(id__in=find_all_replies(post.comment)))
        return post


class ThreadForm(AbstractPostForm):
    attachments_ = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}), required=False)

    class Meta:
        model = Thread

        fields = ['name', 'subject', 'comment', 'board', 'attachments_']
        widgets = {'comment': forms.Textarea(), 'board': forms.HiddenInput()}
