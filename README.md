# 🤖 PDF Chatbot – AI-Powered Document Assistant

**PDF Chatbot** is a smart web application that allows users to **upload any PDF** and **chat with it** using natural language. It uses the **Mistral AI API** to understand and answer your queries based on the document’s content.

---

## 🔗 Live Demo

🌐 [View Live](https://pdf-chatbot-663p.onrender.com/)  

DEMO : 
 ![image](https://github.com/user-attachments/assets/bf120ccf-0753-4c4a-9085-3ee6d665d4cf)
 ![image](https://github.com/user-attachments/assets/6a2294d2-e0a6-49da-bb75-b228045859e0)
![image](https://github.com/user-attachments/assets/75daf5eb-86e5-4266-a787-f5b81a62017f)


https://github.com/user-attachments/assets/ce42ea19-eaf8-4b08-bbbf-11715c7e7e8e






---

## ✨ Features

- 🔐 **Google OAuth 2.0 Login** – Secure and seamless authentication
- 📄 **PDF Upload & Parsing** – Fast extraction of document content
- 💬 **Chat Interface** – Ask anything about your uploaded PDF
- 🤖 **Mistral AI Integration** – Context-aware, AI-generated answers
- 📱 **Responsive Design** – Works great on both desktop and mobile
- ☁️ **Deployable on Render** – One-click cloud deployment

---

## 🛠 Tech Stack

- **Backend:** Flask, Gunicorn  
- **Frontend:** HTML5, CSS3, JavaScript  
- **PDF Parsing:** PyMuPDF  
- **Authentication:** Flask-Login, Authlib (Google OAuth)  
- **AI Engine:** Mistral AI API  
- **Deployment:** Render

---

## 🚀 Getting Started

### 📦 Prerequisites

- Python 3.8 or higher  
- pip (Python package installer)  
- A Google Cloud project with OAuth 2.0 credentials  
- A Mistral AI API Key

---

## 🔧 Installation & Setup

### 1. Clone the repository


git clone https://github.com/your-username/pdf_chatbot.git
cd pdf_chatbot 


2. Create a virtual environment
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
.\venv\Scripts\activate

3. Install Dependency 
pip install -r requirements.txt

4.  Set up environment variables
SECRET_KEY=your_secret_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
MISTRAL_API_KEY=your_mistral_api_key



▶️ Running the Application

flask run

Access the app at: http://localhost:5000


☁️ Deployment on Render
Step-by-Step:
Push your code to a GitHub repository

Go to Render and create a New Web Service

Connect your GitHub repo

Render will detect the render.yaml and auto-configure settings


🔌 API Endpoints
Endpoint	Method	Description
/	GET	Loads the main page
/login	GET	Starts Google OAuth login
/authorize	GET	Callback route for Google OAuth
/logout	GET	Logs out the current user
/user	GET	Returns authenticated user's profile info
/api/upload	POST	Uploads a PDF (requires authentication)
/api/query	POST	Sends user’s question and returns AI response



🙌 Feedback & Contributions
Have feedback or want to contribute?
Feel free to fork the repo, raise issues, or submit a pull request.

