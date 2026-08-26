"""
Design tokens taken from CDDA_Meeting_Manager_claude_design.html.

The mockup is a Claude Design export written in that tool's own template syntax
(<sc-for>, <sc-if>, {{ }}). None of that markup can be served directly - Jinja
would try to evaluate every {{ }} and fail. What carries over is the visual
language, which lives here as tokens and small style dicts that app.py composes.
"""

# --- Colour -----------------------------------------------------------------
NAVY = "#0B1D3A"          # header, headings
NAVY_DEEP = "#16294A"     # hover on navy
RED = "#E4202D"           # Lilly red - primary action, active accent
RED_DARK = "#C4141F"
BLUE = "#1E4EBC"          # links, eyebrow labels, secondary accent
BLUE_LIGHT = "#6FABDC"
PAGE_BG = "#E9ECF1"
SURFACE = "#FFFFFF"
SURFACE_MUTED = "#F2F4F7"
SURFACE_ROW = "#F8FAFC"
TINT_BLUE = "#E8EEFB"     # selected row, badges
TINT_SKY = "#EAF3FA"      # forum card
BORDER = "#E4E8EF"
BORDER_SKY = "#D5E3F0"
BORDER_BLUE = "#CFDBF5"
RULE = "#CBD3E0"
TEXT = "#3A4658"
TEXT_MUTED = "#6B7789"
TEXT_FAINT = "#8A95A6"

STATUS_APPROVED = "#1E7A4C"
STATUS_PENDING = "#B26B00"

# --- Type -------------------------------------------------------------------
FONT = "'Aptos','Segoe UI',Arial,Helvetica,sans-serif"
FONT_DISPLAY = "'Aptos Display','Aptos',Arial,sans-serif"

SHADOW_CARD = "0 2px 4px rgba(11,29,58,.04),0 14px 40px rgba(11,29,58,.10)"
TRANSITION = "160ms cubic-bezier(.2,.6,.2,1)"

MAX_WIDTH = "1160px"


# --- Reusable style dicts ---------------------------------------------------
def eyebrow(color: str = TEXT_MUTED) -> dict:
    """Small uppercase label above a heading."""
    return {
        "font": f"700 11px/1 {FONT}",
        "letterSpacing": "0.14em",
        "textTransform": "uppercase",
        "color": color,
    }


PAGE = {
    "minHeight": "100vh",
    "background": PAGE_BG,
    "fontFamily": FONT,
    "color": TEXT,
    "WebkitFontSmoothing": "antialiased",
}

HEADER = {"background": NAVY, "borderBottom": f"3px solid {RED}"}

HEADER_INNER = {
    "maxWidth": MAX_WIDTH,
    "margin": "0 auto",
    "padding": "0 28px",
    "height": "64px",
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "space-between",
    "gap": "24px",
}

MAIN = {"maxWidth": MAX_WIDTH, "margin": "0 auto", "padding": "36px 28px 72px"}

CARD = {
    "background": SURFACE,
    "borderRadius": "12px",
    "boxShadow": SHADOW_CARD,
    "overflow": "hidden",
}

H1 = {
    "margin": "0",
    "font": f"700 34px/1.15 {FONT_DISPLAY}",
    "letterSpacing": "-0.015em",
    "color": NAVY,
}

H2 = {
    "margin": "0",
    "font": f"700 22px/1.25 {FONT}",
    "letterSpacing": "-0.005em",
    "color": NAVY,
}

BODY = {"margin": "0", "font": f"400 16px/1.6 {FONT}", "color": TEXT}

BTN_PRIMARY = {
    "display": "inline-flex",
    "alignItems": "center",
    "gap": "10px",
    "background": RED,
    "color": SURFACE,
    "border": "none",
    "borderRadius": "4px",
    "padding": "13px 24px",
    "font": f"700 14px/1 {FONT}",
    "letterSpacing": "0.08em",
    "textTransform": "uppercase",
    "cursor": "pointer",
}

BTN_DARK = {
    **BTN_PRIMARY,
    "background": NAVY,
    "padding": "12px 24px",
}

BTN_QUIET = {
    "background": "none",
    "border": "none",
    "padding": "0",
    "font": f"700 13px/1 {FONT}",
    "color": TEXT_MUTED,
    "cursor": "pointer",
}

BTN_ICON = {
    "display": "inline-flex",
    "alignItems": "center",
    "justifyContent": "center",
    "minWidth": "36px",
    "height": "36px",
    "padding": "0 10px",
    "background": "none",
    "border": f"1px solid {BORDER}",
    "borderRadius": "4px",
    "color": TEXT_MUTED,
    "font": f"700 12px/1 {FONT}",
    "cursor": "pointer",
}

INPUT = {
    "border": f"1px solid {BORDER}",
    "borderRadius": "4px",
    "background": SURFACE,
    "padding": "11px 14px",
    "font": f"400 15px/1.3 {FONT}",
    "color": NAVY,
    "width": "100%",
}

LABEL = {
    "display": "flex",
    "flexDirection": "column",
    "gap": "6px",
    "font": f"700 12px/1 {FONT}",
    "letterSpacing": "0.08em",
    "textTransform": "uppercase",
    "color": TEXT_MUTED,
}

BADGE = {
    "display": "inline-flex",
    "alignItems": "center",
    "gap": "8px",
    "alignSelf": "flex-start",
    "background": TINT_BLUE,
    "borderRadius": "4px",
    "padding": "5px 10px",
    "font": f"700 11px/1 {FONT}",
    "letterSpacing": "0.08em",
    "textTransform": "uppercase",
    "color": BLUE,
}

BANNER = {
    "maxWidth": MAX_WIDTH,
    "margin": "20px auto 0",
    "padding": "16px 20px",
    "background": SURFACE_MUTED,
    "borderRadius": "8px",
    "borderLeft": f"3px solid {RED}",
    "font": f"400 14px/1.5 {FONT}",
    "color": TEXT,
}

# Global CSS that Dash injects via index_string - hover/focus states cannot be
# expressed in inline style dicts.
INDEX_CSS = f"""
  html, body {{ margin:0; padding:0; background:{PAGE_BG}; }}
  * {{ box-sizing: border-box; }}
  a {{ color:{BLUE}; text-decoration:none; }}
  a:hover {{ color:{NAVY_DEEP}; text-decoration:underline; }}
  button, input, select, textarea {{ font-family:{FONT}; }}
  ::placeholder {{ color:{TEXT_FAINT}; }}
  .btn-primary:hover {{ background:{RED_DARK} !important; }}
  .btn-primary:active {{ transform:scale(.985); }}
  .btn-dark:hover {{ background:{NAVY_DEEP} !important; }}
  .btn-quiet:hover {{ color:{NAVY} !important; }}
  .btn-icon:hover {{ color:{RED} !important; border-color:{RED} !important; }}
  .date-row:hover {{ background:{TINT_BLUE} !important; }}
  button:disabled {{ opacity:.45; cursor:not-allowed; }}
  input:focus, select:focus, textarea:focus, button:focus-visible {{
    outline:none; box-shadow:0 0 0 3px rgba(30,78,188,.35);
  }}
  .forum-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(380px,1fr)); gap:20px; }}
  .agenda-split {{ display:grid; grid-template-columns:340px 1fr; align-items:start; }}
  @media (max-width: 860px) {{
    .agenda-split {{ grid-template-columns:1fr; }}
  }}
"""
