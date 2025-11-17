# knitting_crochet_helper_app.py (fully updated)
# Streamlit app: Knitting & Crochet Helper (English UI)
# - Sidebar descriptions for each tab
# - Improved Color Combination Helper: keyword -> biased palettes, palette modes, regenerate, CSV preview/download
# - Animal Pattern Design Helper: fixed selection, cat images from TheCatAPI (no text overlay), "See more images", simplified color reduction, CSV preview/download
# - Convert Image to Pattern: upload image -> pixelate -> extract palette -> preview + CSV download

import streamlit as st
import requests
import hashlib
import io
import csv
from PIL import Image, ImageDraw
import numpy as np
import os

# Optional OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

# Clustering for color simplification
try:
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

st.set_page_config(page_title="Knitting & Crochet Helper", layout="wide")

SYSTEM_PROMPT = (
    "You are a master of knitting and crochet. You understand yarn types, stitch techniques, and garment construction. "
    "You teach people how to improve their craft, offering detailed guidance about patterns, texture combinations, "
    "and project planning. Use a warm, encouraging, and patient tone. Give tips about tools, color palettes, "
    "and creative inspiration for both beginners and experienced crafters."
)

# ---------------- Sidebar ----------------
with st.sidebar:
    st.title("Knitting & Crochet Helper")
    st.markdown("**AI Helper**: Ask knitting & crochet questions and get expert guidance via OpenAI (optional API key).")
    st.markdown("**Color Combination Helper**: Enter a keyword, choose a palette mode, and get multiple palette suggestions. Preview and download CSV.")
    st.markdown("**Animal Pattern Design Helper**: Browse dog & cat images, select one, convert to a simplified pixel pattern, and download palette CSV.")
    st.markdown("**Convert Image to Pattern**: Upload any image and convert it into a pixelated pattern with simplified palette and CSV export.")
    st.write('---')
    st.markdown('Developed for knitters & crocheters — palettes and patterns are suggestions; always swatch first!')

# ---------------- Helpers ----------------

def hex_from_rgb(rgb):
    return '#%02x%02x%02x' % tuple(int(x) for x in rgb)

def biased_palette_for_keyword(keyword: str, mode: str, seed_offset: int = 0, n_colors: int = 5):
    """Generate a palette biased by a keyword. For strong color words (e.g., 'yellow'), bias hue."""
    kw = keyword.lower()
    # Simple semantic hue mapping
    hue_map = {
        'red': 0,
        'orange': 30,
        'yellow': 60,
        'green': 120,
        'blue': 210,
        'purple': 270,
        'pink': 330,
        'brown': 30,
        'grey': 0,
        'gray': 0,
        'black': 0,
        'white': 0,
    }

    base_hue = None
    for k, h in hue_map.items():
        if k in kw:
            base_hue = h
            break

    # deterministic random but influenced by keyword
    seed = abs(hash(keyword + str(seed_offset))) % (2**32)
    rng = np.random.RandomState(seed)

    colors = []
    for i in range(n_colors):
        if base_hue is not None:
            # generate around base_hue
            hue = (base_hue + rng.randint(-25, 25)) % 360
            sat = rng.randint(40, 95)
            val = rng.randint(40, 95)
        else:
            hue = rng.randint(0,360)
            sat = rng.randint(30,95)
            val = rng.randint(35,95)

        # Mode adjustments
        if mode == 'pastel':
            sat = int(sat * 0.5)
            val = min(95, int(val * 1.05))
        elif mode == 'vibrant':
            sat = min(100, int(sat * 1.2))
            val = min(100, val)
        elif mode == 'earthy':
            sat = int(sat * 0.7)
            val = int(val * 0.8)
        elif mode == 'monochrome':
            # vary value only
            hue = hue
            sat = int(sat * 0.2)

        # HSV -> RGB
        c = hsv_to_rgb(hue/360.0, sat/100.0, val/100.0)
        colors.append(hex_from_rgb([int(x*255) for x in c]))

    return colors


def hsv_to_rgb(h, s, v):
    # h in [0,1], s in [0,1], v in [0,1]
    if s == 0.0:
        return (v, v, v)
    i = int(h*6.0)
    f = (h*6.0) - i
    p = v*(1.0 - s)
    q = v*(1.0 - s*f)
    t = v*(1.0 - s*(1.0 - f))
    i = i%6
    if i==0:
        return (v,t,p)
    if i==1:
        return (q,v,p)
    if i==2:
        return (p,v,t)
    if i==3:
        return (p,q,v)
    if i==4:
        return (t,p,v)
    if i==5:
        return (v,p,q)

