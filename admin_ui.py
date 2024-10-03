# app/admin_ui.py

import streamlit as st
import requests

st.title("Admin Panel - Upload Documents")

# Upload document section
st.subheader("Upload a Document")
uploaded_file = st.file_uploader("Choose a file")
if uploaded_file is not None:
    if st.button("Upload"):
        files = {'file': (uploaded_file.name,uploaded_file.getvalue())}
        response = requests.post('http://localhost:5000/upload', files=files)
        if response.status_code == 200:
            st.success("File uploaded successfully!")
        else:
            st.error("Error uploading file!")

# View uploaded documents section
st.subheader("Uploaded Documents")
response = requests.get('http://localhost:5000/documents')
if response.status_code == 200:
    documents = response.json()
    for doc in documents:
        st.write(f"Document ID: {doc['id']}, Filename: {doc['filename']}")
else:
    st.error("Error fetching documents!")
