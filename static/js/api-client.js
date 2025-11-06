/**
 * API Client for Ultimate Media Downloader
 * Handles all communication with the FastAPI backend
 */

import { retryWithBackoff } from './utils.js';

/**
 * API Client class for backend communication
 */
export class ApiClient {
    constructor(baseUrl = '', apiKey = null) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.defaultTimeout = 30000; // 30 seconds
    }

    /**
     * Get default headers for API requests
     * @returns {object} Headers object
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
     * @param {string} endpoint - API endpoint
     * @param {object} options - Fetch options
     * @returns {Promise<object>} Response data
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
                throw new ApiError(
                    errorData.error || errorData.detail || `HTTP ${response.status}`,
                    response.status,
                    errorData
                );
            }

            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);

            if (error.name === 'AbortError') {
                throw new ApiError('Request timeout', 408);
            }

            if (error instanceof ApiError) {
                throw error;
            }

            // Network or other errors
            throw new ApiError(
                error.message || 'Network error',
                0,
                { originalError: error }
            );
        }
    }

    /**
     * GET request
     * @param {string} endpoint - API endpoint
     * @param {object} options - Request options
     * @returns {Promise<object>} Response data
     */
    async get(endpoint, options = {}) {
        return this.request(endpoint, {
            method: 'GET',
            ...options,
        });
    }

    /**
     * POST request
     * @param {string} endpoint - API endpoint
     * @param {object} data - Request body
     * @param {object} options - Request options
     * @returns {Promise<object>} Response data
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
     * @param {object} downloadConfig - Download configuration
     * @returns {Promise<object>} Job information
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
     * @param {string} requestId - Job request ID
     * @returns {Promise<object>} Job status
     */
    async getDownloadStatus(requestId) {
        return this.get(`/downloads/${requestId}`);
    }

    /**
     * Get download job logs
     * @param {string} requestId - Job request ID
     * @returns {Promise<object>} Job logs
     */
    async getDownloadLogs(requestId) {
        return this.get(`/downloads/${requestId}/logs`);
    }

    /**
     * Get video information (uses yt-dlp --dump-json)
     * This endpoint may not exist in backend, but can be added
     * @param {string} url - Video URL
     * @returns {Promise<object>} Video metadata
     */
    async getVideoInfo(url) {
        // Since this endpoint doesn't exist in the current backend,
        // we'll simulate it by creating a download with dry-run
        // For now, return a placeholder that the UI can handle
        try {
            return this.post('/info', { url });
        } catch (error) {
            // If endpoint doesn't exist, return basic info
            console.warn('Video info endpoint not available:', error);
            return {
                title: 'Video information not available',
                platform: this.extractPlatform(url),
                url: url
            };
        }
    }

    /**
     * Extract platform from URL
     * @param {string} url - Video URL
     * @returns {string} Platform name
     */
    extractPlatform(url) {
        if (url.includes('youtube.com') || url.includes('youtu.be')) return 'YouTube';
        if (url.includes('vimeo.com')) return 'Vimeo';
        if (url.includes('twitter.com') || url.includes('x.com')) return 'Twitter';
        if (url.includes('tiktok.com')) return 'TikTok';
        return 'Unknown';
    }

    /**
     * Health check
     * @returns {Promise<object>} Health status
     */
    async healthCheck() {
        return this.get('/healthz');
    }

    /**
     * Get service version
     * @returns {Promise<object>} Version information
     */
    async getVersion() {
        return this.get('/version');
    }

    /**
     * Get service root information
     * @returns {Promise<object>} Service info
     */
    async getServiceInfo() {
        return this.get('/');
    }

    /**
     * Get download file URL
     * @param {string} filePath - File path relative to storage
     * @returns {string} Full file URL
     */
    getFileUrl(filePath) {
        if (!filePath) return null;
        return `${this.baseUrl}/files/${filePath}`;
    }

    /**
     * Poll download status until completion or error
     * @param {string} requestId - Job request ID
     * @param {Function} onProgress - Progress callback
     * @param {number} pollInterval - Poll interval in milliseconds
     * @param {number} maxDuration - Maximum polling duration in milliseconds
     * @returns {Promise<object>} Final job status
     */
    async pollDownloadStatus(requestId, onProgress = null, pollInterval = 2000, maxDuration = 3600000) {
        const startTime = Date.now();

        while (true) {
            // Check if we've exceeded max duration
            if (Date.now() - startTime > maxDuration) {
                throw new ApiError('Polling timeout exceeded', 408);
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
     * Download file with progress tracking
     * @param {string} url - File URL
     * @param {Function} onProgress - Progress callback (percentage)
     * @returns {Promise<Blob>} File blob
     */
    async downloadFile(url, onProgress = null) {
        const response = await fetch(url);

        if (!response.ok) {
            throw new ApiError(`Failed to download file: ${response.statusText}`, response.status);
        }

        const contentLength = response.headers.get('content-length');
        const total = parseInt(contentLength, 10);
        let loaded = 0;

        const reader = response.body.getReader();
        const chunks = [];

        while (true) {
            const { done, value } = await reader.read();

            if (done) break;

            chunks.push(value);
            loaded += value.length;

            if (onProgress && total) {
                const percentage = (loaded / total) * 100;
                onProgress(percentage, loaded, total);
            }
        }

        // Combine chunks into single blob
        const blob = new Blob(chunks);
        return blob;
    }

    /**
     * Retry request with exponential backoff
     * @param {Function} requestFn - Request function to retry
     * @param {number} maxRetries - Maximum retry attempts
     * @returns {Promise<object>} Response data
     */
    async retryRequest(requestFn, maxRetries = 3) {
        return retryWithBackoff(requestFn, maxRetries, 1000);
    }
}

/**
 * Custom API Error class
 */
export class ApiError extends Error {
    constructor(message, statusCode = 0, data = {}) {
        super(message);
        this.name = 'ApiError';
        this.statusCode = statusCode;
        this.data = data;
    }

    /**
     * Check if error is authentication related
     * @returns {boolean} True if auth error
     */
    isAuthError() {
        return this.statusCode === 401 || this.statusCode === 403;
    }

    /**
     * Check if error is network related
     * @returns {boolean} True if network error
     */
    isNetworkError() {
        return this.statusCode === 0 || this.statusCode === 408;
    }

    /**
     * Check if error is server error
     * @returns {boolean} True if server error
     */
    isServerError() {
        return this.statusCode >= 500 && this.statusCode < 600;
    }

    /**
     * Get user-friendly error message
     * @returns {string} User-friendly message
     */
    getUserMessage() {
        if (this.isNetworkError()) {
            return 'Network error. Please check your connection and try again.';
        }

        if (this.isAuthError()) {
            return 'Authentication failed. Please check your API key.';
        }

        if (this.isServerError()) {
            return 'Server error. Please try again later.';
        }

        return this.message || 'An unexpected error occurred.';
    }
}

// Create default client instance
export const apiClient = new ApiClient();
