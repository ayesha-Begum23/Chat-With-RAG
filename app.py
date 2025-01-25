import streamlit as st
import os
import pinecone
import fitz  # PyMuPDF
from dotenv import load_dotenv
from groq import Groq
import numpy as np
import time

# Load environment variables
load_dotenv()

# Initialize Pinecone client
pc = pinecone.Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index_name = "qa-chat-index"

# Create the index if it does not exist
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=1536,  # Ensure this matches your embedding dimension
        metric="cosine",
        spec=pinecone.ServerlessSpec(
            cloud='aws',
            region='us-east-1'
        )
    )

index = pc.Index(index_name)

# Initialize Groq client
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Function to simulate encoding query to vector
def vectorize_query(query):
    return np.random.rand(1536).tolist()  # Replace with actual vectorization logic

# Function to fetch relevant documents from Pinecone
def fetch_relevant_docs(query, top_n=5):
    query_vector = vectorize_query(query)
    results = index.query(
        vector=query_vector,
        top_k=top_n,
        include_values=True,
        include_metadata=True
    )
    docs = [match['metadata']['text'] for match in results['matches']]
    return docs

# Function to get responses from Groq
def generate_response(prompt):
    try:
        documents = fetch_relevant_docs(prompt)
        enriched_prompt = prompt + "\n\n" + "\n".join(documents)
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": enriched_prompt}],
            model="llama3-8b-8192"  # Use appropriate model
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# Streamlit UI
st.set_page_config(page_title="Conversational Q&A Bot", page_icon=":robot_face:")

# Add custom CSS for dynamic styling
st.markdown("""
    <style>
    body {
        background: #F0F0F0;
        color: #333;
        font-family: Arial, sans-serif;
    }
    .chat-box {
        max-height: 500px;
        overflow-y: auto;
        border: 1px solid #D0D0D0;
        border-radius: 8px;
        padding: 10px;
        background-color: #FFFFFF;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    .user-msg, .assistant-msg {
        padding: 10px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .user-msg {
        background-color: #007BFF;
        color: #FFFFFF;
    }
    .assistant-msg {
        background-color: #F8F9FA;
        color: #333;
        border: 1px solid #D0D0D0;
    }
    .loading-spinner {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid #007BFF;
        border-top-color: transparent;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    .button {
        background-color: #007BFF;
        color: white;
        border: none;
        padding: 10px 20px;
        font-size: 14px;
        border-radius: 5px;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    .button:hover {
        background-color: #0056b3;
    }
    </style>
""", unsafe_allow_html=True)

st.sidebar.title("Chatbot Settings")
st.sidebar.subheader("Upload Document")
uploaded_file = st.sidebar.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file is not None:
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as pdf_doc:
        text_content = ""
        for page in pdf_doc:
            text_content += page.get_text()
    st.sidebar.subheader("Document Content")
    st.sidebar.write(text_content)

# Display chat history
if "history" not in st.session_state:
    st.session_state["history"] = []

st.header("Chat with the Assistant")

# Display chat messages
chat_area = st.empty()
with chat_area.container():
    if st.session_state["history"]:
        for msg in st.session_state["history"]:
            if msg["role"] == "user":
                st.markdown(f'<div class="user-msg">{msg["content"]}</div>', unsafe_allow_html=True)
            elif msg["role"] == "assistant":
                st.markdown(f'<div class="assistant-msg">{msg["content"]}</div>', unsafe_allow_html=True)

# Input and submit form
input_col, button_col = st.columns([4, 1])
with input_col:
    user_input = st.text_input("Ask a question:", key="user_input")
with button_col:
    submit_btn = st.button("Send", key="send_button", help="Send your message")

# Loading indicator
loading_placeholder = st.empty()
if st.session_state.get("loading", False):
    with loading_placeholder:
        st.markdown('<div class="loading-spinner"></div>', unsafe_allow_html=True)
        time.sleep(2)
        loading_placeholder.empty()

# Handle user input
if submit_btn:
    if user_input:
        st.session_state["history"].append({"role": "user", "content": user_input})
        st.session_state["loading"] = True
        
        # Prepare query with optional document content
        query = user_input
        if 'text_content' in locals():
            query += f"\nDocument context: {text_content}"
        
        # Get the response from Groq API
        response_text = generate_response(query)
        
        # Update chat history
        st.session_state["history"].append({"role": "assistant", "content": response_text})
        
        # Reset loading state
        st.session_state["loading"] = False
        st.rerun()  # Use the updated method for rerunning
    else:
        st.warning("Please enter a message.")
