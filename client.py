import socket  # модуль для работы с TCP-сокетами
import threading  # для запуска приёма сообщений и сканера в отдельных потоках
import tkinter as tk  # GUI: окна и виджеты
from tkinter import simpledialog  # простые модальные диалоги ввода строк
import ctypes  # для настройки DPI на Windows
import ipaddress  # для вычисления диапазона IP в локальной подсети
import serial  # модуль для связи с платой TrackDuino (pip install pyserial)
import time

# Попытка включить поддержку DPI на Windows (не критично, обернуто в try/except)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    # Если не удалось — продолжаем без ошибки
    pass

# --- НАСТРОЙКИ ПЛАТЫ ---
SERIAL_PORT = 'COM3'  # Укажите порт вашей платы (из Arduino IDE)
BAUD_RATE = 9600      # Скорость должна совпадать со скоростью в Serial.begin()

try:
    # Инициализация подключения к TrackDuino
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    print(f"[!] TrackDuino подключена на порта {SERIAL_PORT}")
except Exception as e:
    # Если плата не подключена, клиент продолжит работу как обычный чат
    print(f"[!] Плата не обнаружена: {e}")
    arduino = None

# Секретный ключ для простого XOR-шифрования (симметричный, демонстрационный)
KEY = "STC_SECRET_KEY"
# Порт сервера (должен совпадать с серверным)
PORT = 5000

def xor_cipher(data, key):
    """Шифрование/дешифрование простым XOR по ключу.
    Принимает строку data и ключ key, возвращает строку того же размера.
    ВНИМАНИЕ: это НЕ безопасное шифрование, используется только в учебных примерах.
    """
    return "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data))

