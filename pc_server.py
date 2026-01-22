import sys
import os
import subprocess
import time
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QHeaderView, QCheckBox, 
                             QGroupBox, QLineEdit, QComboBox, QStatusBar, QFrame,
                             QMessageBox, QFileDialog, QInputDialog)
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QIcon, QFont

# Configuration
SCRCPY_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scrcpy-win64-v3.3.4"))
ADB_EXE = os.path.join(SCRCPY_DIR, "adb.exe")
SCRCPY_EXE = os.path.join(SCRCPY_DIR, "scrcpy.exe")

import socket

# Worker Thread for Broadcast
class BroadcastWorker(QThread):
    def run(self):
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            try:
                udp.sendto(b"PYREMOTE_SERVER_HERE", ('<broadcast>', 9998))
                time.sleep(1.5) 
            except Exception as e:
                time.sleep(5)

# Worker Thread for ADB Polling
class AdbWorker(QThread):
    devices_updated = pyqtSignal(list)

    def run(self):
        while True:
            devices = self.get_devices()
            self.devices_updated.emit(devices)
            time.sleep(2)

    def run_command(self, args):
        try:
            # Creation flags to hide window on Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.run(
                [ADB_EXE] + args, 
                capture_output=True, 
                text=True, 
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def get_devices(self):
        output = self.run_command(["devices", "-l"])
        lines = output.split('\n')[1:]
        device_list = []
        
        for line in lines:
            if not line.strip():
                continue
            parts = line.split()
            serial = parts[0]
            state = parts[1]
            
            # Basic info parsing
            model = "Unknown"
            for part in parts:
                if part.startswith("model:"):
                    model = part.split(":")[1]
            
            # Fetch details (simplified for performance)
            # In a real app, these should be batched or cached
            battery = self.get_battery(serial) if state == "device" else "?"
            wifi = self.get_wifi(serial) if state == "device" else "?"
            android_ver = self.get_android_ver(serial) if state == "device" else "?"
            
            device_list.append({
                "serial": serial,
                "state": state,
                "model": model,
                "battery": battery,
                "wifi": wifi,
                "system": f"Android {android_ver}"
            })
        return device_list

    def get_battery(self, serial):
        out = self.run_command(["-s", serial, "shell", "dumpsys", "battery"])
        for line in out.split('\n'):
            if "level" in line:
                return line.split(":")[1].strip() + "%"
        return "?"

    def get_wifi(self, serial):
        # Simplified check
        out = self.run_command(["-s", serial, "shell", "dumpsys", "wifi"])
        if "Wi-Fi is enabled" in out or "mNetworkInfo" in out:
            return "On"
        return "Off"

    def get_android_ver(self, serial):
        return self.run_command(["-s", serial, "shell", "getprop", "ro.build.version.release"])

class ServerWorker(QThread):
    client_connected = pyqtSignal(str, str) # ip, info

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('0.0.0.0', 9999))
        server.listen(5)
        print("Server listening on 0.0.0.0:9999")
        
        while True:
            client, addr = server.accept()
            ip = addr[0]
            try:
                data = client.recv(1024).decode('utf-8')
                self.client_connected.emit(ip, data)
            except:
                pass

class DeviceManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("多设备远控管理系统 (Multi-Device Remote Control)")
        self.resize(1200, 800)
        self.setup_style()

        self.devices = []
        self.setup_ui()
        
        # Start Server for Custom APK
        self.server_worker = ServerWorker()
        self.server_worker.client_connected.connect(self.on_client_connect)
        self.server_worker.start()

        # Start Broadcast for Auto-Connect
        self.broadcast_worker = BroadcastWorker()
        self.broadcast_worker.start()

        # Enable Drag & Drop
        self.setAcceptDrops(True)
        
        # Start Worker
        self.worker = AdbWorker()
        self.worker.devices_updated.connect(self.update_device_list)
        self.worker.start()

    def setup_style(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; color: #e0e0e0; font-family: "Segoe UI", sans-serif; }
            QTableWidget { 
                background-color: #252526; 
                color: #e0e0e0; 
                gridline-color: #3e3e42; 
                selection-background-color: #3f3f46;
                border: none;
            }
            QHeaderView::section { 
                background-color: #333333; 
                color: #e0e0e0; 
                padding: 6px; 
                border: none; 
                font-weight: bold;
            }
            QPushButton { 
                background-color: #007acc; 
                color: white; 
                border: none; 
                padding: 6px 12px; 
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #0098ff; }
            QPushButton#stopBtn { background-color: #d9534f; }
            QLabel { color: #e0e0e0; }
            QGroupBox { 
                border: 1px solid #3e3e42; 
                margin-top: 1.2em; 
                border-radius: 4px; 
                padding: 10px;
            }
            QGroupBox::title { color: #007acc; subcontrol-origin: margin; left: 10px; }
            QLineEdit, QComboBox { 
                background-color: #3c3c3c; 
                color: white; 
                border: 1px solid #555; 
                padding: 4px; 
                border-radius: 2px;
            }
        """)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left Panel (Preview / Control Area)
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.Shape.StyledPanel)
        left_panel.setStyleSheet("background-color: #000;")
        left_layout = QVBoxLayout(left_panel)
        
        self.preview_label = QLabel("设备预览区域\n(Device Preview Area)")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("color: #666; font-size: 16px;")
        
        left_layout.addWidget(self.preview_label)
        main_layout.addWidget(left_panel, stretch=6)

        # Right Panel (Device List & Controls)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Controls
        controls_group = QGroupBox("控制面板 (Control Panel)")
        controls_layout = QHBoxLayout()
        
        # Scrcpy Settings
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["8 Mbps (高清)", "4 Mbps (均衡)", "2 Mbps (流畅)"])
        self.quality_combo.setToolTip("视频质量 (Bitrate)")
        
        self.fps_input = QLineEdit("60")
        self.fps_input.setPlaceholderText("FPS")
        self.fps_input.setFixedWidth(50)
        self.fps_input.setToolTip("帧率 (Max FPS)")
        
        self.screen_off_chk = QCheckBox("息屏控制")
        self.screen_off_chk.setToolTip("启动后关闭手机屏幕 (Turn Screen Off)")

        self.start_btn = QPushButton("🚀 启动 (Start)")
        self.start_btn.clicked.connect(self.launch_selected)
        
        self.stop_btn = QPushButton("⏹ 停止 (Stop)")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.clicked.connect(self.stop_selected)

        # Additional Buttons
        self.install_btn = QPushButton("📥 安装APK")
        self.install_btn.clicked.connect(self.install_apk)
        self.install_btn.setStyleSheet("background-color: #28a745;")

        self.wifi_btn = QPushButton("📶 WiFi连接")
        self.wifi_btn.clicked.connect(self.show_wifi_dialog)
        self.wifi_btn.setStyleSheet("background-color: #6f42c1;")
        
        # Help/Info Buttons
        self.help_btn = QPushButton("❓ 帮助")
        self.help_btn.clicked.connect(self.show_help)
        self.help_btn.setStyleSheet("background-color: #17a2b8;")
        
        self.pair_btn = QPushButton("🔗 配对")
        self.pair_btn.clicked.connect(self.show_pair_dialog)
        self.pair_btn.setStyleSheet("background-color: #e83e8c;")

        controls_layout.addWidget(QLabel("画质:"))
        controls_layout.addWidget(self.quality_combo)
        controls_layout.addWidget(QLabel("FPS:"))
        controls_layout.addWidget(self.fps_input)
        controls_layout.addWidget(self.screen_off_chk)
        controls_layout.addStretch()
        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.stop_btn)
        
        # Second row for tools
        tools_layout = QHBoxLayout()
        tools_layout.addWidget(self.install_btn)
        tools_layout.addWidget(self.wifi_btn)
        tools_layout.addWidget(self.pair_btn)
        tools_layout.addWidget(self.help_btn)
        
        controls_wrapper = QVBoxLayout()
        controls_wrapper.addLayout(controls_layout)
        controls_wrapper.addLayout(tools_layout)
        controls_group.setLayout(controls_wrapper)

        right_layout.addWidget(controls_group)

        # Device Table
        self.table = QTableWidget()
        # Columns: Select, Flag(Country), Battery, Screen, Wifi, Speed, Activity, System
        columns = ["选中", "序列号", "电池", "WIFI", "型号", "系统", "状态"]
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        right_layout.addWidget(self.table)

        # Bottom Status
        status_layout = QHBoxLayout()
        self.device_count_label = QLabel("设备: 0")
        
        # Tip Label
        self.tip_label = QLabel("💡 提示: 直接拖拽 APK 文件到窗口即可批量安装")
        self.tip_label.setStyleSheet("color: #888; font-style: italic; margin-left: 10px;")
        
        self.port_label = QLabel("端口: 5555")
        status_layout.addWidget(self.device_count_label)
        status_layout.addWidget(self.tip_label)
        status_layout.addStretch()
        status_layout.addWidget(self.port_label)
        right_layout.addLayout(status_layout)

        main_layout.addWidget(right_panel, stretch=4)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def update_device_list(self, devices):
        self.devices = devices
        self.device_count_label.setText(f"设备: {len(devices)}")
        
        # Cache checked states
        checked_serials = set()
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                serial_item = self.table.item(i, 1)
                if serial_item:
                    checked_serials.add(serial_item.text())

        self.table.setRowCount(len(devices))
        
        for i, device in enumerate(devices):
            # Checkbox
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            if device["serial"] in checked_serials or not checked_serials: # Default check new ones if list was empty
                check_item.setCheckState(Qt.CheckState.Checked)
            else:
                check_item.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(i, 0, check_item)
            
            self.table.setItem(i, 1, QTableWidgetItem(device["serial"]))
            self.table.setItem(i, 2, QTableWidgetItem(device["battery"]))
            self.table.setItem(i, 3, QTableWidgetItem(device["wifi"]))
            self.table.setItem(i, 4, QTableWidgetItem(device["model"]))
            self.table.setItem(i, 5, QTableWidgetItem(device["system"]))
            self.table.setItem(i, 6, QTableWidgetItem(device["state"]))

    def launch_selected(self):
        for i in range(self.table.rowCount()):
            if self.table.item(i, 0).checkState() == Qt.CheckState.Checked:
                serial = self.table.item(i, 1).text()
                self.launch_scrcpy(serial)

    def launch_scrcpy(self, serial):
        print(f"Launching scrcpy for {serial}")
        
        # Parse settings
        quality_text = self.quality_combo.currentText().split()[0] # "10"
        fps = self.fps_input.text()
        
        # Calculate bitrate based on "quality" (1-10 scale roughly mapping to mbps)
        bitrate = f"{quality_text}M"
        
        cmd = [
            SCRCPY_EXE, 
            "-s", serial,
            "--window-title", f"Control: {serial}",
            "--video-bit-rate", bitrate,
            "--max-fps", fps,
            "--always-on-top"
        ]
        
        if self.screen_off_chk.isChecked():
            cmd.append("--turn-screen-off")

        subprocess.Popen(cmd, cwd=SCRCPY_DIR)

    def install_apk(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择 APK 文件 (Select APK)", "", "APK Files (*.apk)")
        if not file_path:
            return
        self.start_install_process(file_path)

    def start_install_process(self, file_path):
        selected_serials = []
        for i in range(self.table.rowCount()):
            if self.table.item(i, 0).checkState() == Qt.CheckState.Checked:
                selected_serials.append(self.table.item(i, 1).text())
        
        if not selected_serials:
            QMessageBox.warning(self, "警告", "请先选择至少一台设备！")
            return

        self.status_bar.showMessage(f"正在安装到 {len(selected_serials)} 台设备...")
        
        for serial in selected_serials:
            threading.Thread(target=self._install_thread, args=(serial, file_path)).start()

    def _install_thread(self, serial, apk_path):
        try:
            subprocess.run([ADB_EXE, "-s", serial, "install", "-r", apk_path], check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            print(f"Install success: {serial}")
        except Exception as e:
            print(f"Install failed: {serial} - {e}")

    def stop_selected(self):
        if os.name == 'nt':
            subprocess.run(["taskkill", "/F", "/IM", "scrcpy.exe"], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            subprocess.run(["pkill", "scrcpy"])

    def show_help(self):
        msg = """
        === 核心疑问解答 ===
        
        Q: 我去哪里下载手机端的安装包？
        A: 【没有手机端！】请千万不要去网上找，您不需要下载任何东西到手机上。
           
           这款软件的技术原理是：直接通过数据线接管手机。
           优势：
           1. 手机不卡顿（不占用手机资源）
           2. 不会被杀后台（系统级控制）
           3. 真正的“即插即用”
        
        Q: 那我手机怎么被控制？
        A: 只要开启【USB调试】开关，插上电脑，软件就会自动识别。
        
        === 如何连接 (仅需3步) ===
        
        1. 开启开发者模式：手机设置 -> 关于手机 -> 狂点 "版本号"。
        2. 开启 USB 调试：手机设置 -> 开发者选项 -> 开启 "USB 调试"。
        3. 插线：连接电脑，手机弹出窗口点 "允许"。
        """
        QMessageBox.information(self, "手机端下载说明", msg)

    def show_wifi_dialog(self):
        # 1. Ask for IP
        ip, ok = QLineEdit.getText(self, "无线连接 (WiFi Connect)", "请输入手机 IP 地址:\n(例如: 192.168.1.5)\n\n注意：首次连接必须先插一次 USB 线开启端口！")
        if ok and ip:
            self.connect_wifi(ip)

    def connect_wifi(self, ip):
        # 1. Enable TCP mode (Must be done via USB first usually)
        # But if user already enabled it, we try connect directly
        # We try to restart adb tcpip just in case (needs usb), but if no usb, we just try connect
        
        # Try connect
        QMessageBox.information(self, "连接中", f"正在尝试连接 {ip} ...\n请确保电脑和手机在同一个 WiFi 下。")
        
        def _connect():
            # Try to switch port if USB is attached (Best effort)
            subprocess.run([ADB_EXE, "tcpip", "5555"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            
            # Connect
            res = subprocess.run([ADB_EXE, "connect", f"{ip}:5555"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            
            if "connected to" in res.stdout:
                self.status_bar.showMessage(f"✅ 无线连接成功: {ip}")
            else:
                self.status_bar.showMessage(f"❌ 连接失败: {ip} (请检查 IP 或先插线开启端口)")

        threading.Thread(target=_connect, daemon=True).start()

    def on_client_connect(self, ip, info):
        self.status_bar.showMessage(f"📱 新客户端接入: {ip} - {info}")
        QMessageBox.information(self, "新设备接入", f"检测到手机端 APP 连接！\nIP: {ip}\nInfo: {info}")

    def show_pair_dialog(self):
        # Dialog for Android 11+ Wireless Debugging Pairing
        msg = """
        === 关于“手机端 APK”的重要说明 ===
        
        您提到的“下载本程序的 APK 安装包”是不存在的，因为：
        
        1. 【技术原理】：本程序直接调用安卓系统底层的“开发者通道”，手机端本身就有“接收器”，不需要额外安装 APP。
        2. 【安全优势】：因为不安装 APP，所以不用担心 APP 被植入病毒，也不占用手机内存。
        
        === 如何实现“无 USB、无 APP”连接？ ===
        
        请使用 Android 11+ 自带的“无线调试”功能：
        
        1. 手机连接 WiFi。
        2. 手机设置 -> 开发者选项 -> 开启 "无线调试"。
        3. 点击 "无线调试" (进入详情) -> "使用配对码配对设备"。
        
        屏幕上会出现【IP地址:端口】和【配对码】，请填入下方：
        """
        QMessageBox.information(self, "免插线配对教程 (无需下载APP)", msg)
        
        # 1. Input Pairing Info
        text, ok = QInputDialog.getText(self, "输入配对码", 
                                     "请输入手机屏幕上的信息：\n格式：IP:端口 配对码\n(例如：192.168.1.5:37899 123456)")
        if not ok or not text:
            return

    def open_apk_folder(self):
        # File is now in the project root
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        file_path = os.path.join(project_root, "一键在线编译.ipynb")
        
        if os.path.exists(file_path):
            # Highlight the file in explorer
            subprocess.run(f'explorer /select,"{file_path}"')
        else:
            os.startfile(project_root)
            
        QMessageBox.information(self, "APK 编译方案", 
            "【如何获取 APK 安装包？】\n\n"
            "因为 Windows 环境无法直接编译安卓应用，我已经为您制作了【在线编译脚本】。\n\n"
            "1. 请在浏览器打开 Google Colab (https://colab.research.google.com/)\n"
            "2. 点击 '上传' -> 选择桌面【远控】文件夹里的 【一键在线编译.ipynb】\n"
            "3. 在网页菜单栏点击 '运行时' -> '全部运行'。\n"
            "4. 等待 15 分钟，APK 就会自动下载到您的电脑！")
    
    # Drag & Drop Support
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for f in files:
            if f.endswith(".apk"):
                self.start_install_process(f)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeviceManager()
    window.show()
    sys.exit(app.exec())
