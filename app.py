#pip install google-genai

import streamlit as st, os, time, io, wave
from google import genai
from google.genai import types
from pypdf import PdfReader, PdfWriter


VOICE_OPTIONS = {
    "Kore — Hangat (perempuan)": "Kore",
    "Leda — Lembut (perempuan)": "Leda",
    "Aoede — Ringan (perempuan)": "Aoede",
    "Charon — Tenang (laki-laki)": "Charon",
    "Puck — Ceria (laki-laki)": "Puck",
    "Fenrir — Berwibawa (laki-laki)": "Fenrir",
}

STYLE_OPTIONS = {
    "Hangat & sabar": "Katakan dengan nada hangat, sabar, dan lembut, seperti berbicara kepada orang tersayang:",
    "Tenang & pelan-pelan": "Katakan dengan nada tenang, pelan-pelan, dan menenangkan, cocok untuk didengarkan sebelum tidur:",
    "Ceria & bersemangat": "Katakan dengan nada ceria dan bersemangat:",
    "Netral & jelas": "Katakan dengan nada netral, jelas, dan mudah dipahami:",
}


def setup_page():
    st.set_page_config(
        page_title="Plusone — Teman Saat Sendirian",
        layout="centered"
    )
    
    st.header("👋 Plusone")
    st.caption("Teman yang selalu ada, saat tidak ada orang lain di dekatmu.")

    st.sidebar.header("Pilih Bantuan", divider='rainbow')

    st.sidebar.info(
        "Plusone membantu menjelaskan, bukan menggantikan dokter, "
        "keluarga, atau pendamping profesional. Untuk keputusan penting, "
        "tetap konsultasikan ke orang yang tepat, ya."
    )

    st.sidebar.markdown("**🔊 Pengaturan suara**")
    st.sidebar.selectbox("Pilih suara", list(VOICE_OPTIONS.keys()), key="tts_voice_label")
    st.sidebar.selectbox("Pilih gaya bicara", list(STYLE_OPTIONS.keys()), key="tts_style_label")
    st.sidebar.caption("Berlaku untuk suara yang belum pernah didengarkan. Suara yang sudah tersimpan tidak berubah otomatis.")

    hide_menu_style = """
            <style>
            #MainMenu {visibility: hidden;}
            </style>
            """
    st.markdown(hide_menu_style, unsafe_allow_html=True)

    
def show_usage(usage_metadata):
    if not usage_metadata:
        return
    st.sidebar.markdown("**Pemakaian token**")
    st.sidebar.markdown(f"- Prompt: {usage_metadata.prompt_token_count}")
    if usage_metadata.thoughts_token_count:
        st.sidebar.markdown(f"- Berpikir: {usage_metadata.thoughts_token_count}")
    st.sidebar.markdown(f"- Jawaban: {usage_metadata.candidates_token_count}")
    st.sidebar.markdown(f"- **Total: {usage_metadata.total_token_count}**")


def pcm_to_wav_bytes(pcm_data, channels=1, rate=24000, sample_width=2):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def text_to_speech(text):
    """Turn text into spoken audio (WAV bytes) using Gemini's TTS model,
    applying the voice and speaking style currently selected in the sidebar."""
    voice_label = st.session_state.get("tts_voice_label", next(iter(VOICE_OPTIONS)))
    style_label = st.session_state.get("tts_style_label", next(iter(STYLE_OPTIONS)))
    voice = VOICE_OPTIONS[voice_label]
    style_instruction = STYLE_OPTIONS[style_label]

    response = client.models.generate_content(
        model="gemini-3.1-flash-tts-preview",
        contents=f"{style_instruction} {text}",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
        ),
    )
    pcm_data = response.candidates[0].content.parts[0].inline_data.data
    return pcm_to_wav_bytes(pcm_data)


