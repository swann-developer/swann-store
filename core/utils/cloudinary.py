import cloudinary.utils

def cl_image(public_id, **options):
    url, _ = cloudinary.utils.cloudinary_url(public_id, **options)
    return url