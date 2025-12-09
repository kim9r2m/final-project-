# 🧶 Knitting Pattern Designer

A Streamlit-based knitting and crochet pattern design tool with AI-powered assistance, intelligent color palette generation, and image-to-pattern conversion capabilities.

## 📋 Overview

This application provides comprehensive tools for knitting and crochet enthusiasts, featuring:
- AI-powered knitting/crochet expert chatbot
- Intelligent keyword-based color palette generation
- Animal image to pixel pattern conversion
- Custom image to pattern conversion
- CSV export for all color palettes and patterns

## 🚀 Features

### 🤖 Tab 1: AI Helper

**Knitting & Crochet Expert Chatbot**

Get professional guidance on knitting and crochet techniques, patterns, and project planning through an AI assistant powered by OpenAI GPT-4.

#### Key Components
- Expert persona configuration via system prompt
- Persistent conversation history
- OpenAI API integration

#### How It Works
1. Enter your OpenAI API key
2. Ask knitting/crochet-related questions
3. Receive expert guidance from GPT-4
4. Conversation history is maintained throughout the session
5. Reset conversation anytime with the clear button

---

### 🎨 Tab 2: Color Combination Helper

**Intelligent Keyword-Based Palette Generation**

Generate color palettes based on keywords using a sophisticated 3-tier fallback system, with support for multiple palette modes and pattern poster creation.

#### Core Features

**3-Tier Color Extraction System**
1. **AI-Based** - Hugging Face Zero-Shot Classification API
2. **Semantic Dictionary** - 100+ keyword mappings (seasons, nature, emotions, materials, etc.)
3. **Direct Mapping** - Basic color name recognition

**Multi-Keyword Support**
- Processes compound keywords (e.g., "tropical summer ocean")
- Extracts colors from each word and combines them intelligently

**Special Keyword Handling**
- **Rainbow**: Evenly distributed hues (0°, 60°, 120°, 180°, 240°, 300°)
- **Achromatic** (white/black/gray): Zero saturation, brightness-only adjustment
- **Seasonal/Thematic**: Balanced color distributions (e.g., Christmas → red+green)

#### Palette Modes

| Mode | Effect |
|------|--------|
| `normal` | Original colors as-is |
| `pastel` | Saturation ×0.5, Brightness ×1.05 |
| `vibrant` | Saturation ×1.2 |
| `earthy` | Saturation ×0.7, Brightness ×0.8 |
| `monochrome` | Saturation ×0.2 (single-hue variations) |

#### Pattern Poster Generator

Create 29×29 grid patterns from your color palettes with multiple pattern types:

**Pattern Types**
- **Random**: Shuffled color placement
- **Stripe**: Row-based color cycling
- **Heart/Star/Circle**: 7×7 mask shapes in 3×3 grid layout (9 shapes total)

**Color Editing Features**
- Real-time color picker for instant modifications
- Add/delete colors freely
- User-defined color names
- Session management preserves edits

**Export Options**
- Palette CSV (color codes for each option)
- Pattern PNG (high-resolution grid)
- Pattern CSV (with custom color names)

#### Workflow
```
Keyword Input → 3-Tier Color Extraction → HSV Conversion → Mode Application → HEX Output
                                                                              ↓
Select Palette → Edit Colors → Choose Pattern Type → Generate 29×29 Grid → Download
```

---

### 🐶🐱 Tab 3: Animal Pattern Design Helper

**Convert Animal Images to Pixel Patterns**

Browse dog and cat images from public APIs and convert them into simplified pixel patterns perfect for knitting or crochet projects.

#### Image Sources
- **Dogs**: Dog CEO API (random breed images)
- **Cats**: TheCatAPI (pure images without text overlays)
- **Gallery**: 12 images per load with "See more" refresh

#### Color Simplification
Uses **KMeans clustering** algorithm (scikit-learn) to extract dominant colors:
- User-adjustable color count (2-30 colors)
- Intelligent color quantization
- Pixel-to-nearest-color mapping

#### Enhancement Options
- **Edge Enhancement Mode**: Makes pattern shapes more distinct
  - 2× sharpness boost
  - 1.3× contrast enhancement
  - Edge detection filter
