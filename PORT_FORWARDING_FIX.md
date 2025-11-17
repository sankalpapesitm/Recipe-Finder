# Port Forwarding Image Display Fix

## Problem
When the Flask application was accessed through port forwarding (e.g., ngrok, VS Code port forwarding, or SSH tunnel), generated recipe images were not displaying. This occurred because image URLs were being generated with `_external=True`, which created absolute URLs with the local hostname/IP address (e.g., `http://localhost:5000/uploads/image.png`).

## Root Cause
The `url_for()` function with `_external=True` generates absolute URLs using the local server address. When accessing the app through a forwarded port with a different domain/URL, these absolute URLs become invalid because they still point to the local machine.

## Solution
Changed all image and audio URL generation to use relative URLs by removing the `_external=True` parameter from `url_for()` calls. Relative URLs work seamlessly in both local and forwarded environments.

### Files Modified
1. **app.py** - Three locations fixed:
   - Line ~1773: `/generate_recipe_image` endpoint
   - Line ~1862: Auto-image generation in `/ai_recipe_generator`
   - Line ~2203: Audio generation in `/generate_recipe_audio`

### Changes Made
```python
# BEFORE (absolute URL - breaks with port forwarding)
final_image_url = url_for('uploaded_file', filename=unique_filename, _external=True)

# AFTER (relative URL - works everywhere)
final_image_url = url_for('uploaded_file', filename=unique_filename)
```

## How It Works Now
- **Locally**: Images work at `http://localhost:5000/uploads/image.png`
- **Port Forwarded**: Images work at `https://your-forwarded-url.com/uploads/image.png`
- **Reverse Proxy**: Images work behind nginx, Apache, etc.

## Benefits
✅ Works with any port forwarding solution (ngrok, localtunnel, VS Code, SSH)
✅ Compatible with reverse proxies
✅ No configuration changes needed
✅ Works in both development and production
✅ Maintains backward compatibility with local development

## Testing
1. Start the Flask app locally
2. Forward the port using your preferred method
3. Generate a recipe with images
4. Verify images display correctly through the forwarded URL

## Technical Details
The Flask `url_for()` function:
- With `_external=True`: Generates absolute URLs based on the Flask app's configured SERVER_NAME or the request's host
- Without `_external=True`: Generates relative URLs that work with any domain/proxy

Relative URLs are resolved by the browser based on the current page's base URL, making them portable across different deployment environments.
