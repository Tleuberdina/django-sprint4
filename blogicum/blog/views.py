from django.shortcuts import get_object_or_404, redirect
from django.views.generic import (
    CreateView, UpdateView, DeleteView, ListView, DetailView
)
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordChangeView
from django.db.models import Count
from django.http import Http404
from django.utils import timezone
from django.conf import settings

from .models import Post, Category, Comment
from .forms import PostForm, CommentForm
from .forms import UserProfileForm


def get_posts_queryset(apply_filters=False, apply_annotation=False):
    """Возвращает запросы для модели Post."""
    queryset = Post.objects.select_related('author', 'location', 'category')
    if apply_filters:
        queryset = queryset.filter(
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now()
        )
    if apply_annotation:
        queryset = queryset.annotate(comment_count=Count('comments')
                                     ).order_by('-pub_date')
    return queryset


class OnlyAuthorMixin(UserPassesTestMixin):
    """Миксин для проверки, является ли пользователь автором поста."""

    def test_func(self):
        object = self.get_object()
        return object.author == self.request.user

    def handle_no_permission(self):
        return redirect('blog:index')

    def get_success_url(self):
        return reverse('blog:post_detail',
                       kwargs={'post_id': self.kwargs.get('post_id')})


class CommentMixin:
    model = Comment
    template_name = 'blog/comment.html'

    def get_object(self, queryset=None):
        return get_object_or_404(
            Comment,
            id=self.kwargs.get('comment_id'),
            post_id=self.kwargs['post_id']
        )

    def get_success_url(self):
        return reverse('blog:post_detail',
                       kwargs={'post_id': self.kwargs.get('post_id')})


class PostListView(ListView):
    """Вернет путь к главной странице проекта."""

    template_name = 'blog/index.html'
    paginate_by = settings.QUANTITY_POSTS_PAGE
    queryset = get_posts_queryset(
        apply_filters=True,
        apply_annotation=True)


class PostDetailView(DetailView):
    """Вернет путь к станице отдельной публикации."""

    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def get_object(self, queryset=None):
        post = get_object_or_404(
            Post.objects.select_related(
                'author', 'location', 'category'), pk=self.kwargs['post_id']
        )
        if (post.author != self.request.user
            and (not post.is_published
                 or not post.category.is_published
                 or post.pub_date > timezone.now())):
            raise Http404
        return post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comments.select_related('author')
        return context


class CategoryPostListView(ListView):
    """Вернет путь к странице категории."""

    template_name = 'blog/category.html'
    paginate_by = settings.QUANTITY_POSTS_PAGE
    context_object_name = 'post_list'

    def get_category(self):
        category_slug = self.kwargs['category_slug']
        return get_object_or_404(
            Category,
            is_published=True,
            slug=category_slug
        )

    def get_queryset(self):
        queryset = get_posts_queryset(
            apply_filters=True,
            apply_annotation=True
        )
        category = self.get_category()
        post_list = queryset.filter(
            category=category
        )
        return post_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_category()
        context['category'] = category
        return context


class UserProfileView(ListView):
    """Страница пользователя."""

    model = User
    template_name = 'blog/profile.html'
    paginate_by = settings.QUANTITY_POSTS_PAGE
    pk_url_kwarg = 'username'

    def get_user(self, queryset=None):
        username = self.kwargs.get('username')
        return get_object_or_404(User, username=username)

    def get_queryset(self):
        user = self.get_user()
        queryset = get_posts_queryset(
            apply_filters=user != self.request.user,
            apply_annotation=True
        )
        queryset = queryset.filter(author=user)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.get_user()
        return context


class UserProfileEditView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserProfileForm
    template_name = 'blog/user.html'
    success_url = reverse_lazy('blog:index')

    def get_object(self, queryset=None):
        return self.request.user


class UserPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'blog/profile.html'
    success_url = reverse_lazy('blog:index')


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:profile',
                       kwargs={'username': self.request.user.username})


class PostUpdateView(LoginRequiredMixin, OnlyAuthorMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        post = get_object_or_404(Post, pk=kwargs['post_id'])
        if request.user != post.author:
            return redirect('blog:post_detail', post_id=post.id)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.pk})


class PostDeleteView(LoginRequiredMixin, OnlyAuthorMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def get_object(self, queryset=None):
        return get_object_or_404(Post, pk=self.kwargs['post_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        context['form'] = PostForm(instance=post)
        context['post'] = post
        context['location'] = post.location
        return context

    def get_success_url(self):
        return reverse('blog:profile',
                       kwargs={'username': self.request.user.username})


class CommentCreateView(LoginRequiredMixin, CreateView):
    """Комментарии к публикациям."""

    model = Comment
    form_class = CommentForm
    template_name = 'comments.html'

    def form_valid(self, form):
        comment = form.save(commit=False)
        comment.author = self.request.user
        comment.post = get_object_or_404(
            Post,
            id=self.kwargs['post_id'],
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now()
        )
        comment.save()
        return redirect('blog:post_detail', post_id=comment.post.id)

    def get_success_url(self):
        return redirect('blog:post_detail', post_id=self.kwargs['post_id'])


class CommentUpdateView(LoginRequiredMixin, OnlyAuthorMixin,
                        CommentMixin, UpdateView
                        ):
    form_class = CommentForm


class CommentDeleteView(LoginRequiredMixin, OnlyAuthorMixin,
                        CommentMixin, DeleteView
                        ):
    pass
