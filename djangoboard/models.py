from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils import timezone

__all__ = ['Board', 'Post', 'Thread', 'Attachment']


class Board(models.Model):
    name = models.CharField(max_length=10, unique=True, primary_key=True)
    short_description = models.CharField(max_length=20, blank=True)
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        permissions = (
            ('delete_posts', 'Delete posts'),

        )

    def __str__(self):
        return self.name


class AbstractPost(models.Model):
    name = models.CharField(max_length=40, default='Anonymous', blank=True)
    subject = models.CharField(max_length=100, blank=True)
    comment = models.CharField(max_length=1000, blank=True, null=True)
    date = models.DateTimeField(default=timezone.now)

    class Meta:
        abstract = True


class Post(AbstractPost):
    thread = models.ForeignKey('Thread', on_delete=models.CASCADE, related_name='posts')
    replies = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='replies_to')
    attachments = GenericRelation('Attachment')

    class Meta:
        ordering = ['date']

    def get_absolute_url(self):
        return "%s#%s" % (
            reverse('djangoboard:thread', args=[self.thread.id]),
            self.id)

    def __str__(self):
        return '%i:%s' % (self.id, self.comment[:15])


class Thread(AbstractPost):
    board = models.ForeignKey('Board', on_delete=models.CASCADE, related_name='threads')
    attachments = GenericRelation('Attachment')

    def get_absolute_url(self):
        return reverse('djangoboard:thread', args=[self.id])

    def __str__(self):
        return '%i:%s' % (self.id, self.comment[:15])


class Attachment(models.Model):
    file = models.FileField(blank=True, upload_to='uploads')
    mime = models.CharField(max_length=10, blank=True)

    content_type = models.ForeignKey(ContentType, related_name="content_type_attachments", on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    post = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return '%s:%s' % (self.mime, self.file.name)
