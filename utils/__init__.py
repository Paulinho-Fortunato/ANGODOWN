from .youtube_api import YouTubeAPI
from .downloader import VideoDownloader
from .rate_limiter import RateLimiter
from .validators import validate_youtube_url, extract_video_id, sanitize_filename

youtube_api = YouTubeAPI()
downloader = VideoDownloader()
rate_limiter = RateLimiter()