#pip install google-genai

import streamlit as st, os, time
from google import genai
from google.genai import types
from pypdf import PdfReader, PdfWriter


def setup_page():
    st.set_page_config(
        page_title="	⚡ Voice Chatbot",
        layout="centered"
    )
    
    st.header("Chatbot using Gemini 3.5 Flash!" )

    st.sidebar.header("Options", divider='rainbow')
    
    hide_menu_style = """
            <style>
            #MainMenu {visibility: hidden;}
            </style>
            """
    st.markdown(hide_menu_style, unsafe_allow_html=True)

    
def show_usage(usage_metadata):
    if not usage_metadata:
        return
    st.sidebar.markdown("**Token usage**")
    st.sidebar.markdown(f"- Prompt: {usage_metadata.prompt_token_count}")
    if usage_metadata.thoughts_token_count:
        st.sidebar.markdown(f"- Thinking: {usage_metadata.thoughts_token_count}")
    st.sidebar.markdown(f"- Response: {usage_metadata.candidates_token_count}")
    st.sidebar.markdown(f"- **Total: {usage_metadata.total_token_count}**")


def render_history(history_key):
    """Redraw every past message in this session so history survives Streamlit reruns."""
    for msg in st.session_state[history_key]:
        avatar = "🧞‍♀️" if msg["role"] == "model" else None
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["text"])


