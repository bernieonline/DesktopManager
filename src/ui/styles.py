BRONZE = "#4FC3F7"
BG_DARK = "#1A1A1A"
BG_CARD = "#252525"
BG_HOVER = "#2E2E2E"
TEXT_PRIMARY = "#E8E8E8"
TEXT_MUTED = "#888888"
BORDER = "#333333"
DANGER = "#C0392B"

# Shop window
BG_SHOP_WINDOW = "rgba(18, 18, 18, 200)"
BG_SHOP_HEADER = "rgba(24, 24, 24, 220)"
BG_SHOP_TILE   = "rgba(38, 38, 38, 220)"
SHOP_BORDER    = BRONZE

# Shortcut status
STATUS_AVAILABLE   = "#4CAF50"
STATUS_UNAVAILABLE = "#FF9800"
STATUS_DEAD        = "#F44336"
STATUS_UNKNOWN     = "#666666"

MAIN_STYLE = f"""
    QMainWindow, QWidget#centralWidget {{
        background-color: {BG_DARK};
    }}
    QLabel {{
        color: {TEXT_PRIMARY};
        font-family: Segoe UI;
        font-size: 13px;
    }}
    QPushButton {{
        background-color: #2E2E2E;
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 6px 14px;
        font-family: Segoe UI;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background-color: #383838;
        border-color: {BRONZE};
    }}
    QPushButton:pressed {{
        background-color: #222222;
    }}
    QPushButton#primaryButton {{
        background-color: {BRONZE};
        color: #1A1A1A;
        font-weight: bold;
        border: none;
    }}
    QPushButton#primaryButton:hover {{
        background-color: #7DD4F8;
    }}
    QPushButton#dangerButton {{
        color: {DANGER};
        border-color: #4A2020;
    }}
    QPushButton#dangerButton:hover {{
        background-color: #3A1A1A;
        border-color: {DANGER};
    }}
    QCheckBox {{
        color: {TEXT_PRIMARY};
        font-family: Segoe UI;
        font-size: 13px;
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {BORDER};
        border-radius: 3px;
        background-color: #2E2E2E;
    }}
    QCheckBox::indicator:checked {{
        background-color: {BRONZE};
        border-color: {BRONZE};
    }}
    QScrollArea {{
        background-color: {BG_DARK};
        border: none;
    }}
    QScrollBar:vertical {{
        background-color: {BG_DARK};
        width: 8px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background-color: #444444;
        border-radius: 4px;
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {BRONZE};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QStatusBar {{
        background-color: #141414;
        color: {TEXT_MUTED};
        font-family: Segoe UI;
        font-size: 12px;
    }}
    QLineEdit {{
        background-color: #2E2E2E;
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 6px 10px;
        font-family: Segoe UI;
        font-size: 13px;
    }}
    QLineEdit:focus {{
        border-color: {BRONZE};
    }}
    QDialog {{
        background-color: {BG_DARK};
    }}
"""

CARD_STYLE = f"""
    QWidget#desktopCard {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 6px;
    }}
    QWidget#desktopCard:hover {{
        border-color: {BRONZE};
    }}
"""
