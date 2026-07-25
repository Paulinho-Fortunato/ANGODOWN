from flask import Flask, render_template, request, jsonify, send_file, abort, redirect, url_for, session, Blueprint, make_response
from config import Config
from utils import youtube_api, downloader, rate_limiter # Assumindo que agora chama a função downloader.download
from utils.validators import sanitize_filename
import os
import logging
import requests
import threading
import time # <-- CORREÇÃO: Importar 'time' se ainda não estiver
import shutil
import sys
import glob # <-- CORREÇÃO: Importar 'glob' para a limpeza na rota
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import atexit

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    Config.init_app(app)

    if not app.config.get('YOUTUBE_API_KEY'):
        app.logger.error("YOUTUBE_API_KEY não configurada!")
        sys.exit(1)

    if not app.debug:
        os.makedirs('logs', exist_ok=True)
        file_handler = RotatingFileHandler('logs/angodown.log', maxBytes=1024000, backupCount=3, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        file_handler.setLevel(logging.INFO)

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        stream_handler.setLevel(logging.WARNING)
        
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass

        app.logger.addHandler(file_handler)
        app.logger.addHandler(stream_handler)
        app.logger.setLevel(logging.INFO)

    with app.app_context():
        try:
            youtube_api._get_service()
            app.logger.info("YouTube API service initialized successfully")
        except Exception as e:
            app.logger.error(f"Failed to initialize YouTube API: {type(e).__name__}")

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Server Error: {error}")
        return render_template('errors/500.html'), 500

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    return app

app = create_app()

COUNTRIES = {
    'AO': 'Angola', 'BR': 'Brasil', 'PT': 'Portugal', 'US': 'EUA',
    'GB': 'Reino Unido', 'FR': 'França', 'DE': 'Alemanha', 'ES': 'Espanha',
    'IT': 'Itália', 'JP': 'Japão', 'KR': 'Coreia do Sul', 'IN': 'Índia',
    'MX': 'México', 'AR': 'Argentina', 'CO': 'Colômbia', 'CL': 'Chile',
    'PE': 'Peru', 'EC': 'Equador', 'VE': 'Venezuela', 'UY': 'Uruguai',
    'PY': 'Paraguai', 'BO': 'Bolívia', 'ZA': 'África do Sul',
    'NG': 'Nigéria', 'KE': 'Quénia', 'GH': 'Gana', 'TZ': 'Tanzânia',
    'MZ': 'Moçambique', 'CV': 'Cabo Verde', 'ST': 'São Tomé',
    'GW': 'Guiné-Bissau', 'GQ': 'Guiné Equatorial', 'TL': 'Timor-Leste',
    'CA': 'Canadá', 'AU': 'Austrália', 'NZ': 'Nova Zelândia',
    'NL': 'Países Baixos', 'BE': 'Bélgica', 'CH': 'Suíça',
    'SE': 'Suécia', 'NO': 'Noruega', 'DK': 'Dinamarca', 'FI': 'Finlândia',
    'RU': 'Rússia', 'CN': 'China', 'TR': 'Turquia', 'EG': 'Egito',
    'MA': 'Marrocos', 'DZ': 'Argélia', 'TN': 'Tunísia',
    'AE': 'Emirados Árabes', 'SA': 'Arábia Saudita', 'QA': 'Catar',
    'SG': 'Singapura', 'MY': 'Malásia', 'ID': 'Indonésia', 'PH': 'Filipinas',
    'TH': 'Tailândia', 'VN': 'Vietname', 'PK': 'Paquistão', 'BD': 'Bangladesh',
    'PL': 'Polónia', 'UA': 'Ucrânia', 'CZ': 'República Checa', 'RO': 'Roménia',
    'HU': 'Hungria', 'AT': 'Áustria', 'GR': 'Grécia', 'IE': 'Irlanda',
    'IL': 'Israel', 'CI': 'Costa do Marfim', 'SN': 'Senegal',
    'CM': 'Camarões', 'CD': 'RD Congo', 'CG': 'Congo'
}

LOCAL_CATEGORIES = {
    'AO': ['kizomba', 'semba', 'kuduro', 'afrobeats', 'rap', 'hip hop'],
    'BR': ['sertanejo', 'funk', 'mpb', 'pagode', 'trap', 'forró'],
    'PT': ['fado', 'pimba', 'hip hop tuga', 'kizomba', 'pop portuguesa'],
    'US': ['pop', 'hip hop', 'rock', 'country', 'rnb', 'electronic'],
    'GB': ['grime', 'drill', 'pop', 'rock', 'electronic', 'indie'],
    'FR': ['rap francais', 'pop', 'electronic', 'afrobeats', 'variete'],
    'ES': ['reggaeton', 'flamenco', 'pop', 'trap', 'indie'],
    'DE': ['techno', 'hip hop', 'pop', 'schlager', 'metal'],
    'JP': ['j pop', 'anime', 'rock', 'electronic', 'hip hop'],
    'KR': ['k pop', 'hip hop', 'rnb', 'ballad', 'trot'],
    'IN': ['bollywood', 'punjabi', 'tamil', 'telugu', 'indie'],
    'ZA': ['amapiano', 'afrobeats', 'kwaito', 'house', 'hip hop'],
    'NG': ['afrobeats', 'afropop', 'fuji', 'highlife', 'hip hop'],
    'MZ': ['marrabenta', 'afrobeats', 'kizomba', 'hip hop', 'dancehall'],
    'CV': ['morna', 'coladeira', 'funana', 'kizomba', 'afrobeats']
}

LANG_COUNTRY_MAP = {
    'pt': 'AO', 'en': 'US', 'es': 'ES', 'fr': 'FR',
    'de': 'DE', 'it': 'IT', 'ja': 'JP', 'ko': 'KR',
    'ru': 'RU', 'zh': 'CN', 'ar': 'EG', 'hi': 'IN'
}

metrics = {
    'downloads': 0,
    'searches': 0,
    'errors': 0,
    'start_time': datetime.now()
}

session_http = requests.Session()
session_http.headers.update({'User-Agent': 'AngoDown/1.0'})
adapter = requests.adapters.HTTPAdapter(pool_connections=5, pool_maxsize=10)
session_http.mount('https://', adapter)
session_http.mount('http://', adapter)

stop_event = threading.Event()

def get_flag(code):
    if len(code) == 2:
        return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)
    return ''

