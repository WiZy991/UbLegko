from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from .models import DeliveryAddress, Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0


class DeliveryAddressInline(admin.TabularInline):
    model = DeliveryAddress
    extra = 0


class UserAdmin(DjangoUserAdmin):
    inlines = [ProfileInline, DeliveryAddressInline]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone')
    search_fields = ('user__username', 'user__email', 'phone')


@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'address', 'is_default', 'created_at')
    list_filter = ('is_default',)
    search_fields = ('name', 'address', 'user__username')
