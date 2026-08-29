from django import forms
from .models import Listing, ListingImage
from PIL import Image


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = ['title', 'description', 'price', 'negotiable', 'condition', 'category', 'neighborhood']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'price': forms.NumberInput(attrs={'min': 0}),
        }


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        # data may be a list of UploadedFile objects
        if isinstance(data, (list, tuple)):
            cleaned = []
            for f in data:
                cleaned.append(super(MultipleFileField, self).clean(f, initial))
            return cleaned
        return [super(MultipleFileField, self).clean(data, initial)]


class ImageUploadForm(forms.Form):
    images = MultipleFileField(required=True)

    def __init__(self, *args, **kwargs):
        # Normalize files so that 'images' key contains a list when multiple files uploaded
        files = kwargs.get('files')
        if files and hasattr(files, 'getlist'):
            files = files.copy()
            files.setlist('images', files.getlist('images'))
            kwargs['files'] = files
        super().__init__(*args, **kwargs)

    def clean_images(self):
        images = self.cleaned_data.get('images', [])

        # enforce at least 3 images
        if len(images) < 3:
            raise forms.ValidationError('Kamida 3 ta rasm yuklashingiz kerak.')

        allowed_formats = {'JPEG', 'PNG', 'WEBP'}
        max_size = 10 * 1024 * 1024  # 10 MB

        validated = []
        for upload in images:
            # size check
            if upload.size > max_size:
                raise forms.ValidationError('Har bir rasm 10 MB dan kichik bo\'lishi kerak.')

            # try to open with Pillow to verify image
            try:
                img = Image.open(upload)
                img.verify()
                fmt = (img.format or '').upper()
            except Exception:
                raise forms.ValidationError('Tanlangan fayllardan biri rasm emas.')

            if fmt not in allowed_formats:
                raise forms.ValidationError('Fayl formati ruxsat etilmagan. Faqat JPG, PNG, WEBP qabul qilinadi.')

            # rewind file pointer for later saving
            upload.seek(0)
            validated.append(upload)

        return validated
