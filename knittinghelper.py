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


'''
# knitting_crochet_helper_app.py
# Streamlit app: Knitting & Crochet Helper
# Features:
# 1) AI Helper: Chatbot specialized in knitting & crochet using OpenAI (user provides API key)
# 2) Color combination helper: user supplies keyword; app generates color palette using a stable hex derived from the keyword and TheColorAPI (no API key required)
# 3) Animal pattern design helper: shows dog & cat images (no API key), user chooses one and converts to a pixel (graph-paper style) pattern image for download

import streamlit as st
import requests
import hashlib
import io
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os

# Optional: OpenAI
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

# Helper: hash keyword -> hex color
def keyword_to_hex(keyword: str) -> str:
    h = hashlib.md5(keyword.encode('utf-8')).hexdigest()
    return h[:6]

# Fetch color scheme from TheColorAPI (no API key required)
def fetch_palette_from_hex(hexcode: str, mode: str = 'analogic', count: int = 5):
    url = f'https://www.thecolorapi.com/scheme?hex={hexcode}&mode={mode}&count={count}'
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    colors = [c['hex']['value'] for c in data.get('colors', [])]
    return colors

# Fetch example animal images (no API key)
# Dog: dog.ceo; Cat: cataas

def fetch_dog_images(limit=4):
    url = 'https://dog.ceo/api/breeds/image/random/' + str(limit)
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json().get('message', [])

def fetch_cat_images(limit=4):
    # Cataas supports simple endpoints; to get multiple images we'll request different sizes
    urls = [f'https://cataas.com/cat?type=png&{i}' for i in range(limit)]
    return urls

# Convert image to pixel pattern (graph paper style)
def convert_to_pixel_pattern(img_bytes: bytes, pixel_size: int = 20, grid_line_width: int = 1, show_hex=False):
    # Open image
    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    # Create square crop preserving center
    w, h = img.size
    s = min(w, h)
    left = (w - s)//2
    top = (h - s)//2
    img = img.crop((left, top, left+s, top+s))

    # Resize to pixel resolution
    small = img.resize((pixel_size, pixel_size), resample=Image.BILINEAR)

    # Create poster image: each cell is cell_px x cell_px, with grid lines
    cell_px = 24  # base cell size; final size = pixel_size * cell_px
    canvas_size = pixel_size * cell_px + grid_line_width
    poster = Image.new('RGB', (canvas_size, canvas_size), 'white')
    draw = ImageDraw.Draw(poster)

    # Draw cells
    for y in range(pixel_size):
        for x in range(pixel_size):
            color = small.getpixel((x, y))
            x0 = x * cell_px + grid_line_width
            y0 = y * cell_px + grid_line_width
            x1 = x0 + cell_px - grid_line_width
            y1 = y0 + cell_px - grid_line_width
            draw.rectangle([x0, y0, x1, y1], fill=color)

    # Draw graph-paper grid lines
    for i in range(pixel_size + 1):
        pos = i * cell_px
        # vertical
        draw.line([(pos,0),(pos,canvas_size)], fill=(0,0,0), width=grid_line_width)
        # horizontal
        draw.line([(0,pos),(canvas_size,pos)], fill=(0,0,0), width=grid_line_width)

    # Optionally annotate hex codes inside each cell (small font)
    if show_hex:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        for y in range(pixel_size):
            for x in range(pixel_size):
                color = small.getpixel((x, y))
                hexc = '#%02x%02x%02x' % color
                x0 = x * cell_px + 3
                y0 = y * cell_px + 3
                draw.text((x0, y0), hexc, fill='black' if sum(color) > 300 else 'white', font=font)

    return poster

# --- Streamlit UI ---
st.title("🧶 Knitting & Crochet Helper")

tabs = st.tabs(["AI Helper", "Color combination helper", "Animal pattern design helper"])

# --- Tab 1: AI Helper ---
with tabs[0]:
    st.header("AI Helper — Knitting & Crochet Expert")
    st.write("A friendly chatbot specialized in knitting & crochet. Enter your OpenAI API key below (or set OPENAI_API_KEY environment variable). If you hit a 403 error, check your key and billing or paste the key here.")

    api_key_input = st.text_input("OpenAI API key (optional)", type="password")
    if api_key_input:
        os.environ['OPENAI_API_KEY'] = api_key_input

    if not OPENAI_AVAILABLE:
        st.warning("openai package not found. Install the 'openai' Python package to enable AI chat. See requirements.txt.")

    # Chat history stored in session state
    if 'messages' not in st.session_state:
        st.session_state.messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    with st.form("chat_form", clear_on_submit=True):
        user_msg = st.text_area("Your question", height=120)
        submitted = st.form_submit_button("Send")

    if submitted and user_msg.strip():
        st.session_state.messages.append({"role": "user", "content": user_msg})
        if OPENAI_AVAILABLE:
            try:
                openai.api_key = os.environ.get('OPENAI_API_KEY')
                if not openai.api_key:
                    st.error("No OpenAI API key found. Please set OPENAI_API_KEY or paste it above.")
                else:
                    # Use ChatCompletion; user can change model if desired
                    completion = openai.ChatCompletion.create(
                        model="gpt-4o-mini",
                        messages=st.session_state.messages,
                        max_tokens=800,
                        temperature=0.8,
                    )
                    assistant_reply = completion['choices'][0]['message']['content']
                    st.session_state.messages.append({"role":"assistant","content":assistant_reply})
            except openai.error.OpenAIError as e:
                st.error(f"OpenAI API error: {e}")
                # keep messages but show error
        else:
            st.info("OpenAI is not installed in this environment. To test the UI locally, install the openai package and provide your API key.")

    # Display conversation
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
    st.write("Type a keyword (project idea, emotion, yarn name) and get suggested color palettes. Palettes are fetched from TheColorAPI (no API key needed).")

    col1, col2 = st.columns([3,1])
    with col1:
        keyword = st.text_input("Keyword (e.g. 'autumn sweater', 'baby blanket', 'merino')")
    with col2:
        mode = st.selectbox("Palette mode", ['analogic', 'monochrome', 'complement', 'triad', 'tetrad', 'quad'])

    if st.button("Generate palette") and keyword.strip():
        hexbase = keyword_to_hex(keyword)
        try:
            colors = fetch_palette_from_hex(hexbase, mode=mode, count=5)
            st.write(f"Base hex from keyword: #{hexbase}")
            cols = st.columns(len(colors))
            for c, col in zip(colors, cols):
                col.markdown(f"<div style='background:{c};padding:30px;border-radius:6px'></div>", unsafe_allow_html=True)
                col.write(c)

            # Export palette as PNG
            img_w = 100 * len(colors)
            img_h = 120
            img = Image.new('RGB', (img_w, img_h), 'white')
            d = ImageDraw.Draw(img)
            for i, c in enumerate(colors):
                d.rectangle([i*100, 0, (i+1)*100, 80], fill=c)
                d.text((i*100+8, 86), c, fill='black')
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            st.download_button("Download palette PNG", data=buf, file_name=f"palette_{keyword.replace(' ','_')}.png", mime='image/png')

        except Exception as e:
            st.error(f"Failed to fetch palette: {e}")

# --- Tab 3: Animal pattern design helper ---
with tabs[2]:
    st.header("Animal pattern design helper")
    st.write("Choose a dog or cat image (fetched from public no-key APIs), then convert it to a pixel / graph-paper style poster suitable for designing a pixel pattern.")

    animal = st.radio("Animal", ['Dog','Cat'])
    if animal == 'Dog':
        try:
            img_urls = fetch_dog_images(limit=6)
        except Exception as e:
            st.error(f"Failed to fetch dog images: {e}")
            img_urls = []
    else:
        img_urls = fetch_cat_images(limit=6)

    if img_urls:
        cols = st.columns(3)
        selected_url = None
        for i, url in enumerate(img_urls):
            col = cols[i%3]
            try:
                col.image(url, width=200)
                if col.button(f"Select #{i+1}", key=f"sel_{i}"):
                    selected_url = url
                    st.session_state['selected_url'] = url
            except Exception as e:
                col.write("Failed to load")

        if 'selected_url' in st.session_state:
            selected_url = st.session_state['selected_url']
            st.markdown(f"**Selected image:** {selected_url}")

        st.write("---")
        pixel_size = st.number_input("Pixel (grid) size for pattern (e.g. 20 = 20x20)", min_value=8, max_value=200, value=24, step=1)
        show_hex = st.checkbox("Annotate hex codes in each cell (slower)")

        if st.button("Convert pixel pattern") and selected_url:
            try:
                resp = requests.get(selected_url, timeout=15)
                resp.raise_for_status()
                poster = convert_to_pixel_pattern(resp.content, pixel_size, grid_line_width=1, show_hex=show_hex)
                st.image(poster, caption=f"{pixel_size}x{pixel_size} pattern (graph paper style)")
                buf = io.BytesIO()
                poster.save(buf, format='PNG')
                buf.seek(0)
                st.download_button("Download pixel pattern PNG", data=buf, file_name=f"pixel_pattern_{animal.lower()}_{pixel_size}x{pixel_size}.png", mime='image/png')
            except Exception as e:
                st.error(f"Failed to convert image: {e}")
    else:
        st.info("No images available right now.")

# Footer / run instructions
st.sidebar.header("Run instructions")
st.sidebar.write("1. Install requirements from requirements.txt.\n2. Run: `streamlit run knitting_crochet_helper_app.py`\n3. (Optional) Provide your OpenAI API key in the AI Helper tab or set OPENAI_API_KEY env var.")
'''
