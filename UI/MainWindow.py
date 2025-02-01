from UI import MainWindowUI as UI
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QMainWindow
from Network import get_host_ip

class MainWindow(QMainWindow):
    link_signal = pyqtSignal(tuple)  # 仅保留服务端信号
    disconnect_signal = pyqtSignal()
    counter_signal = pyqtSignal(int, int)

    def __init__(self):
        # 通过super调用父类构造函数，创建QWidget窗体，这样self就是一个窗体对象了
        # GUI界面与逻辑分离
        super(MainWindow, self).__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint)  # 保持窗口最前
        self.__ui = UI.Ui_MainWindow()
        # 创建UI对象，私有属性__ui包含了可视化设计的UI窗体上的所有组件，所以只有通过
        # self.__ui才可以访问窗体上的组件，包括调用setupUi函数
        # 而__ui是私有属性，在类外部创建对象，是无法通过对象访问窗体上的组件的，为了访问组件，可以定义接口，实现功能
        self.__ui.setupUi(self)
        self.__ui.lineEdit_myIP.setText(get_host_ip())  # 显示本机IP地址

        self.link_flag = self.NoLink
        self.receive_show_flag = True
        self.ReceiveCounter = 0

    NoLink = -1
    ServerTCP = 0
    InfoRec = 1