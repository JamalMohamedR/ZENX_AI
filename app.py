from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import PyPDF2  # for PDF files
import docx  # for Word documents

app = Flask(__name__)

# Configure Gemini API
load_dotenv()
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
model = genai.GenerativeModel("gemini-1.5-flash")

# Store chat history
chat_history = []

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Store document content
document_content = ""

def read_file_content(file_path):
    """Read content from different file types"""
    content = ""
    file_extension = file_path.split('.')[-1].lower()
    
    try:
        if file_extension == 'txt':
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
        elif file_extension == 'pdf':
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
                    
        elif file_extension in ['doc', 'docx']:
            doc = docx.Document(file_path)
            content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            
        return content
    except Exception as e:
        print(f"Error reading file: {str(e)}")
        return ""

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html", chat_history=chat_history)

@app.route('/upload_document', methods=['POST'])
def upload_document():
    global document_content
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file part'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Read the document content
            document_content = read_file_content(file_path)
            
            if document_content:
                return jsonify({
                    'success': True,
                    'message': 'File uploaded and processed successfully',
                    'filename': filename
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to read document content'
                }), 400
                
        else:
            return jsonify({
                'success': False,
                'error': f'Invalid file type. Allowed types are: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/send_message", methods=["POST"])
def send_message():
    global document_content
    user_message = request.form["message"]
    
    # Create context-aware prompt
    if document_content:
        prompt = f"""Context from uploaded document:
{document_content[:1000]}...

User question: {user_message}

Please answer the question based on the document content provided above."""
    else:
        prompt = user_message
    
    # Add user message to chat history
    chat_history.append({"role": "user", "content": user_message})
    
    # Get AI response with context
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            candidate_count=1,
            max_output_tokens=1000,
            temperature=0.7,
        ),
    )
    
    # Add AI response to chat history
    chat_history.append({"role": "assistant", "content": response.text})
    
    return jsonify({"response": response.text})

if __name__ == "__main__":
    app.run(debug=True)