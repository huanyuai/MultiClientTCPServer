from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from Network import get_host_ip
from UI import MainWindowUI as UI


class MainWindowLogic(QMainWindow):
    link_signal = pyqtSignal(int)  # 仅保留服务端信号
    disconnect_signal = pyqtSignal()
    counter_signal = pyqtSignal(int, int)

    def __init__(self, parent=None):
        # 通过super调用父类构造函数，创建QWidget窗体，这样self就是一个窗体对象了
        # GUI界面与逻辑分离
        super().__init__(parent)
        # self.setWindowFlags(Qt.WindowStaysOnTopHint)  # 保持窗口最前
        self.__ui = UI.Ui_MainWindow()
        # 创建UI对象，私有属性__ui包含了可视化设计的UI窗体上的所有组件，所以只有通过
        # self.__ui才可以访问窗体上的组件，包括调用setupUi函数
        # 而__ui是私有属性，在类外部创建对象，是无法通过对象访问窗体上的组件的，为了访问组件，可以定义接口，实现功能
        self.__ui.setupUi(self)
        self.__ui.lineEdit_myIP.setText(get_host_ip())  # 显示本机IP地址

        self.link_flag = self.NoLink
        self.receive_show_flag = True
        self.ReceiveCounter = 0
        # 仅保留必要信号连接

        self.__ui.pushButton_connect.toggled.connect(self.connect_button_toggled_handler)

    def connect_button_toggled_handler(self, state):
        if state:
            self.click_link_handler()
        else:
            self.click_disconnect()
            self.editable(True)

    def editable(self, able: bool = True):
        """仅控制本地端口输入"""
        self.__ui.spinBox_port.setReadOnly(not able)

    def click_link_handler(self):
        """简化连接逻辑，仅处理TCP服务端"""
        port = self.__ui.spinBox_port.value()
        if not port:
            QMessageBox.critical(self, "错误", "请输入本地端口号")
            self.__ui.pushButton_connect.setChecked(False)
            return

        try:
            if not (0 < port <= 65535):
                raise ValueError
        except ValueError:
            QMessageBox.critical(self, "错误", "无效端口号")
            self.__ui.pushButton_connect.setChecked(False)
            return

        self.editable(False)
        self.link_signal.emit(port)
        self.link_flag = self.ServerTCP

    def msg_write(self, msg: str):
        """接收信息显示"""
        print(msg)
        self.__ui.textBrowser_history.append(msg)

    def info_write(self, info: str, client_info: str):
        """带客户端信息的显示"""
        formatted = f'<font color="blue">[{client_info}] {info}</font>\n'
        print(formatted)
        self.__ui.textBrowser_history.append(formatted)
        self.ReceiveCounter += 1
        # self.counter_signal.emit(0, self.ReceiveCounter)

    def click_disconnect(self):
        self.disconnect_signal.emit()
        self.link_flag = self.NoLink

    NoLink = -1
    ServerTCP = 0
    InfoRec = 1
