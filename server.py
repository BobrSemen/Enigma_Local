# Простой TCP-чатовый сервер: принимает подключения, получает сообщения от клиентов
# и рассылает их всем остальным подключённым клиентам.

import socket  # модуль для сетевых сокетов (TCP/UDP)
import threading  # модуль для работы с потоками (обработчики клиентов в отдельных потоках)

# Порт по умолчанию, на котором будет работать сервер
PORT = 5000

# Список текущих подключённых клиентских сокетов
clients = []

def broadcast(message, current_client):
    """Отправляет зашифрованное сообщение всем, кроме отправителя."""
    # Перебираем копию списка клиентов или сам список — отправляем всем, кроме отправителя
    for client in clients:
        if client != current_client:
            try:
                # Отправка байтового сообщения клиенту
                client.send(message)
            except:
                # Если при отправке возникла ошибка (клиент отключился),
                # безопасно удаляем его из списка клиентов
                if client in clients:
                    clients.remove(client)

def handle_client(client_socket):
    # Обработчик одного клиента, работает в отдельном потоке
    while True:
        try:
            # Ожидаем данные от клиента (макс. 1024 байта за раз)
            message = client_socket.recv(1024)
            # Если пришла пустая строка, клиент закрыл соединение
            if not message:
                break
            # Рассылаем полученное сообщение всем остальным клиентам
            broadcast(message, client_socket)
        except:
            # При ошибке чтения/сети выходим из цикла и завершаем обработчик
            break
    # Убираем сокет клиента из списка при завершении обработки и закрываем его
    if client_socket in clients:
        clients.remove(client_socket)
    client_socket.close()

def start_server(count_users, port):
    # Создаём TCP сокет
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Позволяет быстро перезапускать сервер на том же порту (SO_REUSEADDR)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Привязываем сокет к всем интерфейсам (0.0.0.0) и указанному порту
    server.bind(('0.0.0.0', port))
    # Начинаем слушать входящие подключения, backlog = count_users
    server.listen(count_users)
    # Вывод статуса. Обратите внимание: здесь используется глобальная константа PORT,
    # хотя функция принимает параметр port — в текущем коде они одинаковы.
    print(f"[*] Сервер запущен на порту {PORT}...")

    # Главный цикл: принимаем подключения и создаём для каждого поток-обработчик
    while True:
        client_sock, addr = server.accept()  # блокирует до входящего соединения
        print(f"[+] Подключено: {addr}")  # лог подключения
        clients.append(client_sock)  # добавляем сокет в список клиентов
        # Запускаем функцию-обработчик в отдельном демоническом потоке
        threading.Thread(target=handle_client, args=(client_sock,), daemon=True).start()

if __name__ == "__main__":
    # Точка входа: запускаем сервер с максимально 5 ожидающими подключениями и портом PORT
    start_server(5, PORT)
# ...existing