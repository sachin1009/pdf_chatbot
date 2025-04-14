from flask import Flask, request, jsonify, redirect, url_for, session
import fitz  # PyMuPDF
import requests
import base64
import os
import json
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from datetime import timedelta

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable cross-origin requests

# Secret key and session config
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key_change_in_production")
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(app.root_path, 'sessions')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize OAuth
oauth = OAuth(app)

# ========== Google OAuth Configuration ==========
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "your_google_client_id")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "your_google_client_secret")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url=GOOGLE_DISCOVERY_URL,
    client_kwargs={'scope': 'openid email profile'}
)

# User model
class User(UserMixin):
    def __init__(self, id, name, email, profile_pic):
        self.id = id
        self.name = name
        self.email = email
        self.profile_pic = profile_pic

@login_manager.user_loader
def load_user(user_id):
    if 'users' not in session:
        return None
    users = session['users']
    if user_id in users:
        user_info = users[user_id]
        return User(
            id=user_id,
            name=user_info['name'],
            email=user_info['email'],
            profile_pic=user_info['profile_pic']
        )
    return None

# ========== MISTRAL API CONFIGURATION ==========
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "F19TFQQ8UD4XRCXDcxFcL1pXHv8j1HA7")
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

def extract_text_from_pdf(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text, len(doc)

def query_mistral(prompt):
    payload = {
        "model": "mistral-medium",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post(MISTRAL_API_URL, headers=HEADERS, json=payload)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"❌ Error: {response.status_code} - {response.text}"

# ========== AUTHENTICATION ROUTES ==========
@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    user_info = resp.json()

    if 'users' not in session:
        session['users'] = {}

    user_id = user_info['sub']
    session['users'][user_id] = {
        'name': user_info['name'],
        'email': user_info['email'],
        'profile_pic': user_info.get('picture', '')
    }

    user = User(
        id=user_id,
        name=user_info['name'],
        email=user_info['email'],
        profile_pic=user_info.get('picture', '')
    )
    login_user(user)
    return redirect('/')

@app.route('/logout')
def logout():
    logout_user()
    return redirect('/')

@app.route('/user')
def get_user():
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'name': current_user.name,
            'email': current_user.email,
            'profile_pic': current_user.profile_pic
        })
    else:
        return jsonify({'authenticated': False})

# ========== API ENDPOINTS ==========
@app.route('/api/upload', methods=['POST'])
@login_required
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
                'text': text[:2000],
                'full_text': text,
                'char_count': len(text)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Only PDF files are allowed'}), 400

@app.route('/api/query', methods=['POST'])
@login_required
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

@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
