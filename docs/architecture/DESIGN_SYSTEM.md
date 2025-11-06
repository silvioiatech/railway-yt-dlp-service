# Ultimate Media Downloader - Design System Documentation

## Overview

A modern, accessible, and mobile-first design system for the Ultimate Media Downloader web application. Built with Tailwind CSS and Alpine.js for rapid development and seamless user experience.

---

## Design Philosophy

### Core Principles

1. **Mobile-First**: Designed for touch interfaces, then enhanced for desktop
2. **Speed**: Fast loading, immediate feedback, smooth animations
3. **Accessibility**: WCAG 2.1 AA compliant, keyboard navigable, screen reader friendly
4. **Clarity**: Clear information hierarchy, intuitive interactions
5. **Delight**: Subtle animations, smooth transitions, satisfying micro-interactions

### Visual Direction

- **Modern Minimalism**: Clean layouts with generous whitespace
- **Gradient Accents**: Subtle gradients for depth and visual interest
- **Glass Morphism**: Translucent elements for modern aesthetic
- **Bold Typography**: Clear hierarchy with varied font weights
- **Vibrant Colors**: Indigo-purple gradient as primary brand

---

## Color System

### Primary Palette

```css
/* Indigo - Primary Brand Color */
--indigo-50:  #eef2ff
--indigo-100: #e0e7ff
--indigo-500: #6366f1  /* Primary CTA */
--indigo-600: #4f46e5  /* Hover state */
--indigo-700: #4338ca  /* Active state */

/* Purple - Accent Color */
--purple-500: #8b5cf6
--purple-600: #7c3aed

/* Pink - Highlight */
--pink-500: #ec4899
--pink-600: #db2777
```

### Semantic Colors

```css
/* Success */
--green-500: #10b981
--green-600: #059669

/* Warning */
--yellow-500: #f59e0b
--yellow-600: #d97706

/* Error */
--red-500: #ef4444
--red-600: #dc2626

/* Info */
--blue-500: #3b82f6
--blue-600: #2563eb
```

### Neutral Palette

```css
/* Light Mode */
--gray-50:  #f9fafb  /* Backgrounds */
--gray-100: #f3f4f6  /* Surfaces */
--gray-300: #d1d5db  /* Borders */
--gray-500: #6b7280  /* Secondary text */
--gray-700: #374151  /* Primary text */
--gray-900: #111827  /* Headlines */

/* Dark Mode */
--gray-800: #1f2937  /* Backgrounds */
--gray-700: #374151  /* Surfaces */
--gray-600: #4b5563  /* Borders */
--gray-400: #9ca3af  /* Secondary text */
--gray-200: #e5e7eb  /* Primary text */
--white:    #ffffff  /* Headlines */
```

---

## Typography

### Font Stack

```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
             'Roboto', 'Helvetica', 'Arial', sans-serif;
```

### Type Scale (Mobile-First)

```css
/* Display - Hero Headlines */
.text-4xl { font-size: 2.25rem; line-height: 2.5rem; }    /* 36px */
.text-5xl { font-size: 3rem; line-height: 1; }            /* 48px */

/* Headings */
.text-3xl { font-size: 1.875rem; line-height: 2.25rem; }  /* 30px */
.text-2xl { font-size: 1.5rem; line-height: 2rem; }       /* 24px */
.text-xl  { font-size: 1.25rem; line-height: 1.75rem; }   /* 20px */
.text-lg  { font-size: 1.125rem; line-height: 1.75rem; }  /* 18px */

/* Body */
.text-base { font-size: 1rem; line-height: 1.5rem; }      /* 16px */
.text-sm   { font-size: 0.875rem; line-height: 1.25rem; } /* 14px */
.text-xs   { font-size: 0.75rem; line-height: 1rem; }     /* 12px */
```

### Font Weights

```css
.font-normal    { font-weight: 400; }  /* Body text */
.font-medium    { font-weight: 500; }  /* Emphasis */
.font-semibold  { font-weight: 600; }  /* Subheadings */
.font-bold      { font-weight: 700; }  /* Headlines, CTAs */
```

