import io
import base64
import os
import json
import re
import logging
import traceback
import requests
from flask import Flask, request, jsonify, send_file, render_template
from PIL import Image

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='../templates')

# Konfigurasi
MAX_BATCH_SIZE = 10
MAX_FILE_SIZE_MB = 50
MAX_TITLE_LEN = 100
MAX_DESC_LEN = 150
MAX_KEYWORD_COUNT = 49

# Model Gemini yang tersedia
GEMINI_MODELS = {
    'gemini-2.0-flash-lite': 'Fast & Lite (Free, 15 RPM)',
    'gemini-2.0-flash': 'Fast & Balanced (Free, 15 RPM)',
    'gemini-2.5-flash-preview': 'Latest Flash (Free, 2 RPM)',
    'gemini-2.5-pro': 'Most Powerful (Free, 2 RPM)'
}


# ============ FUNGSI PEMBANTU ============

def clean_microstock_keywords(keyword_str):
    """Bersihkan keyword string menjadi list untuk microstock (max 49 keywords)"""
    if not keyword_str or not isinstance(keyword_str, str):
        return []
    
    raw_list = keyword_str.split(',')
    cleaned_list = []
    
    for kw in raw_list:
        clean_kw = kw.strip().lower()
        clean_kw = re.sub(r'[^\w\-\s]', '', clean_kw)
        clean_kw = clean_kw.replace(' ', '-')
        clean_kw = re.sub(r'-+', '-', clean_kw)
        clean_kw = clean_kw.strip('-')
        
        if clean_kw and len(clean_kw) >= 2 and len(clean_kw) <= 50:
            cleaned_list.append(clean_kw)
    
    return cleaned_list[:MAX_KEYWORD_COUNT]


def create_xmp_packet(title, description, keywords_list):
    """Membuat XMP packet untuk JPG/PNG/EPS (Dublin Core schema)"""
    # Escape XML special characters
    title = title[:MAX_TITLE_LEN].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    description = description[:MAX_DESC_LEN].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    keywords_rdf = ""
    for kw in keywords_list[:MAX_KEYWORD_COUNT]:
        safe_kw = kw.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        keywords_rdf += f"<rdf:li>{safe_kw}</rdf:li>"
    
    xmp_template = f'''<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 5.6-c140">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:dc="http://purl.org/dc/elements/1.1/">
   <dc:title>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">{title}</rdf:li>
    </rdf:Alt>
   </dc:title>
   <dc:description>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">{description}</rdf:li>
    </rdf:Alt>
   </dc:description>
   <dc:subject>
    <rdf:Bag>
     {keywords_rdf}
    </rdf:Bag>
   </dc:subject>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>'''
    
    return xmp_template.encode('utf-8')


def inject_xmp_to_eps(eps_file, title, description, keywords_list):
    """Inject XMP metadata LANGSUNG ke file EPS (manipulasi teks PostScript)"""
    try:
        eps_content = eps_file.read().decode('utf-8', errors='ignore')
    except:
        eps_file.seek(0)
        eps_content = eps_file.read().decode('latin-1')
    
    xmp_packet = create_xmp_packet(title, description, keywords_list).decode('utf-8')
    xmp_comment = f"%%BeginClientData: xmp\n{xmp_packet}\n%%EndClientData\n"
    
    # Cek apakah sudah ada XMP
    if '%%BeginClientData: xmp' in eps_content:
        pattern = r'%%BeginClientData: xmp\n.*?\n%%EndClientData\n'
        eps_content = re.sub(pattern, xmp_comment, eps_content, flags=re.DOTALL)
    elif '%!PS-Adobe' in eps_content:
        eps_content = eps_content.replace('%!PS-Adobe', f'%!PS-Adobe\n{xmp_comment}', 1)
    else:
        eps_content = xmp_comment + eps_content
    
    return eps_content.encode('utf-8')


