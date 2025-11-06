# PWA Icons

This directory contains icons for the Progressive Web App (PWA).

## Required Icon Sizes

For optimal PWA support, the following icon sizes are needed:

- 72x72px
- 96x96px
- 128x128px
- 144x144px
- 152x152px
- 192x192px
- 384x384px
- 512x512px

## Generating Icons

You can use online tools to generate PWA icons from a single source image:

1. **PWA Asset Generator**: https://www.pwabuilder.com/imageGenerator
2. **Favicon Generator**: https://realfavicongenerator.net/
3. **Image Resize Tool**: https://www.iloveimg.com/resize-image

## Design Guidelines

- Use a simple, recognizable icon (e.g., lightning bolt ⚡)
- Ensure good contrast for both light and dark backgrounds
- Make the icon work at small sizes (72x72px)
- Follow platform-specific icon guidelines (iOS, Android)

## Placeholder Icons

Until proper icons are created, the app uses an SVG emoji as a favicon.

To create placeholder PNGs:

```bash
# Using ImageMagick
for size in 72 96 128 144 152 192 384 512; do
  convert -size ${size}x${size} xc:transparent \
    -font "Arial-Unicode-MS" -pointsize $((size*3/4)) \
    -fill "#6366f1" -gravity center \
    -annotate +0+0 "⚡" \
    icon-${size}x${size}.png
done
```

Or use an online service to generate from a vector graphic.