# Palette modes offered
PALETTE_MODES = ['pastel','vibrant','earthy','monochrome','analogous','complementary']

# Fetch images
def fetch_dog_images(limit=12):
    try:
        url = f'https://dog.ceo/api/breeds/image/random/{limit}'
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json().get('message', [])
    except Exception:
        return []

def fetch_cat_images(limit=12):
    # Use TheCatAPI (no API key required for basic requests)
    try:
        url = f'https://api.thecatapi.com/v1/images/search?limit={limit}'
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return [item.get('url') for item in data if item.get('url')]
    except Exception:
        # Fallback to cataas but avoid text overlay by using /cat endpoint without text
        return [f'https://cataas.com/cat?{i}' for i in range(limit)]

# Simplify image colors using KMeans
def extract_palette_from_image(img: Image.Image, n_colors=8):
    img = img.convert('RGB')
    arr = np.array(img)
    h, w, _ = arr.shape
    pixels = arr.reshape((-1,3)).astype(float)
    if not SKLEARN_AVAILABLE:
        # simple fallback: random sample
        rng = np.random.RandomState(0)
        choices = pixels[rng.choice(len(pixels), size=min(n_colors, len(pixels)), replace=False)]
        colors = [tuple(map(int, c)) for c in choices]
        return [(*c, hex_from_rgb(c)) for c in colors]

    # KMeans
    km = KMeans(n_clusters=min(n_colors, len(pixels)), n_init='auto', random_state=0)
    labels = km.fit_predict(pixels)
    centers = km.cluster_centers_.astype(int)
    # count frequency
    counts = np.bincount(labels)
    # sort by frequency desc
    order = np.argsort(-counts)
    palette = []
    for idx in order:
        rgb = tuple(centers[idx])
        palette.append((rgb[0], rgb[1], rgb[2], hex_from_rgb(rgb)))
    return palette

# Convert to pixel pattern (resized to target size then simplified colors)
def convert_to_pixel_pattern_from_image(img: Image.Image, pixel_w: int, pixel_h: int, n_colors: int):
    # crop square center for nicer aspect handling if desired, but we will simply resize to target
    small = img.convert('RGB').resize((pixel_w, pixel_h), resample=Image.BILINEAR)
    # simplify colors by clustering on small image
    palette = extract_palette_from_image(small, n_colors)

    # Map each pixel to nearest palette color
    pal_rgb = np.array([[c[0],c[1],c[2]] for c in palette])
    arr = np.array(small)
    h,w,_ = arr.shape
    flat = arr.reshape((-1,3)).astype(int)
    # compute distances
    dists = np.sqrt(((flat[:,None,:] - pal_rgb[None,:,:])**2).sum(axis=2))
    nearest = dists.argmin(axis=1)
    new_flat = pal_rgb[nearest]
    new_img = new_flat.reshape((h,w,3)).astype(np.uint8)
    poster_cell = 24
    canvas = Image.new('RGB', (w*poster_cell, h*poster_cell), 'white')
    draw = ImageDraw.Draw(canvas)
    for y in range(h):
        for x in range(w):
            col = tuple(new_img[y,x])
            draw.rectangle([x*poster_cell, y*poster_cell, (x+1)*poster_cell, (y+1)*poster_cell], fill=col)
    # draw grid lines
    for i in range(w+1):
        draw.line([(i*poster_cell,0),(i*poster_cell,h*poster_cell)], fill=(0,0,0), width=1)
    for j in range(h+1):
        draw.line([(0,j*poster_cell),(w*poster_cell,j*poster_cell)], fill=(0,0,0), width=1)

    return canvas, palette

# ---------------- UI ----------------
st.title("🧶 Knitting & Crochet Helper")

tabs = st.tabs(["AI Helper", "Color combination helper", "Animal pattern design helper", "Convert image to pattern"])

