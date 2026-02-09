import streamlit as st

file_path = 'storytelling-main/index.html'

with open(file_path, 'r') as file:
    file_content = file.read()

st.html(file_content, unsafe_allow_javascript=True)
