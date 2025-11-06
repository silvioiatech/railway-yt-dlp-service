# Ultimate Media Downloader - Frontend

## Overview

A modern, responsive web interface for the Ultimate Media Downloader service built with vanilla JavaScript, Alpine.js, and Tailwind CSS.

## Technology Stack

- **Framework**: Alpine.js 3.x (lightweight reactivity)
- **Styling**: Tailwind CSS 3.x (utility-first CSS)
- **JavaScript**: ES6+ Modules
- **PWA**: Service Worker for offline functionality
- **Build**: No build step required (serves directly from static/)

## File Structure

```
static/
├── index.html              # Main application page
├── manifest.json           # PWA manifest
├── service-worker.js       # PWA service worker
├── css/
│   └── custom.css         # Custom styles and animations
├── js/
│   ├── app.js             # Main application logic
│   ├── api.js             # API client for backend communication
│   └── utils.js           # Utility functions
└── icons/                 # PWA icons (192x192, 512x512, etc.)
```

## Features

### Core Functionality
- Single video downloads with real-time progress tracking
- Advanced quality selection (Best, 4K, 1080p, 720p, 480p, 360p, Audio Only)
- Format selection (MP4, MKV, WebM for video; MP3, M4A, FLAC for audio)
- Subtitle download options
- Thumbnail and metadata embedding
- Recent downloads history (localStorage)

### UI/UX Features
- Dark/light theme toggle with persistence
- Responsive design (mobile-first, 320px - 1920px)
- Toast notifications for user feedback
- Real-time download status updates
- Settings modal for API key and preferences
- Keyboard navigation and accessibility (ARIA labels)

### Progressive Web App (PWA)
- Installable on desktop and mobile devices
- Offline functionality via Service Worker
- App-like experience with standalone mode
- Share target API support (Android)
- Custom app shortcuts

## API Integration

The frontend communicates with the FastAPI backend through the `MediaDownloaderAPI` class defined in `api.js`.

### Key API Endpoints Used

```javascript
// Download Management
POST /download                 // Create new download
GET /downloads/:id            // Get download status
GET /downloads/:id/logs       // Get download logs

// Metadata
GET /api/v1/metadata          // Get video information

// Playlist (Future Enhancement)
GET /api/v1/playlist/info     // Get playlist information
POST /api/v1/playlist/download // Download playlist

// Batch (Future Enhancement)
POST /api/v1/batch/download   // Batch download multiple URLs
GET /api/v1/batch/:id         // Get batch status
```

## State Management

The application uses Alpine.js for reactive state management with localStorage persistence:

- **Downloads**: Array of download objects (persisted)
- **Settings**: API key, auto-refresh, refresh interval (persisted)
- **UI State**: Dark mode, modals, toasts (theme persisted)

## Configuration

### API Key (Optional)

If the backend requires authentication:

1. Click the Settings icon in the header
2. Enter your API key
3. Click "Done"

The API key is stored in localStorage and sent with all API requests via the `X-API-Key` header.

### Auto-Refresh

Downloads are automatically refreshed every 3 seconds (configurable) when active. This can be toggled in settings.

## Development

### Local Development

1. Ensure the backend is running on `http://localhost:8080`
2. Open `static/index.html` directly in a browser, or
3. Serve via the FastAPI backend: `python -m uvicorn app.main:app --reload`

### Browser Requirements

- Modern browsers with ES6 module support
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- iOS Safari 14+

### Testing

Open browser DevTools and check:

1. **Console**: No JavaScript errors
2. **Network**: API calls return 200/201 responses
3. **Application** > Storage: localStorage items persist
4. **Application** > Service Workers: Service worker registers
5. **Lighthouse**: PWA score 90+

## Customization

### Theming

Edit `static/css/custom.css` to customize:
- Colors (dark/light mode)
- Animations
- Layout spacing
- Typography

### Features

Add new features by:
1. Adding UI elements to `index.html`
2. Implementing logic in `app.js`
3. Adding API methods to `api.js` if needed
4. Creating utility functions in `utils.js`

## Performance

### Optimization Techniques

- **CDN Loading**: Tailwind and Alpine.js loaded from CDN
- **Lazy Loading**: Images and content loaded on demand
- **Caching**: Service Worker caches static assets
- **LocalStorage**: Minimizes API calls for settings
- **Debouncing**: Input handlers debounced to reduce updates

### Core Web Vitals

Target metrics:
- **LCP** (Largest Contentful Paint): < 2.5s
- **FID** (First Input Delay): < 100ms
- **CLS** (Cumulative Layout Shift): < 0.1

## Accessibility

### ARIA Support

- Proper semantic HTML
- ARIA labels for interactive elements
- Keyboard navigation support
- Focus indicators
- Screen reader friendly

### Mobile Optimization

- Touch targets minimum 44x44px
- Swipe gestures (future enhancement)
- Bottom sheet modals on mobile
- Responsive breakpoints
- Viewport-safe areas

## Security

### Best Practices

- **XSS Prevention**: All user input escaped
- **HTTPS Only**: Service Worker requires HTTPS (or localhost)
- **Content Security Policy**: Configured in HTML meta tags
- **API Key Storage**: Stored in localStorage (user-controlled)
- **No Sensitive Data**: No personal information collected

## Browser Storage

### LocalStorage Keys

```javascript
{
  "darkMode": "true|false",
  "apiKey": "user-api-key",
  "autoRefresh": "true|false",
  "refreshInterval": "3",
  "downloads": "[array of download objects]"
}
```

## Troubleshooting

### Common Issues

**Downloads not appearing**
- Check browser console for API errors
- Verify backend is running
- Check API key in settings if auth enabled

**Service Worker not registering**
- Ensure HTTPS or localhost
- Clear browser cache
- Check browser console for errors

**Dark mode not persisting**
- Check localStorage is enabled
- Clear browser data and retry

## Future Enhancements

- Playlist browser with preview
- Channel download support
- Batch download UI
- Download queue management
- WebSocket for real-time updates
- Background sync for offline downloads
- Push notifications
- Export/import download history
- Advanced filters and search
- Statistics dashboard

## Contributing

To contribute to the frontend:

1. Follow the existing code style
2. Test on multiple browsers and devices
3. Ensure accessibility standards are met
4. Keep bundle size minimal
5. Document new features

## License

See main project LICENSE file.

## Support

For issues or questions:
- Check the main project README
- Review API documentation at `/docs`
- Open an issue on GitHub
