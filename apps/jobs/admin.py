from django import forms
from django.contrib import admin
from .models import Job, Category, Application

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'employer', 'category', 'location', 'job_type', 'posted_date', 'is_active')
    list_filter = ('is_active', 'job_type', 'category')
    search_fields = ('title', 'description', 'location')
    date_hierarchy = 'posted_date'

class CategoryForm(forms.ModelForm):
    ICON_CHOICES = [
        ('fas fa-code', '💻 Code (Web Development)'),
        ('fas fa-mobile-alt', '📱 Mobile'),
        ('fas fa-palette', '🎨 Design'),
        ('fas fa-database', '🗄️ Database'),
        ('fas fa-bullhorn', '📢 Marketing'),
        ('fas fa-chart-line', '📈 Sales'),
        ('fas fa-headset', '🎧 Customer Service'),
        ('fas fa-money-bill-wave', '💰 Finance'),
        ('fas fa-hospital', '🏥 Healthcare'),
        ('fas fa-graduation-cap', '🎓 Education'),
        ('fas fa-cogs', '⚙️ Engineering'),
        ('fas fa-users', '👥 Human Resources'),
        ('fas fa-tasks', '📋 Project Management'),
        ('fas fa-pen', '✍️ Writing'),
        ('fas fa-balance-scale', '⚖️ Legal'),
        ('fas fa-briefcase', '💼 Administration'),
    ]
    
    icon = forms.ChoiceField(
        choices=ICON_CHOICES,
        widget=forms.Select(attrs={'class': 'select2'}),
        help_text='Select an icon for this category'
    )

    class Meta:
        model = Category
        fields = '__all__'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryForm
    list_display = ('name', 'icon_preview', 'job_count')
    search_fields = ('name',)

    def icon_preview(self, obj):
        return f'<i class="{obj.icon}"></i> {obj.icon}'
    icon_preview.short_description = 'Icon'
    icon_preview.allow_tags = True

    def job_count(self, obj):
        return obj.job_set.count()
    job_count.short_description = 'Number of Jobs'

    class Media:
        css = {
            'all': (
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
                'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css',
            )
        }
        js = (
            'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js',
        )

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('job', 'job_seeker', 'applied_date', 'status')
    list_filter = ('status', 'applied_date')
    search_fields = ('job__title', 'job_seeker__user__username')
    date_hierarchy = 'applied_date'