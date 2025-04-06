"""
Custom CSS styles for the Visio Stencil Explorer application.
This module provides functions to inject custom CSS for improved UI layout and spacing.
"""

import streamlit as st

def inject_custom_css():
    """
    Inject custom CSS to improve UI layout and spacing throughout the application.
    This addresses various spacing and alignment issues.
    """
    st.markdown("""
    <style>
        /* Global spacing variables */
        :root {
            --spacing-xs: 4px;
            --spacing-sm: 8px;
            --spacing-md: 16px;
            --spacing-lg: 24px;
            --spacing-xl: 32px;
        }

        /* ===== 0. Critical Layout Fixes ===== */
        /* Ensure containers have proper height and scrolling */
        @media (min-width: 992px) {
            /* Desktop */
            [data-testid="stCaptionContainer"] div[data-baseweb="card"],
            div[data-baseweb="card"] {
                min-height: 300px !important;
                max-height: 600px !important;
            }
            .sidebar div[data-baseweb="card"] {
                min-height: 150px !important;
            }
        }

        @media (max-width: 991px) and (min-width: 768px) {
            /* Tablet */
            [data-testid="stCaptionContainer"] div[data-baseweb="card"],
            div[data-baseweb="card"] {
                min-height: 250px !important;
                max-height: 500px !important;
            }
            .sidebar div[data-baseweb="card"] {
                min-height: 120px !important;
            }
        }

        @media (max-width: 767px) {
            /* Mobile */
            [data-testid="stCaptionContainer"] div[data-baseweb="card"],
            div[data-baseweb="card"] {
                min-height: 200px !important;
                max-height: 400px !important;
            }
            .sidebar div[data-baseweb="card"] {
                min-height: 100px !important;
            }
        }

        /* ===== 1. Input Field Alignment ===== */
        /* Ensure date inputs have consistent height and alignment - simplified selector */
        div[data-baseweb="form-control"] {
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
        }

        /* Add consistent padding to date input labels */
        div[data-baseweb="form-control"] > label {
            margin-bottom: 8px;
        }

        /* ===== 2. Slider Input Labels Spacing ===== */
        /* Add more space between slider labels and the slider itself - simplified selector */
        div[data-testid="stSlider"] > div:first-child {
            margin-bottom: 10px;
        }

        /* ===== 3. Slider Values Positioning ===== */
        /* Improve spacing for slider values - simplified selector */
        div[data-testid="stSlider"] > div:last-child {
            margin-top: 5px;
            padding: 0 10px;
            display: flex;
            justify-content: space-between;
        }

        /* Fix slider value display to remove leading zeros */
        div[data-testid="stSlider"] > div:last-child > div {
            min-width: 40px;
            text-align: center;
        }

        /* Ensure the slider values on the track are properly displayed */
        div[data-testid="stSlider"] span {
            font-variant-numeric: normal !important;
            font-size: 0.9rem;
            font-weight: 400;
            color: rgba(255, 255, 255, 0.8);
        }

        /* Improve slider handle appearance */
        div[data-testid="stSlider"] div[role="slider"] {
            background-color: #ff4b4b;
            border: 2px solid white;
            box-shadow: 0 0 5px rgba(0, 0, 0, 0.3);
        }

        /* Improve slider track appearance */
        div[data-testid="stSlider"] div[data-baseweb="slider"] div {
            border-radius: 4px;
        }

        /* Add more space below sliders for the custom labels and ensure full width */
        div[data-testid="stSlider"] {
            margin-bottom: 25px;
            position: relative;
            width: 100% !important;
        }

        /* Ensure the slider container spans full width */
        div[data-testid="stSlider"] > div {
            width: 100% !important;
        }

        /* Make sure the slider element itself spans full width */
        div[data-baseweb="slider-container"] {
            width: 100% !important;
        }

        /* Ensure the slider track spans full width */
        div[data-baseweb="slider"] {
            width: 100% !important;
        }

        /* Fix any parent container width issues */
        div[data-testid="stSlider"] > div {
            width: 100% !important;
            max-width: 100% !important;
        }

        /* Ensure the slider container in expanders spans full width */
        div[data-testid="stExpander"] div[data-testid="stSlider"] {
            width: 100% !important;
            max-width: 100% !important;
        }

        /* Improve slider active track color */
        div[data-testid="stActiveTrack"] {
            background-color: #ff4b4b !important;
        }

        /* Ensure slider labels have proper spacing */
        div[data-testid="stSlider"] > label {
            margin-bottom: 12px;
            display: block;
            font-weight: 500;
        }

        /* Ensure slider track has proper spacing */
        div[data-testid="stSlider"] > div:nth-child(2) {
            margin: 10px 0;
            padding: 5px 0;
        }

        /* ===== 4. Recent Searches Layout ===== */
        /* Add consistent spacing to search history buttons - simplified selector */
        div[data-testid="column"] {
            padding: 0 5px;
        }

        /* Add margin to the buttons */
        button {
            margin: 5px 0;
        }

        /* ===== 5 & 6. Tools Section and Results Header Spacing ===== */
        /* Add spacing between sections */
        .spacer-sm {
            margin-top: 10px;
            margin-bottom: 10px;
        }

        .spacer-md {
            margin-top: 20px;
            margin-bottom: 20px;
        }

        /* ===== 7. Shape Preview Section ===== */
        /* Improve image padding and centering in preview */
        div[data-testid="stImage"] {
            padding: 15px;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        div[data-testid="stImage"] > img {
            max-width: 90%;
            max-height: 90%;
            object-fit: contain;
        }

        /* ===== 8. General Spacing Consistency ===== */
        /* Add consistent vertical spacing between elements */
        div[data-testid="stVerticalBlock"] > div {
            margin-bottom: var(--spacing-md);
        }

        /* Add consistent spacing to headings */
        h1, h2, h3, h4, h5, h6 {
            margin-top: var(--spacing-lg);
            margin-bottom: var(--spacing-md);
        }

        /* Add consistent padding to containers */
        div[data-testid="stContainer"] {
            padding: var(--spacing-md);
        }

        /* Ensure buttons have consistent spacing */
        button {
            margin: var(--spacing-xs) 0;
        }

        /* Ensure form elements have consistent spacing */
        div[data-baseweb="form-control"] {
            margin-bottom: var(--spacing-md);
        }

        /* Add consistent spacing to captions */
        div[data-testid="stCaptionContainer"] {
            margin-top: var(--spacing-xs);
            margin-bottom: var(--spacing-sm);
        }

        /* Ensure consistent spacing in the sidebar */
        .sidebar .element-container {
            margin-bottom: var(--spacing-md);
        }

        /* Make sure content scrolls if it exceeds the container height */
        div[data-baseweb="card"] > div {
            overflow-y: auto;
        }
    </style>
    """, unsafe_allow_html=True)

def inject_spacer(height_px=20):
    """
    Inject a vertical spacer with the specified height.

    Args:
        height_px (int): Height of the spacer in pixels
    """
    st.markdown(f"<div style='height: {height_px}px;'></div>", unsafe_allow_html=True)