# ---------------- Tab 1: AI Helper ----------------
with tabs[0]:
    st.header("AI Helper — Knitting & Crochet Expert")
    st.write("Ask craft questions and get friendly, practical guidance.")

    api_key_input = st.text_input("OpenAI API key (optional)", type="password")
    if api_key_input:
        os.environ['OPENAI_API_KEY'] = api_key_input

    if not OPENAI_AVAILABLE:
        st.warning("OpenAI SDK not installed. Install the 'openai' package to use the AI helper.")

    if 'messages' not in st.session_state:
        st.session_state.messages = [{"role":"system","content":SYSTEM_PROMPT}]

    with st.form('ai_form', clear_on_submit=True):
        user_q = st.text_area('Your question', height=120)
        submitted = st.form_submit_button('Send')

    if submitted and user_q.strip():
        st.session_state.messages.append({"role":"user","content":user_q})
        if OPENAI_AVAILABLE:
            try:
                openai.api_key = os.environ.get('OPENAI_API_KEY')
                completion = openai.ChatCompletion.create(
                    model='gpt-4o-mini',
                    messages=st.session_state.messages,
                    max_tokens=600
                )
                reply = completion['choices'][0]['message']['content']
                st.session_state.messages.append({"role":"assistant","content":reply})
            except Exception as e:
                st.error(f"OpenAI error: {e}")
        else:
            st.info('OpenAI not available — this is a UI demo. Install openai and set an API key to enable real replies.')

    for msg in st.session_state.messages[1:]:
        if msg['role']=='user':
            st.markdown(f"**You:** {msg['content']}")
        else:
            st.markdown(f"**Expert:** {msg['content']}")

    if st.button('Clear conversation'):
        st.session_state.messages = [{"role":"system","content":SYSTEM_PROMPT}]
        st.experimental_rerun()

# ---------------- Tab 2: Color combination helper ----------------
with tabs[1]:
    st.header("Color combination helper")
    st.write("Enter a keyword and choose a palette mode. Palettes are biased to the keyword when possible. You can regenerate and download CSV. Preview CSV below.")

    col1, col2, col3 = st.columns([3,2,1])
    with col1:
        keyword = st.text_input("Keyword (e.g. 'yellow', 'autumn sweater')")
    with col2:
        mode = st.selectbox("Palette mode", PALETTE_MODES, index=0)
    with col3:
        regen = st.button('Regenerate palettes')

    if 'palette_seed' not in st.session_state:
        st.session_state['palette_seed'] = 0

    if regen:
        st.session_state['palette_seed'] += 1

    if st.button('Generate palettes') or regen:
        if not keyword.strip():
            st.warning('Please enter a keyword.')
        else:
            # make 3 palette options
            palettes = []
            for i in range(3):
                pal = biased_palette_for_keyword(keyword, mode, seed_offset=st.session_state['palette_seed']+i, n_colors=5)
                palettes.append(pal)
            st.session_state['palettes'] = palettes

    if 'palettes' in st.session_state:
        palettes = st.session_state['palettes']
        # Display palettes and CSV preview
        rows = []
        for idx, pal in enumerate(palettes):
            st.subheader(f"Palette Option {idx+1}")
            cols = st.columns(len(pal))
            for c, col in zip(pal, cols):
                col.markdown(f"<div style='background:{c};padding:28px;border-radius:8px'></div>", unsafe_allow_html=True)
                col.write(c)
            rows.append([f'Option {idx+1}'] + pal)

        # CSV and dataframe
        header = ['Option','Color1','Color2','Color3','Color4','Color5']
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(header)
        for r in rows:
            writer.writerow(r)
        csv_value = csv_buf.getvalue()

        st.download_button('Download palettes CSV', data=csv_value, file_name=f'palettes_{keyword.replace(" ","_")}.csv', mime='text/csv')

        # show dataframe
        import pandas as pd
        df = pd.DataFrame(rows, columns=header)
        st.dataframe(df)

    st.markdown("**Palette Modes (short):**")
    st.markdown("""
**Palette Modes**

- **pastel**: soft, low-saturation colors.
- **vibrant**: bold and strong colors.
- **earthy**: natural, warm organic tones.
- **monochrome**: shades and tints of a single hue.
- **analogous**: colors next to each other on the color wheel.
- **complementary**: colors opposite on the color wheel.
""")


    # Explain input-processing-output for debugging
    if keyword:
        st.markdown('**Debug — keyword processing**')
        st.write(f"Keyword: '{keyword}' → detected hue bias: {', '.join([k for k in ['yellow','red','blue','green','purple','pink','orange','brown'] if k in keyword.lower()]) or 'none (random)'}")

