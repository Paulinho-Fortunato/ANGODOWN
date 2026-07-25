import yt_dlp
import os
import uuid
import logging
import re
import glob # (Permanece importado)
import time # <-- CORREÇÃO: Adicione esta linha para importar 'time'
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
            except ValueError: # Melhoria: capturar especificamente ValueError
                self.active_downloads[download_id] = 0
        elif d['status'] == 'finished':
            self.active_downloads[download_id] = 100

    def download(self, video_id, format_type='mp3'):
        download_id = str(uuid.uuid4())
        output_dir = current_app.config['DOWNLOAD_DIR']
        output_template = os.path.join(output_dir, f'{download_id}.%(ext)s')

        # Melhoria: Opções de log para depuração (ajuste conforme necessário)
        # Remova 'quiet', 'no_warnings', 'no_color' para ver mais detalhes do yt-dlp se necessário
        ydl_opts = {
            'outtmpl': output_template,
            'quiet': True,  # Defina para False para debug detalhado
            'no_warnings': True, # Defina para False para debug detalhado
            'no_color': True,
            'progress_hooks': [lambda d: self._progress_hook(d, download_id)],
            'noplaylist': True,
            'extract_flat': False,
            'concurrent_fragment_downloads': 4,
            'retries': 5,
            'fragment_retries': 5,
            'socket_timeout': 30,
            'extractor_args': {'youtube': {'player_client': ['web', 'mweb', 'android_vr']}}, # Pode ajudar com blocos
            'js_runtimes': {'node': {}}, # Pode ser necessário
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        if format_type == 'mp3':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'postprocessor_args': ['-ar', '44100'],
            })
            ext = 'mp3'
        elif format_type == '720':
            ydl_opts.update({
                'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]', # Melhoria: Garante compatibilidade
                'merge_output_format': 'mp4',
            })
            ext = 'mp4'
        elif format_type == '1080':
            ydl_opts.update({
                'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]', # Melhoria: Garante compatibilidade
                'merge_output_format': 'mp4',
            })
            ext = 'mp4'
        else:
            raise ValueError(f"Formato inválido: {format_type}")

        url = f'https://www.youtube.com/watch?v={video_id}'

        try:
            with self.download_lock: # Mantém o lock para um único download por vez
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    original_title = info.get('title', 'audio')

                    # Melhoria: Tentar obter o nome do arquivo gerado diretamente do info_dict
                    # Se o yt-dlp usar o outtmpl padrão, o nome final estará aqui
                    # Caso contrário, seguir com a busca glob
                    final_file = info.get('_filename')
                    if not final_file or not os.path.exists(final_file):
                        # Busca baseada no padrão UUID se '_filename' falhar ou não existir
                        pattern = os.path.join(output_dir, f'{download_id}*')
                        files = glob.glob(pattern)
                        # Filtrar apenas arquivos de áudio/vídeo (não thumbnails)
                        # Mesmo que não sejam baixados, filtrar é seguro
                        actual_files = [f for f in files if not f.endswith(('.jpg', '.png', '.webp', '.webm'))]

                        if actual_files:
                            final_file = actual_files[0]
                        else:
                            # Se não encontrar arquivos, tentar o caminho esperado
                            final_file = os.path.join(output_dir, f'{download_id}.{ext}')

                    # Garantir extensão correta (mesmo que improvável de falhar agora)
                    target_ext = '.mp3' if format_type == 'mp3' else '.mp4'
                    if not final_file.lower().endswith(target_ext):
                        new_file = final_file.rsplit('.', 1)[0] + target_ext
                        if os.path.exists(final_file) and final_file != new_file: # Verifica se é diferente para evitar erro
                            os.rename(final_file, new_file)
                            final_file = new_file
                            logger.info(f"Arquivo renomeado para garantir extensão: {new_file}")

            # Retorna o caminho real do arquivo e o nome baseado no título original
            return {
                'filepath': final_file,
                'filename': f"{original_title}{target_ext}", # Usa target_ext calculado
                'download_id': download_id
            }
        except yt_dlp.DownloadError as e:
            logger.error(f"yt-dlp DownloadError para {video_id} ({format_type}): {e}")
            raise # Re-lança para ser tratado pela rota
        except yt_dlp.GeoRestrictedError as e:
            logger.error(f"yt-dlp GeoRestrictedError para {video_id} ({format_type}): {e}")
            raise # Re-lança para ser tratado pela rota
        except yt_dlp.AgeRestrictedError as e:
            logger.error(f"yt-dlp AgeRestrictedError para {video_id} ({format_type}): {e}")
            raise # Re-lança para ser tratado pela rota
        except Exception as e: # Captura outros erros inesperados
            logger.error(f"Erro inesperado no download de {video_id} ({format_type}): {type(e).__name__}: {str(e)}")
            raise # Re-lança para ser tratado pela rota

    def cleanup_old_files(self, max_age=3600):
        output_dir = current_app.config['DOWNLOAD_DIR']
        now = time.time() # <-- CORREÇÃO: Agora 'time' está disponível
        for file in os.listdir(output_dir):
            filepath = os.path.join(output_dir, file)
            try:
                if os.path.isfile(filepath) and now - os.path.getmtime(filepath) > max_age:
                    os.remove(filepath)
                    logger.info(f"Arquivo antigo removido: {filepath}") # Log de limpeza
            except OSError as e: # Captura erros específicos de sistema de arquivos
                 logger.error(f"Erro ao remover arquivo antigo {filepath}: {e}")

downloader_instance = VideoDownloader() # Cria uma instância global

# Função para ser chamada pelas rotas
def download(video_id, format_type='mp3'):
    return downloader_instance.download(video_id, format_type)

# Função para ser chamada pela thread de limpeza (se necessário)
def cleanup_old_downloads(max_age=3600):
    downloader_instance.cleanup_old_files(max_age)
