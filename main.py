from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
import socket
import threading
import platform

class RemoteClient(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=50, spacing=20)
        
        self.title_lbl = Label(text="PyRemote Client", font_size='30sp', size_hint_y=None, height='60dp', color=(0, 0.7, 1, 1))
        self.layout.add_widget(self.title_lbl)
        
        self.status_lbl = Label(text="Status: Not Connected", font_size='18sp')
        self.layout.add_widget(self.status_lbl)
        
        self.ip_input = TextInput(text='192.168.1.x', multiline=False, size_hint_y=None, height='50dp', font_size='20sp')
        self.layout.add_widget(self.ip_input)
        
        self.connect_btn = Button(text="Connect to PC", size_hint_y=None, height='80dp', background_color=(0, 0.8, 0, 1), font_size='24sp')
        self.connect_btn.bind(on_press=self.start_connection)
        self.layout.add_widget(self.connect_btn)
        
        return self.layout

    def start_connection(self, instance):
        ip = self.ip_input.text
        self.status_lbl.text = f"Connecting to {ip}..."
        threading.Thread(target=self.connect_to_server, args=(ip,), daemon=True).start()

    def connect_to_server(self, ip):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, 9999))
            
            # Send device info
            info = f"Device: {platform.machine()} | System: {platform.system()}"
            s.send(info.encode('utf-8'))
            
            Clock.schedule_once(lambda dt: self.update_status("✅ Connected! Online."))
            
            # Keep alive loop
            while True:
                data = s.recv(1024)
                if not data: break
        except Exception as e:
            Clock.schedule_once(lambda dt: self.update_status(f"❌ Failed: {str(e)}"))

    def update_status(self, text):
        self.status_lbl.text = text

if __name__ == '__main__':
    RemoteClient().run()
