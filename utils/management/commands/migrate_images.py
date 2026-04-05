import cloudinary.uploader
from django.core.management.base import BaseCommand
from core.models import ProductImage
from django.conf import settings
import os


class Command(BaseCommand):
    help = "Migrate images to Cloudinary (clean)"

    def handle(self, *args, **kwargs):

        for img in ProductImage.objects.all():

            if not img.image:
                continue

            image_url = str(img.image)

            # ✅ Skip already migrated
            if image_url.startswith("http"):
                self.stdout.write(f"⏭️ Skipped: {image_url}")
                continue

            # ✅ Build correct path
            file_path = os.path.join(settings.MEDIA_ROOT, image_url)

            if not os.path.exists(file_path):
                self.stdout.write(f"❌ Missing: {file_path}")
                continue

            try:
                filename = os.path.basename(file_path)
                public_id = os.path.splitext(filename)[0]

                self.stdout.write(f"Uploading: {file_path}")

                result = cloudinary.uploader.upload(
                    file_path,
                    public_id=f"products/{public_id}",  # 🔥 prevents duplicates
                    overwrite=True
                )

                img.image = result["secure_url"]
                img.save(update_fields=["image"])

                self.stdout.write(f"✅ Done: {result['secure_url']}")

            except Exception as e:
                self.stdout.write(f"❌ Failed: {e}")