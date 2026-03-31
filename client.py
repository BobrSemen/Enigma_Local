import socket
import threading
import tkinter as tk
from tkinter import simpledialog

KEY = "GUI_SECRET_KEY"
PORT = 5000

def xor_cipher(data, key):
    """Шифрование/дешифрование данных"""
    return "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data))

class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Messenger")
        self.root.geometry("400x500")
        self.sock = None

        # --- Интерфейс ---
        self.chat_field = tk.Text(self.root, state='disabled', wrap='word', font=("Arial", 10))
        self.chat_field.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Настройка стилей
        self.chat_field.tag_configure("my_msg", background="#e1f5fe", lmargin1=20, lmargin2=20, rmargin=10)
        self.chat_field.tag_configure("other_msg", background="#f5f5f5", lmargin1=10, lmargin2=10, rmargin=20)
        self.chat_field.tag_configure("system", foreground="gray", justify='center', font=("Arial", 8, "italic"))

        self.entry_field = tk.Entry(self.root)
        self.entry_field.bind("<Return>", lambda e: self.send_message())
        self.entry_field.pack(padx=10, pady=5, side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(self.root, text="Отправить", command=self.send_message).pack(padx=10, pady=5, side=tk.RIGHT)

        # Данные пользователя
        self.name = simpledialog.askstring("Имя", "Ваш никнейм:") or "Аноним"
        server_ip = simpledialog.askstring("IP", "IP сервера:", initialvalue="127.0.0.1")
        
        if server_ip:
            self.connect_to_server(server_ip)
        else:
            self.root.destroy()

    def log(self, sender, msg, tag):
        """Вывод текста с проверкой на пустой отправитель"""
        self.chat_field.config(state='normal')
        
        if tag == "system" or not sender:
            # Если отправителя нет (сообщение от другого уже содержит имя), выводим как есть
            self.chat_field.insert(tk.END, f"{msg}\n", tag)
        else:
            # Для ваших сообщений (где sender = "Вы") добавляем двоеточие
            self.chat_field.insert(tk.END, f"{sender}: {msg}\n", tag)
            
        self.chat_field.config(state='disabled')
        self.chat_field.see(tk.END)

    def connect_to_server(self, ip):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((ip, PORT))
            self.log("", f"[*] Добро пожаловать, {self.name}!", "system")
            threading.Thread(target=self.receive_loop, daemon=True).start()
        except Exception as e:
            self.log("", f"[!] Ошибка подключения: {e}", "system")

    def receive_loop(self):
        while True:
            try:
                data = self.sock.recv(1024).decode('utf-8')
                if not data: break
                decrypted = xor_cipher(data, KEY)
                # Вызываем с пустым sender, так как decrypted уже выглядит как "Имя: текст"
                self.log("", decrypted, "other_msg")
            except: break
        self.log("", "[!] Связь разорвана.", "system")

    def send_message(self):
        msg = self.entry_field.get()
        if msg and self.sock:
            # Локально пишем "Вы: сообщение"
            self.log("Вы", msg, "my_msg")
            
            # В сеть шлем "Ник: сообщение"
            full_msg = f"{self.name}: {msg}"
            encrypted = xor_cipher(full_msg, KEY)
            self.sock.send(encrypted.encode('utf-8'))
            
            self.entry_field.delete(0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    ChatClient(root)
    root.mainloop()