def render_message(role, text, key):
    """Show one chat bubble. Model replies get a 'read aloud' button (TTS),
    cached in session_state so it only needs to be generated once."""
    avatar = "🧞‍♀️" if role == "model" else None
    with st.chat_message(role, avatar=avatar):
        st.markdown(text)
        if role == "model":
            audio_key = f"audio_{key}"
            if audio_key not in st.session_state:
                if st.button("🔊 Dengarkan jawaban ini", key=f"btn_{key}"):
                    with st.spinner("Menyiapkan suara..."):
                        st.session_state[audio_key] = text_to_speech(text)
            if audio_key in st.session_state:
                st.audio(st.session_state[audio_key], format="audio/wav")


def offer_full_read(chat, history_key, prompt_text="Tolong bacakan dan jelaskan isi file ini untukku secara lengkap namun ringkas."):
    """One-click button right after upload: ask Plusone to summarize the file
    out loud, without the user needing to type anything."""
    if st.button("🔊 Bacakan seluruh isi file ini", key=f"fullread_{history_key}"):
        with st.spinner("Plusone sedang membaca file..."):
            ask_and_respond(chat, history_key, prompt_text)


def render_history(history_key):
    """Redraw every past message in this session so history survives Streamlit reruns."""
    for i, msg in enumerate(st.session_state[history_key]):
        render_message(msg["role"], msg["text"], f"{history_key}_{i}")


def ask_and_respond(chat, history_key, prompt):
    """Send one new prompt to an existing chat, show it, and append both turns to history."""
    st.session_state[history_key].append({"role": "user", "text": prompt})
    idx_user = len(st.session_state[history_key]) - 1
    render_message("user", prompt, f"{history_key}_{idx_user}")

    with st.spinner("Plusone sedang menjawab..."):
        response = chat.send_message(prompt)

    st.session_state[history_key].append({"role": "model", "text": response.text})
    idx_model = len(st.session_state[history_key]) - 1
    render_message("model", response.text, f"{history_key}_{idx_model}")

    st.sidebar.markdown("---")
    show_usage(response.usage_metadata)


def get_choice():
    choice = st.sidebar.radio("Pilih:", ["💬 Ngobrol dengan Plusone",
                                          "📄 Bacakan surat/dokumen",
                                          "📚 Bacakan beberapa dokumen",
                                          "🖼️ Lihatkan foto ini",
                                          "🎙️ Dengarkan pesan suara ini",
                                          "🎬 Tonton video ini bersamaku"],)
    return choice

 
def get_clear():
    clear_button=st.sidebar.button("🔄 Mulai obrolan baru", key="clear")
    return clear_button


def clear_session_keys(*keys):
    for key in keys:
        st.session_state.pop(key, None)


