# -*- coding: utf-8 -*-
"""
Bytez AI Image Generator Module
Integrates Bytez AI for natural, realistic food image generation
"""
import os
import base64
import tempfile
import ssl
from datetime import datetime
from PIL import Image
from io import BytesIO

# Disable SSL warnings for image downloads
import urllib3
try:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except:
    pass

try:
    from bytez import Bytez
    BYTEZ_AVAILABLE = True
except ImportError:
    BYTEZ_AVAILABLE = False
    print("Bytez not available. Please install: pip install bytez")


class BytezImageGenerator:
    """
    High-quality image generator using Bytez AI
    Designed specifically for natural, realistic food photography
    """
    
    def __init__(self, api_key=None):
        """
        Initialize Bytez image generator
        
        Args:
            api_key: Bytez API key (required, should be passed from config.py)
        """
        self.api_key = api_key
        self.bytez_client = None
        self.model = None
        
        if BYTEZ_AVAILABLE and self.api_key:
            try:
                self.bytez_client = Bytez(self.api_key)
                # Use dreamlike-photoreal model for natural, realistic images
                self.model = self.bytez_client.model("dreamlike-art/dreamlike-photoreal-2.0")
                print("Bytez Photoreal 2.0 model initialized successfully")
            except Exception as e:
                print(f"Bytez initialization failed: {e}")
                self.bytez_client = None
    
    def is_available(self):
        """Check if Bytez is properly configured"""
        return BYTEZ_AVAILABLE and self.bytez_client is not None
    
    def build_enhanced_prompt(self, user_description, ingredients=""):
        """
        Build an optimized prompt for natural food photography
        
        Args:
            user_description: Main description of the dish
            ingredients: Optional ingredients list
            
        Returns:
            Enhanced prompt string
        """
        # Clean the description
        clean_description = user_description.strip()
        
        # Specific prompt for actual cooked/prepared food only, not packaging
        if ingredients:
            # Use only top 2 key ingredients
            ing_list = [i.strip() for i in ingredients.split(',')[:2]]
            ing_text = ', '.join(ing_list)
            prompt = f"cooked {clean_description} dish with {ing_text}, served on plate, food photography, restaurant plating"
        else:
            prompt = f"cooked {clean_description} dish, served on plate, food photography, restaurant plating"
        
        return prompt
    
    def generate_image(self, description, ingredients="", logo_path=None):
        """
        Generate a high-quality food image
        
        Args:
            description: Description of the dish to generate
            ingredients: Optional ingredients string
            logo_path: Optional path to logo file to overlay
            
        Returns:
            dict with 'success', 'image_path', 'error' keys
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'Bytez not available. Please install: pip install bytez'
            }
        
        try:
            # Build the prompt
            prompt = self.build_enhanced_prompt(description, ingredients)
            print(f"Generating image with prompt: {prompt}")
            
            # Call Bytez API - simplified without unsupported parameters
            try:
                result = self.model.run(prompt)
                print(f"Bytez API returned result type: {type(result)}")
            except Exception as model_error:
                print(f"Bytez model.run() failed: {model_error}")
                return {
                    'success': False,
                    'error': f'Bytez API error: {str(model_error)}'
                }
            
            # Process the result
            image_path = self._process_bytez_output(result, logo_path)
            
            if image_path:
                print(f"Image successfully saved to: {image_path}")
                return {
                    'success': True,
                    'image_path': image_path,
                    'prompt': prompt
                }
            else:
                return {
                    'success': False,
                    'error': 'No image generated from Bytez API - processing failed'
                }
                
        except Exception as e:
            print(f"Exception in generate_image: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f"Bytez generation error: {str(e)}"
            }
    
    def _process_bytez_output(self, output, logo_path=None):
        """
        Process Bytez API output and save image
        
        Args:
            output: Bytez API response
            logo_path: Optional logo to overlay
            
        Returns:
            Path to saved image file, or None
        """
        try:
            print(f"Processing Bytez output, type: {type(output)}")
            
            # Handle different output formats
            images_to_process = output if isinstance(output, list) else [output]
            
            for idx, image_data in enumerate(images_to_process):
                print(f"Processing image {idx+1}/{len(images_to_process)}, type: {type(image_data)}")
                
                if image_data is None:
                    print("Skipping None image data")
                    continue
                
                # Create temp file
                temp_dir = tempfile.gettempdir()
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                file_path = os.path.join(temp_dir, f"bytez_food_{timestamp}.png")
                
                # Get image bytes
                image_bytes = self._extract_image_bytes(image_data)
                
                if not image_bytes:
                    print(f"Failed to extract image bytes from data at index {idx}")
                    continue
                
                print(f"Successfully extracted {len(image_bytes)} bytes")
                
                # Save and optionally process with logo
                try:
                    with open(file_path, 'wb') as f:
                        f.write(image_bytes)
                    print(f"Saved image to: {file_path}")
                except Exception as save_error:
                    print(f"Error saving image: {save_error}")
                    continue
                
                # Verify the image file is valid
                try:
                    test_img = Image.open(file_path)
                    test_img.verify()
                    print(f"Image verified successfully: {test_img.size}, {test_img.format}")
                except Exception as verify_error:
                    print(f"Image verification failed: {verify_error}")
                    # Try to continue anyway, might still work
                
                # Overlay logo if provided
                if logo_path and os.path.exists(logo_path):
                    try:
                        file_path = self._overlay_logo(file_path, logo_path)
                        print(f"Logo overlay applied successfully")
                    except Exception as e:
                        print(f"Logo overlay failed: {e}")
                        # Continue without logo
                
                return file_path
            
            print("No valid images found in output")
            return None
            
        except Exception as e:
            print(f"Error processing Bytez output: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_image_bytes(self, image_data):
        """
        Extract image bytes from various data formats
        
        Args:
            image_data: Image data in various formats
            
        Returns:
            bytes or None
        """
        try:
            print(f"DEBUG: image_data type = {type(image_data)}")
            if isinstance(image_data, str):
                print(f"DEBUG: String data preview = {image_data[:100] if len(image_data) > 100 else image_data}")
            
            # Handle dict/JSON response (common for Bytez API)
            if isinstance(image_data, dict):
                print(f"DEBUG: Dict keys = {list(image_data.keys())}")
                # Try common keys for image URLs
                for key in ['url', 'image_url', 'output', 'image', 'result', 'data']:
                    if key in image_data:
                        print(f"DEBUG: Found key '{key}' in dict")
                        return self._extract_image_bytes(image_data[key])
                # If dict has no known keys, try to extract first value
                if image_data:
                    first_value = list(image_data.values())[0]
                    print(f"DEBUG: Trying first dict value, type = {type(first_value)}")
                    return self._extract_image_bytes(first_value)
            
            # Handle list (take first item)
            if isinstance(image_data, (list, tuple)) and len(image_data) > 0:
                print(f"DEBUG: List/tuple with {len(image_data)} items, trying first")
                return self._extract_image_bytes(image_data[0])
            
            # Handle PIL Image object (common Bytez output)
            if hasattr(image_data, 'save') and hasattr(image_data, 'mode'):
                try:
                    print("DEBUG: Converting PIL Image to bytes")
                    buffer = BytesIO()
                    image_data.save(buffer, format='PNG')
                    return buffer.getvalue()
                except Exception as pil_error:
                    print(f"Error converting PIL Image: {pil_error}")
            
            # Handle bytes
            if isinstance(image_data, bytes):
                print(f"DEBUG: Already bytes, length = {len(image_data)}")
                return image_data
            
            # Handle file-like object
            if hasattr(image_data, 'read'):
                print("DEBUG: Reading from file-like object")
                return image_data.read()
            
            # Handle URL - Bytez often returns URLs
            if isinstance(image_data, str) and (image_data.startswith('http://') or image_data.startswith('https://')):
                print(f"DEBUG: Downloading from URL: {image_data}")
                try:
                    import requests
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'image/*,*/*'
                    }
                    # Disable SSL verification for problematic certificates
                    response = requests.get(image_data, timeout=90, headers=headers, stream=True, verify=False)
                    response.raise_for_status()
                    content = response.content
                    print(f"DEBUG: Downloaded {len(content)} bytes from URL")
                    return content
                except Exception as req_error:
                    print(f"Error downloading from URL with requests: {req_error}")
                    # Try alternative method without SSL verification
                    try:
                        import urllib.request
                        import ssl
                        # Create unverified SSL context
                        ssl_context = ssl._create_unverified_context()
                        req = urllib.request.Request(image_data, headers=headers)
                        with urllib.request.urlopen(req, timeout=90, context=ssl_context) as url_response:
                            content = url_response.read()
                            print(f"DEBUG: Downloaded {len(content)} bytes via urllib")
                            return content
                    except Exception as urllib_error:
                        print(f"Urllib also failed: {urllib_error}")
                        return None
            
            # Handle base64 data URL
            if isinstance(image_data, str) and 'data:image' in image_data:
                print("DEBUG: Decoding base64 data URL")
                try:
                    if ',' in image_data:
                        header, base64_data = image_data.split(',', 1)
                    else:
                        base64_data = image_data
                    base64_data = base64_data.strip()
                    # Add padding if needed
                    padding = len(base64_data) % 4
                    if padding:
                        base64_data += '=' * (4 - padding)
                    decoded = base64.b64decode(base64_data)
                    print(f"DEBUG: Decoded {len(decoded)} bytes from base64")
                    return decoded
                except Exception as b64_error:
                    print(f"Error decoding base64 data URL: {b64_error}")
            
            # Handle plain base64 string (last resort)
            if isinstance(image_data, str) and len(image_data) > 100:
                print("DEBUG: Attempting plain base64 decode")
                try:
                    base64_data = image_data.strip()
                    padding = len(base64_data) % 4
                    if padding:
                        base64_data += '=' * (4 - padding)
                    decoded = base64.b64decode(base64_data)
                    # Verify it's actually image data
                    if decoded[:4] in [b'\x89PNG', b'\xff\xd8\xff', b'GIF8']:
                        print(f"DEBUG: Successfully decoded {len(decoded)} bytes from plain base64")
                        return decoded
                    else:
                        print(f"DEBUG: Decoded data doesn't look like an image, header: {decoded[:4]}")
                except Exception as b64_error:
                    print(f"Error decoding plain base64: {b64_error}")
            
            print(f"WARNING: Unhandled image_data type: {type(image_data)}")
            if hasattr(image_data, '__dict__'):
                print(f"DEBUG: Object attributes: {dir(image_data)}")
            return None
            
        except Exception as e:
            print(f"Error extracting image bytes: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _overlay_logo(self, image_path, logo_path):
        """
        Overlay logo on image
        
        Args:
            image_path: Path to base image
            logo_path: Path to logo image
            
        Returns:
            Path to new image with logo
        """
        # Open images
        base_image = Image.open(image_path).convert("RGBA")
        logo = Image.open(logo_path).convert("RGBA")
        
        # Calculate logo size (15% of image width)
        logo_width = int(base_image.width * 0.15)
        logo_height = int(logo_width * (logo.height / logo.width))
        
        # Resize logo
        logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
        
        # Create composite
        result = base_image.copy()
        result.paste(logo, (30, 30), logo)
        
        # Save
        output_path = image_path.replace(".png", "_with_logo.png")
        result.save(output_path, "PNG")
        
        return output_path
    
    def generate_placeholder(self, description, output_path=None):
        """
        Generate a simple placeholder image
        
        Args:
            description: Text to include in placeholder
            output_path: Optional path to save to
            
        Returns:
            Path to placeholder image
        """
        if not output_path:
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(temp_dir, f"placeholder_{timestamp}.png")
        
        # Create simple placeholder
        width, height = 800, 1200
        image = Image.new('RGB', (width, height), color='lightblue')
        
        try:
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(image)
            
            try:
                font = ImageFont.truetype("arial.ttf", 40)
            except:
                font = ImageFont.load_default()
            
            draw.text((width//2, height//2), "AI Generated Image", 
                     fill="black", font=font, anchor="mm")
            draw.text((width//2, height//2 + 60), description[:50] + "...", 
                     fill="darkblue", font=font, anchor="mm")
        except:
            pass
        
        image.save(output_path, "PNG")
        return output_path
