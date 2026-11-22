"""Dark Qt stylesheet."""

ACCENT = "#7c5cff"

STYLESHEET = f"""
QWidget {{ background: #15161b; color: #e6e6eb; font-family: 'Segoe UI'; font-size: 10pt; }}
QGroupBox {{ border: 1px solid #2c2e38; border-radius: 8px; margin-top: 14px; padding: 10px 8px 8px 8px;
            background: #1b1c23; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #a99bff; font-weight: 600; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QListWidget {{
    background: #23242d; border: 1px solid #343645; border-radius: 5px; padding: 4px 6px;
    selection-background-color: {ACCENT}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox QAbstractItemView {{ background: #23242d; selection-background-color: {ACCENT}; }}
QPushButton {{ background: #2a2c38; border: 1px solid #3a3d4e; border-radius: 6px; padding: 6px 12px; }}
QPushButton:hover {{ background: #343748; border-color: {ACCENT}; }}
QPushButton:pressed {{ background: #3d4055; }}
QPushButton:disabled {{ color: #6b6d7a; background: #1f2028; border-color: #2a2c36; }}
QPushButton#primary {{ background: {ACCENT}; border-color: {ACCENT}; color: white; font-weight: 600; }}
QPushButton#primary:hover {{ background: #8d70ff; }}
QPushButton#primary:disabled {{ background: #3b335f; color: #9d97b8; }}
QPushButton#danger {{ background: #b3263a; border-color: #d43a50; color: white; font-weight: 600; }}
QPushButton#danger:hover {{ background: #cf2f46; }}
QPushButton#danger:disabled {{ background: #4a2229; color: #a07c82; }}
QProgressBar {{ background: #23242d; border: 1px solid #343645; border-radius: 5px; text-align: center; height: 18px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 4px; }}
QLabel#value {{ color: #ffffff; font-weight: 600; }}
QLabel#rec {{ color: #ff5d73; font-weight: 700; font-size: 12pt; }}
QLabel#hint {{ color: #8b8d9c; font-size: 9pt; }}
QCheckBox::indicator {{ width: 16px; height: 16px; }}
QPlainTextEdit {{ font-family: Consolas; font-size: 9pt; }}
QScrollArea {{ border: none; }}
"""