def get_country_name(code):
    return COUNTRIES.get(code, code)

def get_local_categories(code):
    return LOCAL_CATEGORIES.get(code, ['pop', 'rock', 'hip hop', 'electronic', 'jazz', 'classical'])

def detect_real_ip():
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        ips = request.environ['HTTP_X_FORWARDED_FOR'].split(',')
        for ip in ips:
            ip = ip.strip()
            if ip and not ip.startswith(('10.', '172.16.', '192.168.')):
                return ip
    if request.environ.get('HTTP_X_REAL_IP'):
        return request.environ['HTTP_X_REAL_IP']
    return request.remote_addr

def detect_country(ip):
    api_services = [
        {'url': f'https://ipapi.co/{ip}/country/', 'key': None},
        {'url': f'http://ip-api.com/json/{ip}?fields=countryCode', 'key': 'countryCode'},
    ]
    for service in api_services:
        try:
            response = session_http.get(service['url'], timeout=2)
            if response.status_code == 200:
                if service['key']:
                    code = response.json().get(service['key'], '')
                else:
                    code = response.text.strip()
                if len(code) == 2 and code.isalpha():
                    return code.upper()
        except:
            continue
    return None

def get_client_country():
    if 'country' in session:
        cached = session.get('country')
        if cached and cached in COUNTRIES:
            return cached

    cf_country = request.headers.get('CF-IPCountry', '').strip()
    if cf_country and len(cf_country) == 2 and cf_country != 'XX':
        session['country'] = cf_country
        return cf_country

    ip = detect_real_ip()
    is_private = ip.startswith(('10.', '172.16.', '192.168.', '127.')) or ip == '::1' or ip == 'localhost'

    if is_private:
        lang = request.headers.get('Accept-Language', '')
        for key, value in LANG_COUNTRY_MAP.items():
            if key in lang:
                session['country'] = value
                return value
        return 'US'

    country = detect_country(ip)
    if country:
        session['country'] = country
        return country

    return 'US'

def format_number(num):
    try:
        num = int(num)
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        return str(num)
    except:
        return str(num)

def cleanup_downloads():
    while not stop_event.is_set():
        stop_event.wait(7200)
        if stop_event.is_set():
            break
        download_dir = app.config['DOWNLOAD_DIR']
        if os.path.exists(download_dir):
            count = 0
            for file in os.listdir(download_dir):
                filepath = os.path.join(download_dir, file)
                try:
                    if os.path.isfile(filepath):
                        os.remove(filepath)
                        count += 1
                    elif os.path.isdir(filepath):
                        shutil.rmtree(filepath)
                        count += 1
                except:
                    pass
            if count > 0:
                app.logger.info(f"Cleanup: {count} files removed")

