/**
 * Main Application Logic for Ultimate Media Downloader
 * Built with Alpine.js and vanilla JavaScript
 */

import { MediaDownloaderAPI } from './api.js';
import { formatBytes, formatDate, formatDuration } from './utils.js';

// Global app state
function app() {
    return {
        // Core state
        url: '',
        urlInfo: null,
        videoInfo: null,
        downloads: [],
        downloading: false,
        loadingInfo: false,

        // UI state
        darkMode: localStorage.getItem('darkMode') === 'true' || false,
        showAdvanced: false,
        showSettings: false,
        showMenu: false,
        toasts: [],

        // Settings
        apiKey: localStorage.getItem('apiKey') || '',
        autoRefresh: localStorage.getItem('autoRefresh') === 'true' || true,
        refreshInterval: parseInt(localStorage.getItem('refreshInterval') || '3'),

        // Advanced download options
        selectedQuality: 'best',
        videoFormat: 'mp4',
        audioFormat: 'm4a',
        downloadSubtitles: false,
        embedThumbnail: true,
        embedMetadata: true,

        // API client
        api: null,

        // Polling interval
        pollInterval: null,

        // Initialization
        init() {
            // Initialize API client
            this.api = new MediaDownloaderAPI('', this.apiKey);

            // Apply dark mode
            if (this.darkMode) {
                document.documentElement.classList.add('dark');
            }

            // Focus URL input
            setTimeout(() => {
                const input = document.getElementById('url-input');
                if (input) input.focus();
            }, 100);

            // Load saved downloads from localStorage
            const saved = localStorage.getItem('downloads');
            if (saved) {
                try {
                    this.downloads = JSON.parse(saved);
                } catch (e) {
                    console.error('Failed to load downloads:', e);
                    this.downloads = [];
                }
            }

            // Start auto-refresh if enabled
            if (this.autoRefresh) {
                this.startAutoRefresh();
            }

            // Register service worker for PWA
            this.registerServiceWorker();
        },

        // Computed properties
        get activeDownloadsCount() {
            return this.downloads.filter(d =>
                d.status === 'RUNNING' || d.status === 'QUEUED'
            ).length;
        },

        // Dark mode toggle
        toggleDarkMode() {
            this.darkMode = !this.darkMode;
            document.documentElement.classList.toggle('dark');
            localStorage.setItem('darkMode', this.darkMode);
        },

        // Save settings
        saveSettings() {
            localStorage.setItem('apiKey', this.apiKey);
            localStorage.setItem('autoRefresh', this.autoRefresh);
            localStorage.setItem('refreshInterval', this.refreshInterval);

            // Update API client with new key
            this.api = new MediaDownloaderAPI('', this.apiKey);

            // Restart auto-refresh if interval changed
            if (this.autoRefresh) {
                this.stopAutoRefresh();
                this.startAutoRefresh();
            }

            this.showToast('Settings saved', 'success');
        },

        // Handle paste event
        handlePaste(event) {
            setTimeout(() => this.urlChanged(), 100);
        },

        // URL changed - detect type
        urlChanged() {
            if (!this.url) {
                this.urlInfo = null;
                return;
            }

            // Simple detection logic
            if (this.url.includes('playlist') || this.url.includes('/c/') || this.url.includes('/@')) {
                this.urlInfo = {
                    type: 'playlist',
                    videoCount: '~50'
                };
            } else {
                this.urlInfo = {
                    type: 'video'
                };
            }
        },

        // Get video/metadata info
        async getInfo() {
            if (!this.url || this.loadingInfo) return;

            this.loadingInfo = true;

            try {
                // Call metadata API
                const info = await this.api.getMetadata(this.url);

                this.videoInfo = {
                    title: info.title || 'Unknown',
                    uploader: info.uploader || info.channel || 'Unknown',
                    thumbnail: info.thumbnail || '',
                    views: this.formatViews(info.view_count),
                    duration: formatDuration(info.duration),
                    fileSize: info.filesize ? formatBytes(info.filesize) : 'Unknown',
                    description: info.description || '',
                    uploadDate: info.upload_date || ''
                };

                this.showToast('Video information retrieved', 'success');
            } catch (error) {
                console.error('Failed to get info:', error);
                this.showToast(error.getUserMessage ? error.getUserMessage() : 'Failed to get video info', 'error');
            } finally {
                this.loadingInfo = false;
            }
        },

        // Start download
        async startDownload(mode) {
            if (!this.url || this.downloading) return;

            this.downloading = true;

            try {
                // Build format string based on mode and settings
                let formatString = 'bv*+ba/best';

                if (mode === 'custom') {
                    formatString = this.buildFormatString();
                } else if (mode === 'best') {
                    formatString = 'bv*+ba/best';
                }

                // Create download request
                const request = {
                    url: this.url,
                    format: formatString,
                    dest: 'RAILWAY',
                    path: 'videos/{safe_title}-{id}.{ext}'
                };

                // Submit download
                const response = await this.api.createDownload(request);

                // Create download object for UI
                const download = {
                    id: Date.now(),
                    request_id: response.request_id,
                    url: this.url,
                    title: 'Fetching information...',
                    status: response.status || 'QUEUED',
                    bytes: response.bytes || 0,
                    file_url: response.file_url || null,
                    logs_url: response.logs_url || null,
                    error: response.error || null,
                    created_at: response.created_at || new Date().toISOString(),
                    deletion_time: response.deletion_time || null
                };

                this.downloads.unshift(download);
                this.saveDownloads();

                this.showToast('Download started', 'success');

                // Start polling for this download
                this.pollDownloadStatus(download.request_id);

            } catch (error) {
                console.error('Failed to start download:', error);
                this.showToast(error.getUserMessage ? error.getUserMessage() : 'Failed to start download', 'error');
                this.downloading = false;
            }
        },

        // Build format string from advanced settings
        buildFormatString() {
            let format = '';

            if (this.selectedQuality === 'audio') {
                // Audio only
                format = 'bestaudio/best';
            } else if (this.selectedQuality === 'best') {
                format = `bestvideo[ext=${this.videoFormat}]+bestaudio[ext=${this.audioFormat}]/best`;
            } else {
                // Specific quality
                const height = this.selectedQuality.replace('p', '');
                format = `bestvideo[height<=${height}][ext=${this.videoFormat}]+bestaudio[ext=${this.audioFormat}]/best`;
            }

            return format;
        },

        // Poll download status
        async pollDownloadStatus(requestId) {
            const maxAttempts = 60; // 60 * 3 seconds = 3 minutes max
            let attempts = 0;

            const poll = async () => {
                if (attempts >= maxAttempts) {
                    console.log('Polling timeout for', requestId);
                    return;
                }

                try {
                    const status = await this.api.getDownloadStatus(requestId);
                    this.updateDownload(requestId, status);

                    // Continue polling if still running
                    if (status.status === 'RUNNING' || status.status === 'QUEUED') {
                        attempts++;
                        setTimeout(poll, this.refreshInterval * 1000);
                    } else {
                        // Download finished
                        this.downloading = false;

                        if (status.status === 'DONE') {
                            this.showToast('Download completed!', 'success');
                        } else if (status.status === 'ERROR') {
                            this.showToast('Download failed', 'error');
                        }
                    }
                } catch (error) {
                    console.error('Polling error:', error);
                    attempts++;

                    // Continue polling unless we hit max attempts
                    if (attempts < maxAttempts) {
                        setTimeout(poll, this.refreshInterval * 1000);
                    } else {
                        this.downloading = false;
                    }
                }
            };

            // Start polling
            poll();
        },

        // Update download in list
        updateDownload(requestId, statusData) {
            const download = this.downloads.find(d => d.request_id === requestId);
            if (!download) return;

            download.status = statusData.status;
            download.bytes = statusData.bytes || download.bytes;
            download.file_url = statusData.file_url || download.file_url;
            download.error = statusData.error || null;
            download.duration_sec = statusData.duration_sec || download.duration_sec;
            download.deletion_time = statusData.deletion_time || download.deletion_time;

            // Try to extract title from URL if not set
            if (download.title === 'Fetching information...' && statusData.file_url) {
                const filename = statusData.file_url.split('/').pop();
                download.title = filename.split('.')[0] || 'Downloaded file';
            }

            this.saveDownloads();
        },

        // Refresh individual download
        async refreshDownload(requestId) {
            try {
                const status = await this.api.getDownloadStatus(requestId);
                this.updateDownload(requestId, status);
                this.showToast('Status refreshed', 'info');
            } catch (error) {
                console.error('Failed to refresh:', error);
                this.showToast('Failed to refresh status', 'error');
            }
        },

        // Retry failed download
        async retryDownload(download) {
            // Remove old download
            this.downloads = this.downloads.filter(d => d.id !== download.id);

            // Set URL and start new download
            this.url = download.url;
            await this.startDownload('best');
        },

        // Remove download from list
        removeDownload(id) {
            this.downloads = this.downloads.filter(d => d.id !== id);
            this.saveDownloads();
        },

        // View logs
        async viewLogs(requestId) {
            try {
                const logs = await this.api.getDownloadLogs(requestId);

                // Create a modal or new window with logs
                const logWindow = window.open('', 'Download Logs', 'width=800,height=600');
                if (logWindow) {
                    logWindow.document.write(`
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>Download Logs - ${requestId}</title>
                            <style>
                                body {
                                    font-family: 'Courier New', monospace;
                                    background: #1a1a1a;
                                    color: #00ff00;
                                    padding: 20px;
                                    margin: 0;
                                }
                                pre {
                                    white-space: pre-wrap;
                                    word-wrap: break-word;
                                }
                                h1 {
                                    color: #00ff00;
                                    border-bottom: 2px solid #00ff00;
                                    padding-bottom: 10px;
                                }
                            </style>
                        </head>
                        <body>
                            <h1>Download Logs</h1>
                            <p>Request ID: ${requestId}</p>
                            <p>Status: ${logs.status}</p>
                            <p>Log Count: ${logs.log_count}</p>
                            <hr>
                            <pre>${logs.logs.join('\n')}</pre>
                        </body>
                        </html>
                    `);
                }
            } catch (error) {
                console.error('Failed to get logs:', error);
                this.showToast('Failed to load logs', 'error');
            }
        },

        // Open file in new tab
        openFile(url) {
            window.open(url, '_blank');
        },

        // Save downloads to localStorage
        saveDownloads() {
            try {
                localStorage.setItem('downloads', JSON.stringify(this.downloads.slice(0, 20)));
            } catch (e) {
                console.error('Failed to save downloads:', e);
            }
        },

        // Auto-refresh active downloads
        startAutoRefresh() {
            if (this.pollInterval) return;

            this.pollInterval = setInterval(() => {
                const activeDownloads = this.downloads.filter(d =>
                    d.status === 'RUNNING' || d.status === 'QUEUED'
                );

                activeDownloads.forEach(download => {
                    this.refreshDownload(download.request_id);
                });
            }, this.refreshInterval * 1000);
        },

        stopAutoRefresh() {
            if (this.pollInterval) {
                clearInterval(this.pollInterval);
                this.pollInterval = null;
            }
        },

        // Show toast notification
        showToast(message, type = 'info') {
            const toast = {
                id: Date.now(),
                message,
                type,
                visible: true
            };

            this.toasts.push(toast);

            // Auto-remove after 5 seconds
            setTimeout(() => {
                this.removeToast(toast.id);
            }, 5000);
        },

        removeToast(id) {
            const toast = this.toasts.find(t => t.id === id);
            if (toast) {
                toast.visible = false;
                setTimeout(() => {
                    this.toasts = this.toasts.filter(t => t.id !== id);
                }, 300);
            }
        },

        // Format helpers
        formatBytes(bytes) {
            return formatBytes(bytes);
        },

        formatDate(dateString) {
            return formatDate(dateString);
        },

        formatViews(count) {
            if (!count) return '0';
            if (count >= 1000000) {
                return (count / 1000000).toFixed(1) + 'M';
            }
            if (count >= 1000) {
                return (count / 1000).toFixed(1) + 'K';
            }
            return count.toString();
        },

        // PWA Service Worker Registration
        async registerServiceWorker() {
            if ('serviceWorker' in navigator) {
                try {
                    const registration = await navigator.serviceWorker.register('/static/service-worker.js');
                    console.log('Service Worker registered:', registration);
                } catch (error) {
                    console.error('Service Worker registration failed:', error);
                }
            }
        }
    }
}

// Make app function globally available for Alpine.js
window.app = app;