def generate_metadata_with_gemini(image_file, api_key, model_name, custom_prompt=None):
    """Generate metadata menggunakan Google Gemini API (vision)"""
    try:
        image_file.seek(0)
        img_bytes = image_file.read()
        image_file.seek(0)
        
        if len(img_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise Exception(f"File too large (max {MAX_FILE_SIZE_MB}MB)")
        
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        mime_type = 'image/jpeg'
        filename = getattr(image_file, 'filename', 'image.jpg')
        if filename.lower().endswith('.png'):
            mime_type = 'image/png'
        elif filename.lower().endswith('.webp'):
            mime_type = 'image/webp'
        
        if not custom_prompt:
            custom_prompt = """Analyze this image and generate metadata for microstock photography.

Return ONLY valid JSON in this exact format, no other text or markdown:

{
  "title": "Short descriptive title under 10 words, capitalize first letter of each word",
  "description": "Detailed description under 30 words explaining what's in the image",
  "keywords": "comma,separated,keywords,without,spaces,after,commas,use,10,to,30,keywords"
}

Guidelines:
- Title: Descriptive, SEO-friendly, max 10 words, capitalize each word
- Description: Explain what's in the image, max 30 words
- Keywords: Relevant terms, use singular form, no special characters except commas
- Focus on: main subjects, actions, colors, composition, style, use cases"""
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": custom_prompt},
                    {"inline_data": {"mime_type": mime_type, "data": img_base64}}
                ]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 500,
                "topP": 0.95
            }
        }
        
        headers = {"Content-Type": "application/json"}
        
        logger.info(f"Calling Gemini API with model: {model_name}")
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        if response.status_code != 200:
            try:
                error_json = response.json()
                error_msg = error_json.get('error', {}).get('message', response.text)
            except:
                error_msg = response.text
            raise Exception(f"Gemini API error: {error_msg}")
        
        result = response.json()
        
        try:
            generated_text = result['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError) as e:
            raise Exception(f"Invalid Gemini response: {str(e)}")
        
        # Clean response
        generated_text = generated_text.strip()
        generated_text = re.sub(r'```json\s*', '', generated_text)
        generated_text = re.sub(r'```\s*', '', generated_text)
        
        # Extract JSON
        json_match = re.search(r'\{[^{}]*"title"[^{}]*"description"[^{}]*"keywords"[^{}]*\}', generated_text, re.DOTALL)
        if json_match:
            generated_text = json_match.group(0)
        
        try:
            metadata = json.loads(generated_text)
        except json.JSONDecodeError:
            metadata = extract_metadata_from_text(generated_text)
        
        title = metadata.get('title', '')[:MAX_TITLE_LEN]
        description = metadata.get('description', '')[:MAX_DESC_LEN]
        keywords = metadata.get('keywords', '')
        
        if keywords:
            keywords = keywords.replace(', ', ',').replace(' ,', ',')
            keywords = re.sub(r'[^\w\.,\-]', '', keywords)
        else:
            keywords = "image,photography,stock,digital,creative"
        
        return {
            "title": title or "Untitled Image",
            "description": description or "Professional stock photography",
            "keywords": keywords
        }
        
    except requests.exceptions.Timeout:
        raise Exception("Gemini API timeout (took >60 seconds). Please try again.")
    except requests.exceptions.ConnectionError:
        raise Exception("Network error connecting to Gemini API")
    except Exception as e:
        logger.error(f"Gemini error: {traceback.format_exc()}")
        raise Exception(f"Gemini error: {str(e)}")


def extract_metadata_from_text(text):
    """Fallback: extract metadata dari plain text response"""
    title_match = re.search(r'(?:title|Title)[:\s]+["\']?([^"\'\n]+)', text)
    desc_match = re.search(r'(?:description|Description)[:\s]+["\']?([^"\'\n]+)', text)
    kw_match = re.search(r'(?:keywords|Keywords|tags|Tags)[:\s]+["\']?([^"\'\n]+)', text)
    
    title = title_match.group(1).strip() if title_match else "Generated Image"
    description = desc_match.group(1).strip() if desc_match else "Professional stock photography"
    keywords = kw_match.group(1).strip() if kw_match else "image,photography,stock,digital,creative"
    
    keywords = keywords.replace(', ', ',').replace(' ,', ',')
    keywords = re.sub(r'[^\w\.,\-]', '', keywords)[:500]
    
    return {
        "title": title[:MAX_TITLE_LEN],
        "description": description[:MAX_DESC_LEN],
        "keywords": keywords
    }


# ============ FLASK ROUTES ============

@app.route('/')
def index():
    """Halaman utama"""
    return render_template('index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'app': 'Mob Stocker Metadata', 'version': '1.0.0'})


@app.route('/api/generate-metadata', methods=['POST'])
def generate_metadata():
    """Generate metadata dari gambar menggunakan Google Gemini API"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        api_key = request.form.get('api_key', '').strip()
        model_name = request.form.get('model_name', 'gemini-2.0-flash-lite')
        custom_prompt = request.form.get('custom_prompt', '')
        
        if not api_key:
            return jsonify({'error': 'Gemini API key is required. Get it free from https://aistudio.google.com/'}), 400
        
        allowed_extensions = ('.jpg', '.jpeg', '.png', '.webp')
        if not file.filename.lower().endswith(allowed_extensions):
            return jsonify({'error': 'AI analysis only supports JPG, PNG, or WebP images'}), 400
        
        metadata = generate_metadata_with_gemini(file, api_key, model_name, custom_prompt)
        return jsonify(metadata)
        
    except Exception as e:
        logger.error(f"Generate metadata error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/process-preview', methods=['POST'])
def process_preview():
    """Generate preview thumbnail untuk file JPG/PNG"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        files = request.files.getlist('files')
        preview_data = []
        
        for file in files:
            if not file or file.filename == '':
                continue
                
            if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
            
            try:
                file.seek(0)
                img = Image.open(file)
                
                # Handle transparency
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize thumbnail
                img.thumbnail((80, 80))
                
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=70)
                img_base64 = base64.b64encode(buffered.getvalue()).decode()
                
                preview_data.append({
                    'filename': file.filename,
                    'preview_src': f"data:image/jpeg;base64,{img_base64}"
                })
            except Exception as e:
                logger.warning(f"Preview error for {file.filename}: {e}")
                continue
        
        return jsonify({'previews': preview_data})
        
    except Exception as e:
        logger.error(f"Preview error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/inject-jpg', methods=['POST'])
def inject_jpg():
    """Inject XMP metadata ke file JPG/PNG"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Missing file'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        keywords_raw = request.form.get('keywords', '').strip()
        
        if not title or not description or not keywords_raw:
            return jsonify({'error': 'Title, description, and keywords are required'}), 400
        
        keywords_list = clean_microstock_keywords(keywords_raw)
        
        if not keywords_list:
            return jsonify({'error': 'At least one valid keyword is required (min 2 chars, max 50)'}), 400
        
        file.seek(0)
        img = Image.open(file)
        
        # Handle transparency
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        xmp_packet = create_xmp_packet(title, description, keywords_list)
        output_buffer = io.BytesIO()
        img.save(output_buffer, format="JPEG", quality=95, xmp=xmp_packet)
        output_buffer.seek(0)
        
        # Sanitize filename
        safe_filename = re.sub(r'[^\w\-.]', '_', file.filename)
        
        return send_file(
            output_buffer,
            mimetype='image/jpeg',
            as_attachment=True,
            download_name=f"mobstock_{safe_filename}"
        )
        
    except Exception as e:
        logger.error(f"Inject JPG error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/inject-eps', methods=['POST'])
def inject_eps():
    """Inject XMP metadata LANGSUNG ke file EPS (manipulasi teks)"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Missing file'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        if not file.filename.lower().endswith('.eps'):
            return jsonify({'error': 'File must be EPS format'}), 400
        
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        keywords_raw = request.form.get('keywords', '').strip()
        
        if not title or not description or not keywords_raw:
            return jsonify({'error': 'Title, description, and keywords are required'}), 400
        
        keywords_list = clean_microstock_keywords(keywords_raw)
        
        if not keywords_list:
            return jsonify({'error': 'At least one valid keyword is required'}), 400
        
        file.seek(0)
        eps_with_metadata = inject_xmp_to_eps(file, title, description, keywords_list)
        
        output = io.BytesIO(eps_with_metadata)
        output.seek(0)
        
        # Sanitize filename
        safe_filename = re.sub(r'[^\w\-.]', '_', file.filename)
        
        return send_file(
            output,
            mimetype='application/postscript',
            as_attachment=True,
            download_name=f"mobstock_{safe_filename}"
        )
        
    except Exception as e:
        logger.error(f"Inject EPS error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


# ============ RUN SERVER ============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
