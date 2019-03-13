from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import *
from .models import *
from .templatetags.postmarkup import postmarkup, find_all_replies


class PostThreadModelTest(TestCase):
    def test_thread(self):
        board = Board.objects.create(name='mock')

        thread = Thread.objects.create(board=board, name='anonymous', subject='Good news',
                                       comment='I can now create threads')
        self.assertFalse(thread.posts.all())
        Post.objects.create(thread=thread, name='anonymous', subject='Good news',
                            comment='I can now post')
        self.assertTrue(thread.posts.all())
        self.assertEqual(len(thread.posts.all()), 1)

    def test_reply(self):
        board = Board.objects.create(name='mock')

        thread = Thread.objects.create(board=board, name='anonymous', subject='Good news',
                                       comment='I can now create threads')
        p1 = Post.objects.create(thread=thread, name='anonymous', subject='Good news',
                                 comment='I can now post')
        p2 = Post.objects.create(thread=thread, name='anonymous', subject='Good news',
                                 comment='I can now post')
        p2.replies_to.add(p1)
        self.assertEqual(p2.replies_to.all()[0], p1)
        self.assertEqual(p1.replies.all()[0], p2)


class PostFormTest(TestCase):
    def setUp(self):
        board = Board.objects.create(name='mock')

        self.thread = Thread.objects.create(board=board)

    def test_without_attachment(self):
        form = PostForm(data={
            'name': 'Anonymous',
            'subject': 'Good News',
            'comment': 'I can post!',
            'thread': self.thread.id
        }, initial={'thread': self.thread.id, })
        self.assertTrue(form.is_valid())

    def test_empty(self):
        form = PostForm(data={
            'name': 'Anonymous',
            'subject': 'Good News',
            'thread': self.thread
        }, )
        self.assertFalse(form.is_valid())


class ThreadFormTest(TestCase):
    def setUp(self):
        self.board = Board.objects.create(name='mock')

    def test_without_attachment(self):
        form = ThreadForm(data={
            'name': 'Anonymous',
            'subject': 'Good News',
            'comment': 'I can post!',
            'board': self.board.name
        }, )
        self.assertTrue(form.is_valid())

    def test_empty(self):
        form = PostForm(data={
            'name': 'Anonymous',
            'subject': 'Good News',
            'board': self.board.name
        }, )
        self.assertFalse(form.is_valid())


class BoardViewTest(TestCase):

    def test_response_status(self):
        board = Board.objects.create(name='b')
        response = self.client.get(reverse('djangoboard:board', args=[board.name]))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('djangoboard:board', args=['c']))
        self.assertEqual(response.status_code, 404)

    def test_content(self):
        b = Board.objects.create(name='b')
        t = Thread.objects.create(board=b, comment='test thread')
        response = self.client.get(reverse('djangoboard:board', args=[b.name]))
        self.assertEqual(response.context['threads'].first(), t)

    def test_threads_order(self):
        b = Board.objects.create(name='b')
        now = timezone.now()

        # latest thread should come first
        first = Thread.objects.create(board=b, comment='test thread', date=now - timezone.timedelta(days=2))
        second = Thread.objects.create(board=b, comment='test thread',
                                       date=now - timezone.timedelta(days=1))
        response = self.client.get(reverse('djangoboard:board', args=[b.name]))
        self.assertEqual(response.context['threads'].first(), second)

        # but if an earlier thread gets a new post, then this thread should come first
        Post.objects.create(thread=first, date=now - timezone.timedelta(days=1))
        response = self.client.get(reverse('djangoboard:board', args=[b.name]))
        self.assertEqual(response.context['threads'].first(), first)

        latest = Thread.objects.create(board=b, comment='now I should come first',
                                       date=now - timezone.timedelta(hours=2))

        # when a yet newer thread gets created, then it is now coming first
        response = self.client.get(reverse('djangoboard:board', args=[b.name]))
        self.assertEqual(response.context['threads'].first(), latest)

    def test_prefetch(self):
        b = Board.objects.create(name='b')
        thread = Thread.objects.create(board=b, comment='test thread')

        for i in range(settings.DJANGOBOARD_POSTS_PREVIEWED + 5):
            Post.objects.create(thread=thread, comment='post %i' % i)
        response = self.client.get(reverse('djangoboard:board', args=[b.name]))
        t = response.context['threads'].first()
        self.assertEqual(len(t.posts.all()), settings.DJANGOBOARD_POSTS_PREVIEWED)

    def test_form(self):
        b = Board.objects.create(name='b')
        self.assertFalse(Thread.objects.filter(board=b))
        response = self.client.get(reverse('djangoboard:board', args=[b.name]))
        form = response.context['form']
        self.assertIsInstance(form, ThreadForm)
        self.assertEqual(form.initial['board'], b.name)

    def test_num_queries(self):
        b = Board.objects.create(name='b')

        thread1 = Thread.objects.create(board=b, comment='test thread')
        thread1_replies = [Post(thread=thread1) for _ in range(10)]

        thread2 = Thread.objects.create(board=b, comment='test thread2')
        thread2_replies = [Post(thread=thread2) for _ in range(10)]

        Post.objects.bulk_create(thread1_replies + thread2_replies)

        with self.assertNumQueries(6):
            self.client.get(reverse('djangoboard:board', args=[b.name]))


