from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from .models import *


def exterminate(modeladmin, request, queryset):
    Post.objects.filter(pseudoip__in=queryset.values_list('pseudoip', flat=True)).delete()


class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'comment']
    ordering = ['id']
    actions = [exterminate]


class BoardAdmin(GuardedModelAdmin):
    pass


admin.site.register(Thread)
admin.site.register(Post, PostAdmin)
admin.site.register(Board, BoardAdmin)