def ask_and_respond(chat, history_key, prompt):
    """Send one new prompt to an existing chat, show it, and append both turns to history."""
    st.session_state[history_key].append({"role": "user", "text": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("model", avatar="🧞‍♀️"):
        response = chat.send_message(prompt)
        st.markdown(response.text)
        st.sidebar.markdown("---")
        show_usage(response.usage_metadata)

    st.session_state[history_key].append({"role": "model", "text": response.text})


def get_choice():
    choice = st.sidebar.radio("Choose:", ["Converse with Gemini 2.0",
                                          "Chat with a PDF",
                                          "Chat with many PDFs",
                                          "Chat with an image",
                                          "Chat with audio",
                                          "Chat with video"],)
    return choice

 
def get_clear():
    clear_button=st.sidebar.button("Start new session", key="clear")
    return clear_button


def clear_session_keys(*keys):
    for key in keys:
        st.session_state.pop(key, None)

     
def main():
    choice = get_choice()
    
    if choice == "Converse with Gemini 2.0":
        st.subheader("Ask Gemini")
        clear = get_clear()
        if clear:
            clear_session_keys('history_converse', 'chat_converse')

        if 'history_converse' not in st.session_state:
            st.session_state.history_converse = []

        if 'chat_converse' not in st.session_state:
            st.session_state.chat_converse = client.chats.create(
                model=MODEL_ID,
                config=types.GenerateContentConfig(
                    system_instruction="You are a helpful assistant. Your answers need to brief and concise.",
                ),
            )

        render_history('history_converse')

        prompt = st.chat_input("Enter your question here")
        if prompt:
            ask_and_respond(st.session_state.chat_converse, 'history_converse', prompt)

    elif choice == "Chat with a PDF":
        st.subheader("Chat with your PDF file")
        clear = get_clear()
        if clear:
            clear_session_keys('history_pdf', 'chat_pdf', 'pdf_file_name')

        if 'history_pdf' not in st.session_state:
            st.session_state.history_pdf = []

        uploaded_file = st.file_uploader("Choose your pdf file", type=['pdf'], accept_multiple_files=False)

        if uploaded_file:
            # Only (re)upload and start a fresh chat when a genuinely new file is chosen —
            # not on every rerun, which was wiping the conversation on each question.
            if st.session_state.get('pdf_file_name') != uploaded_file.name:
                file_upload = client.files.upload(file=uploaded_file.name)
                st.session_state.chat_pdf = client.chats.create(
                    model=MODEL_ID,
                    history=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_uri(
                                    file_uri=file_upload.uri,
                                    mime_type=file_upload.mime_type),
                            ]
                        ),
                    ]
                )
                st.session_state.pdf_file_name = uploaded_file.name
                st.session_state.history_pdf = []

            render_history('history_pdf')

            prompt2 = st.chat_input("Enter your question here")
            if prompt2:
                ask_and_respond(st.session_state.chat_pdf, 'history_pdf', prompt2)

    elif choice == "Chat with many PDFs":
        st.subheader("Chat with your PDF file")
        clear = get_clear()
        if clear:
            clear_session_keys('history_pdfs', 'chat_pdfs', 'pdfs_file_names')

        if 'history_pdfs' not in st.session_state:
            st.session_state.history_pdfs = []

        uploaded_files2 = st.file_uploader("Choose 1 or more files",  type=['pdf'], accept_multiple_files=True)

        if uploaded_files2:
            current_names = tuple(f.name for f in uploaded_files2)
            if st.session_state.get('pdfs_file_names') != current_names:
                writer = PdfWriter()
                for file in uploaded_files2:
                    writer.append(file)

                fullfile = "merged_all_files.pdf"
                with open(fullfile, "wb") as f:
                    writer.write(f)
                writer.close()

                file_upload = client.files.upload(file=fullfile)
                st.session_state.chat_pdfs = client.chats.create(
                    model=MODEL_ID,
                    history=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_uri(
                                    file_uri=file_upload.uri,
                                    mime_type=file_upload.mime_type),
                            ]
                        ),
                    ]
                )
                st.session_state.pdfs_file_names = current_names
                st.session_state.history_pdfs = []

            render_history('history_pdfs')

            prompt2b = st.chat_input("Enter your question here")
            if prompt2b:
                ask_and_respond(st.session_state.chat_pdfs, 'history_pdfs', prompt2b)

    elif choice == "Chat with an image":
        st.subheader("Chat with your image file")
        clear = get_clear()
        if clear:
            clear_session_keys('history_image', 'chat_image', 'image_file_name')

        if 'history_image' not in st.session_state:
            st.session_state.history_image = []

        uploaded_image = st.file_uploader("Choose your PNG or JPEG file",  type=['png','jpg'], accept_multiple_files=False)

        if uploaded_image:
            if st.session_state.get('image_file_name') != uploaded_image.name:
                file_upload = client.files.upload(file=uploaded_image.name)
                st.session_state.chat_image = client.chats.create(
                    model=MODEL_ID,
                    history=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_uri(
                                    file_uri=file_upload.uri,
                                    mime_type=file_upload.mime_type),
                            ]
                        ),
                    ]
                )
                st.session_state.image_file_name = uploaded_image.name
                st.session_state.history_image = []

            render_history('history_image')

            prompt3 = st.chat_input("Enter your question here")
            if prompt3:
                ask_and_respond(st.session_state.chat_image, 'history_image', prompt3)

    elif choice == "Chat with audio":
        st.subheader("Chat with your audio file")
        clear = get_clear()
        if clear:
            clear_session_keys('history_audio', 'chat_audio', 'audio_file_name')

        if 'history_audio' not in st.session_state:
            st.session_state.history_audio = []

        uploaded_audio = st.file_uploader("Choose your mp3 or wav file",  type=['mp3','wav'], accept_multiple_files=False)

        if uploaded_audio:
            if st.session_state.get('audio_file_name') != uploaded_audio.name:
                file_upload = client.files.upload(file=uploaded_audio.name)
                st.session_state.chat_audio = client.chats.create(
                    model=MODEL_ID,
                    history=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_uri(
                                    file_uri=file_upload.uri,
                                    mime_type=file_upload.mime_type),
                            ]
                        ),
                    ]
                )
                st.session_state.audio_file_name = uploaded_audio.name
                st.session_state.history_audio = []

            render_history('history_audio')

            prompt5 = st.chat_input("Enter your question here")
            if prompt5:
                ask_and_respond(st.session_state.chat_audio, 'history_audio', prompt5)

    elif choice == "Chat with video":
        st.subheader("Chat with your video file")
        clear = get_clear()
        if clear:
            clear_session_keys('history_video', 'chat_video', 'video_file_name')

        if 'history_video' not in st.session_state:
            st.session_state.history_video = []

        uploaded_video = st.file_uploader("Choose your mp4 or mov file",  type=['mp4','mov'], accept_multiple_files=False)

        if uploaded_video:
            if st.session_state.get('video_file_name') != uploaded_video.name:
                video_file = client.files.upload(file=uploaded_video.name)
                while video_file.state == "PROCESSING":
                    time.sleep(10)
                    video_file = client.files.get(name=video_file.name)

                if video_file.state == "FAILED":
                    raise ValueError(video_file.state)

                st.session_state.chat_video = client.chats.create(
                    model=MODEL_ID,
                    history=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_uri(
                                    file_uri=video_file.uri,
                                    mime_type=video_file.mime_type),
                            ]
                        ),
                    ]
                )
                st.session_state.video_file_name = uploaded_video.name
                st.session_state.history_video = []

            render_history('history_video')

            prompt4 = st.chat_input("Enter your question here")
            if prompt4:
                ask_and_respond(st.session_state.chat_video, 'history_video', prompt4)


if __name__ == '__main__':
    setup_page()
    api_key = os.environ.get('GOOGLE_API_KEY_NEW')

    if not api_key:
        st.error(
            "GOOGLE_API_KEY_NEW belum diset. "
            "Buka Manage app → Settings → Secrets di Streamlit Cloud, lalu tambahkan:\n\n"
            'GOOGLE_API_KEY_NEW = "your-api-key-here"'
        )
        st.stop()

    if 'genai_client' not in st.session_state:
        st.session_state.genai_client = genai.Client(api_key=api_key)
    client = st.session_state.genai_client

    MODEL_ID = "gemini-3.5-flash"
    main()
