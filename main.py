import locale
import json
import sqlite3
import sys
import os

from PyQt6 import uic
from PyQt6.QtCore import Qt, QSize, QLocale, QTranslator
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog, QDialog, QMessageBox
from PyQt6.QtGui import QIcon

MAIN_DIR = os.path.dirname(__file__)


class MainMenu(QMainWindow):
    def __init__(self):
        self.projects_view_widget = ProjectsView(self)
        self.create_project_widget = CreateProject(self)
        self.settings_widget = SettingsWidget()

        super().__init__()
        self.initUI()
        self.init_handlers()

    def initUI(self):
        # Основная инициализация UI
        uic.loadUi("ui/main_menu.ui", self)
        self.setFixedSize(820, 600)
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinimizeButtonHint)

        # Установка иконок кнопок
        self.createBtn.setIcon(QIcon("svg/create_icon.svg"))
        self.createBtn.setIconSize(QSize(30, 30))
        self.settingsBtn.setIcon(QIcon("svg/settings_icon.svg"))
        self.settingsBtn.setIconSize(QSize(35, 35))
        self.openBtn.setIcon(QIcon("svg/folder_icon.svg"))
        self.openBtn.setIconSize(QSize(35, 35))

    def init_handlers(self):
        self.settingsBtn.clicked.connect(self.settings_widget.show)
        self.createBtn.clicked.connect(self.create_project_widget.show)
        self.openBtn.clicked.connect(self.projects_view_widget.show)


class SettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Основная инициализация UI
        uic.loadUi("ui/settings_widget.ui", self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint)
        self.setFixedSize(400, 300)


class CreateProject(QWidget):
    def __init__(self, parent):
        self.project_menu = None
        self.parent = parent

        super().__init__()
        self.initUI()
        self.handlers()

    def initUI(self):
        # Основная инициализация UI
        uic.loadUi("ui/create_project.ui", self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint)
        self.setFixedSize(400, 300)

        # Установка иконок кнопок
        self.locationBtn.setIcon(QIcon("svg/folder_icon.svg"))

        # Установка значений LineEdit
        self.locationEdit.setText(f"{MAIN_DIR}\\projects")
        self.createInEdit.setText(f"{self.locationEdit.text()}\\{self.nameEdit.text()}")

    def handlers(self):
        self.createBtn.clicked.connect(self.create_project)
        self.cancelBtn.clicked.connect(self.close)
        self.locationBtn.clicked.connect(self.choose_location)
        self.nameEdit.textChanged.connect(self.set_location_creating)
        self.locationEdit.textChanged.connect(self.set_location_creating)

    def set_location_creating(self):
        self.createInEdit.setText(f"{self.locationEdit.text()}\\{self.nameEdit.text()}")

    def choose_location(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder_path:
            folder_path = folder_path.replace("/", "\\")
            self.locationEdit.setText(folder_path)

    def create_project(self):
        try:
            if self.nameEdit.text():
                project_dir = self.createInEdit.text().replace("\\", "/")
                os.makedirs(f"{project_dir}/files", exist_ok=False)
                with open(f"{project_dir}/files/README.md", "w") as f_readme:
                    with open(f"data/base_readme.txt", "r") as f_base_readme:
                        text = f_base_readme.read()
                    text = f"# {self.nameEdit.text()}\n" + text
                    f_readme.write(text)
            else:
                QMessageBox.information(self, "Не удалось создать проект", "Имя проекта не может быть пустым")
        except FileExistsError:
            QMessageBox.information(self, "Не удалось создать проект", "Папка c таким именем уже существует")
            return

        try:
            with sqlite3.connect("data/toDev.db") as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO projects (title, dir) VALUES (?, ?)",
                               (self.nameEdit.text(), project_dir,))
                response = cursor.execute("SELECT * FROM projects WHERE dir = ?", (project_dir,)).fetchone()
                project_id, title, desc, project_dir, logo, state = response
            with open(f"{project_dir}/config.json", "w") as f_config:
                f_config.write(json.dumps(
                    {"project_id": project_id,
                     "title": title,
                     "description": desc,
                     "dir": project_dir,
                     "logo": logo,
                     "state": state}))
        except Exception:
            QMessageBox.information(self, "Не удалось создать проект",
                                    "База данных не синхронизирована с данными на компьютере")
            return
        self.close()
        self.parent.close()

        # Запуск основного окна
        self.project_menu = ProjectMenu(project_dir)
        self.project_menu.show()


