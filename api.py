# app/api.py

import os
from openai import OpenAI
from pinecone.grpc import PineconeGRPC as Pinecone
import sqlite3
from flask import Flask, request, jsonify
import pymupdf
import docx
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)

# Initialize Pinecone for vector storage and search
# pinecone = Pinecone(api_key='c957c561-ee00-4050-ad69-a65e5661460c')
# index = pinecone.Index("document-index")

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai_client = OpenAI(api_key=OPENAI_API_KEY)

PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
PINECONE_INDEX_NAME = os.getenv('PINECONE_INDEX_NAME')

# Pinecone Client initialization
pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
pinecone_index = pinecone_client.Index(PINECONE_INDEX_NAME)

UPLOAD_FOLDER = './uploads'

# Initialize SQLite Database for user management and document tracking
def init_db():
    conn = sqlite3.connect('database.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, filename TEXT, metadata TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)''')
    conn.close()

def split_document_into_chunks(file_content):
    # Initialize the RecursiveTextSplitter with desired parameters
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,  # Maximum size of each chunk
        chunk_overlap=200,  # Overlap between chunks to maintain context
        length_function=len  # Function to calculate length of text
    )
    
    # Split the document content into chunks
    chunks = text_splitter.split_text(file_content)
    return chunks
# Function to store document embeddings in Pinecone
def store_embedding(text, filename):
    try:
        response = openai_client.embeddings.create(input=[text], model="text-embedding-3-large")
        embedding = response.data[0].embedding
        
        # Upsert the embedding along with metadata (filename and text)
        metadata = {
            "filename": filename,
            "text": text  
        }
        pinecone_index.upsert([(filename, embedding, metadata)])
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@app.route('/test', methods=['Get'])
def test():
    return jsonify({"message": "Login Successful"})

# Admin route for uploading documents
@app.route('/upload', methods=['POST'])
def upload_document():
    try:
        file = request.files['file']
        if file:
            
            file_content=""
            filename = file.filename
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            file_extension = filename.rsplit('.', 1)[1].lower()
            if file_extension == 'txt':
                file_content = file.read().decode('utf-8')
            elif file_extension == 'pdf':
                doc = pymupdf.open(file_path) 
                for page in doc: 
                    file_content += page.get_text("text")
            elif file_extension == 'docx':
                doc = docx.Document(file_path)
                file_content = '\n'.join([para.text for para in doc.paragraphs])
            else:
                return jsonify({"error": "Unsupported file type"}), 400
            
            # Chunking the document
            chunks = split_document_into_chunks(file_content)

            filename = file.filename
            # Store each chunk in Pinecone
            for i, chunk in enumerate(chunks):
                store_embedding(chunk, f"{filename}_{i}")
            
            # Store metadata in SQLite
            conn = sqlite3.connect('database.db')
            conn.execute("INSERT INTO documents (filename, metadata) VALUES (?, ?)", (filename, ""))
            conn.commit()
            conn.close()

            return jsonify({"message": "File uploaded and processed successfully!"})
        return jsonify({"error": "No file provided!"}), 400
    except Exception as e:
        return jsonify({f"error": {e}}), 500

# User route for querying documents
@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    user_query = data.get("query")

    # Get embeddings for the user query
    query_embedding = openai_client.embeddings.create(input=[user_query], model="text-embedding-3-large")

    # Perform search in Pinecone
    search_response = pinecone_index.query(
                        vector=query_embedding.data[0].embedding,
                        top_k=3,
                        include_values=True,
                        include_metadata=True
                    )
    # Get most relevant document from search results
    most_relevant_doc = search_response['matches'][0]['metadata']['text']

    return jsonify({"response": most_relevant_doc})

# User Registration endpoint
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    # Check if the user already exists
    conn = sqlite3.connect('database.db')
    cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if user:
        return jsonify({"error": "User already exists!"}), 400
    else:
        # Insert new user into the users table
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return jsonify({"message": "User registered successfully!"}), 201
    
# User login endpoint
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    

    conn = sqlite3.connect('database.db')
    
    cursor = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()

    if user:
        return jsonify({"message": "Login successful"}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

# Admin route to view uploaded documents
@app.route('/documents', methods=['GET'])
def get_documents():
    conn = sqlite3.connect('database.db')
    cursor = conn.execute("SELECT * FROM documents")
    documents = [{"id": row[0], "filename": row[1]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(documents)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
