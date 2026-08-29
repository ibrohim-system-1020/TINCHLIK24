from django.db import models
from django.conf import settings

class Listing(models.Model):
    CONDITION_NEW = 'new'
    CONDITION_USED = 'used'
    CONDITION_CHOICES = [
        (CONDITION_NEW, 'Yangi'),
        (CONDITION_USED, 'Ishlatilgan'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_SOLD = 'sold'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Tekshirilmoqda'),
        (STATUS_APPROVED, 'Tasdiqlandi'),
        (STATUS_SOLD, 'Sotilgan'),
        (STATUS_REJECTED, 'Rad etildi'),
    ]

    CATEGORY_CHOICES = [
        ('phone', 'Telefon va elektronika'),
        ('computer', 'Kompyuter va texnika'),
        ('home', 'Uy jihozlari'),
        ('furniture', 'Mebel'),
        ('clothes', 'Kiyim-kechak'),
        ('kids', 'Bolalar uchun'),
        ('auto', 'Avtomobil ehtiyot qismlari'),
        ('bike', 'Velosiped'),
        ('tools', 'Qurilish buyumlari'),
        ('garden', 'Bog\' va tomorqa'),
        ('other', 'Boshqa'),
    ]

    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listings')
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.PositiveIntegerField()
    negotiable = models.BooleanField(default=False)
    condition = models.CharField(max_length=10, choices=CONDITION_CHOICES, default=CONDITION_USED)
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default='other')
    neighborhood = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='listings/')
    order = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f"Image for {self.listing_id}#{self.order}"