---

## Spacing System

### Scale (Tailwind Default - 4px base)

```css
.p-1  { padding: 0.25rem; }   /* 4px */
.p-2  { padding: 0.5rem; }    /* 8px */
.p-3  { padding: 0.75rem; }   /* 12px */
.p-4  { padding: 1rem; }      /* 16px - Default */
.p-6  { padding: 1.5rem; }    /* 24px - Section */
.p-8  { padding: 2rem; }      /* 32px - Large */
.p-12 { padding: 3rem; }      /* 48px - Hero */
```

### Layout Spacing

- **Component Internal**: 16px (p-4)
- **Between Components**: 24px (space-y-6)
- **Section Spacing**: 48px (mb-12)
- **Mobile Safe Area**: 16px minimum

---

## Layout Grid

### Responsive Breakpoints

```css
/* Mobile First */
default:   /* 0px - 639px */
sm:  640px  /* Small tablets */
md:  768px  /* Tablets */
lg:  1024px /* Desktop */
xl:  1280px /* Large desktop */
2xl: 1536px /* Extra large */
```

### Container

```css
.max-w-7xl { max-width: 80rem; }  /* 1280px - Main content */
.max-w-3xl { max-width: 48rem; }  /* 768px - Form/card width */
```

### Grid System

```css
/* Mobile: Single column */
.grid-cols-1

/* Tablet: 2 columns */
.sm:grid-cols-2

/* Desktop: 3 columns */
.md:grid-cols-3
```

---

## Components

### Buttons

#### Primary Button

```html
<button class="px-6 py-4 bg-gradient-to-r from-indigo-600 to-purple-600
               text-white font-semibold rounded-xl
               hover:from-indigo-700 hover:to-purple-700
               disabled:opacity-50 disabled:cursor-not-allowed
               shadow-lg hover:shadow-xl
               transform hover:-translate-y-0.5
               transition-all">
    Download
</button>
```

**Specs:**
- Height: 56px (py-4)
- Padding: 24px horizontal
- Border radius: 12px (rounded-xl)
- Font: Semibold, 16px
- Gradient background
- Hover lift effect

#### Secondary Button

```html
<button class="px-6 py-4 bg-white dark:bg-gray-700
               text-gray-700 dark:text-gray-200
               font-semibold rounded-xl
               border-2 border-gray-300 dark:border-gray-600
               hover:border-indigo-500 dark:hover:border-indigo-500
               hover:bg-gray-50 dark:hover:bg-gray-600
               transition-all">
    Get Info
</button>
```

#### Mobile Touch Button (44x44px minimum)

```html
<button class="min-w-[44px] min-h-[44px] p-3
               rounded-lg active:scale-95
               transition-transform">
    <!-- Icon -->
</button>
```

### Input Fields

#### Text Input

```html
<input type="text"
       class="w-full px-4 py-4 text-lg rounded-xl
              border-2 border-gray-300 dark:border-gray-600
              bg-white dark:bg-gray-900
              text-gray-900 dark:text-white
              placeholder-gray-400
              focus:border-indigo-500
              focus:ring-4 focus:ring-indigo-500/20
              outline-none transition-all"
       placeholder="https://youtube.com/watch?v=...">
```

**Specs:**
- Height: 56px (py-4)
- Font size: 18px (mobile), 16px (desktop)
- Border: 2px solid
- Border radius: 12px
- Focus ring: 4px, 20% opacity

#### Select Dropdown

```html
<select class="w-full px-4 py-3 rounded-lg
               border-2 border-gray-300 dark:border-gray-600
               bg-white dark:bg-gray-700
               text-gray-900 dark:text-white
               focus:border-indigo-500 focus:ring-4
               focus:ring-indigo-500/20 outline-none">
    <option>MP4 (recommended)</option>
    <option>MKV</option>
</select>
```

#### Checkbox

```html
<label class="flex items-center cursor-pointer">
    <input type="checkbox"
           class="w-5 h-5 rounded border-gray-300
                  text-indigo-600
                  focus:ring-indigo-500 focus:ring-offset-0
                  cursor-pointer">
    <span class="ml-3 text-sm font-medium text-gray-700 dark:text-gray-300">
        Download subtitles
    </span>
</label>
```