class ChatClient:
    """GUI-клиент для подключение к простому TCP-чату.
    Отображает окно, сканирует локальную сеть для поиска сервера и общается по TCP.
    """
    def __init__(self, root):
        # Сохранение корневого окна tkinter
        self.root = root
        self.root.title("Messenger + TrackDuino")
        # Фиксированный размер окна и запрет изменения размера
        self.root.geometry("450x600")
        self.root.resizable(False, False)

        # --- Интерфейс: поле чата ---
        # Текстовое поле только для чтения (state='disabled') — будем включать/выключать при вставке
        self.chat_field = tk.Text(
            self.root,
            state='disabled',
            wrap='word',
            font=("Segoe UI", 11),
            bg="#ffffff",
            fg="#333333",
            padx=10,
            pady=10,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground="#cccccc"
        )
        # Размещение поля через абсолютные относительные координаты (place)
        self.chat_field.place(relx=0.05, rely=0.05, relwidth=0.9, relheight=0.75)

        # Теги для форматирования сообщений в поле чата
        # "my_msg" — сообщения пользователя, "other_msg" — от других, "system" — служебные
        self.chat_field.tag_configure("my_msg", background="#dcf8c6", lmargin1=20, lmargin2=20)
        self.chat_field.tag_configure("other_msg", background="#ebebeb", lmargin1=10, lmargin2=10)
        self.chat_field.tag_configure("system", foreground="#7f8c8d", justify='center', font=("Segoe UI", 9, "italic"))

        # Поле ввода текста и привязка Enter к отправке
        self.entry_field = tk.Entry(self.root, font=("Segoe UI", 12), borderwidth=5, relief=tk.FLAT)
        self.entry_field.bind("<Return>", lambda e: self.send_message())
        self.entry_field.place(relx=0.05, rely=0.85, relwidth=0.65, relheight=0.08)

        # Кнопка отправки сообщения
        self.send_btn = tk.Button(
            self.root,
            text="➤",
            command=self.send_message,
            bg="#27ae60",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.send_btn.place(relx=0.72, rely=0.85, relwidth=0.23, relheight=0.08)

        # 1) Запрашиваем ник у пользователя (модальный диалог)
        self.name = simpledialog.askstring("Имя", "Ваш никнейм:") or "Аноним"

        # 2) Автоматический поиск IP в локальной сети и выбор сервера
        server_ip = self.discover_ip()

        # Если IP найден/введён — подключаемся, иначе — закрываем GUI
        if server_ip:
            self.connect_to_server(server_ip)
        else:
            self.root.destroy()

    def discover_ip(self):
        """Сканирует локальную /24 подсеть и предлагает IP для подключения.
        Возвращает строку с IP или None.
        """
        # Всплывающее окно "Поиск" — информирует пользователя о процессе
        wait_win = tk.Toplevel(self.root)
        wait_win.title("Поиск")
        wait_win.geometry("250x100")
        tk.Label(wait_win, text="\nПоиск серверов в сети...\nПожалуйста, подождите.").pack()
        # Делает окно модальным (блокирует взаимодействие с основным окном)
        wait_win.grab_set()

        found_ips = []  # список найденных адресов с доступным PORT
        scan_done = threading.Event()  # событие, сигнализирующее об окончании сканирования

        def scan(ip):
            """Проверка конкретного IP: открыт ли TCP-порт PORT."""
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)  # короткий таймаут для ускорения сканирования
                # connect_ex возвращает 0 при успешном соединении
                if s.connect_ex((str(ip), PORT)) == 0:
                    found_ips.append(str(ip))

        def run_scanner():
            """Фоновой запуск сканирования диапазона адресов подсети."""
            try:
                # Попытка получить локальный IP по имени хоста
                my_ip = socket.gethostbyname(socket.gethostname())
                # Формируем подсеть /24 на основе локального IP
                subnet = ".".join(my_ip.split(".")[:-1]) + ".0/24"
                # Создаём потоки для проверки каждого адреса в подсети
                threads = [threading.Thread(target=scan, args=(ip,)) for ip in ipaddress.IPv4Network(subnet)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
            except Exception:
                # Если что-то пошло не так — просто завершаем сканирование
                pass
            finally:
                # Сигнал завершения сканирования (независимо от результата)
                scan_done.set()

        # Запуск сканера в отдельном потоке, чтобы не блокировать GUI
        threading.Thread(target=run_scanner, daemon=True).start()

        # Периодически проверяем состояние и закрываем окно по завершении
        def check_status():
            if scan_done.is_set():
                wait_win.destroy()
            else:
                wait_win.after(100, check_status)

        wait_win.after(100, check_status)
        # Ждём закрытия окна wait_win (модальность)
        self.root.wait_window(wait_win)

        # После сканирования: если ничего не найдено — предлагаем ввести IP вручную
        if not found_ips:
            return simpledialog.askstring("IP", "Серверы не найдены.\nВведите IP вручную:", initialvalue="127.0.0.1")
        else:
            # Формируем сообщение со списком найденных адресов и предлагаем выбрать/ввести IP
            msg = "Найдены активные серверы:\n" + "\n".join(found_ips) + "\n\nВведите IP для подключения:"
            # По умолчанию подставляем первый найденный адрес
            return simpledialog.askstring("Выбор сервера", msg, initialvalue=found_ips[0])

    def log(self, sender, msg, tag):
        """Добавляет строку в окно чата.
        sender: имя отправителя (строка) — если пусто, выводится как системное сообщение.
        msg: текст сообщения.
        tag: тег форматирования ('my_msg', 'other_msg', 'system').
        """
        # Разрешаем редактирование временно, чтобы вставить текст
        self.chat_field.config(state='normal')
        if tag == "system" or not sender:
            # Системные сообщения выводим отдельно
            self.chat_field.insert(tk.END, f"\n{msg}\n", tag)
        else:
            # Нормальные сообщения с префиксом "Имя: текст"
            self.chat_field.insert(tk.END, f"\n{sender}: {msg}\n", tag)
        # Возвращаем поле в режим только для чтения и прокручиваем вниз
        self.chat_field.config(state='disabled')
        self.chat_field.see(tk.END)

    def connect_to_server(self, ip):
        """Устанавливает TCP-соединение с выбранным IP и запускает приёмный поток."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Попытка подключения к серверу по указанному IP и порту
            self.sock.connect((ip, PORT))
            

            if arduino:
                status_msg = f"[*] Добро пожаловать, {self.name}! Управление платой готово."
            else:
                status_msg = f"[*] Добро пожаловать, {self.name}! (Плата не подключена)"
            
            # Информируем пользователя о статусе
            self.log("", status_msg, "system")
            # -------------------------------------

            # Запускаем фоновый поток, который будет принимать сообщения от сервера
            threading.Thread(target=self.receive_loop, daemon=True).start()
        except Exception as e:
            # При ошибке подключения выводим сообщение в интерфейс
            self.log("", f"[!] Ошибка подключения: {e}", "system")

    def receive_loop(self):
        """Цикл приёма данных от сервера.
        Полученные байты декодируются в utf-8, затем дешифруются XOR и выводятся.
        В этой версии команды на плату НЕ передаются из сети (приватное управление).
        """
        while True:
            try:
                # Получаем до 1024 байт от сервера (блокирующий вызов)
                data = self.sock.recv(1024).decode('utf-8')
                # Если пришла пустая строка — сервер закрыл соединение
                if not data:
                    break
                # Дешифруем простым XOR и выводим в чат
                decrypted = xor_cipher(data, KEY)
                self.log("", decrypted, "other_msg")
                
                # Здесь мы НЕ вызываем управление платой, чтобы другие не могли ей командовать.
            except Exception:
                # При ошибке (сеть/сокет) прерываем цикл приёма
                break
        # Сообщаем пользователю о разрыве связи
        self.log("", "[!] Связь разорвана.", "system")

    def send_message(self):
        """Берёт текст из поля ввода, отображает локально и отправляет на сервер.
        Также проверяет наличие команд для TrackDuino.
        """
        msg = self.entry_field.get()
        if msg:
            # Отображаем собственное сообщение в интерфейсе
            self.log("Вы", msg, "my_msg")

            # --- БЛОК УПРАВЛЕНИЯ ПЛАТОЙ ---
            # Проверяем: если введена команда для платы и плата физически подключена
            if arduino and "TrackDuino:" in msg:
                try:
                    # Извлекаем текст команды после префикса
                    command = msg.split("TrackDuino:")[1].strip()
                    # Отправляем команду в последовательный порт
                    arduino.write((command + "\n").encode('utf-8'))
                    print(f"[LOCAL] Плата получила команду: {command}")
                except Exception as e:
                    print(f"[!] Ошибка Serial: {e}")

            # Формируем строку вида "Ник: сообщение" и шифруем её
            full_msg = f"{self.name}: {msg}"
            encrypted = xor_cipher(full_msg, KEY)
            try:
                # Отправляем зашифрованную строку в кодировке utf-8
                self.sock.send(encrypted.encode('utf-8'))
            except Exception:
                # При ошибке отправки информируем пользователя
                self.log("", "[!] Ошибка отправки", "system")
            # Очищаем поле ввода
            self.entry_field.delete(0, tk.END)

# Точка входа: создание окна tkinter и запуск клиента
if __name__ == "__main__":
    root = tk.Tk()
    ChatClient(root)
    root.mainloop()