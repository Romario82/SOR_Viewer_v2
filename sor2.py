import sys
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QFileDialog,
                               QWidget, QSizePolicy, QHBoxLayout, QSpacerItem, QListWidget)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pyotdr.read import sorparse
from sor_qt import Ui_MainWindow


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


class SORViewer(QMainWindow):
    def __init__(self):
        super(SORViewer, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Словарь для хранения данных: { "имя_файла": (meta, trace_raw) }
        self.files_data = {}

        # --- НАСТРОЙКА ИНТЕРФЕЙСА ---
        # Основной вертикальный слой
        self.main_layout = QVBoxLayout(self.ui.centralwidget)

        # 1. Кнопка открытия (верхняя панель)
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.ui.OpenSOR)
        self.button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.main_layout.addLayout(self.button_layout)

        # 2. Средняя часть: График слева + Список файлов справа
        self.middle_layout = QHBoxLayout()

        # Контейнер для графика
        self.graph_vbox = QVBoxLayout()
        self.canvas = MplCanvas(self)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.graph_vbox.addWidget(self.toolbar)
        self.graph_vbox.addWidget(self.canvas)

        # Список файлов (Боковая панель)
        self.file_list = QListWidget()
        self.file_list.setFixedWidth(200)
        self.file_list.itemClicked.connect(self.on_file_selected)

        self.middle_layout.addLayout(self.graph_vbox, stretch=4)
        self.middle_layout.addWidget(self.file_list, stretch=1)

        self.main_layout.addLayout(self.middle_layout, stretch=10)

        # 3. Таблица (низ)
        self.ui.tableView.setMaximumHeight(220)
        self.main_layout.addWidget(self.ui.tableView)

        self.model = QStandardItemModel()
        self.ui.tableView.setModel(self.model)

        self.ui.OpenSOR.clicked.connect(self.load_sor_file)

    def load_sor_file(self):
        # Позволяем выбирать сразу несколько файлов (getOpenFileNames)
        files, _ = QFileDialog.getOpenFileNames(self, "Open SOR files", "", "SOR Files (*.sor)")
        if files:
            for file_path in files:
                try:
                    name = file_path.split('/')[-1]
                    # Если файл уже загружен, не дублируем
                    if name not in self.files_data:
                        _, meta, trace_raw = sorparse(file_path)
                        self.files_data[name] = (meta, trace_raw)
                        self.file_list.addItem(name)
                except Exception as e:
                    print(f"Ошибка загрузки {file_path}: {e}")

            # Выбираем последний загруженный файл автоматически
            if self.file_list.count() > 0:
                last_item = self.file_list.item(self.file_list.count() - 1)
                self.file_list.setCurrentItem(last_item)
                self.on_file_selected(last_item)

    def on_file_selected(self, item):
        filename = item.text()
        meta, trace_raw = self.files_data[filename]
        self.process_data(meta, trace_raw)

    def process_data(self, meta, trace_raw):
        # Обработка данных (как в вашем коде)
        distances, powers = [], []
        for line in trace_raw:
            parts = line.strip().split('\t')
            if len(parts) == 2:
                distances.append(float(parts[0]))
                powers.append(float(parts[1]))

        dist_np, pwr_np = np.array(distances), np.array(powers)

        # Отрисовка
        self.canvas.axes.clear()
        self.canvas.axes.plot(dist_np, pwr_np, color='#2c3e50', linewidth=1)
        self.canvas.axes.set_title(f"File: {meta.get('filename', 'N/A')}")
        self.canvas.axes.grid(True, alpha=0.3)
        self.canvas.axes.set_xlabel("Distance (km)")
        self.canvas.axes.set_ylabel("Power (dB)")

        # Таблица событий
        self.model.clear()
        key_events = meta.get('KeyEvents', {})
        num_events = key_events.get('num events', 0)

        row_labels = ["Distance (km)", "Loss (dB)", "Reflection (dB)"]
        self.model.setRowCount(len(row_labels))
        self.model.setVerticalHeaderLabels(row_labels)

        for i in range(1, num_events + 1):
            ev = key_events.get(f'event {i}')
            if ev:
                col = i - 1
                self.model.setHorizontalHeaderItem(col, QStandardItem(f"Event {i}"))
                self.model.setItem(0, col, QStandardItem(str(ev.get('distance', '0'))))
                self.model.setItem(1, col, QStandardItem(str(ev.get('splice loss', '0'))))
                self.model.setItem(2, col, QStandardItem(str(ev.get('refl loss', '0'))))

                # Маркеры
                d = float(ev.get('distance', 0))
                idx = np.abs(dist_np - d).argmin()
                self.canvas.axes.plot(dist_np[idx], pwr_np[idx], 'ro')
                self.canvas.axes.annotate(f"{i}", (dist_np[idx], pwr_np[idx]),
                                          xytext=(0, 5), textcoords='offset points', ha='center')

        self.canvas.draw()
        self.ui.tableView.resizeColumnsToContents()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SORViewer()
    window.show()
    sys.exit(app.exec())