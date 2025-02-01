import PyQt5
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import QObject, pyqtSignal
import sys
import UI.MainWindow as UI
from Network import NetworkLogic


class MainWindow(UI.MainWindow):
    def __init__(self, parent=None):
        super().__init__()
        self.Network = NetworkLogic()
        self.tool_ui = UI.MainWindow()  # Qt 界面实例
        # 仅保留TCP服务端相关信号连接
        self.link_signal.connect(self.link_signal_handler)
        self.disconnect_signal.connect(self.disconnect_signal_handler)
        # self.Network.tcp_signal_write_msg.connect(self.msg_write)
        # self.Network.tcp_signal_write_info.connect(self.info_write)

    def link_signal_handler(self, signal):
        # 仅处理TCP服务端启动
        link_type, _, port = signal
        if link_type == self.ServerTCP:
            self.Network.tcp_server_start(port)

    def disconnect_signal_handler(self):
        if self.link_flag == self.ServerTCP:
            self.Network.tcp_close()

    def run(self):
        self.tool_ui.show()  # 显示界面


# 主程序入口
if __name__ == "__main__":
    app = PyQt5.QtWidgets.QApplication(sys.argv)
    ui = MainWindow()
    ui.run()  # ui就会显示出来
    sys.exit(app.exec_())