# ---------------- Tab 3: Animal pattern design helper ----------------
with tabs[2]:
    st.header('Animal pattern design helper')
    st.write('Browse dog or cat images, select one, convert to a simplified pixel pattern, and get the palette CSV. Use "See more images" to load more.')

    animal = st.radio('Animal', ['Dog','Cat'])
    see_more = st.button('See more images')
    # maintain images in session state to prevent reordering
    key_imgs = f'img_urls_{animal}'
    if key_imgs not in st.session_state or see_more:
        if animal == 'Dog':
            st.session_state[key_imgs] = fetch_dog_images(limit=12)
        else:
            st.session_state[key_imgs] = fetch_cat_images(limit=12)

    img_urls = st.session_state.get(key_imgs, [])
    img_urls = [url for url in img_urls if not url.lower().endswith(".gif")] #!!

    # Display images and selection buttons in a stable way
    cols = st.columns(3)
    for i, url in enumerate(img_urls):
        col = cols[i%3]
        try:
            col.image(url, width=220)
        except Exception:
            col.write('Failed to load')
        if col.button(f'Select #{i+1}', key=f'select_{animal}_{i}'):
            st.session_state['selected_url'] = url
            st.session_state['selected_index'] = i

    selected_url = st.session_state.get('selected_url', None)
    selected_index = st.session_state.get('selected_index', None)

    if selected_url:
        st.markdown(f"**Selected image (index {selected_index}):** {selected_url}")
        st.image(selected_url, width=360)

        # pixel options
        px_input = st.text_input('Pixel size (width x height)', value='24x24')
        try:
            pw, ph = map(int, px_input.lower().split('x'))
        except Exception:
            pw = ph = 24
        n_colors = st.slider('Number of colors (simplify)', min_value=4, max_value=24, value=8)

        if st.button('Convert to pixel pattern'):
            try:
                r = requests.get(selected_url, timeout=15)
                r.raise_for_status()
                img = Image.open(io.BytesIO(r.content)).convert('RGB')
                poster, palette = convert_to_pixel_pattern_from_image(img, pw, ph, n_colors)
                st.image(poster, caption=f'{pw}x{ph} pixel pattern')
                buf = io.BytesIO()
                poster.save(buf, format='PNG')
                buf.seek(0)
                st.download_button('Download pixel pattern PNG', data=buf.getvalue(), file_name=f'pixel_pattern_{animal}_{selected_index}.png', mime='image/png')

                # Palette CSV and preview
                header = ['R','G','B','Hex']
                csv_buf = io.StringIO()
                writer = csv.writer(csv_buf)
                writer.writerow(header)
                rows = []
                for c in palette:
                    writer.writerow([c[0],c[1],c[2],c[3]])
                    rows.append({'R':c[0],'G':c[1],'B':c[2],'Hex':c[3]})
                csv_val = csv_buf.getvalue()
                st.download_button('Download palette CSV', data=csv_val, file_name=f'palette_{animal}_{selected_index}.csv', mime='text/csv')

                import pandas as pd
                df = pd.DataFrame(rows)
                st.dataframe(df)

            except Exception as e:
                st.error(f'Failed to convert image: {e}')

# ---------------- Tab 4: Convert image to pattern ----------------
with tabs[3]:
    st.header('Convert image to pattern')
    st.write('Upload an image and convert it into a pixelated knitting/crochet pattern. Preview and download CSV of palette.')

    uploaded = st.file_uploader('Upload an image', type=['png','jpg','jpeg'])
    px_input = st.text_input('Pixel size (width x height)', value='30x30', key='conv_px')
    try:
        pw, ph = map(int, px_input.lower().split('x'))
    except Exception:
        pw = ph = 30
    n_colors = st.slider('Number of colors (simplify)', min_value=4, max_value=24, value=10, key='conv_colors')

    if uploaded and st.button('Generate pattern'):
        try:
            img = Image.open(uploaded).convert('RGB')
            poster, palette = convert_to_pixel_pattern_from_image(img, pw, ph, n_colors)
            st.image(poster, caption=f'{pw}x{ph} pixel pattern')

            buf = io.BytesIO()
            poster.save(buf, format='PNG')
            buf.seek(0)
            st.download_button('Download pattern PNG', data=buf.getvalue(), file_name='custom_pattern.png', mime='image/png')

            header = ['R','G','B','Hex']
            csv_buf = io.StringIO()
            writer = csv.writer(csv_buf)
            writer.writerow(header)
            rows = []
            for c in palette:
                writer.writerow([c[0],c[1],c[2],c[3]])
                rows.append({'R':c[0],'G':c[1],'B':c[2],'Hex':c[3]})
            csv_val = csv_buf.getvalue()
            st.download_button('Download palette CSV', data=csv_val, file_name='custom_palette.csv', mime='text/csv')

            import pandas as pd
            df = pd.DataFrame(rows)
            st.dataframe(df)

        except Exception as e:
            st.error(f'Error generating pattern: {e}')

# ---------------- Requirements ----------------
# Save the following lines into requirements.txt for full functionality:
# streamlit
# requests
# pillow
# numpy
# scikit-learn
# openai  # optional for AI Helper
# pandas

# End of file
