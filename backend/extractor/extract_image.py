from PIL import Image                    # pip install Pillow
from PIL.ExifTags import TAGS

def extract(filepath: str) -> dict:
    """
    Image.open() is lazy — it reads the header only, not all pixel data.
    img.verify() would close the file, so we re-open for EXIF.

    img._getexif() returns a dict keyed by numeric tag IDs.
    TAGS is a lookup dict that maps those IDs → human-readable names
    e.g. {271: 'Make', 272: 'Model', 306: 'DateTime', ...}
    GPS data lives under tag 34853 ('GPSInfo') as a nested dict.
    """
    img  = Image.open(filepath)
    info = {
        "format": img.format,           # 'JPEG', 'PNG', …
        "mode":   img.mode,             # 'RGB', 'RGBA', 'L' (greyscale), …
        "width":  img.size[0],
        "height": img.size[1],
        "exif":   {}
    }

    # EXIF is JPEG-specific; PNG usually has no EXIF
    try:
        raw_exif = img._getexif()       # returns None for PNG
        if raw_exif:
            for tag_id, value in raw_exif.items():
                tag = TAGS.get(tag_id, str(tag_id))   # fallback to numeric id
                # Skip large binary blobs (thumbnail bytes, etc.)
                if isinstance(value, bytes) and len(value) > 64:
                    continue
                info["exif"][tag] = str(value)
    except AttributeError:
        pass    # PNG / non-EXIF formats

    return info