"""
主界面 - 数据可视化模块
功能：
1. 实时波形显示
2. 多客户端独立视图
3. 动态颜色分配
"""

import numpy as np
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QFileDialog
from Module.Tcp import get_host_ip
from UI import MainWindowUI
import pyqtgraph as pg
import threading
import gc
import pandas as pd


class MainWindowLogic(QMainWindow):
    link_signal = pyqtSignal(int)  # 仅保留服务端信号
    disconnect_signal = pyqtSignal()
    counter_signal = pyqtSignal(int, int)
    filename_signal = pyqtSignal(str)
    

    def __init__(self, parent=None):
        # 通过super调用父类构造函数，创建QWidget窗体，这样self就是一个窗体对象了
        # GUI界面与逻辑分离
        super().__init__(parent)
        # self.setWindowFlags(Qt.WindowStaysOnTopHint)  # 保持窗口最前
        self.__ui = MainWindowUI.Ui_MainWindow()
        # 创建UI对象，私有属性__ui包含了可视化设计的UI窗体上的所有组件，所以只有通过
        # self.__ui才可以访问窗体上的组件，包括调用setupUi函数
        # 而__ui是私有属性，在类外部创建对象，是无法通过对象访问窗体上的组件的，为了访问组件，可以定义接口，实现功能
        # 需要在定义组件之前
        pg.setConfigOptions(
            useOpenGL=True,
            antialias=False,
            enableExperimental=False,
            background='w',
            foreground='k'
        )

        self.__ui.setupUi(self)

        self.__ui.lineEdit_myIP.setText(get_host_ip())  # 显示本机IP地址 
        self.receive_show_flag = True
        self.ReceiveCounter = 0
        # 仅保留必要信号连接
        self.__ui.pushButton_connect.toggled.connect(self.connect_button_toggled_handler)
        self.__ui.pushButton_clear.clicked.connect(self.clear_all_waveforms)  # 连接清除按钮
        self.__ui.pushButton_import.clicked.connect(self.openfile)  # 导入波形
        
        # 配置绘图参数
        self.max_points = 1000  # 显示点数
        self.waveform_data = {}  # {client_id: {'curve', 'x', 'y'}}
        self.plot_row = 0
        # 启用硬件加速
        self.__ui.graphicsView_plot.useOpenGL()
    def openfile(self):
        fileName_choose, filetype = QFileDialog.getOpenFileName(  
            self,  
            "选取文件",  
            '', 
            "All Files (*);;Text Files (*.txt);;CSV Files (*.csv)")  # 添加CSV过滤
        if fileName_choose == "":
            return
        
        # CSV文件处理逻辑
        if fileName_choose.lower().endswith('.csv'):
            try:
                df = pd.read_csv(fileName_choose)
                if not all(col in df.columns for col in ['AX', 'AY', 'AZ']):
                    QMessageBox.warning(self, "格式错误", "CSV文件中未找到AX、AY、AZ列")
                    return
                
                # 清除现有波形
                self.clear_all_waveforms()
                
                # 分别处理三轴数据
                for col, axis in zip(['AX', 'AY', 'AZ'], ['X轴', 'Y轴', 'Z轴']):
                    data = df[col].astype(int).tolist()
                    self.update_waveform(f"CSV_{axis}", data)
                
                # 计算矢量幅度并添加为第四条波形
                ax_data = np.array(df['AX'].astype(int))
                ay_data = np.array(df['AY'].astype(int))
                az_data = np.array(df['AZ'].astype(int))
                
                # 计算矢量幅度: sqrt(x^2 + y^2 + z^2)
                magnitude = np.sqrt(ax_data**2 + ay_data**2 + az_data**2).tolist()
                self.update_waveform("CSV_矢量幅度", magnitude)
                
                QMessageBox.information(self, "成功", "CSV文件导入完成")
                return
                
            except Exception as e:
                QMessageBox.warning(self, "读取错误", f"CSV文件处理失败: {str(e)}")
                return
        
        # 原有文件处理逻辑
        self.filename_signal.emit(fileName_choose)
        
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
        """直接显示预处理好的消息"""
        self.__ui.textBrowser_history.append(msg)
        self.ReceiveCounter += 1

    def click_disconnect(self):
        self.disconnect_signal.emit()

    def update_waveform(self, client_id: str, batch: list):
        """更新指定客户端的波形"""
        if client_id not in self.waveform_data:
            self._init_client_plot(client_id)

        data = self.waveform_data[client_id]

        # 追加新数据
        data['y'] = np.append(data['y'], batch)
        data['x'] = np.arange(len(data['y']))  # X轴为采样点序号

        # 更新曲线
        if len(data['y']) > self.max_points:
            data['curve'].setData(x=data['x'], y=data['y'], _callSync='off')
        else:
            data['curve'].setData(x=data['x'][-self.max_points:],
                                  y=data['y'][-self.max_points:],
                                  _callSync='off')

        # 优化视图更新
        data['plot'].enableAutoRange(enable=False)  # 禁用自动范围
        if len(data['y']) > self.max_points:
            x_range = (len(data['y']) - self.max_points, len(data['y']))
        else:
            x_range = (0, self.max_points)
        data['plot'].setXRange(*x_range, padding=0)
        data['plot'].setYRange(np.min(data['y'][-self.max_points:]),
                               np.max(data['y'][-self.max_points:]),
                               padding=0.1)

    def _init_client_plot(self, client_id):
        """为每个客户端创建独立绘图行"""
        plot = self.__ui.graphicsView_plot.addPlot(row=self.plot_row, col=0)
        plot.setTitle(title=client_id, size="8pt")
        self.plot_row += 1  # 下个客户端绘制在新行

        # 初始化数据存储
        self.waveform_data[client_id] = {
            'plot': plot,
            'curve': plot.plot(pen=self._gen_color(client_id)),
            'x': np.array([], dtype=np.int32),
            'y': np.array([], dtype=np.float32)
        }

    @staticmethod
    def _gen_color(client_id) -> pg.mkPen:
        """生成客户端唯一颜色"""
        return pg.mkColor(hash(client_id) % 0xFFFFFF | 0xFF000000)

    def clear_all_waveforms(self):
        """安全清空所有波形数据"""
        # 加锁防止数据竞争
        with threading.Lock():
            # 逐个移除客户端绘图
            for client_id in list(self.waveform_data.keys()):
                item = self.waveform_data[client_id]['plot']
                self.__ui.graphicsView_plot.removeItem(item)
            
            # 重置数据结构
            self.waveform_data = {}
            self.plot_row = 0  # 重置行计数器
            
            # 清理图形视图缓存
            self.__ui.graphicsView_plot.clear()

        # 强制垃圾回收
        gc.collect()
        
        # 打印调试信息
        print(f"[DEBUG] 已释放 {len(self.waveform_data)} 个客户端波形数据")
        self.statusBar().showMessage("已清除所有波形数据", 3000)  # 显示3秒

    ServerTCP = 0
