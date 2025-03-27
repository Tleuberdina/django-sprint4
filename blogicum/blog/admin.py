from django.contrib import admin

from .models import Post, Category, Location, Comment


admin.site.empty_value_display = 'Не задано'


class PostAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'text',
        'pub_date',
        'author',
        'location',
        'category',
        'is_published',
        'created_at'
    )
    search_fields = ('title',)
    list_filter = ('category',)
    list_display_links = ('title',)


admin.site.register(Post, PostAdmin)
admin.site.register(Category)
admin.site.register(Location)
admin.site.register(Comment)
