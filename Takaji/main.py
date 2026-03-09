import sys
import random
import requests
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
                             QHBoxLayout, QScrollArea, QSizePolicy, QFileDialog)
from PyQt5.QtCore import Qt, QPoint, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPixmap, QFont, QPalette, QBrush


class Heart:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.alpha = 255
        self.size = random.randint(12, 20)
    def update(self):
        self.y -= 1
        self.alpha -= 5
    def is_dead(self):
        return self.alpha <= 0


class DeepSeekThread(QThread):
    finished = pyqtSignal(str)
    def __init__(self, user_text, api_key, messages):
        super().__init__()
        self.user_text = user_text
        self.api_key = api_key
        self.messages = messages
    def run(self):
        url = "https://api.deepseek.com/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        self.messages.append({"role": "user", "content": self.user_text})
        data = {"model": "deepseek-chat", "messages": self.messages}
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            ai_text = result["choices"][0]["message"]["content"]
            self.messages.append({"role": "assistant", "content": ai_text})
        except Exception:
            ai_text = "调用 API 出错"
        self.finished.emit(ai_text)


class PixelPet(QWidget):
    def __init__(self, img_path, api_key, user_avatar_path):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.pixmap = QPixmap(img_path)
        self.resize(self.pixmap.width(), self.pixmap.height())
        self.show()
        self.offset = QPoint()
        self.chat_window = None
        self.hearts = []
        self.api_key = api_key
        self.user_avatar_path = user_avatar_path

        self.paint_timer = QTimer()
        self.paint_timer.timeout.connect(self.update)
        self.paint_timer.start(30)
        self.heart_timer = QTimer()
        self.heart_timer.timeout.connect(self.generate_heart)
        self.heart_timer.start(800)

    def generate_heart(self):
        hx = random.randint(self.width()//4, self.width()*3//4)
        hy = self.height()//2
        self.hearts.append(Heart(hx, hy))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)
        for heart in self.hearts[:]:
            color = QColor(255, 0, 0, max(0, heart.alpha))
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            size = heart.size
            painter.drawEllipse(heart.x, heart.y, size//2, size//2)
            painter.drawEllipse(heart.x+size//2, heart.y, size//2, size//2)
            painter.drawPolygon(QPoint(heart.x, heart.y+size//2),
                                QPoint(heart.x+size, heart.y+size//2),
                                QPoint(heart.x+size//2, heart.y+size))
            heart.update()
            if heart.is_dead():
                self.hearts.remove(heart)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.offset = event.pos()
        elif event.button() == Qt.RightButton:
            self.show_chat_window()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.offset)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            QApplication.quit()

    def show_chat_window(self):
        if self.chat_window is None:
            self.chat_window = ChatWindow(api_key=self.api_key, user_avatar_path=self.user_avatar_path,
                                          wallpaper_path="bg.jpg")
        self.chat_window.show()
        self.chat_window.raise_()


class ChatWindow(QWidget):
    def __init__(self, api_key, user_avatar_path, wallpaper_path=None):
        super().__init__()
        self.api_key = api_key
        self.user_avatar_path = user_avatar_path
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.resize(320, 400)

        self.messages = [{"role": "system",
                          "content": "你是擅长捉弄人的高木同学，友善幽默温柔，回答用户问题时保持可爱风格，用户就是与你恋爱的西片同学。"}]

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(5,5,5,5)
        self.main_layout.setSpacing(5)

        if wallpaper_path:
            palette = self.palette()
            pixmap = QPixmap(wallpaper_path).scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            palette.setBrush(QPalette.Window, QBrush(pixmap))
            self.setAutoFillBackground(True)
            self.setPalette(palette)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout()
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_widget.setLayout(self.chat_layout)
        self.scroll_area.setWidget(self.chat_widget)
        self.main_layout.addWidget(self.scroll_area)

        self.input_box = QLineEdit()
        self.input_box.setFont(QFont("Arial",10))
        self.input_box.setPlaceholderText("输入文字然后回车...")
        self.input_box.setStyleSheet("""
            QLineEdit {background-color: rgba(50,50,50,220);
            color:white; border-radius:10px; padding:5px;}
        """)
        self.input_box.returnPressed.connect(self.reply)
        self.main_layout.addWidget(self.input_box)
        self.setLayout(self.main_layout)
        self.setMinimumSize(250,200)

        self.pet_avatar = "avatar.jpg"

    def add_message(self, text, sender="user"):
        container = QWidget()
        v_layout = QVBoxLayout()
        v_layout.setSpacing(2)
        v_layout.setContentsMargins(5,5,5,5)

        avatar_path = self.user_avatar_path if sender=="user" else self.pet_avatar
        if avatar_path:
            avatar_label = QLabel()
            pix = QPixmap(avatar_path).scaled(32,32,Qt.KeepAspectRatio, Qt.SmoothTransformation)
            avatar_label.setPixmap(pix)
            avatar_label.setFixedSize(32,32)
            h_layout_avatar = QHBoxLayout()
            if sender=="user":
                h_layout_avatar.addStretch()
                h_layout_avatar.addWidget(avatar_label)
            else:
                h_layout_avatar.addWidget(avatar_label)
                h_layout_avatar.addStretch()
            v_layout.addLayout(h_layout_avatar)

        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setFont(QFont("Arial",10))
        bubble.setContentsMargins(8,5,8,5)
        bubble.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        bubble.setStyleSheet(
            "background-color:#2a8cff; color:white; border-radius:10px; padding:5px;" if sender=="user"
            else "background-color:#ff8080; color:white; border-radius:10px; padding:5px;"
        )

        h_bubble_layout = QHBoxLayout()
        h_bubble_layout.setContentsMargins(0,0,0,0)
        if sender=="user":
            h_bubble_layout.addStretch()
            h_bubble_layout.addWidget(bubble)
        else:
            h_bubble_layout.addWidget(bubble)
            h_bubble_layout.addStretch()
        v_layout.addLayout(h_bubble_layout)

        container.setLayout(v_layout)
        self.chat_layout.addWidget(container)
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def reply(self):
        user_text = self.input_box.text()
        if not user_text.strip(): return
        self.add_message(user_text, sender="user")
        self.input_box.clear()
        self.thread = DeepSeekThread(user_text, self.api_key, self.messages)
        self.thread.finished.connect(lambda text: self.add_message(text, sender="assistant"))
        self.thread.start()


class APIKeyWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("请输入 DeepSeek API Key")
        self.setFixedSize(400, 120)
        layout = QVBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("请输入你的 DeepSeek API Key")
        layout.addWidget(self.input_box)
        self.ok_button = QPushButton("确定")
        layout.addWidget(self.ok_button)
        self.setLayout(layout)
        self.ok_button.clicked.connect(self.ok_clicked)

    def ok_clicked(self):
        key = self.input_box.text().strip()
        if key:
            self.close()
            global avatar_window
            avatar_window = AvatarUploadWindow(api_key=key)
            avatar_window.show()
        else:
            self.input_box.setPlaceholderText("API Key不能为空！")


class AvatarUploadWindow(QWidget):
    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key
        self.setWindowTitle("上传用户头像")
        self.setFixedSize(400, 120)
        layout = QVBoxLayout()
        self.label = QLabel("请选择用户头像图片")
        layout.addWidget(self.label)
        self.upload_button = QPushButton("选择图片")
        layout.addWidget(self.upload_button)
        self.ok_button = QPushButton("确定")
        layout.addWidget(self.ok_button)
        self.setLayout(layout)
        self.upload_button.clicked.connect(self.select_image)
        self.ok_button.clicked.connect(self.ok_clicked)
        self.avatar_path = None

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择头像图片", "", "Images (*.png *.jpg *.bmp)")
        if file_path:
            self.avatar_path = file_path
            self.label.setText(f"已选择: {file_path}")

    def ok_clicked(self):
        if self.avatar_path:
            self.close()
            global pet_window
            pet_window = PixelPet("takaji.png", api_key=self.api_key, user_avatar_path=self.avatar_path)
            pet_window.show()
        else:
            self.label.setText("请先选择图片！")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    api_window = APIKeyWindow()
    api_window.show()
    sys.exit(app.exec_())