def save_uploaded_file(uploaded_file):
    """Streamlit's uploaded file only lives in memory — write it to disk first
    so client.files.upload() (which needs a real file path) can find it."""
    path = uploaded_file.name
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path

     
def main():
    choice = get_choice()
    
    if choice == "💬 Ngobrol dengan Plusone":
        st.subheader("Ngobrol santai")
        clear = get_clear()
        if clear:
            clear_session_keys('history_converse', 'chat_converse')

        if 'history_converse' not in st.session_state:
            st.session_state.history_converse = []

        if 'chat_converse' not in st.session_state:
            st.session_state.chat_converse = client.chats.create(
                model=MODEL_ID,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "You are Plusone, a warm, patient, and friendly companion for "
                        "people who are often alone — such as elderly users or people "
                        "with disabilities. Speak simply, kindly, and unhurriedly, in "
                        "the same language the user uses. Keep answers short and clear. "
                        "You are a companion, not a replacement for real human contact, "
                        "medical professionals, or emergency help — gently encourage the "
                        "user to reach out to family, caregivers, or professionals when "
                        "something serious comes up."
                    ),
                ),
            )

        render_history('history_converse')

        prompt = st.chat_input("Tulis apa saja yang ingin kamu obrolkan...")
        if prompt:
            ask_and_respond(st.session_state.chat_converse, 'history_converse', prompt)

    elif choice == "📄 Bacakan surat/dokumen":
        st.subheader("Bacakan surat atau dokumen")
        st.caption("Unggah surat, resep dokter, tagihan, atau dokumen apa pun — Plusone akan bantu jelaskan isinya dengan bahasa sederhana.")
        clear = get_clear()
        if clear:
            clear_session_keys('history_pdf', 'chat_pdf', 'pdf_file_name')

        if 'history_pdf' not in st.session_state:
            st.session_state.history_pdf = []

        uploaded_file = st.file_uploader("Pilih file PDF", type=['pdf'], accept_multiple_files=False)

        if uploaded_file:
            # Only (re)upload and start a fresh chat when a genuinely new file is chosen —
            # not on every rerun, which was wiping the conversation on each question.
            if st.session_state.get('pdf_file_name') != uploaded_file.name:
                saved_path = save_uploaded_file(uploaded_file)
                file_upload = client.files.upload(file=saved_path)
                st.session_state.chat_pdf = client.chats.create(
                    model=MODEL_ID,
                    config=types.GenerateContentConfig(
                        system_instruction=(
                            "You are Plusone, a warm and patient companion helping someone "
                            "understand a document. Explain in simple, plain language, in "
                            "the same language the user uses. If the document involves "
                            "medical or legal content, explain what it says without giving "
                            "a diagnosis or legal ruling, and gently remind the user to "
                            "confirm important decisions with a doctor, lawyer, or family member."
                        ),
                    ),
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

            offer_full_read(st.session_state.chat_pdf, 'history_pdf')
            render_history('history_pdf')

            prompt2 = st.chat_input("Tanyakan apa saja tentang dokumen ini...")
            if prompt2:
                ask_and_respond(st.session_state.chat_pdf, 'history_pdf', prompt2)

    elif choice == "📚 Bacakan beberapa dokumen":
        st.subheader("Bacakan beberapa dokumen sekaligus")
        st.caption("Punya beberapa surat atau dokumen yang berhubungan? Unggah semuanya, Plusone akan bantu bacakan dan bandingkan.")
        clear = get_clear()
        if clear:
            clear_session_keys('history_pdfs', 'chat_pdfs', 'pdfs_file_names')

        if 'history_pdfs' not in st.session_state:
            st.session_state.history_pdfs = []

        uploaded_files2 = st.file_uploader("Pilih 1 atau lebih file PDF",  type=['pdf'], accept_multiple_files=True)

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
                    config=types.GenerateContentConfig(
                        system_instruction=(
                            "You are Plusone, a warm and patient companion helping someone "
                            "understand several documents together. Explain in simple, plain "
                            "language, in the same language the user uses. If the documents "
                            "involve medical or legal content, explain what they say without "
                            "giving a diagnosis or legal ruling, and gently remind the user to "
                            "confirm important decisions with a doctor, lawyer, or family member."
                        ),
                    ),
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

            offer_full_read(st.session_state.chat_pdfs, 'history_pdfs')
            render_history('history_pdfs')

            prompt2b = st.chat_input("Tanyakan apa saja tentang dokumen-dokumen ini...")
            if prompt2b:
                ask_and_respond(st.session_state.chat_pdfs, 'history_pdfs', prompt2b)

    elif choice == "🖼️ Lihatkan foto ini":
        st.subheader("Lihatkan foto ini untukku")
        st.caption("Foto obat, kondisi kulit, surat, atau apa pun yang ingin kamu tanyakan — Plusone akan bantu jelaskan.")
        clear = get_clear()
        if clear:
            clear_session_keys('history_image', 'chat_image', 'image_file_name')

        if 'history_image' not in st.session_state:
            st.session_state.history_image = []

        uploaded_image = st.file_uploader("Pilih file PNG atau JPEG",  type=['png','jpg'], accept_multiple_files=False)

        if uploaded_image:
            if st.session_state.get('image_file_name') != uploaded_image.name:
                saved_path = save_uploaded_file(uploaded_image)
                file_upload = client.files.upload(file=saved_path)
                st.session_state.chat_image = client.chats.create(
                    model=MODEL_ID,
                    config=types.GenerateContentConfig(
                        system_instruction=(
                            "You are Plusone, a warm and patient companion helping someone "
                            "understand what is in a photo. Describe and explain in simple, "
                            "plain language, in the same language the user uses. If the photo "
                            "shows something medical (medication, skin condition, injury), "
                            "explain what you see without giving a diagnosis, and gently "
                            "remind the user to confirm with a doctor or caregiver."
                        ),
                    ),
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

            offer_full_read(st.session_state.chat_image, 'history_image', "Tolong lihat dan jelaskan isi foto ini untukku secara lengkap namun ringkas.")
            render_history('history_image')

            prompt3 = st.chat_input("Tanyakan apa saja tentang foto ini...")
            if prompt3:
                ask_and_respond(st.session_state.chat_image, 'history_image', prompt3)

    elif choice == "🎙️ Dengarkan pesan suara ini":
        st.subheader("Dengarkan pesan suara ini untukku")
        st.caption("Rekaman pesan keluarga, dokter, atau catatan suaramu sendiri — Plusone akan bantu dengarkan dan jelaskan.")
        clear = get_clear()
        if clear:
            clear_session_keys('history_audio', 'chat_audio', 'audio_file_name')

        if 'history_audio' not in st.session_state:
            st.session_state.history_audio = []

        uploaded_audio = st.file_uploader("Pilih file MP3 atau WAV",  type=['mp3','wav'], accept_multiple_files=False)

        if uploaded_audio:
            if st.session_state.get('audio_file_name') != uploaded_audio.name:
                saved_path = save_uploaded_file(uploaded_audio)
                file_upload = client.files.upload(file=saved_path)
                st.session_state.chat_audio = client.chats.create(
                    model=MODEL_ID,
                    config=types.GenerateContentConfig(
                        system_instruction=(
                            "You are Plusone, a warm and patient companion helping someone "
                            "understand an audio recording — such as a voice message from "
                            "family, a doctor, or their own notes. Summarize and explain in "
                            "simple, plain language, in the same language the user uses."
                        ),
                    ),
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

            offer_full_read(st.session_state.chat_audio, 'history_audio', "Tolong dengarkan dan jelaskan isi pesan suara ini untukku secara lengkap namun ringkas.")
            render_history('history_audio')

            prompt5 = st.chat_input("Tanyakan apa saja tentang pesan suara ini...")
            if prompt5:
                ask_and_respond(st.session_state.chat_audio, 'history_audio', prompt5)

    elif choice == "🎬 Tonton video ini bersamaku":
        st.subheader("Tonton video ini bersamaku")
        st.caption("Video call rekaman keluarga, instruksi terapi, atau video apa pun — Plusone akan bantu jelaskan.")
        clear = get_clear()
        if clear:
            clear_session_keys('history_video', 'chat_video', 'video_file_name')

        if 'history_video' not in st.session_state:
            st.session_state.history_video = []

        uploaded_video = st.file_uploader("Pilih file MP4 atau MOV",  type=['mp4','mov'], accept_multiple_files=False)

        if uploaded_video:
            if st.session_state.get('video_file_name') != uploaded_video.name:
                saved_path = save_uploaded_file(uploaded_video)
                video_file = client.files.upload(file=saved_path)
                while video_file.state == "PROCESSING":
                    time.sleep(10)
                    video_file = client.files.get(name=video_file.name)

                if video_file.state == "FAILED":
                    raise ValueError(video_file.state)

                st.session_state.chat_video = client.chats.create(
                    model=MODEL_ID,
                    config=types.GenerateContentConfig(
                        system_instruction=(
                            "You are Plusone, a warm and patient companion helping someone "
                            "understand a video — such as a family video call recording or "
                            "an instructional video (e.g. how to use a medical device). "
                            "Summarize and explain in simple, plain language, step by step "
                            "if relevant, in the same language the user uses."
                        ),
                    ),
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

            offer_full_read(st.session_state.chat_video, 'history_video', "Tolong tonton dan jelaskan isi video ini untukku secara lengkap namun ringkas.")
            render_history('history_video')

            prompt4 = st.chat_input("Tanyakan apa saja tentang video ini...")
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
