import socket
from PyQt5.QtCore import pyqtSignal, QObject, QByteArray
from PyQt5.QtNetwork import QTcpServer, QTcpSocket, QHostAddress, QAbstractSocket



def get_host_ip() -> str:
    """获取本机IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


class TcpLogic(QObject):
    tcp_signal_msg = pyqtSignal(str)
    tcp_signal_data = pyqtSignal(str, bytes)

    def __init__(self):
        super().__init__()
        self.tcp_server = None
        self.tcp_socket = None
        self.client_socket_list = []
        self.link_flag = self.NoLink  # 用于标记是否开启了连接
        self.sever_th = None
        self.client_th = None  # 保留兼容性
        


    def tcp_server_start(self, port: int) -> None:
        """
        功能函数，TCP服务端开启的方法
        """
        self.tcp_server = QTcpServer(self)
        self.tcp_server.newConnection.connect(self._handle_new_connection)

        if self.tcp_server.listen(QHostAddress.AnyIPv4, port):
            self.link_flag = self.ServerTCP
            msg = f"TCP服务端正在监听端口:{port}\n"
            print(msg)
            self.tcp_signal_msg.emit(msg)
        else:
            msg = f"TCP服务端启动失败: {self.tcp_server.errorString()}\n"
            self.tcp_signal_msg.emit(msg)

    def _handle_new_connection(self):
        """处理新的客户端连接"""
        client_socket = self.tcp_server.nextPendingConnection()
        if client_socket:
            client_socket.readyRead.connect(lambda: self._read_data(client_socket))
            client_socket.disconnected.connect(lambda: self._handle_disconnect(client_socket))

            client_address = (client_socket.peerAddress().toString(), client_socket.peerPort())
            self.client_socket_list.append((client_socket, client_address))

            msg = f"TCP服务端已连接{client_address[0]}:{client_address[1]}\n"
            self.tcp_signal_msg.emit(msg)

    def _read_data(self, client_socket):
        """读取客户端发送的数据"""
        for client, address in self.client_socket_list:
            if client == client_socket:
                data = client.readAll()
                if data:
                    # 通过信号发送数据，而不是直接调用方法
                    client_id = f"{address[0]}:{address[1]}"
                    self.tcp_signal_data.emit(client_id, bytes(data))
                break

    def _handle_disconnect(self, client_socket):
        """处理客户端断开连接"""
        for client, address in list(self.client_socket_list):
            if client == client_socket:
                self.client_socket_list.remove((client, address))
                client.deleteLater()
                msg = f"客户端断开连接 IP:{address[0]}端口:{address[1]}\n"
                self.tcp_signal_msg.emit(msg)
                break

    def tcp_client_start(self, ip, port):
        """
        功能函数，TCP客户端连接服务器的方法
        """
        self.tcp_socket = QTcpSocket(self)
        self.tcp_socket.connected.connect(self._handle_connected)
        self.tcp_socket.disconnected.connect(self._handle_client_disconnect)
        self.tcp_socket.readyRead.connect(self._handle_client_read)
        self.tcp_socket.error.connect(self._handle_error)

        self.tcp_socket.connectToHost(QHostAddress(ip), port)
        self.link_flag = self.ClientTCP

    def _handle_connected(self):
        """处理客户端连接成功"""
        msg = f"已连接到服务器\n"
        self.tcp_signal_msg.emit(msg)

    def _handle_client_disconnect(self):
        """处理客户端断开连接"""
        msg = "与服务器断开连接\n"
        self.tcp_signal_msg.emit(msg)
        self.link_flag = self.NoLink

    def _handle_client_read(self):
        """处理客户端接收服务端的数据"""
        data = self.tcp_socket.readAll()
        if data:
            info = bytes(data).decode("utf-8")
            msg = "接收到服务器数据:"
            self.tcp_signal_msg.emit(msg)
            self.tcp_signal_msg.emit(info)

    def _handle_error(self, socket_error):
        """处理连接错误"""
        error_msg = f"连接错误: {self.tcp_socket.errorString()}\n"
        self.tcp_signal_msg.emit(error_msg)
        self.link_flag = self.NoLink

    def tcp_send(self, send_data):
        """
        功能函数，用于TCP服务端和客户端发送消息
        """
        if self.link_flag == self.ServerTCP:
            # 向所有连接的客户端发送数据
            for client, _ in self.client_socket_list:
                client.write(QByteArray(send_data.encode('utf-8')))
        elif self.link_flag == self.ClientTCP:
            # 客户端向服务器发送数据
            if self.tcp_socket and self.tcp_socket.state() == QAbstractSocket.ConnectedState:
                self.tcp_socket.write(QByteArray(send_data.encode('utf-8')))

    def tcp_close(self) -> None:
        """
        功能函数，关闭网络连接的方法
        """
        if self.link_flag == self.ServerTCP:
            # 关闭所有客户端连接
            for client, _ in self.client_socket_list:
                client.close()
                client.deleteLater()

            self.client_socket_list = []

            # 关闭服务器
            if self.tcp_server:
                self.tcp_server.close()
                self.tcp_server.deleteLater()
                self.tcp_server = None

            msg = "已断开网络\n"
            self.tcp_signal_msg.emit(msg)
            self.link_flag = self.NoLink

        elif self.link_flag == self.ClientTCP:
            # 关闭客户端连接
            if self.tcp_socket:
                self.tcp_socket.close()
                self.tcp_socket.deleteLater()
                self.tcp_socket = None

            msg = "已断开网络\n"
            self.tcp_signal_msg.emit(msg)
            self.link_flag = self.NoLink
        



    NoLink = -1
    ServerTCP = 0
    ClientTCP = 1