### Cards

#### Basic Card

```html
<div class="bg-white dark:bg-gray-800
            rounded-2xl shadow-2xl
            p-6 sm:p-8
            border border-gray-100 dark:border-gray-700">
    <!-- Content -->
</div>
```

**Specs:**
- Border radius: 16px (rounded-2xl)
- Padding: 24px mobile, 32px desktop
- Shadow: xl or 2xl
- Border: 1px subtle

#### Progress Card

```html
<div class="bg-white dark:bg-gray-800
            rounded-xl shadow-lg
            p-6 border border-gray-100 dark:border-gray-700
            animate-slide-up">
    <!-- Title -->
    <h4 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        Video Title
    </h4>

    <!-- Progress Bar -->
    <div class="w-full bg-gray-200 dark:bg-gray-700
                rounded-full h-3 overflow-hidden">
        <div class="h-full bg-gradient-to-r from-indigo-500 to-purple-500
                    progress-animated rounded-full transition-all"
             style="width: 45%"></div>
    </div>
</div>
```

### Badges

#### Status Badge

```html
<span class="px-3 py-1 rounded-full text-xs font-semibold
             bg-blue-100 text-blue-800
             dark:bg-blue-900 dark:text-blue-200">
    Downloading
</span>
```

**Variants:**
- **Queued**: Yellow (bg-yellow-100 text-yellow-800)
- **Downloading**: Blue (bg-blue-100 text-blue-800)
- **Completed**: Green (bg-green-100 text-green-800)
- **Failed**: Red (bg-red-100 text-red-800)

### Progress Bars

```html
<div class="w-full bg-gray-200 dark:bg-gray-700
            rounded-full h-3 overflow-hidden">
    <div class="h-full bg-gradient-to-r from-indigo-500 to-purple-500
                progress-animated rounded-full transition-all duration-300"
         style="width: 45%"></div>
</div>
```

**Animation (CSS):**

```css
@keyframes progress {
    0% { background-position: 0 0; }
    100% { background-position: 40px 0; }
}

.progress-animated {
    background: linear-gradient(
        45deg,
        transparent 25%,
        rgba(255, 255, 255, 0.2) 25%,
        rgba(255, 255, 255, 0.2) 50%,
        transparent 50%,
        transparent 75%,
        rgba(255, 255, 255, 0.2) 75%,
        rgba(255, 255, 255, 0.2)
    );
    background-size: 40px 40px;
    animation: progress 1s linear infinite;
}
```

---

## Animations & Transitions

### Standard Transitions

```css
/* Default transition for colors, backgrounds */
transition: background-color 0.2s, border-color 0.2s, color 0.2s;

/* Transform transitions */
transition: transform 0.3s ease-out, opacity 0.3s ease-out;
```

### Micro-Interactions

#### Slide Up (Entry Animation)

```css
@keyframes slideUp {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-slide-up {
    animation: slideUp 0.3s ease-out;
}
```

#### Button Hover Shine

```css
.btn-primary {
    position: relative;
    overflow: hidden;
}

.btn-primary::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    transition: left 0.5s;
}

.btn-primary:hover::before {
    left: 100%;
}
```

#### Touch Feedback (Mobile)

```css
.touch-feedback:active {
    transform: scale(0.95);
    opacity: 0.8;
}
```

### Loading States

#### Pulse Animation

```css
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.animate-pulse-slow {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
```

---

## Mobile-Specific Patterns

### Bottom Sheet Modal

```html
<div class="fixed inset-0 bg-black/50 z-50"
     @click.self="showModal = false">
    <div class="fixed bottom-0 left-0 right-0
                bg-white dark:bg-gray-800
                rounded-t-3xl max-h-[85vh]
                overflow-y-auto transform transition-transform">
        <!-- Handle -->
        <div class="w-10 h-1 bg-gray-300 rounded-full
                    mx-auto my-3"></div>

        <!-- Content -->
        <div class="px-4 pb-6">
            <!-- ... -->
        </div>
    </div>
</div>
```

