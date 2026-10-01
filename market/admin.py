from django.contrib import admin, messages
from .models import Listing, ListingImage

class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1


@admin.action(description="Tasdiqlash va umumiy marketda ko‘rsatish")
def approve_listings(modeladmin, request, queryset):
    updated_count = queryset.filter(status=Listing.STATUS_PENDING).update(
        status=Listing.STATUS_APPROVED
    )
    modeladmin.message_user(
        request,
        f"{updated_count} ta e'lon tasdiqlandi va umumiy marketda ko‘rinadi.",
        messages.SUCCESS,
    )


@admin.action(description="Rad etish")
def reject_listings(modeladmin, request, queryset):
    updated_count = queryset.filter(status=Listing.STATUS_PENDING).update(
        status=Listing.STATUS_REJECTED
    )
    modeladmin.message_user(
        request,
        f"{updated_count} ta e'lon rad etildi.",
        messages.WARNING,
    )


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'price', 'condition', 'status', 'created_at')
    list_filter = ('status', 'condition', 'category')
    inlines = [ListingImageInline]
    actions = [approve_listings, reject_listings]

@admin.register(ListingImage)
class ListingImageAdmin(admin.ModelAdmin):
    list_display = ('listing', 'order')
