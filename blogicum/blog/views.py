from datetime import datetime

from django.shortcuts import get_object_or_404, redirect
from django.core.paginator import Paginator
from django.views.generic import (
    CreateView, UpdateView, DeleteView, ListView, DetailView
)
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordChangeView
from django.db.models import Q

from .models import Post, Category, Comment
from .forms import PostForm, CommentForm
from .forms import UserProfileForm
from .constants import QUANTITY_POSTS_PAGE


class OnlyAuthorMixin(UserPassesTestMixin):
    """Миксин для проверки, является ли пользователь автором поста."""

    def test_func(self):
        object = self.get_object()
        return object.author == self.request.user

    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if not self.test_func():
            return redirect('blog:post_detail', post_id=post.id)
        return super().dispatch(request, *args, **kwargs)


class PostListView(ListView):
    """Вернет путь к главной странице проекта."""

    model = Post
    template_name = 'blog/index.html'
    ordering = '-pub_date'
    paginate_by = QUANTITY_POSTS_PAGE
    context_object_name = 'posts'

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            is_published=True,
            category__is_published=True,
            pub_date__lte=datetime.now()
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for post in context['posts']:
            post.comment_count = post.comments.count()
        return context


class PostDetailView(DetailView):
    """Вернет путь к станице отдельной публикации."""

    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            return queryset.filter(Q(is_published=True) | Q(author=user))
        else:
            return queryset.filter(
                is_published=True,
                category__is_published=True,
                pub_date__lte=datetime.now()
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comments.select_related('author')
        return context


class CategoryPostListView(ListView):
    """Вернет путь к странице категории."""

    model = Post
    template_name = 'blog/category.html'
    paginate_by = QUANTITY_POSTS_PAGE
    context_object_name = 'post_list'

    def get_queryset(self):
        queryset = super().get_queryset()
        category_slug = self.kwargs['category_slug']
        category = get_object_or_404(
            Category,
            slug=category_slug,
            is_published=True)
        post_list = queryset.filter(
            is_published=True,
            category__is_published=True,
            pub_date__lte=datetime.now(),
            category=category
        ).order_by('-pub_date')
        for post in post_list:
            post.comment_count = post.comments.count()
        return post_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_slug = self.kwargs['category_slug']
        context['category'] = get_object_or_404(
            Category,
            slug=category_slug,
            is_published=True
        )
        return context


class UserProfileView(DetailView):
    """Страница пользователя."""

    model = User
    template_name = 'blog/profile.html'
    context_object_name = 'profile'

    def get_object(self, queryset=None):
        username = self.kwargs.get('username')
        return get_object_or_404(User, username=username)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_user = self.request.user
        if current_user == self.object:
            posts = Post.objects.filter(
                author=self.object).order_by('-pub_date')
        else:
            posts = Post.objects.filter(
                author=self.object,
                is_published=True,
                category__is_published=True,
                pub_date__lte=datetime.now()
            ).order_by('-pub_date')
        for post in posts:
            post.comment_count = post.comments.count()
        paginator = Paginator(posts, 10)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj
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


class PostUpdateView(OnlyAuthorMixin, LoginRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.pk})


class PostDeleteView(OnlyAuthorMixin, LoginRequiredMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PostForm()
        context['post'] = self.object
        context['location'] = self.object.location
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
        post = get_object_or_404(
            Post,
            id=self.kwargs['post_id'],
            is_published=True,
            category__is_published=True,
            pub_date__lte=datetime.now()
        )
        comment = form.save(commit=False)
        comment.author = self.request.user
        comment.post = post
        comment.save()
        return redirect('blog:post_detail', post_id=post.id)

    def get_success_url(self):
        return redirect('blog:post_detail', post_id=self.kwargs['post_id'])


class CommentUpdateView(OnlyAuthorMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'

    def get_object(self, queryset=None):
        comment_id = self.kwargs.get('comment_id')
        return get_object_or_404(Comment, id=comment_id)

    def get_success_url(self):
        return reverse('blog:post_detail',
                       kwargs={'post_id': self.object.post.pk})


class CommentDeleteView(OnlyAuthorMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'

    def get_object(self, queryset=None):
        comment_id = self.kwargs.get('comment_id')
        return get_object_or_404(Comment, id=comment_id)

    def get_success_url(self):
        return reverse('blog:post_detail',
                       kwargs={'post_id': self.object.post.pk}
                       )