### Safe Area Handling

```css
@supports(padding: max(0px)) {
    .safe-area-top {
        padding-top: max(env(safe-area-inset-top), 16px);
    }
    .safe-area-bottom {
        padding-bottom: max(env(safe-area-inset-bottom), 16px);
    }
}
```

### Touch Target Size

**Minimum**: 44x44px (iOS HIG, Material Design)

```html
<button class="min-w-[44px] min-h-[44px] p-3">
    <svg class="w-6 h-6"><!-- Icon --></svg>
</button>
```

---

## Dark Mode

### Implementation

```javascript
// Toggle dark mode
function toggleDarkMode() {
    document.documentElement.classList.toggle('dark');
    localStorage.setItem('darkMode',
        document.documentElement.classList.contains('dark'));
}

// Initialize
if (localStorage.getItem('darkMode') === 'true') {
    document.documentElement.classList.add('dark');
}
```

### Dark Mode Colors

```html
<!-- Background -->
<div class="bg-white dark:bg-gray-800">

<!-- Text -->
<p class="text-gray-900 dark:text-white">

<!-- Border -->
<div class="border-gray-200 dark:border-gray-700">

<!-- Input -->
<input class="bg-white dark:bg-gray-900
              text-gray-900 dark:text-white
              border-gray-300 dark:border-gray-600">
```

---

## Icons

### Icon Library

**Heroicons** - Used throughout (via inline SVG)

```html
<!-- Download Icon -->
<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4">
    </path>
</svg>
```

### Icon Sizes

```css
.w-4.h-4   /* 16px - Small inline */
.w-5.h-5   /* 20px - Button icons */
.w-6.h-6   /* 24px - Navigation */
.w-8.h-8   /* 32px - Feature icons */
.w-12.h-12 /* 48px - Hero icons */
```

---

## Accessibility

### WCAG 2.1 AA Compliance

#### Color Contrast

- **Normal Text**: 4.5:1 minimum
- **Large Text (18px+)**: 3:1 minimum
- **Interactive Elements**: 3:1 minimum

#### Focus States

```css
/* Visible focus ring */
.focus:ring-4 .focus:ring-indigo-500/20

/* Keyboard navigation */
.focus-visible:outline-2
.focus-visible:outline-offset-2
.focus-visible:outline-indigo-500
```

#### Screen Reader Support

```html
<!-- Hidden labels -->
<label class="sr-only" for="url-input">Video URL</label>

<!-- ARIA labels -->
<button aria-label="Toggle dark mode" title="Toggle dark mode">
    <svg><!-- Icon --></svg>
</button>

<!-- Live regions -->
<div role="status" aria-live="polite" aria-atomic="true">
    Download progress: 45%
</div>
```

#### Keyboard Navigation

- **Tab order**: Logical flow
- **Enter/Space**: Activate buttons
- **Escape**: Close modals
- **Arrow keys**: Navigate options

---

## Responsive Breakpoints

### Mobile First Approach

```html
<!-- Default: Mobile (0-639px) -->
<div class="text-sm p-4">

<!-- Tablet (640px+) -->
<div class="sm:text-base sm:p-6">

<!-- Desktop (1024px+) -->
<div class="lg:text-lg lg:p-8">
```

### Common Patterns

```html
<!-- Stack on mobile, grid on desktop -->
<div class="grid grid-cols-1 md:grid-cols-3 gap-4">

<!-- Full width on mobile, contained on desktop -->
<div class="w-full md:max-w-3xl md:mx-auto">

<!-- Hide on mobile, show on desktop -->
<div class="hidden md:block">

<!-- Show on mobile, hide on desktop -->
<div class="block md:hidden">
```

---

## Performance Optimization

### Image Loading

```html
<!-- Lazy loading -->
<img loading="lazy" src="thumbnail.jpg" alt="Video thumbnail">

<!-- Responsive images -->
<img srcset="thumb-320.jpg 320w, thumb-640.jpg 640w"
     sizes="(max-width: 640px) 320px, 640px">
```

