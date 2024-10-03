import os
import streamlit as st
import requests
from langchain_core.messages import AIMessage, HumanMessage
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

openai_client = OpenAI(api_key=OPENAI_API_KEY)


st.title("User Chat Platform")

# Hide the Streamlit menu and footer using custom CSS
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

def get_response(user_query):
    # Make the request to the server with the user's query
    response = requests.post('http://localhost:5000/query', json={"query": user_query})
    if response.status_code == 200:
        relevant_doc_content = response.json().get('response', "No answer from server.")
    else:
        relevant_doc_content = "No relevant information found"        
    
    template = f"""
    You are a helpful assistant. Answer the user's question based strictly on the relevant information retrieved from the database. 

    {f"Relevant Document Information: {relevant_doc_content}" if relevant_doc_content else "No relevant document information was found for this query."}

    User question: {user_query}

    Instructions:
    - If relevant document information is provided, use it to answer the user's question.
    - If no relevant document information is available, respond by stating that there is no relevant information to answer the question at the moment.
    - Do not provide any speculative or hallucinated information. Stick strictly to the available data.
    """
    
    return openai_client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=[
            {"role": "user", "content": template}
        ],
        max_tokens=500,
        stream=True
    )


# Manage login state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    
# Logout button if user is logged in
if st.session_state.logged_in:
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.chat_history = []
        st.rerun()  # Rerun the app to show the login form again

# If the user is not logged in, show the login/registration form
if not st.session_state.logged_in:
    st.subheader("Login or Register")
    choice = st.radio("Login or Signup", ['Login', 'Signup'])

    # Username and password input fields
    username = st.text_input("Username")
    password = st.text_input("Password", type='password')

    # Registration logic
    if choice == 'Signup':
        if st.button("Register"):
            if username and password:
                response = requests.post('http://localhost:5000/register', json={"username": username, "password": password})
                if response.status_code == 201:
                    st.success("Registration successful! Please login.")
                elif response.status_code == 400:
                    st.error(response.json().get("error"))
                else:
                    st.error("Error registering the user")
            else:
                st.error("Please provide a username and password")

    # Login logic
    if choice == 'Login':
        if st.button("Login"):
            if username and password:
                response = requests.post('http://localhost:5000/login', json={"username": username, "password": password})
                if response.status_code == 200:
                    st.session_state.logged_in = True
                    st.success("Login successful!")
                    st.rerun() 
                else:
                    st.error("Invalid credentials")
            else:
                st.error("Please provide a username and password")

# If the user is logged in, show the chat interface
if st.session_state.logged_in:
    st.subheader("Query the Documents (Chat Interface)")

    # Set up chat history in session state if not already
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [AIMessage(content="Hello, how can I help you?")]

    # Display conversation history
    for message in st.session_state.chat_history:
        with st.chat_message("AI" if isinstance(message, AIMessage) else "Human"):
            st.write(message.content)

    # Handle user input for new queries
    user_query = st.chat_input("Type your message here...")
    
    if user_query is not None and user_query != "":
        # Append the user query to chat history
        st.session_state.chat_history.append(HumanMessage(content=user_query))
        
        with st.chat_message("Human"):
            st.markdown(user_query)
        
        # Make the request to the server with the user's query
        # response = requests.post('http://localhost:5000/query', json={"query": user_query})
        
        # if response.status_code == 200:
        #     response_text = response.json().get('answer', "No answer from server.")
        # else:
        #     response_text = "Error querying the documents."
        
        # # Append the AI's response to chat history
        # st.session_state.chat_history.append(AIMessage(content=response_text))
        
        # # Display the AI's response
        # with st.chat_message("AI"):
        #     st.write(response_text)

        with st.chat_message("AI"):
            response = st.write_stream(get_response(user_query))

        st.session_state.chat_history.append(AIMessage(content=response))