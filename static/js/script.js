document.addEventListener('DOMContentLoaded', function () {
    // Download buttons
    document.querySelectorAll('.download-btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const url = this.href;
            const originalHtml = this.innerHTML;
            this.innerHTML = '<i class="ph ph-spinner"></i> 0%';
            this.style.opacity = '0.7';
            this.style.pointerEvents = 'none';

            fetch(url)
                .then(function (response) {
                    if (!response.ok) throw new Error('Erro');
                    const contentLength = response.headers.get('Content-Length');
                    const total = parseInt(contentLength, 10);
                    let loaded = 0;

                    const reader = response.body.getReader();
                    const chunks = [];

                    function pump() {
                        return reader.read().then(function (result) {
                            if (result.done) {
                                const blob = new Blob(chunks);
                                const downloadUrl = window.URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.href = downloadUrl;
                                a.download = url.split('/').pop();
                                a.click();
                                window.URL.revokeObjectURL(downloadUrl);
                                btn.innerHTML = '<i class="ph ph-check-circle"></i> Concluído';
                                btn.style.opacity = '1';
                                btn.style.pointerEvents = 'auto';
                                setTimeout(function () {
                                    btn.innerHTML = originalHtml;
                                }, 2000);
                                return;
                            }
                            chunks.push(result.value);
                            loaded += result.value.length;
                            if (total) {
                                const percent = Math.round((loaded / total) * 100);
                                btn.innerHTML = '<i class="ph ph-spinner"></i> ' + percent + '%';
                            }
                            return pump();
                        });
                    }

                    return pump();
                })
                .catch(function () {
                    btn.innerHTML = originalHtml;
                    btn.style.opacity = '1';
                    btn.style.pointerEvents = 'auto';
                });
        });
    });

    // Preview modal
    const modal = document.getElementById('previewModal');
    const modalClose = document.getElementById('previewClose');
    const modalOverlay = modal ? modal.querySelector('.preview-overlay') : null;
    const previewPlayer = document.getElementById('previewPlayer');

    document.querySelectorAll('.preview-btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            const videoId = this.dataset.videoId;
            previewPlayer.innerHTML = '<iframe src="https://www.youtube.com/embed/' + videoId + '?autoplay=1&origin=' + window.location.origin + '" frameborder="0" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>';
            modal.classList.add('active');
        });
    });

    function closePreview() {
        modal.classList.remove('active');
        previewPlayer.innerHTML = '';
    }

    if (modalClose) {
        modalClose.addEventListener('click', closePreview);
    }

    if (modalOverlay) {
        modalOverlay.addEventListener('click', closePreview);
    }

    // Pagination AJAX
    document.querySelectorAll('.page-link').forEach(function (link) {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const href = this.href;
            const url = new URL(href);
            const params = url.searchParams;

            fetch('/api/buscar?q=' + params.get('q') + '&pagina=' + params.get('pagina'))
                .then(function (response) { return response.json(); })
                .then(function (data) {
                    if (data.results) {
                        updateResults(data.results, params.get('q'), parseInt(params.get('pagina')));
                    }
                });

            document.querySelectorAll('.page-link').forEach(function (l) {
                l.classList.remove('active');
            });
            this.classList.add('active');
        });
    });

    function updateResults(results, query, page) {
        const grid = document.querySelector('.results-grid');
        const pagination = document.querySelector('.pagination');

        grid.innerHTML = '';
        results.forEach(function (video) {
            const card = document.createElement('div');
            card.className = 'result-card';
            card.innerHTML =
                '<div class="result-thumb-wrapper">' +
                '<img src="' + video.thumbnail + '" alt="' + video.titulo + '" class="result-thumb" loading="lazy">' +
                '<span class="result-duration-badge">' + video.duracao + '</span>' +
                '<button class="preview-btn" data-video-id="' + video.id + '" title="Pré-visualizar">' +
                '<i class="ph ph-play"></i>' +
                '</button>' +
                '</div>' +
                '<div class="result-info">' +
                '<h3 class="result-title">' + video.titulo + '</h3>' +
                '<p class="result-channel">' + video.canal + '</p>' +
                '<div class="result-meta">' +
                '<span class="result-views">' + video.views + ' visualizações</span>' +
                '</div>' +
                '<div class="result-actions">' +
                '<a href="/download/' + video.id + '/mp3" class="download-btn">' +
                '<i class="ph ph-music-notes"></i> MP3' +
                '</a>' +
                '<a href="/download/' + video.id + '/720" class="download-btn secondary">' +
                '<i class="ph ph-video"></i> MP4 720p' +
                '</a>' +
                '<a href="/download/' + video.id + '/1080" class="download-btn secondary">' +
                '<i class="ph ph-film-strip"></i> MP4 1080p' +
                '</a>' +
                '</div>' +
                '</div>';
            grid.appendChild(card);
        });

        pagination.innerHTML = '';
        for (var i = 1; i <= 5; i++) {
            var link = document.createElement('a');
            link.href = '?q=' + query + '&pagina=' + i;
            link.className = 'page-link' + (i === page ? ' active' : '');
            link.textContent = i;
            link.addEventListener('click', function (e) {
                e.preventDefault();
                var p = parseInt(this.textContent);
                fetch('/api/buscar?q=' + query + '&pagina=' + p)
                    .then(function (r) { return r.json(); })
                    .then(function (d) {
                        updateResults(d.results, query, p);
                    });
            });
            pagination.appendChild(link);
        }

        // Rebind preview buttons
        document.querySelectorAll('.preview-btn').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                const videoId = this.dataset.videoId;
                previewPlayer.innerHTML = '<iframe src="https://www.youtube.com/embed/' + videoId + '?autoplay=1&origin=' + window.location.origin + '" frameborder="0" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>';
                modal.classList.add('active');
            });
        });
    }

    // Share buttons
    document.querySelectorAll('.result-card').forEach(function (card) {
        if (!card.querySelector('.share-btn')) {
            const actions = card.querySelector('.result-actions');
            const title = card.querySelector('.result-title').textContent;
            const url = window.location.href;

            const shareContainer = document.createElement('div');
            shareContainer.className = 'share-container';

            const shareBtn = document.createElement('button');
            shareBtn.className = 'share-btn';
            shareBtn.innerHTML = '<i class="ph ph-share-network"></i>';
            shareBtn.title = 'Compartilhar';

            const shareMenu = document.createElement('div');
            shareMenu.className = 'share-menu';
            shareMenu.innerHTML =
                '<a href="https://wa.me/?text=' + encodeURIComponent(title + ' ' + url) + '" target="_blank" class="share-link whatsapp">' +
                '<i class="ph ph-whatsapp-logo"></i>' +
                '</a>' +
                '<a href="https://twitter.com/intent/tweet?text=' + encodeURIComponent(title) + '&url=' + encodeURIComponent(url) + '" target="_blank" class="share-link twitter">' +
                '<i class="ph ph-x-logo"></i>' +
                '</a>';

            shareBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                shareMenu.classList.toggle('active');
            });

            shareContainer.appendChild(shareBtn);
            shareContainer.appendChild(shareMenu);
            actions.appendChild(shareContainer);
        }
    });

    document.addEventListener('click', function () {
        document.querySelectorAll('.share-menu.active').forEach(function (menu) {
            menu.classList.remove('active');
        });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            if (modal.classList.contains('active')) {
                closePreview();
            }
        }

        if (e.key === 'Enter' && document.activeElement.tagName === 'INPUT') {
            const form = document.activeElement.closest('form');
            if (form) {
                e.preventDefault();
                form.submit();
            }
        }
    });
});
// Download queue
const downloadQueue = [];
let isProcessing = false;

