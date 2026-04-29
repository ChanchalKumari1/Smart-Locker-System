# Version1.0

import sys, os, cv2
import numpy as np
import face_recognition
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from picamera2 import Picamera2
import RPi.GPIO as GPIO

# ---------------- CONFIG ----------------
PIN_CODE = "123456" # change it or I can link to get from API for next version
FACES_DIR = "faces" # Please create directory where the codes saved
LOCK_PIN = 23

if not os.path.exists(FACES_DIR):
    os.makedirs(FACES_DIR)

# ---------------- GPIO ----------------
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(LOCK_PIN, GPIO.OUT)
GPIO.output(LOCK_PIN, GPIO.LOW)

# ---------------- CAMERA ----------------
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
picam2.start()

# ---------------- FACE DATA ----------------
known_encodings, known_names = [], []

def load_faces():
    known_encodings.clear()
    known_names.clear()
    for file in os.listdir(FACES_DIR):
        path = os.path.join(FACES_DIR, file)
        img = face_recognition.load_image_file(path)
        enc = face_recognition.face_encodings(img)
        if enc:
            known_encodings.append(enc[0])
            known_names.append(os.path.splitext(file)[0])

load_faces()


# ---------------- DOOR STATUS WIDGET ----------------
class DoorStatusWidget(QWidget):
    """Animated door status pill — shows LOCKED / UNLOCKED with color pulse."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._unlocked = False
        self._pulse = 0.0
        self._direction = 1

        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Pulse animation
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick_pulse)
        self._anim_timer.start(30)

    def set_unlocked(self, state: bool):
        self._unlocked = state
        self._pulse = 0.0
        self.update()

    def _tick_pulse(self):
        if self._unlocked:
            self._pulse += 0.06 * self._direction
            if self._pulse >= 1.0:
                self._direction = -1
            elif self._pulse <= 0.0:
                self._direction = 1
        else:
            self._pulse = 0.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        r = self.rect()

        # Background pill
        base_color = QColor(20, 34, 52)
        p.setBrush(base_color)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(r, 22, 22)

        # Glow / indicator color
        if self._unlocked:
            glow = QColor(0, 230, 118)
            border_color = QColor(0, int(180 + 50 * self._pulse), int(80 + 38 * self._pulse))
            text = "DOOR OPEN"
        else:
            glow = QColor(239, 68, 68)
            border_color = QColor(180, 40, 40)
            text = "DOOR LOCKED"

        # Glowing border
        pen = QPen(border_color, 2)
        if self._unlocked:
            alpha = int(160 + 95 * self._pulse)
            c = QColor(glow)
            c.setAlpha(alpha)
            pen.setColor(c)
            pen.setWidth(2)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 21, 21)

        # Dot indicator
        dot_r = 10
        dot_x = 18
        dot_y = r.height() // 2
        if self._unlocked:
            alpha_dot = int(180 + 75 * self._pulse)
            dot_color = QColor(0, 230, 118, alpha_dot)
        else:
            dot_color = QColor(239, 68, 68, 220)
        p.setBrush(dot_color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPoint(dot_x, dot_y), dot_r // 2 + (1 if self._unlocked else 0), dot_r // 2 + (1 if self._unlocked else 0))

        # Text
        font = QFont("Monospace", 11, QFont.Bold)
        p.setFont(font)
        p.setPen(QColor(220, 230, 255))
        text_rect = QRect(36, 0, r.width() - 44, r.height())
        p.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text)

        p.end()


# ---------------- PIN DIALOG ----------------
class PinDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setFixedSize(320, 360)
        self.setStyleSheet("""
            QDialog { background-color: #0a1628; color: white; border-radius: 14px; }
            QPushButton {
                background: #1a2d4a; color: white;
                border-radius: 10px; padding: 10px;
                font-size: 16px; font-weight: bold;
            }
            QPushButton:hover { background: #2a3d5a; }
            QPushButton:pressed { background: #0e7490; }
            QLineEdit {
                background: #1a2d4a; color: #00e676;
                border: 2px solid #0e7490; border-radius: 10px;
                padding: 8px; font-size: 20px; letter-spacing: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        self.entry = QLineEdit()
        self.entry.setEchoMode(QLineEdit.Password)
        self.entry.setAlignment(Qt.AlignCenter)
        self.entry.setPlaceholderText("● ● ● ● ● ●")
        layout.addWidget(self.entry)

        grid = QGridLayout()
        grid.setSpacing(8)
        for i in range(1, 10):
            btn = QPushButton(str(i))
            btn.setFixedHeight(48)
            btn.clicked.connect(lambda _, n=i: self.entry.setText(self.entry.text() + str(n)))
            grid.addWidget(btn, (i - 1) // 3, (i - 1) % 3)

        # Bottom row: clear, 0, ok
        clr = QPushButton("⌫")
        clr.setFixedHeight(48)
        clr.clicked.connect(lambda: self.entry.setText(self.entry.text()[:-1]))
        grid.addWidget(clr, 3, 0)

        zero = QPushButton("0")
        zero.setFixedHeight(48)
        zero.clicked.connect(lambda: self.entry.setText(self.entry.text() + "0"))
        grid.addWidget(zero, 3, 1)

        ok = QPushButton("✔")
        ok.setFixedHeight(48)
        ok.setStyleSheet("background: #0e7490; color: white; border-radius: 10px; font-size: 18px;")
        ok.clicked.connect(self.check_pin)
        grid.addWidget(ok, 3, 2)

        layout.addLayout(grid)

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel)

    def check_pin(self):
        if self.entry.text() == PIN_CODE:
            self.accept()
        else:
            self.entry.clear()
            self.entry.setPlaceholderText("❌ Wrong PIN")


# ---------------- ON-SCREEN KEYBOARD ----------------
class Keyboard(QWidget):
    def __init__(self, target):
        super().__init__()
        self.target = target
        self.setStyleSheet("""
            QPushButton {
                background: #1a2d4a; color: white;
                border-radius: 6px; font-size: 13px;
                padding: 4px; min-width: 32px; min-height: 32px;
            }
            QPushButton:hover { background: #2a3d5a; }
        """)

        layout = QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        rows = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
        for r, row in enumerate(rows):
            offset = r
            for c, key in enumerate(row):
                btn = QPushButton(key)
                btn.clicked.connect(lambda _, k=key: self.target.setText(self.target.text() + k))
                layout.addWidget(btn, r, c + offset)

        nums = "1234567890"
        for c, key in enumerate(nums):
            btn = QPushButton(key)
            btn.clicked.connect(lambda _, k=key: self.target.setText(self.target.text() + k))
            layout.addWidget(btn, 3, c)

        clr = QPushButton("⌫")
        clr.clicked.connect(lambda: self.target.setText(self.target.text()[:-1]))
        layout.addWidget(clr, 3, 10)


# ---------------- MAIN WINDOW ----------------
class SmartLocker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Locker")
        self.showFullScreen()

        self._door_open = False

        # Central stacked widget
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.home_page = self._build_home()
        self.admin_page = self._build_admin()

        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.admin_page)

        # Camera timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(100)

    #  HOME PAGE
    def _build_home(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        # ── Top bar ──
        topbar = QHBoxLayout()
        topbar.setSpacing(8)

        title = QLabel("SMART LOCKER")
        title.setStyleSheet("""
            font-family: 'Courier New', monospace;
            font-size: 20px; font-weight: bold;
            color: #7dd3fc; letter-spacing: 4px;
        """)
        topbar.addWidget(title)
        topbar.addStretch()

        # Door status pill
        self.door_status = DoorStatusWidget()
        topbar.addWidget(self.door_status, 1)

        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(70, 70)
        settings_btn.setStyleSheet("""
            QPushButton {
                background: #1a2d4a; color: #e2e8f0;
                border-radius: 12px; font-size: 32px;
                border: 1px solid #2a3d5a;
            }
            QPushButton:hover { background: #2a3d5a; }
            QPushButton:pressed { background: #0e7490; }
        """)
        settings_btn.setToolTip("Admin Panel")
        settings_btn.clicked.connect(self._open_admin)
        topbar.addWidget(settings_btn)

        root.addLayout(topbar)

        # ── Camera feed ──
        cam_frame = QFrame()
        cam_frame.setStyleSheet("""
            QFrame { background: #0a1628;
                     border: 2px solid #1e3a5f;
                     border-radius: 14px; }
        """)
        cam_layout = QVBoxLayout(cam_frame)
        cam_layout.setContentsMargins(4, 4, 4, 4)

        self.cam_home = QLabel()
        self.cam_home.setAlignment(Qt.AlignCenter)
        self.cam_home.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.cam_home.setMinimumHeight(200)
        cam_layout.addWidget(self.cam_home)

        root.addWidget(cam_frame, 1)

        # ── Status bar ──
        self.status_label = QLabel("Scanning for faces...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            background: #0e1f35;
            border: 1px solid #1e3a5f;
            border-radius: 10px;
            padding: 10px;
            font-size: 15px;
            color: #94a3b8;
        """)
        self.status_label.setFixedHeight(46)
        root.addWidget(self.status_label)

        return page

    #  ADMIN PAGE
    def _build_admin(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        # ── Top bar ──
        topbar = QHBoxLayout()
        lbl = QLabel("ADMIN PANEL")
        lbl.setStyleSheet("""
            font-family: 'Courier New', monospace;
            font-size: 18px; font-weight: bold;
            color: #fb923c; letter-spacing: 3px;
        """)
        topbar.addWidget(lbl)
        topbar.addStretch()

        back_btn = QPushButton("← Back")
        back_btn.setFixedHeight(38)
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        topbar.addWidget(back_btn)
        root.addLayout(topbar)

        # ── Main body ──
        body = QHBoxLayout()
        body.setSpacing(12)

        # LEFT: camera + capture controls
        left = QVBoxLayout()
        left.setSpacing(8)

        cam_frame = QFrame()
        cam_frame.setStyleSheet("""
            QFrame { background: #0a1628;
                     border: 2px solid #2a3d5a;
                     border-radius: 12px; }
        """)
        cam_inner = QVBoxLayout(cam_frame)
        cam_inner.setContentsMargins(4, 4, 4, 4)

        self.cam_admin = QLabel()
        self.cam_admin.setAlignment(Qt.AlignCenter)
        self.cam_admin.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.cam_admin.setMinimumHeight(160)
        cam_inner.addWidget(self.cam_admin)
        left.addWidget(cam_frame, 1)

        # Name input row
        input_row = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter name...")
        self.name_input.hide()
        input_row.addWidget(self.name_input)

        self.save_btn = QPushButton("Save Face")
        self.save_btn.setFixedHeight(38)
        self.save_btn.clicked.connect(self._save_face)
        self.save_btn.hide()
        input_row.addWidget(self.save_btn)
        left.addLayout(input_row)

        self.keyboard = Keyboard(self.name_input)
        self.keyboard.hide()
        left.addWidget(self.keyboard)

        self.add_btn = QPushButton("Register New Face")
        self.add_btn.setFixedHeight(42)
        self.add_btn.clicked.connect(self._show_input)
        left.addWidget(self.add_btn)

        # RIGHT: user list
        right = QVBoxLayout()
        right.setSpacing(6)

        users_label = QLabel("Registered Users")
        users_label.setStyleSheet("font-size: 14px; color: #7dd3fc; font-weight: bold;")
        right.addWidget(users_label)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: #0a1628; color: white;
                border: 1px solid #1e3a5f; border-radius: 10px;
                font-size: 14px; padding: 4px;
            }
            QListWidget::item { padding: 8px; border-radius: 6px; }
            QListWidget::item:selected { background: #1e3a5f; }
            QListWidget::item:hover { background: #162033; }
        """)
        self._refresh_list()
        right.addWidget(self.list_widget, 1)

        del_btn = QPushButton("🗑  Delete Selected")
        del_btn.setFixedHeight(40)
        del_btn.setStyleSheet("""
            QPushButton { background: #7f1d1d; color: white;
                          border-radius: 10px; font-size: 13px; }
            QPushButton:hover { background: #991b1b; }
        """)
        del_btn.clicked.connect(self._delete_user)
        right.addWidget(del_btn)

        body.addLayout(left, 3)
        body.addLayout(right, 2)
        root.addLayout(body, 1)

        return page

    # Admin helpers
    def _show_input(self):
        self.name_input.show()
        self.keyboard.show()
        self.save_btn.show()
        self.add_btn.hide()

    def _save_face(self):
        name = self.name_input.text().strip()
        if not name:
            return
        frame = picam2.capture_array()
        cv2.imwrite(f"{FACES_DIR}/{name}.jpg", cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        load_faces()
        self._refresh_list()
        self.name_input.clear()
        self.name_input.hide()
        self.keyboard.hide()
        self.save_btn.hide()
        self.add_btn.show()

    def _refresh_list(self):
        self.list_widget.clear()
        if os.path.exists(FACES_DIR):
            for file in sorted(os.listdir(FACES_DIR)):
                if file.lower().endswith((".jpg", ".jpeg", ".png")):
                    name = os.path.splitext(file)[0]
                    if name in known_names:
                        self.list_widget.addItem(f"  {name}")
                    else:
                        item = QListWidgetItem(f"  {name}  [no face detected]")
                        item.setForeground(QColor("#f97316"))
                        self.list_widget.addItem(item)

    def _delete_user(self):
        item = self.list_widget.currentItem()
        if item:
            # Strip leading spaces and any trailing warning tag like "[no face detected]"
            raw = item.text().strip()
            name = raw.split("  [")[0].strip()
            path = f"{FACES_DIR}/{name}.jpg"
            if os.path.exists(path):
                os.remove(path)
            load_faces()
            self._refresh_list()

    # ─── Open admin (PIN gate) 
    def _open_admin(self):
        dlg = PinDialog(self)
        if dlg.exec_():
            self._refresh_list()   # ensure list is current when entering admin
            self.stack.setCurrentIndex(1)

    # ─── Unlock helper 
    def _unlock_door(self):
        GPIO.output(LOCK_PIN, GPIO.HIGH)
        self._door_open = True
        self.door_status.set_unlocked(True)
        QTimer.singleShot(5000, self._lock_door)

    def _lock_door(self):
        GPIO.output(LOCK_PIN, GPIO.LOW)
        self._door_open = False
        self.door_status.set_unlocked(False)

    # ─── Camera update 
    def _update_frame(self):
        frame = picam2.capture_array()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Face recognition
        faces = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, faces)

        # Draw boxes on a copy so recognition data is intact
        display = rgb.copy()

        for i, encoding in enumerate(encodings):
            matches = face_recognition.compare_faces(known_encodings, encoding)
            top, right, bottom, left = faces[i]

            if True in matches:
                name = known_names[matches.index(True)]
                # Green box + name label for recognised face
                box_color = (0, 230, 118)
                cv2.rectangle(display, (left, top), (right, bottom), box_color, 2)
                # Label background
                label = name
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
                cv2.rectangle(display, (left, bottom), (left + tw + 10, bottom + th + 10), box_color, -1)
                cv2.putText(display, label, (left + 5, bottom + th + 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)

                self._set_status(f"Welcome, {name}!", "#00e676")
                if not self._door_open:
                    self._unlock_door()
                QTimer.singleShot(3000, lambda: self._set_status("Scanning for faces...", "#94a3b8"))
            else:
                # Red box for unknown face
                box_color = (239, 68, 68)
                cv2.rectangle(display, (left, top), (right, bottom), box_color, 2)
                label = "Unknown"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
                cv2.rectangle(display, (left, bottom), (left + tw + 10, bottom + th + 10), box_color, -1)
                cv2.putText(display, label, (left + 5, bottom + th + 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

                self._set_status("Access Denied", "#ef4444")
                QTimer.singleShot(2000, lambda: self._set_status("Scanning for faces...", "#94a3b8"))

        # Display frame with highlights
        h, w, ch = display.shape
        qimg = QImage(display.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)

        if self.stack.currentIndex() == 0:
            pix_scaled = pix.scaled(
                self.cam_home.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.cam_home.setPixmap(pix_scaled)
        else:
            pix_scaled = pix.scaled(
                self.cam_admin.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.cam_admin.setPixmap(pix_scaled)

    def _set_status(self, text: str, color: str):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"""
            background: #0e1f35;
            border: 1px solid #1e3a5f;
            border-radius: 10px;
            padding: 10px;
            font-size: 15px;
            color: {color};
        """)

    # ─── Keyboard shortcut 
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def closeEvent(self, event):
        GPIO.cleanup()
        event.accept()


#  APP
app = QApplication(sys.argv)

# Responsive font scaling for 7-inch display (~800×480)
screen = app.primaryScreen().geometry()
base_size = min(screen.width(), screen.height())
scale = base_size / 480  # normalize to 480p height

app.setStyleSheet(f"""
    QMainWindow, QWidget {{
        background-color: #06111f;
        color: #e2e8f0;
        font-family: 'Courier New', monospace;
        font-size: {max(11, int(12 * scale))}px;
    }}
    QPushButton {{
        background: #1a2d4a;
        color: #e2e8f0;
        border-radius: 10px;
        padding: {max(6, int(7 * scale))}px {max(10, int(12 * scale))}px;
        font-size: {max(12, int(13 * scale))}px;
        border: 1px solid #2a3d5a;
    }}
    QPushButton:hover {{ background: #2a3d5a; }}
    QPushButton:pressed {{ background: #0e7490; border-color: #0891b2; }}
    QLineEdit {{
        background: #0e1f35;
        color: #7dd3fc;
        border: 2px solid #1e3a5f;
        border-radius: 10px;
        padding: {max(5, int(6 * scale))}px;
        font-size: {max(13, int(14 * scale))}px;
    }}
    QLineEdit:focus {{ border-color: #0891b2; }}
    QStackedWidget {{ background: #06111f; }}
    QScrollBar:vertical {{
        background: #0a1628; width: 8px; border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: #1e3a5f; border-radius: 4px; min-height: 20px;
    }}
""")

win = SmartLocker()
win.show()
sys.exit(app.exec_())
