from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import requests
import base64
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable cross-origin requests

# ========== CONFIGURATION ==========
MISTRAL_API_KEY = "F19TFQQ8UD4XRCXDcxFcL1pXHv8j1HA7"
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

# ========== FUNCTIONS ==========
def extract_text_from_pdf(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text, len(doc)

def query_mistral(prompt):
    payload = {
        "model": "mistral-medium",  # or mistral-small / mistral-large
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post(MISTRAL_API_URL, headers=HEADERS, json=payload)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"❌ Error: {response.status_code} - {response.text}"

# ========== API ENDPOINTS ==========
@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and file.filename.endswith('.pdf'):
        pdf_bytes = file.read()
        try:
            text, page_count = extract_text_from_pdf(pdf_bytes)
            return jsonify({
                'success': True,
                'filename': file.filename,
                'page_count': page_count,
                'text': text[:2000],  # Preview text
                'full_text': text,    # Full text for future queries
                'char_count': len(text)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Only PDF files are allowed'}), 400

@app.route('/api/query', methods=['POST'])
def query_pdf():
    data = request.json
    if not data or 'pdf_text' not in data or 'question' not in data:
        return jsonify({'error': 'Missing required data'}), 400
    
    pdf_text = data['pdf_text']
    question = data['question']
    
    try:
        context = f"The following text is extracted from a PDF document:\n\n{pdf_text[:5000]}\n\nAnswer this question based on the PDF content:\n{question}"
        answer = query_mistral(context)
        return jsonify({
            'success': True,
            'answer': answer
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Serve static files
@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)