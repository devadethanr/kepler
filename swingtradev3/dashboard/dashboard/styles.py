import reflex as rx

# Theme Colors
BG_COLOR = "#000000"         # Pure Black
CARD_BG = "#0d0d0d"          # Very Dark Gray for pure black contrast
BORDER_COLOR = "#2a1548"     # Deep Purple Border
TEXT_PRIMARY = "#e2d5f8"     # Soft Purple-ish White
TEXT_SECONDARY = "#a78bfa"   # Light Purple

ACCENT_GREEN = "#10b981"         # Emerald Green
ACCENT_GREEN_DIM = "rgba(16, 185, 129, 0.15)"
ACCENT_RED = "#ef4444"           # Keeping Red for errors
ACCENT_RED_DIM = "rgba(239, 68, 68, 0.15)"
ACCENT_PURPLE = "#7c3aed"        # Deep Purple
ACCENT_PURPLE_DIM = "rgba(124, 58, 237, 0.15)"
ACCENT_YELLOW = "#fbbf24"        # Golden Yellow
ACCENT_YELLOW_DIM = "rgba(251, 191, 36, 0.15)"
ACCENT_CYAN = "#06b6d4"          # Cyan accent for variation
ACCENT_BLUE = "#3b82f6"          # Blue Accent

# Styles Map
global_styles = {
    ":root": {
        "color_scheme": "dark",
    },
    "body": {
        "background_color": BG_COLOR,
        "color": TEXT_PRIMARY,
        "font_family": "Inter, sans-serif",
        "margin": "0",
    },
}

card_style = {
    "background_color": CARD_BG,
    "border": f"1px solid {BORDER_COLOR}",
    "border_radius": "12px",
    "box_shadow": "0 4px 6px rgba(0,0,0,0.2)",
    "padding": "1.5rem",
}

badge_style = {
    "padding": "0.25rem 0.75rem",
    "border_radius": "999px",
    "font_size": "0.75rem",
    "font_weight": "bold",
    "display": "inline-flex",
    "align_items": "center",
    "gap": "0.5rem"
}
