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
import colorsys
import random
import requests

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
    st.title("🧶 Knitting & Crochet Helper 🧣")
    st.markdown("**🤖 AI Helper**: Ask knitting & crochet questions and get expert guidance via OpenAI (optional API key).")
    st.markdown("**🎨 Color Combination Helper**: Enter a keyword, choose a palette mode, and get multiple palette suggestions. Preview and download CSV.")
    st.markdown("**🐶🐱 Animal Pattern Design Helper**: Browse dog & cat images, select one, convert to a simplified pixel pattern, and download palette CSV.")
    st.markdown("**🏞️ Convert Image to Pattern**: Upload any image and convert it into a pixelated pattern with simplified palette and CSV export.")
    st.write('---')
    st.markdown('Developed for knitters & crocheters — palettes and patterns are suggestions;  ‼️ always **swatch** first ‼️')

# ---------------- Helpers ----------------

def hex_from_rgb(rgb):
    return '#%02x%02x%02x' % tuple(int(x) for x in rgb)

def biased_palette_for_keyword(keyword: str, mode: str, seed_offset: int = 0, n_colors: int = 5):
    """Generate a palette biased by a keyword. For strong color words (e.g., 'yellow'), bias hue."""
    import colorsys
    COLOR_KEYWORDS = {
    "yellow": 50/360,
    "red": 0/360,
    "blue": 220/360,
    "green": 120/360,
    "purple": 280/360,
    "pink": 330/360,
    "orange": 30/360,
    "brown": 30/360,
    }

    def fetch_colorapi_palette(keyword_hex: str, mode: str, count: int = 5):
    """
    Fetch palette from TheColorAPI. No API key required.
    keyword_hex: e.g., "FFD700"
    mode: monochrome, analogic, complement, triad, quad
    """
        url = f"https://www.thecolorapi.com/scheme?hex={keyword_hex}&mode={mode}&count={count}"
        try:
            resp = requests.get(url, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                return [c["hex"]["value"] for c in data.get("colors", [])]
        except:
            pass
        return None


    def hex_from_hue(h: float) -> str:
        r, g, b = colorsys.hsv_to_rgb(h, 1, 1)
        return f"{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"


    def biased_palette_for_keyword(keyword: str, mode: str, seed_offset: int = 0, n_colors: int = 5):
    """
    MIXED MODE:
    1) Keyword bias → hue 기반 내부 팔레트 생성
    2) TheColorAPI 팔레트 하나 생성
    3) 내부 팔레트 + API 팔레트 → 섞어서 최종 팔레트 생성
    """
        random.seed(seed_offset + hash(keyword) % 99999)
        keyword_lower = keyword.lower()

    # ---- 1) Keyword hue bias detection ----
        hue_base = None
        for k, hv in COLOR_KEYWORDS.items():
            if k in keyword_lower:
                hue_base = hv
                break

    # fallback: random hue
        if hue_base is None:
            hue_base = random.random()

    # ---- 2) Internal algorithm palette ----
        palette_internal = []
        for _ in range(n_colors):
            h = (hue_base + random.uniform(-0.05, 0.05)) % 1.0
            if mode == "pastel":
                s, v = random.uniform(0.2, 0.5), random.uniform(0.85, 1.0)
            elif mode == "vibrant":
                s, v = random.uniform(0.7, 1.0), random.uniform(0.8, 1.0)
            elif mode == "earthy":
                s, v = random.uniform(0.4, 0.7), random.uniform(0.5, 0.8)
            elif mode == "monochrome":
                s, v = 0.0, random.uniform(0.4, 1.0)
            else:
                s, v = random.random(), random.random()

            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            palette_internal.append(f"#{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}")

    # ---- 3) Try fetching TheColorAPI palette ----
        keyword_hex = hex_from_hue(hue_base).replace("#", "")
        colorapi_modes = {
            "pastel": "analogic",
            "vibrant": "complement",
            "earthy": "quad",
            "monochrome": "monochrome"
            }
        colorapi_mode = colorapi_modes.get(mode, "analogic")

        palette_api = fetch_colorapi_palette(keyword_hex, colorapi_mode, count=n_colors)

    # ---- 4) Mix palettes (fallback-safe) ----
        if palette_api:
            combined = []
            for i in range(n_colors):
                if i % 2 == 0:
                    combined.append(palette_internal[i])
                else:
                    combined.append(palette_api[i])
            return combined

    # fallback: API failed → return internal palette only
        return palette_internal

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
PALETTE_MODES = ['pastel','vibrant','earthy','monochrome']

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

tabs = st.tabs(["🤖 AI Helper", "🎨 Color combination helper", "🐶🐱 Animal pattern design helper", "🏞️ Convert image to pattern"])

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
            palettes = []
            for i in range(3):
                pal = biased_palette_for_keyword(keyword, mode, seed_offset=st.session_state['palette_seed']+i, n_colors=5)
                palettes.append(pal)
            st.session_state['palettes'] = palettes

    if 'palettes' in st.session_state:
        palettes = st.session_state['palettes']
        rows = []
        for idx, pal in enumerate(palettes):
            st.subheader(f"Palette Option {idx+1}")
            cols = st.columns(len(pal))
            for c, col in zip(pal, cols):
                col.markdown(f"<div style='background:{c};padding:28px;border-radius:8px'></div>", unsafe_allow_html=True)
                col.write(c)
            rows.append([f'Option {idx+1}'] + pal)

        # CSV
        header = ['Option','Color1','Color2','Color3','Color4','Color5']
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(header)
        for r in rows:
            writer.writerow(r)
        csv_value = csv_buf.getvalue()

        st.download_button('Download palettes CSV', data=csv_value, file_name=f'palettes_{keyword.replace(" ","_")}.csv', mime='text/csv')

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
""")

    # Debug info
    if keyword:
        st.markdown('**Debug — keyword processing**')
        st.write(f"Keyword: '{keyword}' → detected hue bias: {', '.join([k for k in ['yellow','red','blue','green','purple','pink','orange','brown'] if k in keyword.lower()]) or 'none (random)'}")

    # ---------------------------------------------------------
    # ⭐ NEW FEATURE — Random Pattern Poster Generator
    # ---------------------------------------------------------
    st.subheader("Generate Pattern Poster from Palette")

    if 'palettes' in st.session_state:
        palettes = st.session_state['palettes']

        # Choose palette
        chosen_index = st.selectbox(
            "Choose one palette to use for pattern generation",
            options=list(range(len(palettes))),
            format_func=lambda x: f"Palette Option {x+1}"
        )
        chosen_palette = palettes[chosen_index]

        # Initialize edited palette in session state
        palette_key = f'edited_palette_{chosen_index}'
        if palette_key not in st.session_state:
            st.session_state[palette_key] = chosen_palette.copy()

        st.write("Editable palette (you can add/remove/change colors):")
        import pandas as pd
        
        # Create DataFrame
        editable_df = pd.DataFrame({"color": st.session_state[palette_key]})
        
        # Simple data editor without ColorColumn (for older Streamlit versions)
        edited_df = st.data_editor(
            editable_df, 
            num_rows="dynamic",
            hide_index=False,
            use_container_width=True
        )
        
        # Update session state
        st.session_state[palette_key] = edited_df['color'].tolist()

        # Color preview with inline color picker for each color
        st.write("Preview & Edit Colors:")
        if len(edited_df) > 0:
            for idx, color in enumerate(edited_df['color']):
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    st.markdown(f"<div style='background:{color};padding:20px;border-radius:6px;border:1px solid #ddd'></div>", unsafe_allow_html=True)
                with col2:
                    st.text(color)
                with col3:
                    # Individual color picker for each color
                    new_color = st.color_picker(f"Edit", value=color, key=f"picker_{chosen_index}_{idx}")
                    if new_color != color:
                        st.session_state[palette_key][idx] = new_color
                        st.rerun()

        # Add new color section
        st.write("---")
        with st.expander("➕ Add New Color"):
            new_color = st.color_picker("Pick a color to add", value="#5DADE2", key=f"new_color_{chosen_index}")
            if st.button("Add to palette", key=f"add_btn_{chosen_index}"):
                st.session_state[palette_key].append(new_color)
                st.success(f"Added {new_color} ✅")
                st.rerun()

        # Pattern options
        st.write("---")
        pattern_type = st.selectbox("Pattern type", ["random", "stripe", "heart", "star", "circle"])
        generate_pattern = st.button("Generate pattern")

        if generate_pattern:
            import numpy as np
            from PIL import Image, ImageDraw
            import random

            # 격자 설정
            grid_size = 30
            cell_size = 20
            colors_list = st.session_state[palette_key]
            
            if len(colors_list) == 0:
                st.warning("Please add at least one color to the palette.")
            else:
                # ======================= MASK 정의 =======================
                HEART_MASK_7 = [
                    [0,0,1,0,1,0,0],
                    [0,1,1,0,1,1,0],
                    [1,1,1,1,1,1,1],
                    [1,1,1,1,1,1,1],
                    [0,1,1,1,1,1,0],
                    [0,0,1,1,1,0,0],
                    [0,0,0,1,0,0,0],
                ]
                STAR_MASK_7 = [
                    [0,0,0,1,0,0,0],
                    [0,0,0,1,0,0,0],
                    [1,1,1,1,1,1,1],
                    [0,0,1,1,1,0,0],
                    [0,1,1,1,1,1,0],
                    [1,0,0,0,0,0,1],
                    [0,0,0,0,0,0,0]
                ]
                CIRCLE_MASK_7 = [
                    [0,0,1,1,1,0,0],
                    [0,1,1,1,1,1,0],
                    [1,1,1,1,1,1,1],
                    [1,1,1,1,1,1,1],
                    [1,1,1,1,1,1,1],
                    [0,1,1,1,1,1,0],
                    [0,0,1,1,1,0,0]
                ]

                # 캔버스 생성 (배경색은 첫 번째 색상)
                bg_color = colors_list[0]
                img = Image.new("RGB", (grid_size*cell_size, grid_size*cell_size), bg_color)
                draw = ImageDraw.Draw(img)

                # 패턴별 로직
                if pattern_type == "stripe":
                    # 각 가로줄마다 순환하며 색상 할당 (모든 색상 사용)
                    for row in range(grid_size):
                        row_color = colors_list[row % len(colors_list)]
                        for col in range(grid_size):
                            x0, y0 = col*cell_size, row*cell_size
                            x1, y1 = x0+cell_size, y0+cell_size
                            draw.rectangle([x0,y0,x1,y1], fill=row_color)

                elif pattern_type == "random":
                    # 셔플된 색상 리스트를 반복 사용 (모든 색상 균등하게)
                    total_cells = grid_size * grid_size
                    shuffled_colors = colors_list * (total_cells // len(colors_list) + 1)
                    random.shuffle(shuffled_colors)
                    idx = 0
                    for row in range(grid_size):
                        for col in range(grid_size):
                            x0, y0 = col*cell_size, row*cell_size
                            x1, y1 = x0+cell_size, y0+cell_size
                            cell_color = shuffled_colors[idx]
                            draw.rectangle([x0,y0,x1,y1], fill=cell_color)
                            idx += 1

                elif pattern_type in ["heart", "star", "circle"]:
                    if pattern_type == "heart":
                        mask = HEART_MASK_7
                    elif pattern_type == "star":
                        mask = STAR_MASK_7
                    else:
                        mask = CIRCLE_MASK_7
                    
                    mask_h = len(mask)
                    mask_w = len(mask[0])
                    
                    # 🎨 배경색 랜덤 선택 (generate할 때마다 다르게)
                    bg_color = random.choice(colors_list)
                    
                    # 배경 먼저 채우기
                    for row in range(grid_size):
                        for col in range(grid_size):
                            x0, y0 = col*cell_size, row*cell_size
                            x1, y1 = x0+cell_size, y0+cell_size
                            draw.rectangle([x0,y0,x1,y1], fill=bg_color)
                    
                    # 🎯 도형 개수를 팔레트 색상 개수에 맞춤
                    num_shapes = max(len(colors_list), 10)
                    placed_positions = []
                    max_attempts = 200
                    attempts = 0
                    
                    # 배경색을 제외한 나머지 색상들로 순환
                    available_colors = [c for c in colors_list if c != bg_color]
                    if not available_colors:  # 모든 색상이 같은 경우
                        available_colors = colors_list
                    shape_color_idx = 0
                    
                    while len(placed_positions) < num_shapes and attempts < max_attempts:
                        attempts += 1
                        start_row = random.randint(0, grid_size - mask_h)
                        start_col = random.randint(0, grid_size - mask_w)
                        
                        overlaps = False
                        for prev_row, prev_col in placed_positions:
                            if not (start_row + mask_h <= prev_row or 
                                   start_row >= prev_row + mask_h or
                                   start_col + mask_w <= prev_col or 
                                   start_col >= prev_col + mask_w):
                                overlaps = True
                                break
                        
                        if not overlaps:
                            placed_positions.append((start_row, start_col))
                            
                            # 순환 방식으로 색상 선택 (배경 제외)
                            shape_color = available_colors[shape_color_idx % len(available_colors)]
                            shape_color_idx += 1
                            
                            for mask_row in range(mask_h):
                                for mask_col in range(mask_w):
                                    if mask[mask_row][mask_col] == 1:
                                        actual_row = start_row + mask_row
                                        actual_col = start_col + mask_col
                                        if 0 <= actual_row < grid_size and 0 <= actual_col < grid_size:
                                            x0 = actual_col * cell_size
                                            y0 = actual_row * cell_size
                                            x1 = x0 + cell_size
                                            y1 = y0 + cell_size
                                            draw.rectangle([x0,y0,x1,y1], fill=shape_color)
                # 격자선 그리기 
                for i in range(grid_size+1):
                    draw.line([(i*cell_size, 0), (i*cell_size, grid_size*cell_size)], fill=(0,0,0), width=1)
                    draw.line([(0, i*cell_size), (grid_size*cell_size, i*cell_size)], fill=(0,0,0), width=1)

                st.image(img, caption=f"Generated {pattern_type.title()} Pattern (30x30)", use_column_width=True)

                buf = io.BytesIO()
                img.save(buf, format="PNG")
                st.download_button("Download pattern image", data=buf.getvalue(), file_name=f"pattern_{pattern_type}.png", mime="image/png")

                # Pattern Palette CSV (가로 형식)
                st.write("---")
                st.write("**Pattern Colors Used:**")
                
                all_colors = colors_list
                color_columns = {f'Color{i+1}': color for i, color in enumerate(all_colors)}
                pattern_df = pd.DataFrame([color_columns])
                
                color_preview_cols = st.columns(len(all_colors))
                for idx, (col, color) in enumerate(zip(color_preview_cols, all_colors)):
                    col.markdown(f"<div style='background:{color};padding:28px;border-radius:6px;border:1px solid #ddd'></div>", unsafe_allow_html=True)
                    col.write(color)
                
                csv_buf = io.StringIO()
                pattern_df.to_csv(csv_buf, index=False)
                csv_value = csv_buf.getvalue()
                
                st.download_button(
                    'Download pattern colors CSV', 
                    data=csv_value, 
                    file_name=f'pattern_{pattern_type}_colors.csv', 
                    mime='text/csv'
                )
                
                st.dataframe(pattern_df, use_container_width=True)
                
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
        n_colors = st.slider('Number of colors (simplify)', min_value=2, max_value=30, value=10)

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
    n_colors = st.slider('Number of colors (simplify)', min_value=2, max_value=30, value=10, key='conv_colors')

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
