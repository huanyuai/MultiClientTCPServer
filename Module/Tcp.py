import socket
import threading
from time import sleep
import select
import errno  # 添加errno模块

from PyQt5.QtCore import pyqtSignal

from . import StopThreading
def get_host_ip() -> str:
    """获取本机IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


class TcpLogic:
    tcp_signal_write_msg = pyqtSignal(str)

    def __init__(self):
        self.tcp_socket = None
        self.sever_th = None
        self.client_th = None
        self.client_socket_list = list()
        self.link_flag = self.NoLink  # 用于标记是否开启了连接
        # self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.buffer_manager = None  # 由MainWindow注入

    def tcp_server_start(self, port: int) -> None:
        """
        功能函数，TCP服务端开启的方法
        """
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65535)  # 增大接收缓冲区
        self.tcp_socket.setblocking(False)
        self.tcp_socket.bind(("", port))
        self.tcp_socket.listen(5)  # 限制最大同时等待连接数
        self.sever_th = threading.Thread(target=self.tcp_server_concurrency)
        self.sever_th.start()
        msg = "TCP服务端正在监听端口:%s\n" % str(port)
        self.tcp_signal_write_msg.emit(msg)

    def tcp_server_concurrency(self):
        """重构select监听逻辑"""
        inputs = [self.tcp_socket]
        while getattr(threading, "do_run", True):
            try:
                read_list = inputs + [client[0] for client in self.client_socket_list]
                readable, _, _ = select.select(read_list, [], [], 0.1)
                
                for sock in readable:
                    if sock is self.tcp_socket:
                        self._accept_new_connection()
                    else:
                        self._handle_client_data(sock)
                    
                self._check_disconnections()

            except Exception as e:
                print(f"服务器异常: {e}")
                break

    def _accept_new_connection(self):
        try:
            client_socket, client_address = self.tcp_socket.accept()
            client_socket.setblocking(False)
            self.client_socket_list.append((client_socket, client_address))
            print(f"[网络] 新连接: {client_address}")
            msg = f"TCP服务端已连接IP:{client_address[0]}端口:{client_address[1]}\n"
            self.tcp_signal_write_msg.emit(msg)
        except BlockingIOError:
            pass

    def _handle_client_data(self, sock):
        for client, address in self.client_socket_list[:]:
            if sock is client:
                try:
                    total_received = 0
                    data = bytearray()
                    while total_received < 1024*1024:
                        try:
                            chunk = client.recv(8192)
                            if not chunk:
                                break
                            data.extend(chunk)
                            total_received += len(chunk)
                        except IOError as e:
                            if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                                break  # 非阻塞模式下无数据可读
                            else:
                                raise  # 重新抛出其他异常
                                
                    if data:
                        print(f"[网络] 收到来自 {address} 的 {len(data)}字节数据")
                        self._process_data(data, address)
                    else:
                        print(f"[网络] 客户端 {address} 断开连接")
                        self._disconnect_client(client, address)
                    
                except ConnectionResetError:
                    print(f"[网络] 客户端 {address} 异常断开")
                    self._disconnect_client(client, address)

    def _process_data(self, data, address):
        client_id = f"{address[0]}:{address[1]}"
        print(f"存入缓冲区: {client_id} - {len(data)}字节")
        self.buffer_manager.add_data(client_id, data)


    def _disconnect_client(self, client, address):
        """断开客户端连接"""
        client.close()
        self.client_socket_list.remove((client, address))
        msg = f"客户端{address}已断开\n"
        self.tcp_signal_write_msg.emit(msg)

    def _check_disconnections(self):
        """定期检查断开连接"""
        for client, address in self.client_socket_list[:]:
            try:
                # 发送空数据测试连接状态
                client.send(b'')
            except (ConnectionResetError, BrokenPipeError):
                self._disconnect_client(client, address)

    def tcp_client_start(self, ip: str, port: int) -> None:
        """
        功能函数，TCP客户端连接其他服务端的方法
        """
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        address = (ip, port)
        try:
            msg = "正在连接目标服务器……\n"
            self.tcp_signal_write_msg.emit(msg)
            self.tcp_socket.connect(address)
        except Exception as ret:
            msg = "无法连接目标服务器\n"
            self.tcp_signal_write_msg.emit(msg)
        else:
            self.client_th = threading.Thread(
                target=self.tcp_client_concurrency, args=(address,)
            )
            self.client_th.start()
            msg = "TCP客户端已连接IP:%s端口:%s\n" % address
            self.tcp_signal_write_msg.emit(msg)

    def tcp_client_concurrency(self, address) -> None:
        """
        功能函数，用于TCP客户端创建子线程的方法，阻塞式接收
        """
        while True:
            recv_msg = self.tcp_socket.recv(4096)
            if recv_msg:
                info = recv_msg.decode("utf-8")
                msg = f"来自IP:{address[0]}端口:{address[1]}:"
                self.tcp_signal_write_msg.emit(msg)
                self.tcp_signal_write_info.emit(info, self.InfoRec)
            else:
                self.tcp_socket.close()
                msg = "从服务器断开连接\n"
                self.tcp_signal_write_msg.emit(msg)
                break

    def tcp_send(self, send_info: str) -> None:
        """
        功能函数，用于TCP服务端和TCP客户端发送消息
        """
        try:
            send_info_encoded = send_info.encode("utf-8")
            if self.link_flag == self.ServerTCP:
                # 向所有连接的客户端发送消息
                if self.client_socket_list:
                    for client, address in self.client_socket_list:
                        client.send(send_info_encoded)
                    msg = "TCP服务端已发送"
                    self.tcp_signal_write_msg.emit(msg)
                    self.tcp_signal_write_info.emit(send_info, self.InfoSend)
            if self.link_flag == self.ClientTCP:
                self.tcp_socket.send(send_info_encoded)
                msg = "TCP客户端已发送"
                self.tcp_signal_write_msg.emit(msg)
                self.tcp_signal_write_info.emit(send_info, self.InfoSend)
        except Exception as ret:
            msg = "发送失败\n"
            self.tcp_signal_write_msg.emit(msg)

    def tcp_close(self) -> None:
        """
        功能函数，关闭网络连接的方法
        """
        if self.link_flag == self.ServerTCP:
            for client, address in self.client_socket_list:
                client.shutdown(socket.SHUT_RDWR)
                client.close()
            self.client_socket_list = list()  # 把已连接的客户端列表重新置为空列表
            self.tcp_socket.close()
            msg = "已断开网络\n"
            self.tcp_signal_write_msg.emit(msg)

            try:
                StopThreading.stop_thread(self.sever_th)
            except Exception as ret:
                pass

        elif self.link_flag == self.ClientTCP:
            try:
                self.tcp_socket.shutdown(socket.SHUT_RDWR)
                self.tcp_socket.close()
                msg = "已断开网络\n"
                self.tcp_signal_write_msg.emit(msg)
            except Exception as ret:
                pass

            try:
                StopThreading.stop_thread(self.client_th)
            except Exception as ret:
                pass

    NoLink = -1
    ServerTCP = 0
    ClientTCP = 1
    InfoSend = 0
    InfoRec = 1

    CLIENT_TIMEOUT = 60      # 客户端超时时间
    MAX_QUEUE_SIZE = 1000    # 最大待处理事件数
