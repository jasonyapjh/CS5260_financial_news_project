# import streamlit as st

# def show():
#     st.title("⚙️ Settings")
#     st.markdown("""
#     This is where you can configure your preferences for the Financial News Intelligence app. 
#     You can customize your news digest, manage your watchlist, and set up notifications.
#     **Note:** Settings will be saved for your current session. Future versions may include persistent storage.
#     """)
import streamlit as st
import random
from streamlit_elements import elements, mui, html

# --- 1. Global CSS (From your previous big pills / neon theme) ---
st.markdown("""
    <style>
    div.stButton > button:first-child {
        border-radius: 20px !important;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

def show():
    # 2. Form for User Inputs
    with st.form(key="my_form_2"):
        cs, col1, col2, cf = st.columns([0.05, 1, 1, 0.05])
        with col1:
            bg = st.color_picker("🎨 Background Color", "#00d4ff")
            label = st.text_input("🅰️ Button label", value="Analyze AAPL")
            buttonStyle = st.selectbox("🕹️ Button style", ["contained", "outlined"], 0)
            onclick = st.selectbox("🖱️ App rerun on click", ["none", "rerun"], index=1)

        with col2:
            fg = st.color_picker("🎨 Font Color", "#FFFFFF")
            size = st.selectbox("📦 Button size", ["small", "medium", "large"], 1)
            icon_selected = st.selectbox(
                "📸 Icon",
                ["accessible", "add box", "alarm", "arrow back", "arrow downward", 
                 "arrow forward", "arrow upward", "call", "chat", "delete", "save", "send"],
                index=10 # Default to 'send'
            )
            hrefLink = st.text_input("🔗 Hyperlink", "https://mui.com/material-ui/react-button/")

        st.form_submit_button("Preview Changes")

    # 3. Corrected Logic Functions
    def get_icon_data(icon_name):
        # Map labels to MUI icons (PascalCase is required)
        icon_map = {
            "accessible": mui.icon.Accessible,
            "add box": mui.icon.AddBox,
            "alarm": mui.icon.Alarm,
            "arrow back": mui.icon.ArrowBack,
            "arrow downward": mui.icon.ArrowDownward,
            "arrow forward": mui.icon.ArrowForward,
            "arrow upward": mui.icon.ArrowUpward,
            "call": mui.icon.Call,
            "chat": mui.icon.Chat,
            "delete": mui.icon.Delete,
            "save": mui.icon.Save,
            "send": mui.icon.Send,
        }
        # Get the object and the string for code generation
        obj = icon_map.get(icon_name, mui.icon.Send)
        code_str = f"mui.icon.{icon_name.title().replace(' ', '')}"
        return obj, code_str

    st.subheader("Here's your custom button:")

    # 4. Rendering the Elements
    with elements("mui_button_preview"):
        # Get icon object
        icon_obj, icon_code_name = get_icon_data(icon_selected)
        
        # Setup style dictionary (MUI uses backgroundColor not background)
        button_style = {
            "color": fg, 
            "backgroundColor": bg if buttonStyle == "contained" else "transparent",
            "borderRadius": "20px",
            "padding": "10px 25px",
            "fontWeight": "bold"
        }

        # Handle the click behavior
        # Note: In elements, we use 'onClick' (camelCase)
        click_handler = st.rerun if onclick == "rerun" else None

        # Render the MUI Button
        mui.button(
            label,
            variant=buttonStyle,
            size=size,
            startIcon=icon_obj,
            style=button_style,
            onClick=click_handler,
            href=hrefLink,
            target="_blank" if hrefLink else None
        )

    # 5. Code Generator Section
    st.divider()
    st.subheader("Your button's code:")
    st.code(f"""
import streamlit as st
from streamlit_elements import elements, mui

with elements("my_button"):
    mui.button(
        "{label}",
        variant="{buttonStyle}",
        size="{size}",
        startIcon={icon_code_name},
        style={{
            "color": "{fg}",
            "backgroundColor": "{bg if buttonStyle == 'contained' else 'transparent'}",
            "borderRadius": "20px"
        }},
        href="{hrefLink}"
    )
    """, language="python")

