from PyQt5.QtWidgets import QInputDialog, QLabel, QLineEdit, QPushButton, QMainWindow


# 该文件用于自定义UI组件


class ConnectButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.toggled.connect(self.toggled_slot)

    def toggled_slot(self):
        """
        连接按钮状态切换时的额外操作
        """
        if not self.isChecked():
            self.setText("连接网络")
        else:
            self.setText("断开连接")