- **Achromatic Mode**: Converts to grayscale patterns

#### Additional Features
- **Aspect Ratio Display**: Shows simplified ratio using GCD (e.g., 800×600 → 4:3)
- **Customizable Grid Size**: Any width × height combination
- **24px Cell Rendering**: Clear, printable pattern grids

#### Workflow
```
Browse Images → Select One → Set Parameters (size, colors, mode) 
              → Apply Enhancements → Generate Pattern → Download PNG/CSV
```

---

### 🏞️ Tab 4: Convert Image to Pattern

**Upload Your Own Images**

Same powerful conversion engine as Tab 3, but with your own images.

#### Differences from Tab 3

| Feature | Tab 3 | Tab 4 |
|---------|-------|-------|
| Image Source | API (dogs/cats) | User upload |
| Selection Method | Gallery browser | File upload |
| File Format | URL-based | PNG/JPG/JPEG |

#### Supported Formats
- PNG
- JPG/JPEG

Uses the same `convert_to_pixel_pattern_from_image()` function for consistent results.

---

## 🔧 Technical Details

### Core Utility Functions

#### Color Conversion
```python
hsv_to_rgb(h, s, v)  # HSV → RGB conversion
hex_from_rgb(rgb)    # RGB → HEX conversion (#RRGGBB)
```

#### Session State Management

| Key | Purpose |
|-----|---------|
| `messages` | AI conversation history |
| `palettes` | 3 generated palette options |
| `palette_seed` | Regeneration seed counter |
| `edited_palette_{idx}` | Currently edited palette |
| `generated_pattern_{idx}` | Generated pattern image data |
| `pattern_color_names` | User-defined color name mapping |
| `img_urls_{animal}` | Cached animal image URLs |

### Design Patterns

1. **Fallback System**: AI → Dictionary → Random for reliable color extraction
2. **Session-Based State**: Preserves user edits across regenerations
3. **DRY Principle**: Modular image processing shared across tabs
4. **Reactive UI**: Immediate synchronization with `st.rerun()`

---

## 📦 Dependencies

| Library | Purpose |
|---------|---------|
| `streamlit` | UI framework |
| `openai` | GPT-4 chatbot integration |
| `PIL (Pillow)` | Image processing |
| `sklearn` | KMeans clustering for color simplification |
| `requests` | API calls to external services |
| `numpy` | Numerical operations and array handling |
| `pandas` | DataFrame manipulation and CSV export |

---

## 🛠️ Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/knitting-pattern-designer.git
cd knitting-pattern-designer

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run knitting_crochet_helper_app.py
```

### Requirements.txt
```
streamlit
openai
Pillow
scikit-learn
requests
numpy
pandas
```

---

## 🎯 Usage

1. **Launch the app**: `streamlit run knitting_crochet_helper_app.py`
2. **Navigate tabs** using the top menu
3. **AI Helper**: Enter your OpenAI API key and start chatting
4. **Color Helper**: Type a keyword and generate palettes
5. **Animal Patterns**: Browse and convert animal images
6. **Custom Patterns**: Upload your own images

---

## 🌟 Key Features Highlights

### Intelligent Color Detection
- **100+ semantic keywords** mapped to appropriate color schemes
- **AI-powered detection** using Hugging Face models
- **Multi-keyword processing** for complex themes

### Pattern Generation
- **29×29 grid** optimized for knitting/crochet
- **Multiple pattern types** (random, stripe, geometric shapes)
- **Editable color palettes** with unlimited customization

### Image Processing
- **KMeans color quantization** for clean palettes
- **Edge enhancement** for clearer shapes
- **Flexible sizing** for any project scale

---

## 📝 Notes

- Always **swatch first** before starting your project
- Color palettes are suggestions based on algorithmic generation
- API keys are stored in session only (not persisted)
- Image processing may take a few seconds for large images

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

[Your License Here]

---

## 👤 Author

[Your Name/Organization]

---

## 🙏 Acknowledgments

- Dog CEO API for dog images
- TheCatAPI for cat images
- Hugging Face for AI color detection
- OpenAI for GPT-4 integration