class ProjectsView(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.project_menu = None
        self.parent = parent
        self.search_filters = ['title', 'id', 'state']

        self.initUI()
        self.handlers()

    def initUI(self):
        # Основная инициализация UI
        uic.loadUi("ui/projects_view.ui", self)
        self.setFixedSize(600, 350)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint)

        # Показ всех существующих проектов
        self.search()

    def handlers(self):
        self.requestEdit.textChanged.connect(self.search)
        self.openBtn.clicked.connect(self.open_project)

    def open_project(self):
        project = self.projectsList.currentItem()
        if project:
            project_id = project.text().split('\t')[0]
            with sqlite3.connect("data/toDev.db") as conn:
                cursor = conn.cursor()
                project_dir = cursor.execute("SELECT dir FROM projects WHERE id = ?", (project_id,)).fetchone()
            self.close()
            self.parent.close()

            # Запуск основного окна
            self.project_menu = ProjectMenu(project_dir[0])
            self.project_menu.show()

    def search(self):
        self.projectsList.clear()
        filter_by = self.search_filters[self.parameterSelector.currentIndex()]
        if self.requestEdit.text():
            request = self.requestEdit.text()
            query = f"SELECT id, title, dir, state FROM projects WHERE {filter_by} like '{request}%'"
        else:
            query = "SELECT id, title, dir, state FROM projects"

        with (sqlite3.connect("data/toDev.db") as conn):
            cursor = conn.cursor()
            response = cursor.execute(query).fetchall()
        display_list = ["ID\tИмя\tСтатус\tПуть"]
        for project in response:
            project_id, title, path, state = project
            display_text = (f"{project_id}\t{title}\t{state if state else "Не указан"}"
                            f"\t{path if len(path) <= 33 else path[:30] + '...'}")
            display_list.append(display_text)
        self.projectsList.addItems(display_list)
        titles_item = self.projectsList.item(0)
        titles_item.setFlags(~Qt.ItemFlag.ItemIsEnabled)


class ProjectMenu(QMainWindow):
    def __init__(self, project_dir):
        with open(f"{project_dir}/config.json", "r") as f_config:
            self.config = json.loads(f_config.read())
        self.is_saved = True

        super().__init__()
        self.initUI()
        self.handlers()

    def initUI(self):
        # Основная инициализация UI
        uic.loadUi("ui/project_menu.ui", self)
        self.setWindowTitle(f"{self.config['title']} - {self.config['dir']}")

    def handlers(self):
        self.createAct.triggered.connect(self.create_file)
        self.copyFromAct.triggered.connect(self.file_copy_from)
        self.saveProjectAct.triggered.connect(self.save_project)
        self.exitAct.triggered.connect(self.close)

    def update_title(self):
        prefix = "" if self.is_saved else "*"
        self.setWindowTitle(f"{prefix}{self.config['title']} - {self.config['dir']}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_S and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.save_project()
            event.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, a0):
        if not self.is_saved:
            response = QMessageBox.question(
                self,
                "Выход из toDev",
                f"""Вы хотите сохранить проект "{self.config['title']}"?""",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if response == QMessageBox.StandardButton.Save:
                self.save_project()
                a0.accept()
            elif response == QMessageBox.StandardButton.Discard:
                a0.accept()
            else:
                a0.ignore()
        else:
            a0.accept()

    def create_file(self):
        pass

    def file_copy_from(self):
        pass

    def save_project(self):
        with sqlite3.connect("data/toDev.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE projects SET title = ?, description = ?, dir = ?, logo = ?, state = ? WHERE dir = ?",
                (self.config['title'], self.config['description'], self.config['dir'], self.config['logo'],
                 self.config['state'], self.config['dir'])
            )
        self.is_saved = True
        self.update_title()


def init_db():
    if os.path.isfile("data/toDev.db"):
        return
    with sqlite3.connect("data/toDev.db") as conn:
        with open("scripts/init_db.sql", encoding="utf-8") as f_init_db:
            sql_script = f_init_db.read()
        cursor = conn.cursor()
        cursor.executescript(sql_script)


def init_app():
    os.makedirs("projects", exist_ok=True)
    app = QApplication(sys.argv)
    app.setAttribute(Qt.ApplicationAttribute.AA_Use96Dpi)
    return app


if __name__ == '__main__':
    init_db()
    app = init_app()
    window = MainMenu()
    window.show()
    sys.exit(app.exec())