class ThreadViewTest(TestCase):
    def setUp(self):
        self.board = Board.objects.create(name='b')

    def test_response_status(self):
        thread = Thread.objects.create(board=self.board, )
        response = self.client.get(reverse('djangoboard:thread', args=[thread.id]))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('djangoboard:thread', args=[123]))
        self.assertEqual(response.status_code, 404)

    def test_content(self):
        thread = Thread.objects.create(board=self.board, )
        response = self.client.get(reverse('djangoboard:thread', args=[thread.id]))
        self.assertEqual(response.context['thread'], thread)
        earlier = Post.objects.create(thread=thread, comment='regular post', date=timezone.now())
        later = Post.objects.create(thread=thread, comment='regular post',
                                    date=timezone.now() + timezone.timedelta(days=40))
        response = self.client.get(reverse('djangoboard:thread', args=[thread.id]))
        self.assertEqual(response.context['posts'][0], earlier)
        self.assertEqual(response.context['posts'][1], later)

    def test_form(self):
        thread = Thread.objects.create(board=self.board, )
        response = self.client.get(reverse('djangoboard:thread', args=[thread.id]))
        form = response.context['form']
        self.assertIsInstance(form, PostForm)
        self.assertEqual(form.initial['thread'], thread.id)


class PostMarkupTest(TestCase):
    def test_links(self):
        text = 'Blah >>blah >>1 >1'
        marked_up = postmarkup(text)
        self.assertIn('<a', marked_up)
        self.assertEqual(marked_up.count('<a'), 1)

    def test_links_displayed(self):
        text = 'Blah >>1 >>2 >>3'
        marked_up = postmarkup(text, displayed_post_ids=[1, 3])
        self.assertEqual(marked_up.count('<a'), 3)
        self.assertEqual(marked_up.count('#'), 2)

    def test_greentext(self):
        text = '''>be me\n
        >be doing this crap\n
        wat do
        '''
        marked_up = postmarkup(text)
        self.assertEqual(marked_up.count('<sp'), 2)

    def test_is_string(self):
        self.assertIsInstance(postmarkup('blah'), str)
        self.assertIsInstance(postmarkup(''), str)

    def test_links_to_threads(self):
        text = '>>>2 >>>2'
        marked_up = postmarkup(text)
        self.assertEqual(marked_up.count('<a'), 2)
        self.assertEqual(marked_up.count('thread'), 2)

    def test_find_all_links(self):
        text = '>>1 >>2 >>asdf >1'
        links = find_all_replies(text)
        self.assertListEqual(links, ['1', '2'])


class NewThreadViewTest(TestCase):
    def setUp(self):
        super().setUp()
        self.board = Board.objects.create(name='mock')

    @override_settings(DJANGOBOARD_REQUIRE_CAPTCHA=False)
    def test_get(self):
        response = self.client.get(reverse('djangoboard:new_thread'))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], ThreadForm)

    @override_settings(DJANGOBOARD_REQUIRE_CAPTCHA=False)
    def test_post(self):
        response = self.client.post(reverse('djangoboard:new_thread'),
                                    {'comment': 'regular thread', 'board': self.board.name},
                                    HTTP_X_FORWARDED_FOR='1.1.1.1')
        self.assertEqual(response.status_code, 302)
        thread = Thread.objects.get(comment='regular thread')
        self.assertEqual(thread.board, self.board)

    @override_settings(DJANGOBOARD_REQUIRE_CAPTCHA=False)
    def test_board_must_exist(self):
        response = self.client.post(reverse('djangoboard:new_thread'),
                                    {'comment': 'regular thread', 'board': 'i dont exist'})
        self.assertNotEqual(response.status_code, 302)
        with self.assertRaises(Thread.DoesNotExist):
            Thread.objects.get(comment='regular thread')

    @override_settings(DJANGOBOARD_REQUIRE_CAPTCHA=False)
    def test_cannot_post_empty(self):
        response = self.client.post(reverse('djangoboard:new_thread'),
                                    {'board': self.board.name},
                                    HTTP_X_FORWARDED_FOR='1.1.1.1')
        self.assertNotEqual(response.status_code, 302)
        self.assertTrue(response.context['form'].errors)

    @override_settings(DJANGOBOARD_REQUIRE_CAPTCHA=False)
    def test_post_with_attachment(self):
        with open('manage.py', 'rb') as f, open('manage.py', 'rb') as g:
            response = self.client.post(reverse('djangoboard:new_thread'),
                                        {'comment': 'ololo', 'board': self.board.name, 'attachments_': (f, g)})
        self.assertEqual(response.status_code, 302)
        thread = Thread.objects.get(comment='ololo')
        self.assertEqual(thread.board, self.board)
        self.assertTrue(Attachment.objects.all())
        self.assertEqual(Attachment.objects.all().first().post, thread)

    @override_settings(DJANGOBOARD_REQUIRE_CAPTCHA=False)
    def test_not_too_many_attachments(self):
        with open('manage.py', 'rb') as f, \
                open('manage.py', 'rb') as g, \
                open('manage.py', 'rb') as h:
            response = self.client.post(reverse('djangoboard:new_thread'),
                                        {'comment': 'ololo', 'board': self.board.name, 'attachments_': (f, g, h)})
        self.assertNotEqual(response.status_code, 302)


