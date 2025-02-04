import PyQt5
from PyQt5.QtWidgets import QMainWindow

import sys
import threading

from Module.Tcp import TcpLogic
from UI.MainWindow import MainWindowLogic
from Module.RingBuffer import BufferManager
from Module.DataProcessor import DataProcessor


class MainWindow(MainWindowLogic, TcpLogic):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.buffer_manager = BufferManager()
        self.processor = DataProcessor(self.buffer_manager)
        self.proc_thread = threading.Thread(target=self.processor.start_processing)
        self.proc_thread.start()

        # 确保信号正确连接
        self.tcp_signal_write_msg.connect(self.msg_write)
        self.link_signal.connect(self.link_signal_handler)
        self.disconnect_signal.connect(self.disconnect_signal_handler)
        self.processor.update_signal.connect(self.msg_write)

    def link_signal_handler(self, port):
        # 仅处理TCP服务端启动

        self.tcp_server_start(port)

    def disconnect_signal_handler(self):
        if self.link_flag == self.ServerTCP:
            self.tcp_close()

    def run(self):
        self.show()  # 显示界面

    def closeEvent(self, event):
        self.processor.running = False
        self.proc_thread.join()
        super().closeEvent(event)

    def set_display_format(self, show_time=True, show_client=True):
        """设置消息显示格式"""
        self.processor.set_display_format(show_time, show_client)


# 主程序入口
if __name__ == "__main__":
    app = PyQt5.QtWidgets.QApplication(sys.argv)
    ui = MainWindow()
    ui.run()  # ui就会显示出来
    sys.exit(app.exec_())
