import re
from urllib.parse import urlparse, parse_qs

def validate_youtube_url(url):
    patterns = [
        r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^https?://youtu\.be/[\w-]+',
        r'^https?://(?:www\.)?youtube\.com/embed/[\w-]+'
    ]
    for pattern in patterns:
        if re.match(pattern, url):
            return True
    return False

def extract_video_id(url):
    parsed = urlparse(url)
    if 'youtube.com' in parsed.netloc:
        return parse_qs(parsed.query).get('v', [None])[0]
    elif 'youtu.be' in parsed.netloc:
        return parsed.path[1:]
    return None

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)[:200]