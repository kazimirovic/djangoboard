from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.views.generic.base import TemplateView

from . import views

app_name = 'djangoboard'
urlpatterns = [
    path('', views.home, name='homepage'),

    path('new_post', views.new_post, name='new_post'),
    path('new_thread', views.new_thread, name='new_thread'),

    path('post/<int:post_id>', views.post, name='post'),
    path('thread/<int:thread_id>', views.thread, name='thread'),
    path('thread/<int:thread_id>/reply_to/<int:replying_to>', views.thread, name='thread'),

    path('captcha', views.captcha, name='captcha'),

    path('profile', views.profile, name='profile'),
    path('delete', views.delete, name='delete'),

    path('help', TemplateView.as_view(template_name="djangoboard/help.html"), name='help'),
    path('success', TemplateView.as_view(template_name="djangoboard/success.html"), name='success'),

    path('<str:boardname>', views.board, name='board'),

]
if settings.DEBUG:  # otherwise should be configured using server software
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