def cleanup_old_files():
    while not stop_event.is_set():
        stop_event.wait(1800)
        if stop_event.is_set():
            break
        download_dir = app.config['DOWNLOAD_DIR']
        if os.path.exists(download_dir):
            now = time.time()
            for file in os.listdir(download_dir):
                filepath = os.path.join(download_dir, file)
                try:
                    if os.path.isfile(filepath) and now - os.path.getmtime(filepath) > 3600:
                        os.remove(filepath)
                except:
                    pass

cleanup_thread = threading.Thread(target=cleanup_downloads, daemon=True)
cleanup_thread.start()
cleanup_old_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_old_thread.start()

def shutdown():
    app.logger.info("Shutting down...")
    stop_event.set()
    session_http.close()

atexit.register(shutdown)

main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)

@main_bp.route('/')
def home():
    country_code = get_client_country()
    try:
        trends = youtube_api.get_trending(country_code)
    except Exception as e:
        app.logger.error(f"Trending error: {type(e).__name__}")
        metrics['errors'] += 1
        trends = []
    return render_template('home.html',
                         trends=trends,
                         country=get_country_name(country_code),
                         flag=get_flag(country_code),
                         categories=get_local_categories(country_code))

@main_bp.route('/buscar')
def search():
    query = request.args.get('q', '').strip()
    page = request.args.get('pagina', 1, type=int)
    if not query:
        return redirect(url_for('main.home'))
    if len(query) > 200:
        abort(400)
    metrics['searches'] += 1
    try:
        results = youtube_api.search_videos(query, page)
    except Exception as e:
        app.logger.error(f"Search error: {type(e).__name__}")
        metrics['errors'] += 1
        results = []
    return render_template('resultados.html', results=results, query=query, page=page)

@main_bp.route('/video/<video_id>')
def video_detail(video_id):
    try:
        youtube = youtube_api._get_service()
        request_api = youtube.videos().list(
            part='snippet,contentDetails,statistics',
            id=video_id
        )
        response = request_api.execute()
        if not response['items']:
            abort(404)
        item = response['items'][0]
        duration = youtube_api.parse_duration(item['contentDetails']['duration'])
        thumbnails = item['snippet']['thumbnails']
        thumbnail_url = thumbnails.get('maxres', thumbnails.get('high', thumbnails.get('medium')))['url']
        video = {
            'id': video_id,
            'titulo': item['snippet']['title'],
            'canal': item['snippet']['channelTitle'],
            'thumbnail': thumbnail_url,
            'duracao': duration,
            'views': item['statistics'].get('viewCount', '0'),
            'likes': item['statistics'].get('likeCount', '0'),
            'views_fmt': format_number(item['statistics'].get('viewCount', '0')),
            'likes_fmt': format_number(item['statistics'].get('likeCount', '0')),
            'descricao': item['snippet']['description'][:500] if item['snippet']['description'] else 'Sem descrição'
        }
        return render_template('detalhes.html', video=video)
    except Exception as e:
        app.logger.error(f"Video detail error: {type(e).__name__}")
        metrics['errors'] += 1
        abort(500)

