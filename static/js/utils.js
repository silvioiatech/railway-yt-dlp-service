/**
 * Utility functions for the Ultimate Media Downloader
 * Provides common helpers for formatting, validation, and DOM manipulation
 */

/**
 * Format bytes to human-readable string
 * @param {number} bytes - Number of bytes
 * @param {number} decimals - Decimal places
 * @returns {string} Formatted string (e.g., "1.5 MB")
 */
export function formatBytes(bytes, decimals = 2) {
    if (bytes === 0 || bytes === null || bytes === undefined) return '0 B';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Format seconds to human-readable duration
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted string (e.g., "1h 23m 45s")
 */
export function formatDuration(seconds) {
    if (!seconds || seconds < 0) return 'N/A';

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

/**
 * Format date to relative time (e.g., "2 minutes ago")
 * @param {string|Date} date - Date string or Date object
 * @returns {string} Relative time string
 */
export function formatRelativeTime(date) {
    if (!date) return 'Unknown';

    const now = new Date();
    const then = new Date(date);
    const diffMs = now - then;
    const diffSecs = Math.floor(diffMs / 1000);

    if (diffSecs < 60) return 'just now';
    if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)} minutes ago`;
    if (diffSecs < 86400) return `${Math.floor(diffSecs / 3600)} hours ago`;
    if (diffSecs < 2592000) return `${Math.floor(diffSecs / 86400)} days ago`;

    return then.toLocaleDateString();
}

/**
 * Sanitize filename for safe display
 * @param {string} filename - Original filename
 * @returns {string} Sanitized filename
 */
export function sanitizeFilename(filename) {
    if (!filename) return 'unknown';

    // Remove path separators and dangerous characters
    return filename
        .replace(/[/\\?%*:|"<>]/g, '_')
        .replace(/_{2,}/g, '_')
        .trim();
}

/**
 * Validate URL format
 * @param {string} url - URL to validate
 * @returns {boolean} True if valid URL
 */
export function isValidUrl(url) {
    if (!url || typeof url !== 'string') return false;

    try {
        const parsed = new URL(url.trim());
        return parsed.protocol === 'http:' || parsed.protocol === 'https:';
    } catch {
        return false;
    }
}

/**
 * Detect URL type (video, playlist, channel, etc.)
 * @param {string} url - URL to analyze
 * @returns {object} Type information
 */
export function detectUrlType(url) {
    if (!url) return { type: 'unknown' };

    const urlLower = url.toLowerCase();

    // YouTube playlist detection
    if (urlLower.includes('youtube.com') || urlLower.includes('youtu.be')) {
        if (urlLower.includes('playlist') || urlLower.includes('list=')) {
            return { type: 'playlist', platform: 'youtube' };
        }
        if (urlLower.includes('/c/') || urlLower.includes('/@') || urlLower.includes('/channel/')) {
            return { type: 'channel', platform: 'youtube' };
        }
        return { type: 'video', platform: 'youtube' };
    }

    // Generic playlist detection
    if (urlLower.includes('playlist') || urlLower.includes('list')) {
        return { type: 'playlist', platform: 'generic' };
    }

    return { type: 'video', platform: 'generic' };
}

/**
 * Extract domain from URL
 * @param {string} url - URL to parse
 * @returns {string} Domain name
 */
export function extractDomain(url) {
    if (!url) return 'Unknown';

    try {
        const parsed = new URL(url);
        return parsed.hostname.replace('www.', '');
    } catch {
        return 'Unknown';
    }
}

/**
 * Debounce function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
export function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle function calls
 * @param {Function} func - Function to throttle
 * @param {number} limit - Time limit in milliseconds
 * @returns {Function} Throttled function
 */
export function throttle(func, limit = 1000) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>} Success status
 */
export async function copyToClipboard(text) {
    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text);
            return true;
        } else {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            const success = document.execCommand('copy');
            document.body.removeChild(textarea);
            return success;
        }
    } catch (error) {
        console.error('Failed to copy to clipboard:', error);
        return false;
    }
}

/**
 * Generate unique ID
 * @returns {string} Unique identifier
 */
export function generateId() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Parse query parameters from URL
 * @param {string} url - URL to parse
 * @returns {object} Query parameters object
 */
export function parseQueryParams(url = window.location.search) {
    const params = {};
    const searchParams = new URLSearchParams(url);

    for (const [key, value] of searchParams) {
        params[key] = value;
    }

    return params;
}

/**
 * Create query string from object
 * @param {object} params - Parameters object
 * @returns {string} Query string
 */
export function createQueryString(params) {
    const searchParams = new URLSearchParams();

    for (const [key, value] of Object.entries(params)) {
        if (value !== null && value !== undefined) {
            searchParams.append(key, value);
        }
    }

    const queryString = searchParams.toString();
    return queryString ? `?${queryString}` : '';
}

/**
 * Get localStorage item with JSON parsing
 * @param {string} key - Storage key
 * @param {*} defaultValue - Default value if key not found
 * @returns {*} Stored value or default
 */
export function getStorageItem(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
        console.error(`Error reading from localStorage:`, error);
        return defaultValue;
    }
}

/**
 * Set localStorage item with JSON stringification
 * @param {string} key - Storage key
 * @param {*} value - Value to store
 * @returns {boolean} Success status
 */
export function setStorageItem(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
    } catch (error) {
        console.error(`Error writing to localStorage:`, error);
        return false;
    }
}

/**
 * Show browser notification
 * @param {string} title - Notification title
 * @param {object} options - Notification options
 * @returns {Promise<boolean>} Success status
 */
export async function showNotification(title, options = {}) {
    if (!('Notification' in window)) {
        console.warn('Browser does not support notifications');
        return false;
    }

    try {
        if (Notification.permission === 'granted') {
            new Notification(title, {
                icon: '/static/icon-192.png',
                badge: '/static/icon-192.png',
                ...options
            });
            return true;
        } else if (Notification.permission !== 'denied') {
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                new Notification(title, {
                    icon: '/static/icon-192.png',
                    badge: '/static/icon-192.png',
                    ...options
                });
                return true;
            }
        }
    } catch (error) {
        console.error('Failed to show notification:', error);
    }

    return false;
}

/**
 * Retry async function with exponential backoff
 * @param {Function} fn - Async function to retry
 * @param {number} maxRetries - Maximum retry attempts
 * @param {number} baseDelay - Base delay in milliseconds
 * @returns {Promise<*>} Result of function
 */
export async function retryWithBackoff(fn, maxRetries = 3, baseDelay = 1000) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await fn();
        } catch (error) {
            if (i === maxRetries - 1) throw error;

            const delay = baseDelay * Math.pow(2, i);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
}

/**
 * Check if device is mobile
 * @returns {boolean} True if mobile device
 */
export function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

/**
 * Get platform name from URL
 * @param {string} url - URL to analyze
 * @returns {string} Platform name
 */
export function getPlatformName(url) {
    if (!url) return 'Unknown';

    const domain = extractDomain(url).toLowerCase();

    const platforms = {
        'youtube.com': 'YouTube',
        'youtu.be': 'YouTube',
        'vimeo.com': 'Vimeo',
        'twitter.com': 'Twitter',
        'x.com': 'Twitter/X',
        'tiktok.com': 'TikTok',
        'instagram.com': 'Instagram',
        'facebook.com': 'Facebook',
        'reddit.com': 'Reddit',
        'twitch.tv': 'Twitch',
        'dailymotion.com': 'Dailymotion',
        'soundcloud.com': 'SoundCloud'
    };

    for (const [key, name] of Object.entries(platforms)) {
        if (domain.includes(key)) return name;
    }

    return domain;
}

/**
 * Format ETA (estimated time of arrival)
 * @param {number} seconds - Seconds remaining
 * @returns {string} Formatted ETA string
 */
export function formatETA(seconds) {
    if (!seconds || seconds <= 0) return 'Calculating...';
    if (!isFinite(seconds)) return 'Unknown';

    if (seconds < 60) return `${Math.ceil(seconds)}s`;
    if (seconds < 3600) return `${Math.ceil(seconds / 60)}m`;

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.ceil((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
}

/**
 * Calculate download speed
 * @param {number} bytes - Bytes downloaded
 * @param {number} seconds - Time elapsed
 * @returns {string} Formatted speed
 */
export function calculateSpeed(bytes, seconds) {
    if (!bytes || !seconds || seconds <= 0) return '0 B/s';

    const bytesPerSecond = bytes / seconds;
    return formatBytes(bytesPerSecond) + '/s';
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Truncate text with ellipsis
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text
 */
export function truncate(text, maxLength = 50) {
    if (!text || text.length <= maxLength) return text;
    return text.slice(0, maxLength - 3) + '...';
}
