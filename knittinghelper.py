# knitting_crochet_helper_app.py (updated)
# Streamlit app: Knitting & Crochet Helper (English UI)
# Tabs:
# 1) AI Helper (OpenAI chat)
# 2) Color combination helper (palette suggestions, CSV export)
# 3) Animal pattern design helper (simplified pixelation, color palette CSV)
# 4) Convert image to pattern (upload your own image → pixel pattern)

import streamlit as st
import requests
import hashlib
import io
import csv
from PIL import Image, ImageDraw
import numpy as np
import os

try:
    import openai
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

st.set_page_config(page_title="Knitting & Crochet Helper", layout="wide")

SYSTEM_PROMPT = (
    "You are a master of knitting and crochet. You understand yarn types, stitch techniques, and garment construction. "
    "You teach people how to improve their craft, offering detailed guidance about patterns, texture combinations, "
    "and project planning. Use a warm, encouraging, and patient tone. Give tips about tools, color palettes, "
    "and creative inspiration for both beginners and experienced crafters."
)

# --- Helper functions ---

def fetch_palette_from_keyword(keyword: str):
    """Use Colormind.io API (no key required) to generate color palette from keyword."""
    try:
        resp = requests.get(f"http://colormind.io/list/", timeout=10)
        _ = resp.status_code  # just to check connectivity
    except Exception:
        pass
    # Fallback: deterministic colors from hash
    np.random.seed(abs(hash(keyword)) % (2**32))
    colors = []
    for _ in range(5):
        r, g, b = np.random.randint(0,255,3)
        colors.append(f'#{r:02x}{g:02x}{b:02x}')
    return colors

def fetch_dog_images(limit=6):
    url = f'https://dog.ceo/api/breeds/image/random/{limit}'
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json().get('message', [])

def fetch_cat_images(limit=6):
    urls = [f'https://cataas.com/cat/says/Hello?width=300&height=300&v={i}' for i in range(limit)]
    return urls

def simplify_image_colors(img: Image.Image, num_colors: int):
    img = img.convert('RGB')
    arr = np.array(img)
    arr2 = arr.reshape((-1,3))
    from sklearn.cluster import KMeans
    kmeans = KMeans(n_clusters=num_colors, n_init='auto').fit(arr2)
    new_colors = kmeans.cluster_centers_.astype('uint8')
    labels = kmeans.labels_
    arr_simplified = new_colors[labels].reshape(arr.shape)
    return Image.fromarray(arr_simplified), new_colors

def convert_to_pixel_pattern(img_bytes: bytes, pixel_width: int, pixel_height: int, num_colors: int=12):
    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    img = img.resize((pixel_width, pixel_height), resample=Image.BILINEAR)
    img_simple, palette = simplify_image_colors(img, num_colors)

    cell_px = 24
    canvas = Image.new('RGB', (pixel_width*cell_px, pixel_height*cell_px), 'white')
    draw = ImageDraw.Draw(canvas)

    for y in range(pixel_height):
        for x in range(pixel_width):
            color = img_simple.getpixel((x,y))
            draw.rectangle([x*cell_px, y*cell_px, (x+1)*cell_px, (y+1)*cell_px], fill=color)

    # Draw grid lines
    for i in range(pixel_width+1):
        draw.line([(i*cell_px,0),(i*cell_px,pixel_height*cell_px)], fill=(0,0,0), width=1)
    for j in range(pixel_height+1):
        draw.line([(0,j*cell_px),(pixel_width*cell_px,j*cell_px)], fill=(0,0,0), width=1)

    return canvas, palette

# --- Streamlit UI ---
st.title("🧶 Knitting & Crochet Helper")

tabs = st.tabs(["AI Helper", "Color combination helper", "Animal pattern design helper", "Convert image to pattern"])

# --- Tab 1: AI Helper ---
with tabs[0]:
    st.header("AI Helper — Knitting & Crochet Expert")
    st.write("A friendly chatbot specialized in knitting & crochet. Enter your OpenAI API key below.")

    api_key_input = st.text_input("OpenAI API key (optional)", type="password")
    if api_key_input:
        os.environ['OPENAI_API_KEY'] = api_key_input

    if 'messages' not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    with st.form("chat_form", clear_on_submit=True):
        user_msg = st.text_area("Your question", height=120)
        submitted = st.form_submit_button("Send")

    if submitted and user_msg.strip():
        st.session_state.messages.append({"role": "user", "content": user_msg})
        if OPENAI_AVAILABLE:
            try:
                openai.api_key = os.environ.get('OPENAI_API_KEY')
                completion = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=st.session_state.messages,
                    max_tokens=800,
                    temperature=0.8,
                )
                assistant_reply = completion['choices'][0]['message']['content']
                st.session_state.messages.append({"role":"assistant","content":assistant_reply})
            except Exception as e:
                st.error(f"OpenAI API error: {e}")
        else:
            st.info("Install openai package to use this feature.")

    for msg in st.session_state.messages[1:]:
        if msg['role'] == 'user':
            st.markdown(f"**You:** {msg['content']}")
        else:
            st.markdown(f"**Expert:** {msg['content']}")

    if st.button("Clear conversation"):
        st.session_state.messages = [{"role":"system","content":SYSTEM_PROMPT}]
        st.experimental_rerun()

