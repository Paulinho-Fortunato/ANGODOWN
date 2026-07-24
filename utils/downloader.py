import yt_dlp
import os
import uuid
import logging
import re
import glob
from threading import Lock
from flask import current_app

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self):
        self.download_lock = Lock()
        self.active_downloads = {}

    def _progress_hook(self, d, download_id):
        if d['status'] == 'downloading':
            percent_str = d.get('_percent_str', '0%')
            percent_clean = re.sub(r'\x1b\[[0-9;]*m', '', percent_str).replace('%', '').strip()
            try:
                self.active_downloads[download_id] = float(percent_clean)
            except:
                self.active_downloads[download_id] = 0
        elif d['status'] == 'finished':
            self.active_downloads[download_id] = 100

    def download(self, video_id, format_type='mp3'):
        download_id = str(uuid.uuid4())
        output_dir = current_app.config['DOWNLOAD_DIR']
        output_template = os.path.join(output_dir, f'{download_id}.%(ext)s')

        ydl_opts = {
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'no_color': True,
            'progress_hooks': [lambda d: self._progress_hook(d, download_id)],
            'noplaylist': True,
            'extract_flat': False,
            'concurrent_fragment_downloads': 4,
            'retries': 5,
            'fragment_retries': 5,
            'socket_timeout': 30,
            'extractor_args': {'youtube': {'player_client': ['android_vr']}},
            'js_runtimes': {'node': {}},
        }

        if format_type == 'mp3':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }, {
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                }, {
                    'key': 'EmbedThumbnail',
                }],
                'writethumbnail': True,
                'postprocessor_args': ['-ar', '44100'],
            })
            ext = 'mp3'
        elif format_type == '720':
            ydl_opts.update({
                'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
                'merge_output_format': 'mp4',
            })
            ext = 'mp4'
        elif format_type == '1080':
            ydl_opts.update({
                'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                'merge_output_format': 'mp4',
            })
            ext = 'mp4'
        else:
            raise ValueError(f"Formato inválido: {format_type}")

        url = f'https://www.youtube.com/watch?v={video_id}'

        try:
            with self.download_lock:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    original_title = info.get('title', 'audio')
                    
                    pattern = os.path.join(output_dir, f'{download_id}*')
                    files = glob.glob(pattern)
                    actual_files = [f for f in files if not f.endswith(('.jpg', '.png', '.webp'))]
                    
                    if actual_files:
                        final_file = actual_files[0]
                    else:
                        final_file = os.path.join(output_dir, f'{download_id}.{ext}')
                    
                    return {
                        'filepath': final_file,
                        'filename': f"{original_title}.{ext}",
                        'download_id': download_id
                    }
        except Exception as e:
            logger.error(f"Download error: {e}")
            raise

    def cleanup_old_files(self, max_age=3600):
        output_dir = current_app.config['DOWNLOAD_DIR']
        now = os.path.getmtime
        for file in os.listdir(output_dir):
            filepath = os.path.join(output_dir, file)
            try:
                if os.path.isfile(filepath) and now() - os.path.getmtime(filepath) > max_age:
                    os.remove(filepath)
            except:
                pass