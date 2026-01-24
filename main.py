from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
import socket
import threading
import platform
import time

# ================= 配置区域 (Configuration) =================
# 如果您需要【不在同一WiFi下】也能自动连接，请修改下方引号内的内容。
# 填入您的【公网IP】或【内网固定IP】。
# 例如: TARGET_IP = "123.45.67.89"
# 如果留空 ""，APP 将会默认在局域网内自动搜索。
TARGET_IP = ""  
# ==========================================================

class RemoteClient(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=50, spacing=20)
        
        self.title_lbl = Label(text="PyRemote Client", font_size='30sp', size_hint_y=None, height='60dp', color=(0, 0.7, 1, 1))
        self.layout.add_widget(self.title_lbl)
        
        self.status_lbl = Label(text="Status: Initializing...", font_size='18sp')
        self.layout.add_widget(self.status_lbl)
        
        # Default text
        default_ip = TARGET_IP if TARGET_IP else '192.168.1.x'
        self.ip_input = TextInput(text=default_ip, multiline=False, size_hint_y=None, height='50dp', font_size='20sp')
        self.layout.add_widget(self.ip_input)
        
        self.connect_btn = Button(text="Connect to PC", size_hint_y=None, height='80dp', background_color=(0, 0.8, 0, 1), font_size='24sp')
        self.connect_btn.bind(on_press=self.start_connection)
        self.layout.add_widget(self.connect_btn)
        
        return self.layout

    def on_start(self):
        self.connected = False
        # 1. Start LAN Auto Discovery (Always run this in background)
        threading.Thread(target=self.auto_discover, daemon=True).start()

        # 2. If Remote IP is set, try to connect directly (Parallel)
        if TARGET_IP:
            Clock.schedule_once(lambda dt: self.update_status(f"🚀 Connecting to Remote: {TARGET_IP}"))
            threading.Thread(target=self.connect_to_server, args=(TARGET_IP,), daemon=True).start()

    def direct_connect_target(self):
        # Deprecated, merged into on_start
        pass

    def auto_discover(self):
        time.sleep(1) # Wait for UI to be ready
        udp = None
        try:
            udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp.bind(('', 9998))
            
            if not TARGET_IP:
                Clock.schedule_once(lambda dt: self.update_status("🔍 Scanning Local Network..."))
            
            while not self.connected:
                udp.settimeout(2.0) # Check connected flag periodically
                try:
                    data, addr = udp.recvfrom(1024)
                    if data == b"PYREMOTE_SERVER_HERE":
                        server_ip = addr[0]
                        if not self.connected:
                            Clock.schedule_once(lambda dt: self.found_server(server_ip))
                        break
                except socket.timeout:
                    continue
                except:
                    break
        except Exception as e:
            if not TARGET_IP:
                Clock.schedule_once(lambda dt: self.update_status(f"Scan Error: {str(e)}"))
        finally:
            if udp:
                try:
                    udp.close()
                except:
                    pass

    def found_server(self, ip):
        if not self.connected:
            self.ip_input.text = ip
            self.status_lbl.text = f"Found PC: {ip}. Connecting..."
            self.start_connection(None)

    def start_connection(self, instance):
        if self.connected: return
        ip = self.ip_input.text
        self.status_lbl.text = f"Connecting to {ip}..."
        threading.Thread(target=self.connect_to_server, args=(ip,), daemon=True).start()

    def connect_to_server(self, ip):
        if self.connected: return
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Timeout for connection attempt
            s.settimeout(5)
            s.connect((ip, 9999))
            s.settimeout(None) # Reset timeout for data
            
            self.connected = True # Mark as connected
            
            # Send device info
            info = f"Device: {platform.machine()} | System: {platform.system()}"
            s.send(info.encode('utf-8'))
            
            Clock.schedule_once(lambda dt: self.update_status(f"✅ Connected to {ip}!"))
            
            # Keep alive loop
            while True:
                data = s.recv(1024)
                if not data: break
        except Exception as e:
            if not self.connected:
                Clock.schedule_once(lambda dt: self.update_status(f"❌ Failed: {str(e)}"))
                # Retry logic for Remote IP
                if ip == TARGET_IP and not self.connected:
                     Clock.schedule_once(lambda dt: self.update_status(f"🔄 Retrying Remote in 5s..."))
                     time.sleep(5)
                     self.connect_to_server(ip)

    def update_status(self, msg):
        self.status_lbl.text = msg

if __name__ == '__main__':
    RemoteClient().run()
