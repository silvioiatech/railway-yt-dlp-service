/**
 * API Client for Ultimate Media Downloader
 * Handles all communication with the FastAPI backend
 */

/**
 * Custom API Error class
 */
export class APIError extends Error {
    constructor(message, statusCode = 0, data = {}) {
        super(message);
        this.name = 'APIError';
        this.statusCode = statusCode;
        this.data = data;
    }

    isAuthError() {
        return this.statusCode === 401 || this.statusCode === 403;
    }

    isNetworkError() {
        return this.statusCode === 0 || this.statusCode === 408;
    }

    isServerError() {
        return this.statusCode >= 500 && this.statusCode < 600;
    }

    getUserMessage() {
        if (this.isNetworkError()) {
            return 'Network error. Please check your connection and try again.';
        }

        if (this.isAuthError()) {
            return 'Authentication failed. Please check your API key in settings.';
        }

        if (this.isServerError()) {
            return 'Server error. Please try again later.';
        }

        return this.message || 'An unexpected error occurred.';
    }
}

/**
 * API Client class for backend communication
 */
export class MediaDownloaderAPI {
    constructor(baseUrl = '', apiKey = null) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.defaultTimeout = 30000; // 30 seconds
    }

    /**
     * Get default headers for API requests
     */
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };

        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
        }

        return headers;
    }

    /**
     * Make HTTP request with error handling
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const timeout = options.timeout || this.defaultTimeout;

        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    ...this.getHeaders(),
                    ...options.headers,
                },
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            // Handle non-OK responses
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new APIError(
                    errorData.error || errorData.detail || `HTTP ${response.status}`,
                    response.status,
                    errorData
                );
            }

            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);

            if (error.name === 'AbortError') {
                throw new APIError('Request timeout', 408);
            }

            if (error instanceof APIError) {
                throw error;
            }

            // Network or other errors
            throw new APIError(
                error.message || 'Network error',
                0,
                { originalError: error }
            );
        }
    }

    /**
     * GET request
     */
    async get(endpoint, options = {}) {
        return this.request(endpoint, {
            method: 'GET',
            ...options,
        });
    }

    /**
     * POST request
     */
    async post(endpoint, data = {}, options = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
            ...options,
        });
    }

    /**
     * Create a new download job
     */
    async createDownload(downloadConfig) {
        const payload = {
            url: downloadConfig.url,
            dest: downloadConfig.dest || 'RAILWAY',
            path: downloadConfig.path || 'videos/{safe_title}-{id}.{ext}',
            format: downloadConfig.format || 'bv*+ba/best',
            webhook: downloadConfig.webhook || null,
            cookies: downloadConfig.cookies || null,
            timeout_sec: downloadConfig.timeout_sec || 1800,
        };

        return this.post('/download', payload);
    }

    /**
     * Get download job status
     */
    async getDownloadStatus(requestId) {
        return this.get(`/downloads/${requestId}`);
    }

    /**
     * Get download job logs
     */
    async getDownloadLogs(requestId) {
        return this.get(`/downloads/${requestId}/logs`);
    }

    /**
     * Get video metadata without downloading
     */
    async getMetadata(url) {
        try {
            return await this.get(`/api/v1/metadata?url=${encodeURIComponent(url)}`);
        } catch (error) {
            // Fallback to basic info if metadata endpoint fails
            console.warn('Metadata endpoint failed:', error);
            return {
                title: 'Video information not available',
                platform: this.extractPlatform(url),
                url: url
            };
        }
    }

    /**
     * Get available formats for a URL
     */
    async getFormats(url) {
        return this.get(`/api/v1/formats?url=${encodeURIComponent(url)}`);
    }

    /**
     * Get playlist information
     */
    async getPlaylistInfo(url) {
        return this.get(`/api/v1/playlist/info?url=${encodeURIComponent(url)}`);
    }

    /**
     * Download playlist
     */
    async downloadPlaylist(playlistConfig) {
        const payload = {
            url: playlistConfig.url,
            format: playlistConfig.format || 'bv*+ba/best',
            items: playlistConfig.items || null,
            start: playlistConfig.start || null,
            end: playlistConfig.end || null,
        };

        return this.post('/api/v1/playlist/download', payload);
    }

    /**
     * Get channel information
     */
    async getChannelInfo(url, filters = {}) {
        const params = new URLSearchParams({ url, ...filters });
        return this.get(`/api/v1/channel/info?${params}`);
    }

    /**
     * Create batch download
     */
    async createBatch(urls, options = {}) {
        const payload = {
            urls,
            format: options.format || 'bv*+ba/best',
            concurrent_limit: options.concurrent_limit || 3,
        };

        return this.post('/api/v1/batch/download', payload);
    }

    /**
     * Get batch status
     */
    async getBatchStatus(batchId) {
        return this.get(`/api/v1/batch/${batchId}`);
    }

    /**
     * Extract platform from URL
     */
    extractPlatform(url) {
        if (url.includes('youtube.com') || url.includes('youtu.be')) return 'YouTube';
        if (url.includes('vimeo.com')) return 'Vimeo';
        if (url.includes('twitter.com') || url.includes('x.com')) return 'Twitter';
        if (url.includes('tiktok.com')) return 'TikTok';
        if (url.includes('instagram.com')) return 'Instagram';
        if (url.includes('facebook.com')) return 'Facebook';
        if (url.includes('reddit.com')) return 'Reddit';
        if (url.includes('twitch.tv')) return 'Twitch';
        return 'Unknown';
    }

    /**
     * Health check
     */
    async healthCheck() {
        return this.get('/api/v1/health');
    }

    /**
     * Get service version
     */
    async getVersion() {
        return this.get('/version');
    }

    /**
     * Get service root information
     */
    async getServiceInfo() {
        return this.get('/');
    }

    /**
     * Get download file URL
     */
    getFileUrl(filePath) {
        if (!filePath) return null;
        return `${this.baseUrl}/files/${filePath}`;
    }

    /**
     * Poll download status until completion or error
     */
    async pollDownloadStatus(requestId, onProgress = null, pollInterval = 2000, maxDuration = 3600000) {
        const startTime = Date.now();

        while (true) {
            // Check if we've exceeded max duration
            if (Date.now() - startTime > maxDuration) {
                throw new APIError('Polling timeout exceeded', 408);
            }

            try {
                const status = await this.getDownloadStatus(requestId);

                // Call progress callback if provided
                if (onProgress && typeof onProgress === 'function') {
                    onProgress(status);
                }

                // Check if job is in terminal state
                if (status.status === 'DONE' || status.status === 'ERROR') {
                    return status;
                }

                // Wait before next poll
                await new Promise(resolve => setTimeout(resolve, pollInterval));
            } catch (error) {
                // If it's a 404, the job might not exist yet, continue polling
                if (error.statusCode === 404 && Date.now() - startTime < 10000) {
                    await new Promise(resolve => setTimeout(resolve, pollInterval));
                    continue;
                }

                throw error;
            }
        }
    }

    /**
     * Retry request with exponential backoff
     */
    async retryRequest(requestFn, maxRetries = 3) {
        let lastError;

        for (let attempt = 0; attempt < maxRetries; attempt++) {
            try {
                return await requestFn();
            } catch (error) {
                lastError = error;

                // Don't retry auth errors
                if (error.isAuthError && error.isAuthError()) {
                    throw error;
                }

                // Wait before retrying (exponential backoff)
                const delay = Math.min(1000 * Math.pow(2, attempt), 10000);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }

        throw lastError;
    }
}

// Create default client instance
export const apiClient = new MediaDownloaderAPI();
