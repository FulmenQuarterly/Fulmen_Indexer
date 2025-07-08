import streamlit as st
import fitz  # PyMuPDF
import re

# --- Page setup ---
st.set_page_config(page_title="PDF Indexer", layout="centered")

# --- Custom CSS ---
st.markdown("""
    <style>
    html, body, .main {
        background-color: #000000;
        color: #eee;
        font-family: Courier, monospace !important;
    }
    * {
        font-family: Courier, monospace !important;
    }
    h1, h2, h3, h4, h5, h6,
    label, .stMarkdown p, .stTextArea label, .stFileUploader label,
    .stTextInput, .stTextArea, .stDownloadButton, .stButton, .stFileUploader {
        font-family: Courier, monospace !important;
    }
    .stTextInput > div > input, 
    .stFileUploader > div > input, 
    .stTextArea > div > textarea {
        background-color: #222222;
        color: #eee;
        border-radius: 6px;
        border: 1px solid #444444;
        padding: 8px;
        font-size: 1rem;
        font-family: Courier, monospace !important;
        outline-color: white !important;
    }
    .stTextInput > div > input::placeholder,
    .stTextArea > div > textarea::placeholder {
        color: #888888;
        font-family: Courier, monospace !important;
    }

    /* Make inline code in labels red */
    .stTextArea label code,
    .stTextInput label code {
        color: #FF0000 !important;
    }

    .stTextArea > div > label > span > code {
        color: #FF0000 !important;
        font-family: Courier, monospace !important;
    }

    div.stFileUploader > label {
        font-family: Courier, monospace !important;
        color: #eee !important;
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        cursor: default;
        display: inline-block;
        transition: none !important;
        font-size: 1rem;
    }
    div.stFileUploader > label:hover {
        color: #eee !important;
        background-color: transparent !important;
        cursor: default;
    }

    /* File Uploader button */
    .stFileUploader > div > button {
        font-family: Courier, monospace !important;
        background-color: #000000 !important;
        color: #eee !important;
        border: 1px solid #444 !important;
        transition: background-color 0.3s ease, color 0.3s ease;
    }
    .stFileUploader > div > button:hover {
        background-color: #ff4b4b !important;
        color: white !important;
    }

    /* Generate & Download buttons */
    .stButton > button, .stDownloadButton > button {
        font-family: Courier, monospace !important;
        font-weight: 600;
        font-size: 1.1rem;
        border-radius: 6px;
        padding: 10px 24px;
        cursor: pointer;
        transition: color 0.3s ease, background-color 0.3s ease, border-color 0.3s ease;
        background-color: #000000 !important;
        color: white !important;
        border: 0.5px solid white !important;
    }
    .stButton > button {
        float: right;
    }
    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background-color: #000000 !important;
        color: #ff4b4b !important;
        border-color: #ff4b4b !important;
    }
    .stDownloadButton > button {
        float: right;
    }

    .section {
        margin-bottom: 2.5rem;
        clear: both;
    }
    .index-line {
        font-family: Courier, monospace !important;
        font-size: 1rem;
        margin: 4px 0;
        color: #FF0000;
    }
    .index-line:last-of-type {
        margin-bottom: 15px;
    }

    footer, .reportview-container .main footer {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# --- Quote Display ---
st.markdown("""
<div style="text-align: center; color: #aaaaaa; font-style: italic; font-family: Courier, monospace; margin-top: 20px; margin-bottom: 40px;">
+ <br>
There are, indeed, things that cannot be put <br>
into words. They make themselves manifest. <br>
They are what is mystical. <br>
– Wittgenstein, 1921 <br>
+
</div>
""", unsafe_allow_html=True)

# --- UI Input Section ---
st.markdown('<div class="section">', unsafe_allow_html=True)

uploaded_pdf = st.file_uploader("Upload a PDF", type="pdf")

terms_input = st.text_area(
    "Enter index terms (one per line). Use format `Label = term1, term2` for advanced matching.",
    height=250,
    placeholder="Arcadia (Arcadians) = Arcadia, Arcadians\nConan, King = King Conan\nLight"
)

st.markdown('</div>', unsafe_allow_html=True)

# --- Indexing Logic ---

def parse_terms(raw_input):
    term_map = {}
    lines = raw_input.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if '=' in line:
            label, search_terms = line.split('=', 1)
            label = label.strip()
            search_list = [s.strip() for s in search_terms.split(',') if s.strip()]
            term_map[label] = search_list
        else:
            term_map[line] = [line]
    return term_map

def extract_body_text(page, header_threshold=80):
    blocks = page.get_text("blocks")
    body_text = ""
    for b in blocks:
        x0, y0, x1, y1, text, *_ = b
        if y1 < header_threshold:
            continue
        body_text += " " + text
    return body_text

def search_terms_in_pdf(doc, term_map):
    index = {}

    for label, search_terms in term_map.items():
        pages = set()
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = extract_body_text(page)
            for term in search_terms:
                pattern = r'\b' + re.escape(term) + r'\b'
                if re.search(pattern, text, re.IGNORECASE):
                    pages.add(page_num + 1)
                    break
        if pages:
            index[label] = sorted(pages)
    return index

def collapse_ranges(pages):
    if not pages:
        return ""
    ranges = []
    start = prev = pages[0]
    for page in pages[1:]:
        if page == prev + 1:
            prev = page
        else:
            if start == prev:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{prev}")
            start = prev = page
    if start == prev:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{prev}")
    return ", ".join(ranges)

# --- Index Generation & Display ---
st.markdown('<div class="section">', unsafe_allow_html=True)
if st.button("Generate Index"):
    if uploaded_pdf and terms_input.strip():
        doc = fitz.open(stream=uploaded_pdf.read(), filetype="pdf")
        term_map = parse_terms(terms_input)
        index = search_terms_in_pdf(doc, term_map)

        if index:
            index_lines = []
            for label in sorted(index.keys(), key=lambda s: s.lower()):
                collapsed = collapse_ranges(index[label])
                line = f"{label} - {collapsed}"
                st.markdown(f'<div class="index-line">{line}</div>', unsafe_allow_html=True)
                index_lines.append(line)

            index_text = "\n".join(index_lines)
            
            # Right-align the download button
            st.markdown('<div style="text-align: right;">', unsafe_allow_html=True)
            st.download_button("Download Index as .txt", index_text, file_name="index.txt")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("None of the terms were found in the PDF.")
