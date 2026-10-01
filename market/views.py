from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q
from adminpanel.models import Report
from .models import Listing, ListingImage
from .forms import ListingForm, ImageUploadForm, ListingReportForm
from django.contrib import messages


def listings(request):
    """Show recent pending/approved ads separately from approved public ads."""
    qs = Listing.objects.filter(
        status__in=(Listing.STATUS_PENDING, Listing.STATUS_APPROVED)
    ).select_related('seller').prefetch_related('images')

    # Search
    q = request.GET.get('q')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    # Category filter
    category = request.GET.get('category')
    if category:
        qs = qs.filter(category=category)

    # Condition filter
    condition = request.GET.get('condition')
    if condition in (Listing.CONDITION_NEW, Listing.CONDITION_USED):
        qs = qs.filter(condition=condition)

    # Price range
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    try:
        if min_price:
            qs = qs.filter(price__gte=int(min_price))
        if max_price:
            qs = qs.filter(price__lte=int(max_price))
    except ValueError:
        pass

    # Neighborhood filter
    neighborhood = request.GET.get('neighborhood')
    if neighborhood:
        qs = qs.filter(neighborhood__icontains=neighborhood)

    new_listings = qs.order_by('-created_at')[:8]
    has_pending_listings = qs.filter(status=Listing.STATUS_PENDING).exists()
    approved_qs = qs.filter(status=Listing.STATUS_APPROVED).order_by('-created_at')

    # Sorting applies to approved all-listings results; recent ads stay newest-first.
    sort = request.GET.get('sort')
    if sort == 'price_asc':
        approved_qs = approved_qs.order_by('price')
    elif sort == 'price_desc':
        approved_qs = approved_qs.order_by('-price')
    elif sort == 'newest':
        approved_qs = approved_qs.order_by('-created_at')

    # Pagination
    paginator = Paginator(approved_qs, 12)
    page = request.GET.get('page')
    listings_page = paginator.get_page(page)

    filter_names = ('q', 'category', 'condition', 'min_price', 'max_price', 'neighborhood')
    has_active_filters = any(request.GET.get(name, '').strip() for name in filter_names)
    has_active_filters = has_active_filters or request.GET.get('sort', '') not in ('', 'newest')
    filter_query = request.GET.copy()
    filter_query.pop('page', None)
    context = {
        'listings': listings_page,
        'new_listings': new_listings,
        'query': q or '',
        'category_choices': Listing.CATEGORY_CHOICES,
        'condition_choices': Listing.CONDITION_CHOICES,
        'filter_query': filter_query.urlencode(),
        'has_active_filters': has_active_filters,
        'has_pending_listings': has_pending_listings,
    }
    return render(request, 'market/listings.html', context)


def listing_detail(request, pk):
    listing = get_object_or_404(Listing.objects.select_related('seller'), pk=pk)
    if listing.status == Listing.STATUS_REJECTED and not (
        request.user.is_authenticated
        and (request.user.is_staff or listing.seller_id == request.user.pk)
    ):
        raise Http404
    seller = listing.seller
    images = listing.images.exclude(image='').order_by('order')
    published = Listing.objects.filter(status=Listing.STATUS_APPROVED).select_related('seller').prefetch_related('images').exclude(pk=listing.pk)
    similar_listings = published.filter(category=listing.category).order_by('-created_at')[:4]
    seller_listings = published.filter(seller_id=listing.seller_id).order_by('-created_at')[:4]
    return render(request, 'market/detail.html', {
        'listing': listing,
        'images': images,
        'similar_listings': similar_listings,
        'seller_listings': seller_listings,
        'seller_contact': {
            'name': seller.get_full_name() or "E'lon sotuvchisi",
            'avatar_url': seller.profile_photo_url,
            'joined_at': seller.date_joined,
            'phone': seller.telefon if seller.market_phone_visible and seller.telefon else '',
            'email': seller.email if seller.market_email_visible and seller.email else '',
        },
    })


@login_required
def report_listing(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if request.method == 'POST':
        form = ListingReportForm(request.POST)
        if form.is_valid():
            Report.objects.create(
                reporter=request.user,
                target_type=Report.REPORT_TARGET_POST,
                target_id=str(listing.pk),
                reason=form.cleaned_data['reason'],
                details=form.cleaned_data['details'],
            )
            messages.success(request, "Shikoyatingiz moderatorlarga yuborildi.")
        else:
            messages.error(request, "Shikoyat ma'lumotlarini tekshiring.")
    return redirect('market:listing_detail', pk=listing.pk)


@login_required
def my_listings(request):
    qs = request.user.listings.all().order_by('-created_at').prefetch_related('images')
    return render(request, 'market/my_listings.html', {'listings': qs})


@login_required
def create_listing(request):
    if request.method == 'POST':
        form = ListingForm(request.POST)
        image_form = ImageUploadForm(request.POST, request.FILES)

        if form.is_valid() and image_form.is_valid():
            listing = form.save(commit=False)
            listing.seller = request.user
            listing.status = Listing.STATUS_PENDING
            listing.save()

            images = image_form.cleaned_data.get('images', [])
            # save images (limit to 8)
            for idx, f in enumerate(images[:8]):
                ListingImage.objects.create(listing=listing, image=f, order=idx)

            messages.success(request, "E'loningiz moderatsiya uchun yuborildi.")
            return redirect(reverse('market:listing_detail', args=[listing.pk]))
        else:
            # collect errors and show
            if form.errors:
                messages.error(request, 'Iltimos forma xatolarini tekshiring.')
            if image_form.errors:
                for e in image_form.errors.get('__all__', []):
                    messages.error(request, e)
                for field, errs in image_form.errors.items():
                    if field != '__all__':
                        for e in errs:
                            messages.error(request, e)
    else:
        form = ListingForm()
        image_form = ImageUploadForm()
    return render(request, 'market/create.html', {'form': form, 'image_form': image_form})


@login_required
def edit_listing(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if listing.seller_id != request.user.id:
        messages.error(request, 'Siz bu e\'loni tahrirlash huquqiga ega emassiz.')
        return redirect(reverse('market:listing_detail', args=[pk]))

    if request.method == 'POST':
        form = ListingForm(request.POST, instance=listing)
        image_form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid() and image_form.is_valid():
            form.save()
            images = image_form.cleaned_data.get('images', [])
            for img in images[:8]:
                ListingImage.objects.create(listing=listing, image=img)
            messages.success(request, "E'lon muvaffaqiyatli yangilandi.")
            return redirect(reverse('market:listing_detail', args=[pk]))
    else:
        form = ListingForm(instance=listing)
        image_form = ImageUploadForm()

    return render(request, 'market/create.html', {'form': form, 'image_form': image_form, 'editing': True, 'listing': listing})


@login_required
def delete_listing(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if listing.seller_id != request.user.id:
        messages.error(request, 'Siz bu e\'lonni o‘chirish huquqiga ega emassiz.')
        return redirect(reverse('market:listing_detail', args=[pk]))

    if request.method == 'POST':
        listing.delete()
        messages.success(request, 'E\'lon o‘chirildi.')
        return redirect(reverse('market:my_listings'))

    return render(request, 'market/confirm_delete.html', {'listing': listing})


@login_required
def mark_sold(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if listing.seller_id != request.user.id:
        messages.error(request, 'Siz bu amalni bajara olmaysiz.')
        return redirect(reverse('market:listing_detail', args=[pk]))

    listing.status = Listing.STATUS_SOLD
    listing.save()
    messages.success(request, "E'lon sotildi deb belgilandi.")
    return redirect(reverse('market:my_listings'))
