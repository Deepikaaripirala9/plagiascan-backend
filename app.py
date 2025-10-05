# backend.py
from flask import Flask, request, jsonify
from flask_cors import CORS

from werkzeug.utils import secure_filename
import PyPDF2
import docx
import itertools

app = Flask(__name__)
CORS(app)
CORS(app, origins=["https://plagia-checker.vercel.app/"])
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

def read_file_content(file_storage):
    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit('.',1)[1].lower()
    
    if ext == 'txt':
        return file_storage.read().decode('utf-8', errors='ignore')
    elif ext == 'pdf':
        reader = PyPDF2.PdfReader(file_storage)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    elif ext == 'docx':
        doc = docx.Document(file_storage)
        return "\n".join([p.text for p in doc.paragraphs])
    return ""

def compute_similarity(text1, text2):
    words1 = text1.lower().split()
    words2 = text2.lower().split()
    common = [w for w in words1 if w in words2]
    percentage = round(len(common)/max(len(words1), len(words2))*100) if words1 else 0
    
    # Find longest common phrase (2-5 words)
    longest_match = ''
    for i in range(len(words1)-1):
        for j in range(2, min(6, len(words1)-i+1)):
            phrase = ' '.join(words1[i:i+j])
            if phrase in text2.lower() and len(phrase) > len(longest_match):
                longest_match = phrase
    
    unique_ratio = round((len(words1)-len(common))/len(words1)*100) if words1 else 0
    return {"percentage": percentage, "longestMatch": longest_match, "uniqueRatio": unique_ratio}

@app.route('/api/analyze', methods=['POST'])
def analyze_text():
    data = request.get_json()
    text1 = data.get('documentA', '')
    text2 = data.get('documentB', '')
    return jsonify(compute_similarity(text1, text2))

@app.route('/api/upload-multiple', methods=['POST'])
def upload_multiple():
    files = request.files.getlist('files')
    if len(files) < 2:
        return jsonify({"error": "Select at least 2 files"}), 400

    # Read content of all uploaded files
    docs = []
    for f in files:
        if f and allowed_file(f.filename):
            content = read_file_content(f)
            docs.append({'name': secure_filename(f.filename), 'content': content})

    # Compare all unique file pairs
    results = []
    for doc1, doc2 in itertools.combinations(docs, 2):
        sim = compute_similarity(doc1['content'], doc2['content'])
        results.append({
            "doc1": doc1['name'],
            "doc2": doc2['name'],
            **sim
        })

    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