function processQueue() {
    if (isProcessing || downloadQueue.length === 0) return;

    isProcessing = true;
    const queueContainer = document.getElementById('downloadQueue');
    queueContainer.classList.add('active');

    const item = downloadQueue.shift();
    const queueItem = document.createElement('div');
    queueItem.className = 'queue-item';
    queueItem.innerHTML =
        '<i class="ph ph-spinner"></i>' +
        '<div style="flex:1">' +
        '<div>' + item.title + '</div>' +
        '<div class="queue-progress"><div class="queue-progress-bar" style="width:0%"></div></div>' +
        '</div>';
    document.getElementById('queueList').appendChild(queueItem);

    fetch(item.url)
        .then(function (response) {
            const contentLength = response.headers.get('Content-Length');
            const total = parseInt(contentLength, 10);
            let loaded = 0;
            const reader = response.body.getReader();
            const chunks = [];

            function pump() {
                return reader.read().then(function (result) {
                    if (result.done) {
                        const blob = new Blob(chunks);
                        const downloadUrl = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = downloadUrl;
                        a.download = item.filename;
                        a.click();
                        window.URL.revokeObjectURL(downloadUrl);
                        queueItem.querySelector('i').className = 'ph ph-check-circle';
                        queueItem.querySelector('.queue-progress-bar').style.width = '100%';
                        isProcessing = false;
                        processQueue();
                        return;
                    }
                    chunks.push(result.value);
                    loaded += result.value.length;
                    if (total) {
                        const percent = Math.round((loaded / total) * 100);
                        queueItem.querySelector('.queue-progress-bar').style.width = percent + '%';
                    }
                    return pump();
                });
            }
            return pump();
        })
        .catch(function () {
            queueItem.querySelector('i').className = 'ph ph-x-circle';
            isProcessing = false;
            processQueue();
        });
}

document.querySelectorAll('.download-btn').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
        e.preventDefault();
        const url = this.href;
        const card = this.closest('.result-card');
        const title = card ? card.querySelector('.result-title').textContent : url.split('/').pop();

        downloadQueue.push({
            url: url,
            title: title,
            filename: url.split('/').pop()
        });

        processQueue();
    });
});
const queueClose = document.getElementById('queueClose');
if (queueClose) {
    queueClose.addEventListener('click', function () {
        document.getElementById('downloadQueue').classList.remove('active');
    });
}