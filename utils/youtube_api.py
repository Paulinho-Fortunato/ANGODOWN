from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from flask import current_app
import isodate
import time

class YouTubeAPI:
    def __init__(self):
        self.service = None
        self._trending_cache = {}
        self._cache_time = {}
        self._cache_duration = 3600
        self._supported_regions = {
            'AO': 'ZA', 'MZ': 'ZA', 'CV': 'PT', 'ST': 'PT',
            'GW': 'PT', 'GQ': 'ES', 'TL': 'ID', 'BO': 'AR',
            'PY': 'AR', 'UY': 'AR', 'VE': 'CO', 'EC': 'CO',
            'CR': 'MX', 'PA': 'MX', 'DO': 'MX', 'GT': 'MX',
            'HN': 'MX', 'SV': 'MX', 'NI': 'MX', 'KE': 'KE',
            'NG': 'NG', 'GH': 'GH', 'TZ': 'TZ', 'ZA': 'ZA',
            'MA': 'FR', 'DZ': 'FR', 'TN': 'FR', 'SN': 'FR',
            'CI': 'FR', 'CM': 'FR', 'CD': 'FR', 'CG': 'FR',
        }

    def _get_region(self, country):
        return self._supported_regions.get(country, country)

    def _get_service(self):
        if not self.service:
            api_key = current_app.config['YOUTUBE_API_KEY']
            if not api_key:
                raise ValueError("YOUTUBE_API_KEY não configurada")
            self.service = build('youtube', 'v3', developerKey=api_key, cache_discovery=False)
        return self.service

    def parse_duration(self, duration_iso):
        try:
            duration = isodate.parse_duration(duration_iso)
            minutes = duration.seconds // 60
            seconds = duration.seconds % 60
            return f"{minutes}:{seconds:02d}"
        except:
            return "0:00"

    def get_video_details(self, video_ids):
        if not video_ids:
            return {}
        youtube = self._get_service()
        try:
            request = youtube.videos().list(
                part='contentDetails,statistics',
                id=','.join(video_ids)
            )
            response = request.execute()
            details = {}
            for item in response.get('items', []):
                details[item['id']] = {
                    'duracao': self.parse_duration(item['contentDetails']['duration']),
                    'views': item['statistics'].get('viewCount', '0')
                }
            return details
        except HttpError:
            return {}

    def search_videos(self, query, page=1, max_results=12):
        youtube = self._get_service()
        try:
            request = youtube.search().list(
                q=query,
                part='snippet',
                type='video',
                maxResults=max_results,
                videoCategoryId='10',
                fields='items(id/videoId,snippet(title,channelTitle,thumbnails/medium/url))'
            )
            response = request.execute()

            video_ids = []
            for item in response.get('items', []):
                vid = item.get('id', {}).get('videoId')
                if vid:
                    video_ids.append(vid)

            if not video_ids:
                return []

            details = self.get_video_details(video_ids)
            results = []
            for item in response.get('items', []):
                video_id = item.get('id', {}).get('videoId')
                if not video_id:
                    continue
                detail = details.get(video_id, {})
                results.append({
                    'id': video_id,
                    'titulo': item['snippet']['title'],
                    'canal': item['snippet']['channelTitle'],
                    'thumbnail': item['snippet']['thumbnails']['medium']['url'],
                    'duracao': detail.get('duracao', '0:00'),
                    'views': detail.get('views', '0')
                })
            return results
        except HttpError as e:
            current_app.logger.error(f"YouTube API error: {e}")
            return []
        except Exception as e:
            current_app.logger.error(f"Search error: {e}")
            return []

    def get_trending(self, country='US', max_results=8):
        region = self._get_region(country)
        cache_key = f"{region}_{max_results}"
        now = time.time()

        if cache_key in self._trending_cache:
            if now - self._cache_time.get(cache_key, 0) < self._cache_duration:
                return self._trending_cache[cache_key]

        youtube = self._get_service()
        try:
            request = youtube.videos().list(
                part='snippet',
                chart='mostPopular',
                regionCode=region,
                videoCategoryId='10',
                maxResults=max_results,
                fields='items(id,snippet(title,channelTitle,thumbnails/medium/url))'
            )
            response = request.execute()

            trends = []
            for item in response.get('items', []):
                trends.append({
                    'id': item['id'],
                    'titulo': item['snippet']['title'],
                    'canal': item['snippet']['channelTitle'],
                    'thumbnail': item['snippet']['thumbnails']['medium']['url']
                })

            self._trending_cache[cache_key] = trends
            self._cache_time[cache_key] = now
            return trends
        except HttpError as e:
            current_app.logger.error(f"YouTube API error: {e}")
            return self._trending_cache.get(cache_key, [])
        except Exception as e:
            current_app.logger.error(f"Trending error: {e}")
            return self._trending_cache.get(cache_key, [])