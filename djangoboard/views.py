import guardian
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch, Max, Subquery, OuterRef, Case, When
from django.http import HttpRequest, HttpResponseBadRequest, HttpResponseForbidden, HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from djangoboard.utils import human_required
from .forms import *
from .models import *


def home(request: HttpRequest):
    return render(request, 'djangoboard/home.html', {'boards': Board.objects.order_by('name')})


def board(request: HttpRequest, boardname: str):
    board_ = get_object_or_404(Board, name=boardname)

    query = Thread.objects.filter(board=board_) \
        .annotate(num_replies=Count('posts')) \
        .annotate(last_bumped=Case(When(num_replies=0, then='date'), When(num_replies__gt=0, then=Max('posts__date')))) \
        .order_by('-last_bumped') \
        .prefetch_related(Prefetch('posts',
                                   # Only a few of the latest posts need to be displayed
                                   queryset=Post.objects.filter(
                                       id__in=
                                       Subquery(
                                           Post.objects.filter(thread_id=OuterRef('thread_id')) \
                                               .values_list('id', flat=True)[:settings.DJANGOBOARD_POSTS_PREVIEWED]))
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


@human_required
def new_post(request: HttpRequest):
    if request.method == 'POST':
        form = PostForm(data=request.POST, files=request.FILES, )
        if form.is_valid():
            post = form.save()
            return HttpResponseRedirect(request.POST.get('next',
                                                         "%s#%s" % (
                                                             reverse('djangoboard:thread', args=[post.thread.id]),
                                                             post.id)
                                                         ))

    else:
        form = PostForm(initial={'thread': 1})
    return render(request, 'djangoboard/post_form.html',
                  {'form': form, })


@human_required
def new_thread(request: HttpRequest):
    if request.method == 'POST':
        form = ThreadForm(data=request.POST, files=request.FILES, )
        if form.is_valid():
            thread_ = form.save()
            # return HttpResponseRedirect(request.POST.get('next', reverse('djangoboard:success')))
            return HttpResponseRedirect(request.POST.get('next', reverse('djangoboard:thread', args=[thread_.id])))
    else:
        form = ThreadForm(initial={'board': 'b'})

    return render(request, 'djangoboard/thread_form.html',
                  {'form': form, 'next': reverse('djangoboard:homepage')})


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
