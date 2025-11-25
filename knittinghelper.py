# knitting_crochet_helper_app.py (fully updated)
# Streamlit app: Knitting & Crochet Helper (English UI)
# - Sidebar descriptions for each tab
# - Improved Color Combination Helper: keyword -> biased palettes, palette modes, regenerate, CSV preview/download
# - Animal Pattern Design Helper: fixed selection, cat images from TheCatAPI (no text overlay), "See more images", simplified color reduction, CSV preview/download
# - Convert Image to Pattern: upload image -> pixelate -> extract palette -> preview + CSV download

import streamlit as st
import pandas as pd
import requests
import hashlib
import io
import csv
from PIL import Image, ImageDraw
import numpy as np
import os
import json

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

def extract_colors_from_keyword_with_hf(keyword: str):
    """
    1단계: Hugging Face Zero-Shot Classification으로 색상 추출
    BART 모델 사용 (무료, API key 불필요)
    """
    API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
    
    # 확장된 색상 리스트
    colors = [
        'red', 'orange', 'yellow', 'green', 'blue', 'purple', 
        'pink', 'brown', 'white', 'black', 'grey', 'turquoise',
        'gold', 'silver', 'violet', 'cyan', 'lime', 'indigo'
    ]
    
    try:
        response = requests.post(
            API_URL,
            headers={},  # API key 불필요
            json={
                "inputs": keyword,
                "parameters": {
                    "candidate_labels": colors
                }
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            # 신뢰도 30% 이상인 상위 3개 색상 반환
            top_colors = []
            for label, score in zip(result['labels'], result['scores']):
                if score > 0.3:  # 신뢰도 임계값
                    top_colors.append(label)
                if len(top_colors) >= 3:
                    break
            
            if top_colors:
                print(f"✅ HF API detected colors for '{keyword}': {top_colors} (scores: {[f'{s:.2f}' for s in result['scores'][:len(top_colors)]]})")
                return top_colors
        
        return None
            
    except Exception as e:
        print(f"⚠️ HF API error: {e}")
        return None


def biased_palette_for_keyword_3tier(keyword: str, mode: str, seed_offset: int = 0, n_colors: int = 5):
    """
    3단계 Fallback 시스템으로 키워드 기반 팔레트 생성
    복합 키워드 지원: "tropical summer ocean" → 각 단어에서 색상 추출
    
    1단계: Hugging Face API (AI 기반 색상 추출)
    2단계: 확장된 의미 사전 (100+ 키워드)
    3단계: 기본 색상 매핑 (직접 색상명)
    """
    kw = keyword.lower()
    
    # 색상 이름 -> Hue 값 매핑
    color_hue_map = {
        'red': 0, 'orange': 30, 'yellow': 60, 'green': 120,
        'blue': 210, 'purple': 270, 'pink': 330, 'brown': 30,
        'grey': 0, 'gray': 0,
        'violet': 280, 'turquoise': 180, 'gold': 45, 'silver': 0,
        'cyan': 180, 'magenta': 300, 'lime': 80, 'indigo': 250
    }
    
    # ✨ white/black은 특별 처리 (무채색)
    achromatic_colors = ['white', 'black']
    
    # 의미 사전
    semantic_color_map = {
        # 자연/환경
        'forest': [120, 140, 100], 'jungle': [120, 140, 80],
        'ocean': [200, 210, 220], 'sea': [200, 210, 180],
        'mountain': [120, 210, 30], 'desert': [40, 50, 30],
        'sky': [210, 200], 'sunset': [0, 20, 40, 350],
        'sunrise': [20, 40, 60], 'beach': [180, 200, 60],
        'tropical': [150, 330, 30], 'arctic': [180, 200, 0],
        'savanna': [45, 60, 30], 'lake': [200, 210, 120],
        'river': [200, 180, 120], 'meadow': [100, 120, 80],
        'garden': [100, 120, 330], 'park': [120, 80, 200],
        
        # 계절
        'spring': [80, 120, 330, 60], 'summer': [60, 200, 50, 180],
        'autumn': [20, 30, 40, 10], 'fall': [20, 30, 40, 10],
        'winter': [200, 210, 0, 180],
        
        # 시간대
        'dawn': [20, 330, 200, 280], 'morning': [60, 200, 50],
        'noon': [60, 180, 50], 'afternoon': [45, 30, 200],
        'dusk': [270, 20, 340, 280], 'evening': [270, 340, 210],
        'midnight': [240, 260, 0, 280], 'night': [240, 260, 210],
        
        # 음식
        'cherry': [350, 0], 'strawberry': [350, 330], 'berry': [320, 340, 350],
        'apple': [0, 120, 60], 'orange': [30, 40], 'lemon': [55, 65],
        'lime': [80, 100], 'mint': [140, 160, 150], 'basil': [120, 140],
        'chocolate': [20, 30, 25], 'coffee': [25, 30, 20], 'mocha': [25, 30],
        'vanilla': [50, 60, 40], 'caramel': [35, 45], 'honey': [45, 55],
        'lavender': [260, 280, 270], 'rose': [350, 330, 340],
        'cinnamon': [25, 35], 'pumpkin': [30, 40], 'blueberry': [240, 250],
        'grape': [270, 280], 'peach': [20, 330, 40],
        
        # 꽃
        'sunflower': [50, 60, 45], 'daisy': [60, 50, 90],
        'tulip': [350, 330, 60, 340], 'orchid': [280, 290, 330],
        'jasmine': [60, 50, 80], 'hibiscus': [350, 330],
        'magnolia': [330, 50, 280], 'peony': [330, 340, 350],
        'iris': [270, 280, 240], 'lily': [60, 50, 330],
        
        # 보석/금속
        'ruby': [350, 0, 340], 'emerald': [140, 150, 130],
        'sapphire': [220, 230, 240], 'amethyst': [270, 280, 290],
        'topaz': [40, 50, 45], 'pearl': [50, 0, 330],
        'diamond': [180, 200, 0], 'jade': [150, 140, 160],
        'opal': [180, 330, 270], 'coral': [10, 20, 350],
        
        # 감정/분위기
        'calm': [200, 210, 180], 'peaceful': [150, 180, 210],
        'energetic': [0, 50, 60, 30], 'vibrant': [0, 330, 60],
        'cozy': [20, 30, 10, 40], 'warm': [0, 20, 40, 30],
        'cool': [180, 200, 220, 210], 'fresh': [150, 120, 80, 180],
        'romantic': [330, 340, 350, 320], 'elegant': [0, 270, 330],
        'vintage': [30, 40, 200, 25], 'retro': [40, 200, 330],
        'modern': [0, 200, 0, 210], 'minimal': [0, 200, 210],
        'rustic': [30, 40, 120], 'industrial': [0, 210, 30],
        'bohemian': [30, 330, 280, 120], 'luxury': [280, 45, 0],
        
        # 재료/텍스처
        'wool': [40, 50, 30, 0], 'cotton': [50, 60, 200, 180],
        'silk': [330, 270, 50, 280], 'linen': [60, 50, 120],
        'denim': [210, 220, 200], 'leather': [30, 20, 25],
        'suede': [40, 30, 280], 'velvet': [270, 280, 0],
        'cashmere': [330, 280, 50], 'tweed': [30, 120, 40],
        
        # 날씨
        'rainy': [200, 210, 0, 180], 'sunny': [50, 60, 180, 200],
        'cloudy': [0, 200, 210, 180], 'snowy': [180, 200, 0, 210],
        'stormy': [240, 0, 210, 260], 'foggy': [0, 200, 180],
        'misty': [180, 200, 150], 'breezy': [180, 200, 120],
        
        # 도시/장소
        'paris': [0, 330, 30, 210], 'tokyo': [350, 330, 0, 270],
        'london': [0, 210, 30], 'newyork': [0, 210, 60],
        'miami': [180, 330, 30], 'hawaii': [150, 330, 200],
        'bali': [120, 330, 30], 'santorini': [210, 50, 330],
        'morocco': [30, 350, 280], 'provence': [270, 60, 120],
        
        # 예술/스타일
        'watercolor': [200, 330, 120, 280], 'pastel': [330, 200, 60],
        'neon': [330, 180, 60, 280], 'monochrome': [0, 210, 240],
        'rainbow': [0, 60, 120, 180, 240, 300],
    }
    
    # ============================================
    # 🆕 복합 키워드 분석
    # ============================================
    words = kw.split()
    matched_keywords = []
    all_hues = []
    
    # 각 단어별로 색상 매칭 시도
    for word in words:
        word_hues = []
        word_method = None
        
        # 1단계: HF API (전체 키워드로 한 번만)
        if len(matched_keywords) == 0:
            detected_colors = extract_colors_from_keyword_with_hf(keyword)
            if detected_colors:
                for color in detected_colors[:2]:  # 상위 2개만
                    if color in color_hue_map:
                        word_hues.append(color_hue_map[color])
                if word_hues:
                    word_method = "🤗 AI"
        
        # 2단계: 의미 사전
        if not word_hues:
            for key, hues in semantic_color_map.items():
                if key in word:
                    word_hues = hues[:2]  # 각 단어당 최대 2개
                    word_method = f"📚 '{key}'"
                    break
        
        # 3단계: 직접 색상명
        if not word_hues:
            for color, hue in color_hue_map.items():
                if color in word:
                    word_hues = [hue]
                    word_method = f"🎨 '{color}'"
                    break
        
        if word_hues:
            matched_keywords.append({
                'word': word,
                'hues': word_hues,
                'method': word_method
            })
            all_hues.extend(word_hues)
    
    # 매칭된 키워드가 없으면 전체를 하나로 처리
    if not matched_keywords:
        # 원래 로직 (단일 키워드)
        for key, hues in semantic_color_map.items():
            if key in kw:
                all_hues = hues
                matched_keywords.append({'word': keyword, 'hues': hues, 'method': f"📚 '{key}'"})
                break
    
    # 여전히 없으면 랜덤
    detection_method = None
    if matched_keywords:
        methods_str = " + ".join([m['method'] for m in matched_keywords])
        detection_method = f"🔍 Multi-keyword: {methods_str}"
    else:
        detection_method = "🎲 Random (no match found)"
    
    # ============================================
    # 팔레트 생성
    # ============================================
    seed = abs(hash(keyword + str(seed_offset))) % (2**32)
    rng = np.random.RandomState(seed)
    
    colors = []
    
    # 🌈 레인보우 키워드 체크
    is_rainbow = 'rainbow' in kw
    
    # 🎨 무채색 키워드 체크
    is_white = 'white' in kw
    is_black = 'black' in kw
    is_gray = 'gray' in kw or 'grey' in kw
    
    if is_rainbow:
        # 🌈 무지개 팔레트: 고른 색조 분포
        rainbow_hues = [0, 60, 120, 180, 240, 300]  # 빨, 주황, 노랑, 초록, 파랑, 보라
        
        for i in range(n_colors):
            # 무지개 색조를 순환하며 선택
            base_hue = rainbow_hues[i % len(rainbow_hues)]
            # 약간의 변화 추가
            hue = (base_hue + rng.randint(-10, 10)) % 360
            
            # 선명한 색상
            sat = rng.randint(70, 100)
            val = rng.randint(70, 100)
            
            # Mode adjustments
            if mode == 'normal':
                pass
            elif mode == 'pastel':
                sat = int(sat * 0.5)
                val = min(95, int(val * 1.05))
            elif mode == 'vibrant':
                sat = min(100, int(sat * 1.2))
                val = min(100, val)
            elif mode == 'earthy':
                sat = int(sat * 0.7)
                val = int(val * 0.8)
            elif mode == 'monochrome':
                sat = int(sat * 0.2)
            
            c = hsv_to_rgb(hue/360.0, sat/100.0, val/100.0)
            colors.append(hex_from_rgb([int(x*255) for x in c]))
        
        detection_method = "🌈 Rainbow spectrum"
    
    elif is_white or is_black or is_gray:
        # 무채색 팔레트 생성
        for i in range(n_colors):
            hue = 0  # 색조 무관
            sat = 0  # 채도 0 (무채색)
            
            if is_white:
                # 밝은 회색~흰색
                val = rng.randint(85, 100)
            elif is_black:
                # 검정~어두운 회색
                val = rng.randint(0, 30)
            else:  # gray
                # 중간 회색
                val = rng.randint(40, 70)
            
            c = hsv_to_rgb(hue/360.0, sat/100.0, val/100.0)
            colors.append(hex_from_rgb([int(x*255) for x in c]))
        
        detection_method = f"⚪ Achromatic ('{kw}')"
    
    elif all_hues:
        # 매칭된 색조들을 사용하되, 더 큰 변화 추가
        hue_variation = 20 + (seed_offset % 3) * 10  # 20, 30, 40도 변화
        
        for i in range(n_colors):
            base_hue = all_hues[i % len(all_hues)]
            # 변화 범위를 동적으로 조정
            hue = (base_hue + rng.randint(-hue_variation, hue_variation)) % 360
            
            # 채도와 명도도 더 다양하게
            sat = rng.randint(40, 100)
            val = rng.randint(40, 100)
            
            # Mode adjustments
            if mode == 'normal':
                pass
            elif mode == 'pastel':
                sat = int(sat * 0.5)
                val = min(95, int(val * 1.05))
            elif mode == 'vibrant':
                sat = min(100, int(sat * 1.2))
                val = min(100, val)
            elif mode == 'earthy':
                sat = int(sat * 0.7)
                val = int(val * 0.8)
            elif mode == 'monochrome':
                sat = int(sat * 0.2)
            
            c = hsv_to_rgb(hue/360.0, sat/100.0, val/100.0)
            colors.append(hex_from_rgb([int(x*255) for x in c]))
    
    else:
        # 랜덤 생성
        for i in range(n_colors):
            hue = rng.randint(0, 360)
            sat = rng.randint(30, 100)
            val = rng.randint(35, 100)
            
            if mode == 'normal':
                pass
            elif mode == 'pastel':
                sat = int(sat * 0.5)
                val = min(95, int(val * 1.05))
            elif mode == 'vibrant':
                sat = min(100, int(sat * 1.2))
                val = min(100, val)
            elif mode == 'earthy':
                sat = int(sat * 0.7)
                val = int(val * 0.8)
            elif mode == 'monochrome':
                sat = int(sat * 0.2)
            
            c = hsv_to_rgb(hue/360.0, sat/100.0, val/100.0)
            colors.append(hex_from_rgb([int(x*255) for x in c]))
    
    # 디버그 정보
    if detection_method:
        print(f"Detection: {detection_method} for keyword '{keyword}'")
    
    return colors, detection_method
    
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
PALETTE_MODES = ['normal','pastel','vibrant','earthy','monochrome']

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
def convert_to_pixel_pattern_from_image(img: Image.Image, pixel_w: int, pixel_h: int, n_colors: int, color_mode="color"):
    # crop square center for nicer aspect handling if desired, but we will simply resize to target
    if color_mode == "achromatic":
        img = img.convert("L").convert("RGB")

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
                # ✅ 새로운 OpenAI API (v1.0.0+)
                from openai import OpenAI
                client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
                
                completion = client.chat.completions.create(
                    model='gpt-4o-mini',
                    messages=st.session_state.messages,
                    max_tokens=600
                )
                reply = completion.choices[0].message.content
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
        st.rerun()

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

    # Tab 2에서 팔레트 생성 부분 수정:

    if st.button('Generate palettes') or regen:
        if not keyword.strip():
            st.warning('Please enter a keyword.')
        else:
            palettes = []
            methods = []
            for i in range(3):
                # 🆕 각 옵션마다 더 큰 변화를 주기 위해 seed 값 크게 증가
                pal, method = biased_palette_for_keyword_3tier(
                    keyword, 
                    mode, 
                    seed_offset=st.session_state['palette_seed'] * 100 + i * 1000,  # ⭐ 변경
                    n_colors=5
                )
                palettes.append(pal)
                methods.append(method)
            
            st.session_state['palettes'] = palettes
            st.session_state['palette_methods'] = methods

# 팔레트 표시 부분에 감지 방법 추가:
    if 'palettes' in st.session_state:
        palettes = st.session_state['palettes']
        methods = st.session_state.get('palette_methods', [None] * len(palettes))
        rows = []
        
        for idx, pal in enumerate(palettes):
            st.subheader(f"Palette Option {idx+1}")
            
            # 감지 방법 표시
            if idx < len(methods) and methods[idx]:
                st.caption(f"🔍 Detection: {methods[idx]}")
            
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

- **normal**: balanced, natural colors without adjustment.
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
        # --- Tap2: palette editor ---

        if "palette" not in st.session_state:
            st.session_state.palette = []

        df = pd.DataFrame({
            "index": list(range(len(st.session_state.palette))),
            "color": st.session_state.palette
        })
        edited_df = st.data_editor(
            df,
            key="palette_editor_table",
            hide_index=True,
            num_rows="dynamic"
        )

# 데이터 반영
        st.session_state.palette = edited_df["color"].tolist()

        # ▶ 색 미리보기 컬럼 만들기 (HTML)
        def color_preview(hexcode):
            return f"""<div style="width:40px; height:20px; background:{hexcode}; border-radius:4px;"></div>"""

        df["preview"] = df["color"].apply(color_preview)

        # ▶ Edit 버튼 만들기 (각 행마다 고유 key 필요)
        def edit_button(i):
            return st.button("Edit", key=f"edit_{i}")

        edited_df = st.data_editor(
            df,
            column_config={
                "index": st.column_config.NumberColumn("No.", width="small", disabled=True),
                "color": st.column_config.TextColumn("Color Hex"),
                "preview": st.column_config.Column(
                    "Preview",
                    help="Color preview",
                    width="small",
                    disabled=True
                ),
            },
            hide_index=True,
            use_container_width=True,
            unsafe_allow_html=True,
        )

# =========================
# Edit 버튼 처리
# =========================
        for i in range(len(df)):
            cols = st.columns([8, 1])
            with cols[0]:
                pass
            with cols[1]:
                if st.button("Edit", key=f"edit_color_{i}"):
                    new_hex = st.color_picker(f"Select new color for {df.color[i]}", df.color[i], key=f"picker_{i}")
                    st.session_state.palette[i] = new_hex
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

        color_mode = st.selectbox(
            "Color mode",
            ["color", "achromatic"],
            index=0,
            key="animal_color_mode"
        )


        if st.button('Convert to pixel pattern'):
            try:
                r = requests.get(selected_url, timeout=15)
                r.raise_for_status()
                img = Image.open(io.BytesIO(r.content)).convert('RGB')
                poster, palette = convert_to_pixel_pattern_from_image(img, pw, ph, n_colors, color_mode)
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
    
    color_mode = st.selectbox(
        "Color mode",
        ["color", "achromatic"],
        index=0,
        key="convert_color_mode"
    )

    if uploaded and st.button('Generate pattern'):
        try:
            img = Image.open(uploaded).convert('RGB')
            poster, palette = convert_to_pixel_pattern_from_image(img, pw, ph, n_colors, color_mode)
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