@main_bp.route('/download/<video_id>/<formato>')
def download_video(video_id, formato):
    if formato not in app.config['ALLOWED_FORMATS']:
        abort(400)
    result = None
    try:
        result = downloader.download(video_id, formato) # Chama a função específica
        # result['filename'] já vem com a extensão correta do downloader
        safe_filename = sanitize_filename(result['filename'])

        # Garantir que a extensão não foi perdida no sanitize (verificação adicional)
        expected_ext = '.mp3' if formato == 'mp3' else '.mp4'
        if not safe_filename.lower().endswith(expected_ext):
             safe_filename = safe_filename.rsplit('.', 1)[0] + expected_ext

        safe_filename = safe_filename.encode('ascii', 'ignore').decode('ascii')
        if not safe_filename.strip():
            safe_filename = f'download.{formato}'

        metrics['downloads'] += 1

        # Verificar se o arquivo realmente existe antes de tentar enviar
        if not os.path.exists(result['filepath']):
            app.logger.error(f"Arquivo não encontrado após download: {result['filepath']}")
            abort(500)

        mimetype = 'audio/mpeg' if formato == 'mp3' else 'video/mp4'

        response = send_file(
            result['filepath'],
            mimetype=mimetype,
            as_attachment=True,
            download_name=safe_filename
        )

        # Garantir que os cabeçalhos forçam o download com o nome correto
        response.headers['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
        response.headers['Content-Type'] = mimetype
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'

        # Só apaga DEPOIS de enviar, mas sem sleep excessivo
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(result['filepath']):
                    os.remove(result['filepath'])
                    app.logger.info(f"Arquivo baixado removido: {result['filepath']}")
                # CORREÇÃO: Agora 'glob' está importado, a limpeza de thumbnails pode funcionar
                # Remover thumbnails associadas ao ID de download
                base_path_no_ext = result['filepath'].rsplit('.', 1)[0]
                # Procura por arquivos começando com o ID de download (antes da extensão original do yt-dlp)
                # e terminando com extensões comuns de thumbnail
                # Por exemplo, se o arquivo final era 'abc123.mp3', procura 'abc123.jpg', 'abc123.png', etc.
                # OBS: Esta lógica assume que o nome do arquivo base antes da extensão final é o ID UUID
                # Se o yt-dlp renomear significativamente, isso pode não funcionar.
                # A lógica no downloader.py tenta manter o ID UUID no nome final para facilitar isso.
                # Uma abordagem mais robusta seria armazenar os caminhos das thumbnails em uma lista
                # dentro do objeto VideoDownloader e limpá-las lá.
                uuid_part = os.path.basename(base_path_no_ext)
                if uuid_part == result['download_id']: # Verifica se o nome base é o ID UUID
                     thumbnail_pattern = os.path.join(os.path.dirname(result['filepath']), f'{uuid_part}.*')
                     for thumb_path in glob.glob(thumbnail_pattern):
                          if os.path.isfile(thumb_path) and thumb_path != result['filepath']: # Evita apagar o arquivo principal
                              os.remove(thumb_path)
                              app.logger.info(f"Thumbnail removida: {thumb_path}")
            except Exception as e:
                app.logger.error(f"Erro no cleanup do download {result['download_id']}: {e}")

        return response
    except Exception as e:
        app.logger.error(f"Download error para {video_id} ({formato}): {type(e).__name__}: {str(e)}")
        metrics['errors'] += 1
        if result and 'filepath' in result and os.path.exists(result['filepath']):
            try:
                os.remove(result['filepath'])
                app.logger.info(f"Arquivo de download falho removido: {result['filepath']}")
            except OSError as remove_e:
                app.logger.error(f"Falha ao remover arquivo de download falho {result['filepath']}: {remove_e}")
        abort(500)

@api_bp.route('/buscar')
def api_search():
    query = request.args.get('q', '').strip()
    page = request.args.get('pagina', 1, type=int)
    if not query:
        return jsonify({'error': 'Query vazia'}), 400
    metrics['searches'] += 1
    try:
        results = youtube_api.search_videos(query, page)
        return jsonify({'results': results, 'query': query, 'page': page})
    except Exception as e:
        app.logger.error(f"API search error: {type(e).__name__}")
        metrics['errors'] += 1
        return jsonify({'error': 'Erro interno'}), 500

@api_bp.route('/metrics')
def api_metrics():
    uptime = datetime.now() - metrics['start_time']
    return jsonify({
        'downloads': metrics['downloads'],
        'searches': metrics['searches'],
        'errors': metrics['errors'],
        'uptime': str(uptime).split('.')[0],
        'disk_free': shutil.disk_usage(app.config['DOWNLOAD_DIR']).free // (1024 * 1024)
    })

@main_bp.route('/health')
def health():
    country_code = get_client_country()
    disk = shutil.disk_usage(app.config['DOWNLOAD_DIR'])
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'downloads_folder': os.path.exists(app.config['DOWNLOAD_DIR']),
        'detected_country': country_code,
        'country_name': get_country_name(country_code),
        'disk_free_mb': disk.free // (1024 * 1024),
        'disk_total_mb': disk.total // (1024 * 1024),
        'youtube_api': youtube_api.service is not None
    })

app.register_blueprint(main_bp)
app.register_blueprint(api_bp, url_prefix='/api')

@app.before_request
def before_request():
    if request.endpoint in ['main.download_video', 'api.api_search']:
        rate_limiter.check_rate_limit()

@app.errorhandler(400)
def bad_request(e):
    return render_template('errors/404.html'), 400

@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(429)
def too_many_requests(e):
    return render_template('errors/429.html'), 429

@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    return response

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)
