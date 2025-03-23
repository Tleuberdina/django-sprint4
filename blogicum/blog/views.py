from datetime import datetime

from django.shortcuts import get_object_or_404, render, redirect
from django.core.paginator import Paginator
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, DetailView, TemplateView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.decorators import login_required

from .models import Post, Category, Comment
from .constants import LATEST_POSTS_COUNT
from .forms import PostForm, CommentForm
from .forms import UserProfileForm


class OnlyAuthorMixin(UserPassesTestMixin):

    def test_func(self):
        object = self.get_object()
        return object.author == self.request.user


def basic_query():
    """Базовый запрос для всех функций."""
    return Post.objects.select_related(
        'category', 'location', 'author'
    ).filter(
        pub_date__lte=datetime.now(),
        is_published=True,
        category__is_published=True)

    
class PostListView(ListView):
    """Вернет путь к главной странице проекта."""
    model = Post
    template_name = 'blog/index.html'
    ordering = '-pub_date'
    paginate_by = 10
    context_object_name = 'posts'

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(
            is_published=True, 
            category__is_published=True, 
            pub_date__lte=datetime.now()
        )
    
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
            return queryset
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
    paginate_by = 10
    context_object_name = 'post_list'

    def get_queryset(self):
        category_slug = self.kwargs['category_slug']
        category = get_object_or_404(
            Category, 
            slug=category_slug,
            is_published=True)
        post_list = Post.objects.select_related(
            'category', 'location', 'author'
        ).filter(
            pub_date__lte=datetime.now(),
            is_published=True,
            category__is_published=True,
            category=category
        ).order_by('-pub_date')
        for post in post_list:
            post.comment_count = post.comments.count()
        return post_list
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_slug = self.kwargs['category_slug']
        context['category'] = get_object_or_404(Category, slug=category_slug, is_published=True)
        return context


class UserProfileView(DetailView):
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
            posts = Post.objects.filter(author=self.object).order_by('-pub_date')
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
        return reverse('blog:profile', kwargs={'username': self.request.user.username})


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
        context['post.location.name'] = self.object.location
        return context
    
    def get_success_url(self):
        return reverse('blog:profile', kwargs={'username': self.request.user.username})
    

@login_required
def add_comment(request, post_id):
    post = get_object_or_404(
        Post, 
        id=post_id, 
        is_published=True, 
        category__is_published=True, 
        pub_date__lte=datetime.now()
    )
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id=post_id)

@login_required
def edit_comment(request, post_id, comment_id):
    post = get_object_or_404(
        Post, 
        id=post_id, 
        is_published=True, 
        category__is_published=True, 
        pub_date__lte=datetime.now()
    )
    comment = get_object_or_404(Comment, id=comment_id, post=post)
    if request.user == comment.author:
        if request.method == 'POST':
            form = CommentForm(request.POST, instance=comment)
            if form.is_valid():
                form.save()
                return redirect('blog:post_detail', post_id=post_id)
        else:
            form = CommentForm(instance=comment)
    context = {
        'form': form,
        'post': post,
        'comment': comment
    }
    return render(request, 'blog/comment.html', context)

@login_required
def delete_comment(request, post_id, comment_id):
    post = get_object_or_404(
        Post, 
        id=post_id, 
        is_published=True, 
        category__is_published=True, 
        pub_date__lte=datetime.now()
    )
    comment = get_object_or_404(Comment, id=comment_id, post=post)
    if request.user == comment.author:
        if request.method == 'POST':
            comment.delete()
            return redirect('blog:post_detail', post_id=post_id)
    else:
        return redirect('blog:post_detail', post_id=post_id)
    context = {
        'comment': comment
    }
    return render(request, 'blog/comment.html', context)   
