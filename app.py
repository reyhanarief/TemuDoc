from flask import Flask, request, render_template, redirect, url_for
import os
import pandas as pd
import re
from collections import Counter
from werkzeug.utils import secure_filename
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'secretkey'

def read_txt_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def read_docx_file(filepath):
    from docx import Document
    doc = Document(filepath)
    return '\n'.join([p.text for p in doc.paragraphs])

def read_pdf_file(filepath):
    import pdfplumber
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + '\n'
    return text

def case_folding(text):
    return text.lower()

def tokenize(text):
    return re.findall(r'\b\w+\b', text)

def filtering(words, stopwords):
    return [word for word in words if word not in stopwords]

def stemming(words):
    stemmer = StemmerFactory().create_stemmer()
    return [stemmer.stem(word) for word in words]

def format_stemmed_content(stemmed_words):
    word_counts = Counter(stemmed_words)
    formatted_content = []
    for word, count in word_counts.items():
        if count > 1:
            formatted_content.append(f"{word} ({count}x)")
        else:
            formatted_content.append(word)
    return ', '.join(formatted_content)

def clear_uploaded_files():
    folder = app.config['UPLOAD_FOLDER']
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        clear_uploaded_files()
        if 'documents' not in request.files:
            return "No file uploaded"

        files = request.files.getlist('documents')
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        for file in files:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        return redirect(url_for('process_documents'))

    return render_template('index.html')

@app.route('/process', methods=['GET'])
def process_documents():
    stopwords_path = os.path.join('stopwords.csv')
    stopwords = pd.read_csv(stopwords_path, header=None)[0].tolist()

    filepaths = [os.path.join(app.config['UPLOAD_FOLDER'], f) for f in os.listdir(app.config['UPLOAD_FOLDER'])]
    corpus = []
    filenames = []
    uploaded_files = []

    for filepath in filepaths:
        ext = os.path.splitext(filepath)[1]
        if ext == '.txt':
            text = read_txt_file(filepath)
        elif ext == '.docx':
            text = read_docx_file(filepath)
        elif ext == '.pdf':
            text = read_pdf_file(filepath)
        else:
            continue

        filenames.append(os.path.basename(filepath))
        lowered = case_folding(text)
        tokens = tokenize(lowered)
        filtered = filtering(tokens, stopwords)
        stemmed = stemming(filtered)
        corpus.append(' '.join(stemmed))
        stemmed_content = format_stemmed_content(stemmed)
        print(stemmed_content)

        uploaded_files.append({
            'filename': os.path.basename(filepath),
            'stemmed_word_count': len(stemmed),
            'stemmed_content': stemmed_content
        })

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(corpus)

    return render_template('results.html', filenames=filenames, corpus=corpus, uploaded_files=uploaded_files)

@app.route('/search', methods=['POST'])
def search():
    query = request.form['query']
    stopwords_path = os.path.join('stopwords.csv')
    stopwords = pd.read_csv(stopwords_path, header=None)[0].tolist()

    filepaths = [os.path.join(app.config['UPLOAD_FOLDER'], f) for f in os.listdir(app.config['UPLOAD_FOLDER'])]
    corpus = []
    filenames = []
    uploaded_files = []

    for filepath in filepaths:
        ext = os.path.splitext(filepath)[1]
        if ext == '.txt':
            text = read_txt_file(filepath)
        elif ext == '.docx':
            text = read_docx_file(filepath)
        elif ext == '.pdf':
            text = read_pdf_file(filepath)
        else:
            continue

        filenames.append(os.path.basename(filepath))
        lowered = case_folding(text)
        tokens = tokenize(lowered)
        filtered = filtering(tokens, stopwords)
        stemmed = stemming(filtered)
        corpus.append(' '.join(stemmed))
        stemmed_content = format_stemmed_content(stemmed)
        print(stemmed_content)

        uploaded_files.append({
            'filename': os.path.basename(filepath),
            'stemmed_word_count': len(stemmed),
            'stemmed_content': stemmed_content
        })

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(corpus)

    lowered_query = case_folding(query)
    query_tokens = tokenize(lowered_query)
    filtered_query = filtering(query_tokens, stopwords)
    stemmed_query = ' '.join(stemming(filtered_query))
    query_vector = vectorizer.transform([stemmed_query])

    similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
    results = zip(filenames, similarities)
    results = sorted(results, key=lambda x: x[1], reverse=True)

    return render_template('results.html', query=query, results=results, uploaded_files=uploaded_files)

if __name__ == '__main__':
    app.run(debug=True)