import PyQt5
from PyQt5.QtWidgets import QMainWindow

import sys

from Module.Tcp import TcpLogic
from UI.MainWindow import MainWindowLogic
from Module.DataProcessor import DataProcessor

class MainWindow(MainWindowLogic):
    def __init__(self, parent=None):
        # 只继承 MainWindowLogic，使用组合方式包含 TcpLogic
        MainWindowLogic.__init__(self, parent)
        
        # 创建 TcpLogic 实例
        self.tcp_logic = TcpLogic()
        
        # 创建数据处理器 实例
        self.data_processor = DataProcessor(self)
        

        # 连接 TcpLogic 的信号到本类的槽函数
        self.tcp_logic.tcp_signal_msg.connect(self.msg_write)
        self.tcp_logic.tcp_signal_data.connect(self.data_processor.add_data)

        # 连接数据处理器信号
        self.data_processor.text_signal.connect(self.msg_write)
        self.data_processor.waveform_signal.connect(self.update_waveform)

        
        # 保留TCP服务端相关信号连接
        self.link_signal.connect(self.link_signal_handler)
        self.disconnect_signal.connect(self.disconnect_signal_handler)

        


    def link_signal_handler(self, port):
        # 处理TCP服务端启动
        self.tcp_logic.tcp_server_start(port)

    def disconnect_signal_handler(self):
        if self.tcp_logic.link_flag == self.tcp_logic.ServerTCP:
            self.tcp_logic.tcp_close()

    def run(self):
        self.show()  # 显示界面




# 主程序入口
if __name__ == "__main__":
    app = PyQt5.QtWidgets.QApplication(sys.argv)
    ui = MainWindow()
    ui.run()  # ui就会显示出来
    sys.exit(app.exec_())
