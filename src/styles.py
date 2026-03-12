# Streamlit removed for Lean Build
class MockSt:
    @staticmethod
    def markdown(*args, **kwargs): print(f"STYLE: {args}")
st = MockSt()


def apply_material_styles():
    """
    Applies NinjaTrader-inspired Industrial UI styles (Mandatory Dark Mode).
    Focuses on high-density data, sharp corners, and professional gray-scale palette.
    """
    
    # Industrial Theme Palette (Dark Only)
    bg_main = "#121212"  # Match chart background
    bg_pane = "#1A1C23"
    bg_header = "#1E2129"
    bg_sidebar = "#11141C"
    border = "#2D323E"
    text = "#FAFAFA"
    header_text = "#FFFFFF"
    stat_bg = "linear-gradient(to bottom, #2D323E, #1A1C23)"
    accent_blue = "#4B91F7" # Electric Blue
    toast_bg = "#FFFFFF" # White background for Black text (User request)
    toast_text = "#000000"

    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        /* --- 1. APP SHELL & RESET --- */
        /* More aggressive hiding of native Streamlit UI elements */
        [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stHeader"], 
        .stDeployButton, #MainMenu, footer, .stToolbar {{
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            width: 0 !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }}
        
        /* Global App Background */
        .stApp {{
            background: {bg_main};
            font-family: 'Inter', sans-serif;
        }}
        
        /* Reset Main Container to allow for Sidebar footprint */
        [data-testid="stMainBlockContainer"] {{
             padding: 80px 2rem 2rem 2rem !important;
        }}
        
        /* --- 2. CUSTOM HEADER BAR --- */
        .custom-header {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 60px;
            background: {bg_header};
            border-bottom: 1px solid {border};
            z-index: 1000; /* High but not above everything */
            display: flex;
            align-items: center;
            padding: 0 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        
        .header-logo {{
            font-size: 20px;
            font-weight: 800;
            color: {header_text};
            letter-spacing: -0.5px;
            display: flex;
            align-items: center;
            gap: 10px;
            cursor: pointer;
            transition: transform 0.2s ease;
        }}
        
        .header-logo:hover {{
            transform: scale(1.05);
        }}
        
        .status-dot {{
            height: 8px;
            width: 8px;
            border-radius: 50%;
            transition: all 0.3s ease;
        }}
        
        .status-dot.active {{
            background-color: #00E676; /* Live green */
            box-shadow: 0 0 8px #00E676;
            animation: pulse 2s infinite;
        }}
        
        .status-dot.offline {{
            background-color: #888; /* Offline gray */
            box-shadow: none;
            animation: none;
        }}
        
        @keyframes pulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(0, 230, 118, 0.4); }}
            70% {{ box-shadow: 0 0 0 6px rgba(0, 230, 118, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(0, 230, 118, 0); }}
        }}
        
        /* --- 3. GLASSMORPHISM PANELS --- */
        /* Sidebar Styling - Simplified to avoid blocking native controls */
        [data-testid="stSidebar"] {{
            background-color: {bg_sidebar} !important;
            border-right: 1px solid {border};
            z-index: 1000001 !important; /* Above everything */
        }}
        
        div[data-testid="stVerticalBlock"] > div > div.stMetric {{
            background: {bg_pane};
            border: 1px solid {border};
            border-radius: 8px !important;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
            backdrop-filter: blur(8px);
            margin-bottom: 1rem;
        }}
        
        /* --- 4. NATIVE FORM CONTROLS --- */
        /* Inputs */
        input.st-ai, input.st-ah {{
             background-color: {bg_main} !important;
             color: {text} !important;
             border: 1px solid {border} !important;
             border-radius: 6px !important;
             height: 40px;
        }}
        
        input:focus {{
            border-color: {accent_blue} !important;
            box-shadow: 0 0 0 2px rgba(75, 145, 247, 0.2) !important;
        }}

        /* --- 4b. RADIO, CHECKBOX & TOGGLE OVERRIDES --- */
        /* Toggle (Checkbox) styling */
        div[data-testid="stCheckbox"] label div[aria-checked="true"] div {{
             background-color: {accent_blue} !important;
        }}
        
        /* Number Input buttons (+ / -) */
        div[data-testid="stNumberInput"] button:hover {{
            border-color: {accent_blue} !important;
            color: {accent_blue} !important;
        }}
        
        /* Slider styling */
        div[data-testid="stSlider"] div[data-baseweb="slider"] div:nth-child(2) {{
            background-color: {accent_blue} !important;
        }}
        
        /* Buttons - Modern & Flat */
        button.st-emotion-cache-19rxjzo, button.st-emotion-cache-7ym5gk, .stButton > button {{
            border-radius: 6px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease;
            text-transform: none !important; /* Reset uppercase if used previously */
        }}
        
        /* Primary Button */
        button[kind="primary"] {{
            background: linear-gradient(135deg, {accent_blue}, #3b7ad9) !important;
            border: none !important;
            color: white !important;
            box-shadow: 0 4px 14px 0 rgba(0,118,255,0.39);
        }}
        button[kind="primary"]:hover {{
             transform: translateY(-1px);
             box-shadow: 0 6px 20px rgba(0,118,255,0.23);
        }}
        
        /* Secondary Button */
        button[kind="secondary"] {{
            background: {bg_pane} !important; 
            border: 1px solid {border} !important;
            color: {text} !important;
        }}
        button[kind="secondary"]:hover {{
            background: {border} !important;
        }}
        
        /* --- 5. TEXT & TYPOGRAPHY --- */
        h1, h2, h3, h4, .industrial-header {{
            font-family: 'Inter', sans-serif !important;
            color: {header_text} !important;
            font-weight: 700 !important;
            letter-spacing: -0.5px !important;
        }}
        
        /* Selective Text overrides - Avoid breaking components like Toasts */
        p, label, .stMarkdown:not([data-testid="stToast"] *) {{
            color: {text} !important;
        }}

        /* --- 6. SEGMENTED CONTROL FIX --- */
        /* Ensure readable text in unselected and selected states */
        div[data-testid="stSegmentedControl"] button {{
            background-color: {bg_main} !important;
            border: 1px solid {border} !important;
            color: {text} !important;
            transition: all 0.2s ease;
        }}
        
        div[data-testid="stSegmentedControl"] button[aria-checked="true"] {{
            background-color: {accent_blue} !important;
            color: white !important;
            border-color: {accent_blue} !important;
        }}
        
        div[data-testid="stSegmentedControl"] button:hover {{
            border-color: {accent_blue} !important;
            color: {accent_blue} !important;
        }}
        
        div[data-testid="stSegmentedControl"] button[aria-checked="true"]:hover {{
            color: white !important;
        }}

        /* --- 7. EXPANDER & CONTAINER POLISH --- */
        /* Style the expander header to match pane background */
        div[data-testid="stExpander"] {{
            background: {bg_pane} !important;
            border: 1px solid {border} !important;
            border-radius: 8px !important;
            overflow: hidden !important;
        }}
        
        div[data-testid="stExpander"] details summary {{
            background: {bg_header} !important;
            color: {header_text} !important;
            padding: 10px 15px !important;
            border-bottom: 1px solid {border} !important;
        }}
        
        div[data-testid="stExpander"] details summary:hover {{
            color: {accent_blue} !important;
        }}

        /* --- 8. NUMBER INPUT (LOT SIZES) FIX --- */
        /* Ensure input and buttons are industrial and aligned */
        div[data-testid="stNumberInput"] {{
            background: {bg_main} !important;
        }}
        
        div[data-testid="stNumberInput"] div[data-baseweb="input"] {{
            background-color: transparent !important;
        }}
        
        div[data-testid="stNumberInput"] input {{
            color: {text} !important;
            font-weight: 600 !important;
        }}
        
        div[data-testid="stNumberInput"] button {{
            background: {bg_pane} !important;
            color: {text} !important;
            border: 1px solid {border} !important;
        }}

        /* --- 9. DATAFRAME & TOAST --- */
        [data-testid="stToast"] {{
            background-color: {toast_bg} !important;
            border: 1px solid {border} !important;
            color: {toast_text} !important;
            border-radius: 12px !important;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4) !important;
        }}
        
        [data-testid="stToast"] p {{
            color: {toast_text} !important;
            font-weight: 500 !important;
        }}
        
        [data-testid="stToast"] button {{
            color: {toast_text} !important;
        }}
        
        [data-testid="stDataFrame"] {{
             border: 1px solid {border};
             border-radius: 8px;
             overflow: hidden;
        }}
        
        </style>
    """, unsafe_allow_html=True)