class NewPostViewTest(TestCase):
    def setUp(self):
        super().setUp()
        board = Board.objects.create(name='mock')
        self.thread = Thread.objects.create(board=board, comment='mock')

    @override_settings(DJANGOBOARD_REQUIRE_CAPTCHA=False)
    def test_get(self):
        response = self.client.get(reverse('djangoboard:new_post'))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], PostForm)

    @override_settings(DJANGOBOARD_REQUIRE_CAPTCHA=False)
    def test_post(self):
        response = self.client.post(reverse('djangoboard:new_post'),
                                    {'comment': 'regular post', 'thread': self.thread.id},
                                    HTTP_X_FORWARDED_FOR='1.1.1.1')
        self.assertEqual(response.status_code, 302)
        post = Post.objects.get(comment='regular post')
        self.assertEqual(post.thread, self.thread)

    @override_settings(DJANGOBOARD_REQUIRE_CAPTCHA=False)
    def test_cannot_post_to_nonexistent_thread(self):
        response = self.client.post(reverse('djangoboard:new_post'),
                                    {'comment': 'regular post', 'thread': 12324},
                                    HTTP_X_FORWARDED_FOR='1.1.1.1')
        self.assertNotEqual(response.status_code, 302)
        with self.assertRaises(Post.DoesNotExist):
            Post.objects.get(comment='regular post')

    @override_settings(DJANGOBOARD_REQUIRE_CAPTCHA=False)
    def test_cannot_post_empty(self):
        response = self.client.post(reverse('djangoboard:new_post'),
                                    {'thread': self.thread.id},
                                    HTTP_X_FORWARDED_FOR='1.1.1.1')
        self.assertNotEqual(response.status_code, 302)
        self.assertTrue(response.context['form'].errors)

    @override_settings(DJANGOBOARD_REQUIRE_CAPTCHA=False)
    def test_post_with_attachment(self):
        with open('manage.py', 'rb') as f, open('manage.py', 'rb') as g:
            response = self.client.post(reverse('djangoboard:new_post'),
                                        {'comment': 'ololo', 'thread': self.thread.id, 'attachments_': (f, g)})
        self.assertEqual(response.status_code, 302)

        post = Post.objects.get(comment='ololo')
        self.assertEqual(post.thread, self.thread)
        self.assertEqual(Attachment.objects.all().first().post, post)

    @override_settings(DJANGOBOARD_REQUIRE_CAPTCHA=False)
    def test_not_too_many_attachments(self):
        with open('manage.py', 'rb') as f, \
                open('manage.py', 'rb') as g, \
                open('manage.py', 'rb') as h:
            response = self.client.post(reverse('djangoboard:new_post'),
                                        {'comment': 'ololo', 'thread': self.thread.id, 'attachments_': (f, g, h)})
        self.assertNotEqual(response.status_code, 302)

    @override_settings(DJANGOBOARD_REQUIRE_CAPTCHA=False)
    def test_replying(self):
        post1 = Post.objects.create(thread=self.thread)
        response = self.client.post(reverse('djangoboard:new_post'),
                                    {'comment': '>>%i' % post1.id, 'subject': 'subject', 'thread': self.thread.id},
                                    HTTP_X_FORWARDED_FOR='1.1.1.1')
        self.assertEqual(response.status_code, 302)
        post2 = Post.objects.get(subject='subject')
        self.assertIn(post2, post1.replies.all())

        self.assertEqual(post2.thread, self.thread)


class PostViewTest(TestCase):
    def test_nonexistent(self):
        response = self.client.get(reverse('djangoboard:post', args=[1]))
        self.assertNotEqual(response.status_code, 302)

    def test_redirects(self):
        board = Board.objects.create(name='mock')

        thread = Thread.objects.create(board=board, name='anonymous', subject='Good news',
                                       comment='I can now create threads')
        post = Post.objects.create(thread=thread, name='anonymous', subject='Good news',
                                   comment='I can now post')
        response = self.client.get(reverse('djangoboard:post', args=[post.id]))
        self.assertEqual(response.status_code, 302)
