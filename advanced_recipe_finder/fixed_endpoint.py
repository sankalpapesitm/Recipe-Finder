import os
import base64
from io import BytesIO
from uuid import uuid4
from PIL import Image
import requests
from flask import Flask, request, jsonify, url_for

app = Flask(__name__)

@app.route('/generate_recipe_image', methods=['POST'])
def generate_recipe_image_endpoint():
    try:
        data = request.get_json()
        prompt = data.get("prompt", "")
        ingredients = data.get("ingredients", "")
        logo_file = data.get("logo_file", None)

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
            
        if not ingredients:
            ingredients = "no specific ingredients provided"

        # Direct API call to Gemini
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={app.config['GEMINI_API_KEY']}"
        
        request_body = {
            'contents': [{
                'parts': [{
                    'text': f"""Create a professional food photograph.
Main Dish: {prompt}
Made with: {ingredients}
Required style: Professional food photography with commercial quality lighting, high resolution details, appetizing presentation, styled food plating, natural colors and textures, clean background, and sharp focus on the dish."""
                }]
            }],
            'generationConfig': {
                'responseModalities': ['Text', 'Image'],
            }
        }
        
        # Make the API call
        response = requests.post(
            url,
            headers={'Content-Type': 'application/json'},
            json=request_body,
            timeout=120
        )
        
        app.logger.info("Made API request to Gemini")
        
        if response.status_code == 200:
            json_response = response.json()
            
            if 'candidates' in json_response and json_response['candidates']:
                candidate = json_response['candidates'][0]
                
                if candidate.get('content') and candidate['content'].get('parts'):
                    for part in candidate['content']['parts']:
                        if part.get('inlineData') and part['inlineData'].get('data'):
                            image_data = part['inlineData']['data']
                            image_bytes = base64.b64decode(image_data)
                            
                            # Process image with PIL if we have a logo
                            if logo_file:
                                try:
                                    image = Image.open(BytesIO(image_bytes)).convert('RGBA')

                                    # Process logo
                                    logo_bytes = base64.b64decode(logo_file.split(',')[1])
                                    logo = Image.open(BytesIO(logo_bytes)).convert('RGBA')

                                    # Calculate logo size (15% of image width)
                                    logo_width = int(image.width * 0.15)
                                    logo_height = int(logo_width * (logo.height / logo.width))

                                    # Resize logo
                                    logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

                                    # Paste logo with padding
                                    image.paste(logo, (30, 30), logo)

                                    # Convert back to bytes
                                    output = BytesIO()
                                    image.save(output, format='PNG')
                                    image_bytes = output.getvalue()

                                except Exception as e:
                                    app.logger.warning(f"Logo overlay failed: {e}")

                            # Resize image to standard size (512x512)
                            try:
                                image = Image.open(BytesIO(image_bytes))
                                image = image.resize((512, 512), Image.Resampling.LANCZOS)
                                output = BytesIO()
                                image.save(output, format='PNG')
                                image_bytes = output.getvalue()
                            except Exception as e:
                                app.logger.warning(f"Image resize failed: {e}")

                            # Save final image
                            unique_filename = f"{uuid4().hex}.png"
                            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

                            with open(filepath, 'wb') as f:
                                f.write(image_bytes)
                            
                            final_image_url = url_for('uploaded_file', filename=unique_filename, _external=True)
                            
                            return jsonify({
                                "success": True,
                                "image_prompt": f"{prompt} with {ingredients}",
                                "image_url": final_image_url,
                                "user": "Gemini 2.0 Flash Exp",
                                "note": "Image generated by Gemini AI"
                            })
            
            app.logger.error("No valid image in response")
            return jsonify({
                "success": False,
                "error": "Could not generate an image. Please try rephrasing your prompt."
            }), 404
            
        else:
            error_data = response.json()
            error_msg = f"API Error {response.status_code}: {error_data.get('error', {}).get('message', str(error_data))}"
            app.logger.error(error_msg)
            return jsonify({
                "success": False,
                "error": error_msg
            }), response.status_code
            
    except Exception as e:
        app.logger.error(f"Error during image generation: {e}")
        return jsonify({
            "success": False,
            "error": f"An error occurred: {str(e)}"
        }), 500