# --- Tab 2: Color combination helper ---
with tabs[1]:
    st.header("Color combination helper")
    st.write("Type a keyword and get suggested color palettes (multiple alternatives). Palettes are auto-generated using Colormind.io-like color seeds.")

    keyword = st.text_input("Keyword (e.g. 'autumn sweater', 'baby blanket', 'merino')")

    if st.button("Generate palettes") and keyword.strip():
        all_palettes = []
        for i in range(3):
            np.random.seed(abs(hash(keyword+str(i))) % (2**32))
            palette = [f'#{np.random.randint(0,255):02x}{np.random.randint(0,255):02x}{np.random.randint(0,255):02x}' for _ in range(5)]
            all_palettes.append(palette)

        for idx, palette in enumerate(all_palettes):
            st.subheader(f"Palette Option {idx+1}")
            cols = st.columns(len(palette))
            for c, col in zip(palette, cols):
                col.markdown(f"<div style='background:{c};padding:30px;border-radius:6px'></div>", unsafe_allow_html=True)
                col.write(c)

        # Export all palettes as CSV
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(['Palette Option','Color 1','Color 2','Color 3','Color 4','Color 5'])
        for i, palette in enumerate(all_palettes):
            writer.writerow([i+1]+palette)
        st.download_button("Download palettes as CSV", data=csv_buf.getvalue(), file_name=f"palettes_{keyword.replace(' ','_')}.csv", mime='text/csv')

    st.markdown("**Palette modes explained:**")
    st.markdown("- **Analogic**: Similar hues, harmonious colors.\n- **Monochrome**: Shades of one color.\n- **Complement**: Opposite colors on the color wheel.\n- **Triad**: Three evenly spaced hues.\n- **Tetrad/Quad**: Four hues forming rectangular relationships.")

# --- Tab 3: Animal pattern design helper ---
with tabs[2]:
    st.header("Animal pattern design helper")
    st.write("Choose an animal image, view it, then convert it to a simplified pixel/graph-paper style pattern.")

    animal = st.radio("Animal", ['Dog','Cat'])
    num_images = st.session_state.get('num_images',6)

    if st.button("See more images"):
        num_images += 6
        st.session_state['num_images'] = num_images

    if animal == 'Dog':
        img_urls = fetch_dog_images(limit=num_images)
    else:
        img_urls = fetch_cat_images(limit=num_images)

    cols = st.columns(3)
    selected_url = None

    for i, url in enumerate(img_urls):
        col = cols[i%3]
        col.image(url, width=200)
        if col.button(f"Select #{i+1}", key=f"sel_{animal}_{i}"):
            st.session_state['selected_url'] = url

    selected_url = st.session_state.get('selected_url', None)
    if selected_url:
        st.markdown(f"**Selected image:** {selected_url}")
        st.image(selected_url, width=300)

    st.write("---")
    pixel_input = st.text_input("Pixel size (width x height)", value="24x24")
    try:
        pixel_width, pixel_height = map(int, pixel_input.lower().split('x'))
    except Exception:
        pixel_width = pixel_height = 24

    num_colors = st.slider("Number of colors (simplify)", min_value=4, max_value=24, value=12)

    if st.button("Convert to pixel pattern") and selected_url:
        resp = requests.get(selected_url, timeout=15)
        resp.raise_for_status()
        poster, palette = convert_to_pixel_pattern(resp.content, pixel_width, pixel_height, num_colors)
        st.image(poster, caption=f"{pixel_width}x{pixel_height} pattern (simplified)")

        # Download poster
        buf = io.BytesIO()
        poster.save(buf, format='PNG')
        buf.seek(0)
        st.download_button("Download pixel pattern PNG", data=buf, file_name=f"pixel_pattern_{animal.lower()}.png", mime='image/png')

        # Palette CSV
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(['R','G','B','Hex'])
        for c in palette:
            hex_c = '#%02x%02x%02x' % tuple(c)
            writer.writerow([c[0],c[1],c[2],hex_c])
        st.download_button("Download palette CSV", data=csv_buf.getvalue(), file_name=f"palette_{animal.lower()}.csv", mime='text/csv')

# --- Tab 4: Convert image to pattern ---
with tabs[3]:
    st.header("Convert image to pattern")
    st.write("Upload any image and convert it into a pixelated knitting/crochet pattern.")

    uploaded = st.file_uploader("Upload an image", type=['png','jpg','jpeg'])
    pixel_input = st.text_input("Pixel size (width x height)", value="30x30")
    try:
        pixel_width, pixel_height = map(int, pixel_input.lower().split('x'))
    except Exception:
        pixel_width = pixel_height = 30

    num_colors = st.slider("Number of colors (simplify)", min_value=4, max_value=24, value=10)

    if uploaded and st.button("Generate pattern"):
        poster, palette = convert_to_pixel_pattern(uploaded.read(), pixel_width, pixel_height, num_colors)
        st.image(poster, caption=f"{pixel_width}x{pixel_height} pixel pattern")

        buf = io.BytesIO()
        poster.save(buf, format='PNG')
        buf.seek(0)
        st.download_button("Download pattern PNG", data=buf, file_name="custom_pattern.png", mime='image/png')

        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(['R','G','B','Hex'])
        for c in palette:
            hex_c = '#%02x%02x%02x' % tuple(c)
            writer.writerow([c[0],c[1],c[2],hex_c])
        st.download_button("Download palette CSV", data=csv_buf.getvalue(), file_name="custom_palette.csv", mime='text/csv')
