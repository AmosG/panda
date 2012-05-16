#!/usr/bin/env python

from django import forms
from django.conf.urls import patterns, url
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import Group, User
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import models, transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy as _
from djcelery.models import CrontabSchedule, IntervalSchedule, PeriodicTask, TaskState, WorkerState
from livesettings import config_value
from tastypie.admin import ApiKeyInline

from panda.models import Category, TaskStatus, UserProfile

# Hide celery monitors
admin.site.unregister(CrontabSchedule)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(PeriodicTask)
admin.site.unregister(TaskState)
admin.site.unregister(WorkerState)

class PandaUserCreationForm(forms.ModelForm):
    """
    Custom User creation form that eliminates duplication between username
    and email.
    """
    class Meta:
        model = User
        fields = ("username",)

    username = forms.EmailField(label=_("E-mail"), max_length=75)

    def clean_username(self):
        username = self.cleaned_data["username"]
        
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username

        raise forms.ValidationError(_("A user with that email address already exists."))

    def save(self, commit=True):
        user = super(PandaUserCreationForm, self).save(commit=False)
        user.username = user.username.lower()
        user.email = user.username
        user.is_active = False

        if commit:
            user.save()

        return user

class PandaUserChangeForm(UserChangeForm):
    """
    Customized User change form that allows password to be blank.
    (for editing unactivated accounts)
    """
    class Media:
        js = ('panda_user_change_form.js',)

    def __init__(self, *args, **kwargs):
        super(PandaUserChangeForm, self).__init__(*args, **kwargs)

        self.fields['password'].required = False

    def save(self, commit=True):
        user = super(PandaUserChangeForm, self).save(commit=False)
        user.username = user.username.lower()
        user.email = user.username

        if commit:
            user.save()

        return user

class PandaApiKeyInline(ApiKeyInline):
    """
    Customized ApiKeyInline that doesn't allow the creation date to be modified.
    """
    readonly_fields = ('created',)

class UserProfileInline(admin.StackedInline):
    """
    Inline for UserProfile which does not allow the activation key to be modified. 
    """
    model = UserProfile
    
    readonly_fields = ('activation_key', 'activation_key_expiration')

class UserModelAdmin(UserAdmin):
    """
    Heavily modified admin page for editing Users. Eliminates duplication between
    username and email fields. Hides unnecessary cruft. Makes timestamp fields
    readonly. Etc.
    """
    inlines = [UserProfileInline, PandaApiKeyInline]
    add_form = PandaUserCreationForm
    form = PandaUserChangeForm

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name')}
        ),
    )

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    search_fields = ('first_name', 'last_name', 'email')
    ordering = ('email',)

    readonly_fields = ('last_login', 'date_joined')

    @transaction.commit_on_success
    def add_view(self, request, form_url='', extra_context=None):
        """
        This method is overriden in its entirety so that the ApiKey inline won't be
        displayed/parsed on the add_form page.
        """
        model = self.model
        opts = model._meta

        if not self.has_add_permission(request):
            raise PermissionDenied

        ModelForm = self.get_form(request)
        formsets = []
        inline_instances = self.get_inline_instances(request)
        if request.method == 'POST':
            form = ModelForm(request.POST, request.FILES)
            if form.is_valid():
                new_object = self.save_form(request, form, change=False)
                form_validated = True
            else:
                form_validated = False
                new_object = self.model()
            
            PANDA_SKIP_INLINES="""prefixes = {}
            for FormSet, inline in zip(self.get_formsets(request), inline_instances):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1 or not prefix:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(data=request.POST, files=request.FILES,
                                  instance=new_object,
                                  save_as_new="_saveasnew" in request.POST,
                                  prefix=prefix, queryset=inline.queryset(request))
                formsets.append(formset)
            if all_valid(formsets) and form_validated:"""

            if form_validated:
                self.save_model(request, new_object, form, False)
                self.save_related(request, form, formsets, False)
                self.log_addition(request, new_object)
                return self.response_add(request, new_object)
        else:
            # Prepare the dict of initial data from the request.
            # We have to special-case M2Ms as a list of comma-separated PKs.
            initial = dict(request.GET.items())
            for k in initial:
                try:
                    f = opts.get_field(k)
                except models.FieldDoesNotExist:
                    continue
                if isinstance(f, models.ManyToManyField):
                    initial[k] = initial[k].split(",")
            form = ModelForm(initial=initial)

            PANDA_SKIP_INLINES = """prefixes = {}
            
            for FormSet, inline in zip(self.get_formsets(request), inline_instances):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1 or not prefix:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(instance=self.model(), prefix=prefix,
                                  queryset=inline.queryset(request))
                formsets.append(formset)"""

        adminForm = helpers.AdminForm(form, list(self.get_fieldsets(request)),
            self.get_prepopulated_fields(request),
            self.get_readonly_fields(request),
            model_admin=self)
        media = self.media + adminForm.media

        inline_admin_formsets = []
        for inline, formset in zip(inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request))
            readonly = list(inline.get_readonly_fields(request))
            prepopulated = dict(inline.get_prepopulated_fields(request))
            inline_admin_formset = helpers.InlineAdminFormSet(inline, formset,
                fieldsets, prepopulated, readonly, model_admin=self)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media

        context = {
            'title': _('Add %s') % force_unicode(opts.verbose_name),
            'adminform': adminForm,
            'is_popup': "_popup" in request.REQUEST,
            'show_delete': False,
            'media': media,
            'inline_admin_formsets': inline_admin_formsets,
            'errors': helpers.AdminErrorList(form, formsets),
            'app_label': opts.app_label,
            'email_enabled': config_value('EMAIL', 'EMAIL_ENABLED')
        }
        context.update(extra_context or {})
        return self.render_change_form(request, context, form_url=form_url, add=True)

