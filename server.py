import socket
import threading

PORT = 5000
clients = []

def broadcast(message, current_client):
    """Отправляет зашифрованное сообщение всем, кроме отправителя."""
    for client in clients:
        if client != current_client:
            try:
                client.send(message)
            except:
                if client in clients:
                    clients.remove(client)

def handle_client(client_socket):
    while True:
        try:
            message = client_socket.recv(1024)
            if not message: break
            broadcast(message, client_socket)
        except:
            break
    if client_socket in clients:
        clients.remove(client_socket)
    client_socket.close()

def start_server(count_users, port):
    # Используем 0.0.0.0, чтобы принимать подключения со всех интерфейсов
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', port))
    server.listen(count_users)
    print(f"[*] Сервер запущен на порту {PORT}...")

    while True:
        client_sock, addr = server.accept()
        print(f"[+] Подключено: {addr}")
        clients.append(client_sock)
        threading.Thread(target=handle_client, args=(client_sock,), daemon=True).start()

if __name__ == "__main__":
    start_server(5, PORT)