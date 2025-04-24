import streamlit as st
from dotenv import load_dotenv
import os
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from gtts import gTTS
import tempfile
import re
from googletrans import Translator
import time
import requests
from pyvis.network import Network

# Set the page configuration
st.set_page_config(page_title="YouTube Summary + Audio + Enhanced Mind Map", layout="wide")

# Load environment variables
load_dotenv()

# Configure Gemini (Google Generative AI)
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    st.error("Google API Key is missing! Please set it in the .env file.")
else:
    genai.configure(api_key=api_key)

# Load Lottie animation (for loading and success animations)
def load_lottie_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

loading_animation = load_lottie_url("https://lottie.host/70c4d71f-943e-41fa-9948-01914a40917b/2Gf9CRkdtd.json")
success_animation = load_lottie_url("https://lottie.host/da65fae5-b68b-4f20-b915-d0b1d0d2bc4e/KC3bY1KzeX.json")

# Background Styling
page_bg = '''
<style>
.stApp {
    background: linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.6)), 
                url("https://images.unsplash.com/photo-1521747116042-5a810fda9664");
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}

[data-testid="stAppViewContainer"] {
    backdrop-filter: blur(10px);
}

.stMarkdown, .stTitle, .stHeader, .stTextInput, .stButton, .stText, .stSubheader {
    color: white !important; 
    font-weight: bold;
}

.stButton button {
    background-color: #FF5733;
    color: white;
    border-radius: 5px;
    font-weight: bold;
    transition: background-color 0.3s ease; /* Smooth transition */
}

.stButton button:hover {
    background-color: #c0392b; /* Darker shade when hovered */
    cursor: pointer; /* Change cursor to pointer when hovering */
}

.stTextInput input {
    color: black;
}

.stMarkdown, .stText {
    color: white !important;
}

.stTitle, .stHeader, .stSubheader {
    color: white !important;
}

.stTextInput label {
    color: white !important;
}

/* Custom styles for the summary, translated summary, and mind map */
.summary-text, .translated-summary-text, .mind-map-text {
    color: white !important;
    font-weight: bold !important;
    text-transform: uppercase !important;
}

</style>
'''

st.markdown(page_bg, unsafe_allow_html=True)

# Extract YouTube transcript
def extract_transcript_details(youtube_video_url):
    try:
        video_id = youtube_video_url.split("v=")[1].split("&")[0]
        transcript_text = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = " ".join([i["text"] for i in transcript_text])
        return transcript
    except Exception as e:
        st.error(f"Error extracting transcript: {e}")
        return None

# Generate summary using Gemini
def generate_gemini_content(transcript_text, prompt="Summarize this transcript in bullet points:\n"):
    try:
        if len(transcript_text) > 3000:
            transcript_text = transcript_text[:3000] + "..."
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        response = model.generate_content(prompt + "\n" + transcript_text)
        return response.text.strip()
    except Exception as e:
        st.error(f"Error generating summary: {e}")
        return None

# Convert text to speech
def text_to_speech(text, lang='en'):
    try:
        cleaned_text = text.replace("*", "").strip()
        tts = gTTS(cleaned_text, lang=lang)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio_file:
            tts.save(temp_audio_file.name)
            return temp_audio_file.name
    except Exception as e:
        st.error(f"Error generating speech: {e}")
        return None

# Parse summary into hierarchical points
def parse_summary_to_unique_points(summary_text):
    points = []
    sub_points = {}
    lines = re.split(r'\n|- |\u2022', summary_text)
    cleaned_lines = set()
    for line in lines:
        line = line.strip().strip('.').capitalize()
        if len(line) > 0 and line not in cleaned_lines:
            cleaned_lines.add(line)
            points.append(line)
    main_points = points[:4]
    for idx, point in enumerate(main_points):
        subs = []
        start_index = points.index(point)
        for offset in range(1, 3):
            if start_index + offset < len(points):
                next_point = points[start_index + offset]
                if next_point != point:
                    subs.append(next_point)
        sub_points[point] = subs
    return main_points, sub_points