### CSS Optimization

```css
/* GPU acceleration for animations */
.transform {
    will-change: transform;
}

/* Contain layout thrashing */
.card {
    contain: layout style paint;
}
```

### JavaScript

- Defer Alpine.js load
- Use event delegation
- Debounce input handlers
- LocalStorage for state persistence

---

## Browser Support

### Minimum Requirements

- **Desktop**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Mobile**: iOS Safari 14+, Chrome Android 90+
- **Features**: ES6+, CSS Grid, Flexbox, CSS Custom Properties

### Progressive Enhancement

- Core functionality works without JavaScript
- Enhanced experience with Alpine.js
- Graceful degradation for older browsers

---

## File Structure

```
static/
├── index.html              # Desktop-optimized UI
├── mobile.html             # Mobile-specific UI
├── manifest.json           # PWA manifest
├── css/
│   └── custom.css         # Additional custom styles
├── js/
│   ├── app.js             # Main application logic
│   ├── api.js             # API integration
│   └── utils.js           # Helper functions
└── icons/
    └── icon-*.png         # PWA icons
```

---

## Development Workflow

### Quick Start

1. **Include Tailwind CSS via CDN**:
   ```html
   <script src="https://cdn.tailwindcss.com"></script>
   ```

2. **Add Alpine.js for reactivity**:
   ```html
   <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
   ```

3. **Start with mobile layout**, enhance for desktop

### Testing Checklist

- [ ] Mobile (320px - 768px)
- [ ] Tablet (768px - 1024px)
- [ ] Desktop (1024px+)
- [ ] Dark mode
- [ ] Keyboard navigation
- [ ] Screen reader
- [ ] Touch gestures
- [ ] Slow network (throttle to 3G)

---

## API Integration Points

### Required Endpoints

```javascript
// Get video/playlist info
GET /api/metadata?url={url}

// Start download
POST /api/download
{
    "url": "...",
    "quality": "1080p",
    "format": "mp4",
    "subtitles": true
}

// Get download status
GET /api/download/{id}

// Cancel download
DELETE /api/download/{id}
```

### WebSocket for Real-Time Progress

```javascript
const ws = new WebSocket('wss://your-app.railway.app/ws');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Update progress UI
    updateProgress(data.progress, data.speed, data.eta);
};
```

---

## PWA Configuration

### Service Worker

```javascript
// sw.js
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open('v1').then((cache) => {
            return cache.addAll([
                '/',
                '/static/index.html',
                '/static/css/custom.css',
                '/static/js/app.js'
            ]);
        })
    );
});
```

### Installation

```javascript
// Detect installation prompt
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    showInstallButton();
});

// Trigger installation
async function installApp() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        deferredPrompt = null;
    }
}
```

---

## Analytics & Monitoring

### Key Metrics to Track

1. **Performance**
   - Page load time
   - Time to interactive
   - First contentful paint

2. **User Behavior**
   - Download completion rate
   - Average quality selected
   - Most used platforms

3. **Errors**
   - Download failures
   - API errors
   - Network timeouts

---

## Future Enhancements

### Phase 2 Features

- **Playlist Browser**: Grid view with thumbnails
- **Batch Downloads**: Multiple URLs at once
- **Download Queue**: Manage multiple downloads
- **History View**: Searchable download history
- **Settings Panel**: User preferences

### Advanced UI Patterns

- **Drag & Drop**: Drop video links anywhere
- **Swipe Actions**: Swipe to delete/retry
- **Pull to Refresh**: Update download status
- **Haptic Feedback**: Vibration on actions (mobile)
- **Voice Input**: Speak URLs (accessibility)

---

## Credits & Resources

- **Tailwind CSS**: https://tailwindcss.com
- **Alpine.js**: https://alpinejs.dev
- **Heroicons**: https://heroicons.com
- **Color Palette**: Tailwind Colors
- **Inspiration**: Linear, Vercel, Railway

---

**Version**: 1.0
**Last Updated**: 2025-11-04
**Maintained By**: Development Team

---

*This design system is optimized for rapid development while maintaining high quality and accessibility standards.*
