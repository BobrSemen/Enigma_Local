import socket  # модуль для работы с TCP-сокетами
import threading  # для запуска приёма сообщений в отдельном потоке
import tkinter as tk  # GUI: окна, виджеты
from tkinter import simpledialog  # диалог ввода небольших строк (ник, ip)

# Секретный ключ для XOR-шифрования (симметричный, простой пример)
KEY = "STC_SECRET_KEY"
# Порт сервера (должен совпадать с портом сервера)
PORT = 5000

def xor_cipher(data, key):
    """Шифрование/дешифрование простым XOR по ключу.
    Принимает строку data и ключ key, возвращает результат как строку.
    Такая схема не защищает данные в реальных приложениях, используется здесь для примера.
    """
    return "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data))

class ChatClient:
    def __init__(self, root):
        # root — корневое окно tkinter
        self.root = root
        self.root.title("Messenger")  # заголовок окна
        self.root.geometry("400x500")  # размер окна
        self.sock = None  # сокет будет присвоен после подключения

        # --- Интерфейс ---
        # Поле чата только для чтения, автопрокрутка вниз при новых сообщениях
        self.chat_field = tk.Text(self.root, state='disabled', wrap='word', font=("Arial", 10))
        self.chat_field.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Стили для разных типов сообщений (ваши, другие, системные)
        self.chat_field.tag_configure("my_msg", background="#e1f5fe", lmargin1=20, lmargin2=20, rmargin=10)
        self.chat_field.tag_configure("other_msg", background="#f5f5f5", lmargin1=10, lmargin2=10, rmargin=20)
        self.chat_field.tag_configure("system", foreground="gray", justify='center', font=("Arial", 8, "italic"))

        # Поле ввода сообщения и привязка Enter к отправке
        self.entry_field = tk.Entry(self.root)
        self.entry_field.bind("<Return>", lambda e: self.send_message())
        self.entry_field.pack(padx=10, pady=5, side=tk.LEFT, fill=tk.X, expand=True)
        
        # Кнопка отправить (альтернатива нажатию Enter)
        tk.Button(self.root, text="Отправить", command=self.send_message).pack(padx=10, pady=5, side=tk.RIGHT)

        # Запрашиваем у пользователя ник и адрес сервера
        self.name = simpledialog.askstring("Имя", "Ваш никнейм:") or "Аноним"
        server_ip = simpledialog.askstring("IP", "IP сервера:", initialvalue="127.0.0.1")
        
        # Если IP введён — пытаемся подключиться, иначе закрываем приложение
        if server_ip:
            self.connect_to_server(server_ip)
        else:
            self.root.destroy()

    def log(self, sender, msg, tag):
        """Добавляет строку в окно чата.
        sender: имя отправителя (пустая строка — вывод только msg),
        msg: текст сообщения,
        tag: тег оформления (my_msg/other_msg/system).
        """
        self.chat_field.config(state='normal')  # разрешаем запись во view
        
        if tag == "system" or not sender:
            # Системные сообщения (centr) или сообщения, где sender не нужен
            self.chat_field.insert(tk.END, f"{msg}\n", tag)
        else:
            # Обычное сообщение с префиксом "Имя: текст"
            self.chat_field.insert(tk.END, f"{sender}: {msg}\n", tag)
            
        self.chat_field.config(state='disabled')  # снова запрет на редактирование пользователем
        self.chat_field.see(tk.END)  # прокрутка к последнему сообщению

    def connect_to_server(self, ip):
        """Устанавливает TCP-соединение с сервером по IP:PORT и запускает поток приёма."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # создаём TCP-сокет
            self.sock.connect((ip, PORT))  # подключаемся к серверу
            # Показываем приветственное системное сообщение в чате
            self.log("", f"[*] Добро пожаловать, {self.name}!", "system")
            # Запускаем поток, который постоянно читает входящие данные
            threading.Thread(target=self.receive_loop, daemon=True).start()
        except Exception as e:
            # Если не удалось подключиться — уведомляем пользователя
            self.log("", f"[!] Ошибка подключения: {e}", "system")

    def receive_loop(self):
        """Цикл приёма: получает данные, декодирует и отображает их."""
        while True:
            try:
                # Получаем до 1024 байт и декодируем в строку utf-8
                data = self.sock.recv(1024).decode('utf-8')
                if not data: break  # если пусто — соединение закрыто
                # Дешифруем полученные данные XOR-ключом
                decrypted = xor_cipher(data, KEY)
                # decrypted уже содержит формат "Имя: текст", поэтому sender пустой
                self.log("", decrypted, "other_msg")
            except:
                break  # при ошибке (сеть/сокет) — выходим из цикла
        # После выхода — уведомляем пользователя о разрыве связи
        self.log("", "[!] Связь разорвана.", "system")

    def send_message(self):
        """Берёт текст из поля ввода, отображает локально и отправляет на сервер."""
        msg = self.entry_field.get()
        if msg and self.sock:
            # Локально отображаем как ваше сообщение
            self.log("Вы", msg, "my_msg")
            
            # Формируем полное сообщение "Ник: текст", шифруем и отправляем
            full_msg = f"{self.name}: {msg}"
            encrypted = xor_cipher(full_msg, KEY)
            # Отправляем байты, кодируя в utf-8
            self.sock.send(encrypted.encode('utf-8'))
            
            # Очищаем поле ввода после отправки
            self.entry_field.delete(0, tk.END)

if __name__ == "__main__":
    # Точка входа: создаём GUI и запускаем главный цикл tkinter
    root = tk.Tk()
    ChatClient(root)
    root.mainloop()
# ...existing