# Create Interactive Mind Map with Hierarchy
def create_interactive_mind_map(title, main_points, sub_points):
    net = Network(height="500px", width="100%", bgcolor="#ffffff", font_color="black", notebook=False)

    net.add_node("Main", label=title, color="#FF5733", shape="ellipse", size=30)

    node_id = 1
    for point in main_points:
        net.add_node(node_id, label=point, color="#3498db", shape="box", size=20)
        net.add_edge("Main", node_id)
        sub_node_id = node_id + 1
        
        if point in sub_points:
            for sub_point in sub_points[point]:
                net.add_node(sub_node_id, label=sub_point, color="#2ecc71", shape="box", size=15)
                net.add_edge(node_id, sub_node_id)
                sub_node_id += 1

        node_id = sub_node_id

    net.set_options(""" 
        var options = {
            "physics": {
                "enabled": true,
                "barnesHut": {
                    "gravitationalConstant": -8000,
                    "centralGravity": 0.2,
                    "springLength": 150
                },
                "repulsion": {
                    "nodeDistance": 300
                }
            },
            "nodes": {
                "shape": "box",
                "font": {
                    "size": 14
                }
            },
            "edges": {
                "smooth": {
                    "type": "continuous"
                }
            }
        }
    """)

    return net

# Translate text to Marathi, Hindi, or English
def translate_text(text, target_language='en'):
    try:
        translator = Translator()
        translated = translator.translate(text, dest=target_language)
        return translated.text
    except Exception as e:
        st.error(f"Error translating text: {e}")
        return None

# Streamlit UI

st.markdown("<h1 style='color: white;'>🎥 YouTube Summary + 🎧 Audio + 🧠 Mind Map</h1>", unsafe_allow_html=True)


# YouTube link input
youtube_link = st.text_input("Enter YouTube Video Link:")

if youtube_link:
    try:
        video_id = youtube_link.split("v=")[1].split("&")[0]
        st.image(f"http://img.youtube.com/vi/{video_id}/0.jpg", use_column_width=True)
    except:
        st.warning("Invalid YouTube URL format")

# Language selection for translation (Marathi, English, Hindi)
st.markdown("<h6 style='color: white;'>Select Translation Language:</h6>", unsafe_allow_html=True)
target_language = st.selectbox("", ["en", "mr", "hi"])

# Button for generating summary
if st.button("Generate Summary, Audio & Interactive Mind Map"):
    if youtube_link:
        if loading_animation:
            st_lottie(loading_animation, speed=1, width=150, height=150) # type: ignore
        time.sleep(2)

        transcript_text = extract_transcript_details(youtube_link)
        if transcript_text:
            summary = generate_gemini_content(transcript_text)
            if summary:
                st.session_state.summary = summary  # Store summary in session state
                st.session_state.transcript = transcript_text  # Store transcript in session state
                st.success("Summary Generated!")
                if success_animation:
                    st.lottie(success_animation, speed=1, width=150, height=150)

                st.subheader("📝 Summary")
                st.markdown(f"<p class='summary-text;'>{st.session_state.summary}</p>", unsafe_allow_html=True)


                # Translate the summary
                translated_summary = translate_text(st.session_state.summary, target_language)
                if translated_summary:
                    st.subheader(f"🌐 Translated Summary ({target_language.upper()})")
                    st.markdown(f"<p class='translated-summary-text'>{translated_summary}</p>", unsafe_allow_html=True)

                # Audio Output
                language_for_audio = target_language if target_language != 'en' else 'en'
                audio_path = text_to_speech(translated_summary if translated_summary else st.session_state.summary, lang=language_for_audio)
                if audio_path:
                    st.audio(audio_path, format='audio/mp3')
                    os.remove(audio_path)

                # Parse the summary to hierarchical points
                main_points, sub_points = parse_summary_to_unique_points(st.session_state.summary)

                # Generate and display the interactive mind map
                mind_map = create_interactive_mind_map("Video Summary", main_points, sub_points)
                mind_map.save_graph("mind_map.html")

                # Display the interactive mind map
                st.subheader("🧠 Interactive Mind Map")
                with open("mind_map.html", "r", encoding="utf-8") as f:
                    html_code = f.read()
                    st.components.v1.html(html_code, height=500)

            else:
                st.error("Failed to generate summary.")
        else:
            st.error("Transcript could not be extracted.")
    else:
        st.error("Please enter a valid YouTube link.")