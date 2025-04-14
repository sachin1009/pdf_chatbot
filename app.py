from flask import Flask, request, jsonify, redirect, url_for, session
import fitz  # PyMuPDF
import requests
import os
import json
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from datetime import timedelta
from flask_session import Session  # Import Session properly

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable cross-origin requests

# Secret key and session config
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key_change_in_production")
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(app.root_path, 'sessions')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Make sure the sessions directory exists
os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)

# Initialize session
Session(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize OAuth
oauth = OAuth(app)

# ========== Google OAuth Configuration ==========
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Only register Google OAuth if credentials are available
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    google = oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url=GOOGLE_DISCOVERY_URL,
        client_kwargs={'scope': 'openid email profile'}
    )
else:
    print("Warning: Google OAuth credentials not found in environment variables")

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
    users = session.get('users', {})
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
MISTRAL_API_KEY = os.environ.get("F19TFQQ8UD4XRCXDcxFcL1pXHv8j1HA7")
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

def get_mistral_headers():
    if not MISTRAL_API_KEY:
        raise ValueError("Mistral API key not found in environment variables")
    return {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

def chunk_text(text, chunk_size=3000, overlap=500):
    """Break text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Try to find a good breakpoint (e.g., at a period)
        if end < len(text):
            # Find the last period, newline, or space within the chunk
            for char in ['. ', '\n', ' ']:
                last_good_break = text.rfind(char, start, end)
                if last_good_break != -1 and last_good_break > start:
                    end = last_good_break + 1
                    break
        
        chunks.append(text[start:end])
        start = end - overlap  # Create overlap with previous chunk
        
    return chunks

def extract_text_from_pdf(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text, len(doc)

def query_mistral(prompt):
    try:
        payload = {
            "model": "mistral-medium",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        response = requests.post(MISTRAL_API_URL, headers=get_mistral_headers(), json=payload)
        response.raise_for_status()  # Raise exception for HTTP errors
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        return f"❌ Error connecting to Mistral API: {str(e)}"
    except KeyError as e:
        return f"❌ Error parsing Mistral API response: {str(e)}"
    except ValueError as e:
        return f"❌ Configuration error: {str(e)}"
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"

# ========== AUTHENTICATION ROUTES ==========
@app.route('/login')
def login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return jsonify({'error': 'Google OAuth not configured'}), 500
    
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/authorize')
def authorize():
    # Get authorization from Google
    token = google.authorize_access_token()
    resp = google.get('https://www.googleapis.com/oauth2/v3/userinfo')  # Updated URL
    user_info = resp.json()
    
    # Save user info to session
    if 'users' not in session:
        session['users'] = {}
    
    user_id = user_info['sub']
    session['users'][user_id] = {
        'name': user_info['name'],
        'email': user_info['email'],
        'profile_pic': user_info.get('picture', '')
    }
    
    # Create user and login
    user = User(
        id=user_id,
        name=user_info['name'],
        email=user_info['email'],
        profile_pic=user_info.get('picture', '')
    )
    login_user(user)
    
    # Redirect to home page
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
def upload_pdf():
    # Make this endpoint optionally require login
    # @login_required removed to allow testing without auth
    
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
                'full_text': text,
                'char_count': len(text)
            })
        except Exception as e:
            app.logger.error(f"PDF extraction error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Only PDF files are allowed'}), 400

@app.route('/api/query', methods=['POST'])
def query_pdf():
    # Make this endpoint optionally require login
    # @login_required removed to allow testing without auth
    
    data = request.json
    if not data or 'pdf_text' not in data or 'question' not in data:
        return jsonify({'error': 'Missing required data'}), 400

    pdf_text = data['pdf_text']
    question = data['question']

    try:
        # Chunk the text to handle long documents
        chunks = chunk_text(pdf_text)
        
        # For simple implementation, just use the first chunk
        # A more advanced approach would involve proper RAG implementation
        context = f"The following text is extracted from a PDF document:\n\n{chunks[0]}\n\nAnswer this question based on the PDF content:\n{question}"
        
        answer = query_mistral(context)
        return jsonify({
            'success': True,
            'answer': answer
        })
    except Exception as e:
        app.logger.error(f"Query error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 
                    'google_oauth': bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
                    'mistral_api': bool(MISTRAL_API_KEY)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)