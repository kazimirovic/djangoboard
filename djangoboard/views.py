import guardian
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch, Max, Subquery, OuterRef, Case, When
from django.http import HttpRequest, HttpResponseBadRequest, HttpResponseForbidden, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView

from djangoboard.utils import human_required
from .forms import *
from .models import *


@method_decorator(human_required, name='dispatch')
class CreatePostView(CreateView):
    template_name = 'djangoboard/post_form.html'
    form_class = PostForm


@method_decorator(human_required, name='dispatch')
class CreateThreadView(CreateView):
    template_name = 'djangoboard/thread_form.html'
    form_class = ThreadForm


class HomePageView(ListView):
    template_name = 'djangoboard/home.html'
    model = Board


def board(request: HttpRequest, boardname: str):
    board_ = get_object_or_404(Board, name=boardname)
    query = Thread.objects.filter(board=board_).annotate(num_replies=Count('posts')) \
        .annotate(last_bumped=Case(
        When(num_replies=0, then='date'),
        When(num_replies__gt=0, then=Max('posts__date')))) \
        .order_by('-last_bumped') \
        .prefetch_related(Prefetch('posts',
                                   # Only a few of the latest posts need to be displayed
                                   queryset=Post.objects.filter(
                                       id__in=
                                       Subquery(
                                           Post.objects.filter(
                                               thread_id=OuterRef('thread_id')
                                           ).values_list('id', flat=True)[:settings.DJANGOBOARD_POSTS_PREVIEWED])
                                   )
                                   ),
                          'attachments',
                          'posts__attachments'
                          )

    return render(request, 'djangoboard/board.html',
                  {'board': board_,
                   'threads': query,
                   'form': ThreadForm(initial={'board': boardname, }),
                   },
                  )


def post(request: HttpRequest, post_id):
    post_ = get_object_or_404(Post, id=post_id)
    return redirect("%s#%s" % (reverse('djangoboard:thread', args=[post_.thread.id]), post_.id))


def thread(request: HttpRequest, thread_id, replying_to=None):
    thread_ = get_object_or_404(Thread, id=thread_id)
    posts = Post.objects.filter(thread=thread_).prefetch_related('attachments')
    board_ = thread_.board
    return render(request, 'djangoboard/thread.html',
                  {'form': PostForm(
                      initial={
                          'thread': thread_id,
                          'comment': '' if replying_to is None else '>>%i' % replying_to
                      }),
                      'thread': thread_,
                      'board': board_,
                      'posts': posts,
                      'displayed_post_ids': posts.values_list('id', flat=True),
                      'moderation': request.user.has_perm('delete_posts', board)}
                  )


def captcha(request: HttpRequest):
    if request.method == 'POST':
        form = CaptchaForm(request.POST)
        next_ = request.POST.get('next')
        if form.is_valid():
            request.session['human'] = True
            if next_:
                return redirect(next_)
    else:
        next_ = request.GET.get('next', reverse('djangoboard:captcha'))
        form = CaptchaForm()

    return render(request, 'djangoboard/captcha.html', {'form': form, 'next': next_})


@login_required
def profile(request: HttpRequest):
    moderated_boards = guardian.shortcuts.get_objects_for_user(request.user, 'delete_posts', Board)
    return render(request, 'djangoboard/profile.html', {'moderated_boards': moderated_boards})


@login_required
def delete(request: HttpRequest):
    if request.method != 'POST':
        return HttpResponseBadRequest()
    board = request.POST.get('board')
    if not board:
        return HttpResponseBadRequest()

    if not request.user.has_perm('delete_posts', board):
        return HttpResponseForbidden()
    Post.objects.filter(thread__in=Thread.objects.filter(board=board),
                        id__in=filter(lambda x: x.isdigit(), request.POST.keys())).delete()
    return HttpResponse("Success")