admin.site.unregister(Group)
admin.site.unregister(User)
admin.site.register(User, UserModelAdmin)

# Hide sites framework
admin.site.unregister(Site)

class CategoryAdmin(admin.ModelAdmin):
    fields = ('name', 'slug')
    prepopulated_fields = { 'slug': ('name', ) }

    def save_model(self, request, obj, form, change):
        """
        On save, update full text metadata of related datasets. 
        """
        if change:
            datasets = list(obj.datasets.all())
            obj.save()

            for dataset in datasets:
                dataset.update_full_text()
        else:
            obj.save()

    def delete_model(self, request, obj):
        """
        On delete, update full text metadata of related datasets. 
        """
        datasets = list(obj.datasets.all())
        obj.delete()

        for dataset in datasets:
            dataset.update_full_text()

admin.site.register(Category, CategoryAdmin)

class TaskStatusAdmin(admin.ModelAdmin):
    fields = ('task_name', 'status', 'message', 'start', 'end', 'traceback', 'creator')
    readonly_fields = ('task_name', 'status', 'message', 'start', 'end', 'traceback', 'creator')
    
    list_display = ('task_name', 'status', 'start', 'end', 'creator')
    list_filter = ('status', )

    actions = ['abort_task']

    def get_urls(self):
        urls = super(TaskStatusAdmin, self).get_urls()
        custom_urls = patterns('',
            url(r'^(.+)/abort$',
                self.admin_site.admin_view(self.abort_single),
                name='%s_%s_abort' % (self.model._meta.app_label, self.model._meta.module_name)
            ),
        )

        return custom_urls + urls

    def abort_single(self, request, pk):
        task = get_object_or_404(TaskStatus, pk=pk)

        if task.end:
            self.message_user(request, 'You can not abort a task that has already ended.')
        else:
            task.request_abort()
            self.message_user(request, 'Attempting to abort task.')

        return HttpResponseRedirect(
            reverse('admin:panda_taskstatus_changelist')
        )

    def abort_task(self, request, queryset):
        tasks = list(queryset)

        for task in tasks:
            if task.end:
                self.message_user(request, 'You can not abort tasks that have already ended.')
                return

        for task in tasks:
            task.request_abort()
        
        self.message_user(request, 'Attempting to abort %i task(s).' % len(tasks))

    abort_task.short_description = 'Abort task(s)'

admin.site.register(TaskStatus, TaskStatusAdmin)

admin.site.disable_action('delete_selected')

