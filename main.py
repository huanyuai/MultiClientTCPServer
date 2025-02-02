import PyQt5
from PyQt5.QtWidgets import QMainWindow

import sys

from Network import NetworkLogic
from UI.MainWindow import MainWindowLogic


class MainWindow(MainWindowLogic, NetworkLogic):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 仅保留TCP服务端相关信号连接
        self.link_signal.connect(self.link_signal_handler)
        self.disconnect_signal.connect(self.disconnect_signal_handler)
        self.tcp_signal_write_msg.connect(self.msg_write)
        self.tcp_signal_write_info.connect(self.info_write)
        # self.tcp_server_start(1137)

    def link_signal_handler(self, port):
        # 仅处理TCP服务端启动
        self.tcp_server_start(port)

    def disconnect_signal_handler(self):
        if self.link_flag == self.ServerTCP:
            self.tcp_close()

    def run(self):
        self.show()  # 显示界面


# 主程序入口
if __name__ == "__main__":
    app = PyQt5.QtWidgets.QApplication(sys.argv)
    ui = MainWindow()
    ui.run()  # ui就会显示出来
    sys.exit(app.exec_())
