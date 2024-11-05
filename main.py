import json
import shutil
import sqlite3
import sys
import os

from PyQt6 import uic
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog, QMessageBox
from PyQt6.QtGui import QIcon


class MainMenu(QMainWindow):
    def __init__(self):
        self.window = None

        super().__init__()
        self.initUI()
        self.init_handlers()

    def initUI(self):
        # Основная инициализация UI
        uic.loadUi("ui/main_menu.ui", self)
        # self.setFixedSize(820, 600)
        self.setWindowFlags(
            Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinimizeButtonHint
        )

        # Установка иконок кнопок
        self.createBtn.setIcon(QIcon("svg/create_icon.svg"))
        self.createBtn.setIconSize(QSize(30, 30))
        self.settingsBtn.setIcon(QIcon("svg/settings_icon.svg"))
        self.settingsBtn.setIconSize(QSize(35, 35))
        self.openBtn.setIcon(QIcon("svg/folder_icon.svg"))
        self.openBtn.setIconSize(QSize(35, 35))

    def init_handlers(self):
        self.settingsBtn.clicked.connect(self.show_widget)
        self.createBtn.clicked.connect(self.show_widget)
        self.openBtn.clicked.connect(self.show_widget)

    def show_widget(self):
        sender = self.sender()
        if sender == self.createBtn:
            self.window = CreateProject(self)
        elif sender == self.settingsBtn:
            self.window = SettingsWidget()
        elif sender == self.openBtn:
            self.window = ProjectsView(self)
        self.window.show()


class SettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

        # Обработчик self.editProjectsDirButton
        self.editProjectsDirBtn.clicked.connect(self.edit_projects_dir)

    def initUI(self):
        # Основная инициализация UI
        uic.loadUi("ui/settings_widget.ui", self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint)
        self.setFixedSize(400, 300)

        # Установка иконок кнопок
        self.editProjectsDirBtn.setIcon(QIcon("svg/folder_icon.svg"))

        # Установка значений EditLine
        self.projectsDirEdit.setText(PROJECTS_DIR)

        # Установка значений лейблов
        self.verLabel.setText(PRODUCT_VER)

    def edit_projects_dir(self):
        global PROJECTS_DIR
        new_path = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if new_path:
            PROJECTS_DIR = new_path
            self.projectsDirEdit.setText(PROJECTS_DIR)
            with open("config.json", "r+") as f_config:
                config = json.load(f_config)
            config["projectsDir"] = new_path
            with open("config.json", "w") as f_config:
                json.dump(config, f_config, indent=4)


class CreateProject(QWidget):
    def __init__(self, parent):
        self.project_menu = None
        self.parent = parent

        super().__init__()
        self.initUI()
        self.init_handlers()

    def initUI(self):
        # Основная инициализация UI
        uic.loadUi("ui/create_project.ui", self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint)
        self.setFixedSize(400, 300)

        # Установка иконок кнопок
        self.locationBtn.setIcon(QIcon("svg/folder_icon.svg"))

        # Установка значений LineEdit
        self.createInEdit.setText(f"{self.locationEdit.text()}/{self.nameEdit.text()}")

    def init_handlers(self):
        self.createBtn.clicked.connect(self.create_project)
        self.cancelBtn.clicked.connect(self.close)
        self.locationBtn.clicked.connect(self.choose_location)
        self.nameEdit.textChanged.connect(self.set_location_creating)
        self.locationEdit.textChanged.connect(self.set_location_creating)

    def set_location_creating(self):
        self.createInEdit.setText(f"{self.locationEdit.text()}/{self.nameEdit.text()}")

    def choose_location(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder_path:
            self.locationEdit.setText(folder_path)

    def create_project(self):
        try:
            if self.nameEdit.text():
                project_dir = self.createInEdit.text()
                os.makedirs(f"{project_dir}/files", exist_ok=False)
                with open(f"{project_dir}/files/README.md", "w") as f_readme:
                    with open(f"data/init_readme.txt", "r") as f_base_readme:
                        text = f_base_readme.read()
                    text = f"# {self.nameEdit.text()}\n" + text
                    f_readme.write(text)
            else:
                QMessageBox.information(
                    self,
                    "Не удалось создать проект",
                    "Имя проекта не может быть пустым",
                )
        except FileExistsError:
            QMessageBox.information(
                self, "Не удалось создать проект", "Папка c таким именем уже существует"
            )

        try:
            with sqlite3.connect("data/toDev.db") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO projects (title, dir) VALUES (?, ?)",
                    (
                        self.nameEdit.text(),
                        project_dir,
                    ),
                )
                response = cursor.execute(
                    "SELECT * FROM projects WHERE dir = ?", (project_dir,)
                ).fetchone()
                project_id, title, desc, project_dir, logo, state = response
            with open(f"{project_dir}/data.json", "w") as f_data:
                json.dump(
                    {
                        "project_id": project_id,
                        "title": title,
                        "description": desc,
                        "dir": project_dir,
                        "logo": logo,
                        "state": state,
                    },
                    f_data, indent=4
                )
        except sqlite3.IntegrityError:
            return
        except:
            QMessageBox.information(
                self,
                "Не удалось создать проект",
                "База данных не синхронизирована с данными на компьютере",
            )
            return
        self.close()
        self.parent.close()

        # Запуск основного окна
        self.project_menu = ProjectMenu(project_dir)
        self.project_menu.show()

    def showEvent(self, a0):
        self.locationEdit.setText(PROJECTS_DIR)
        return super().showEvent(a0)


class ProjectsView(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.project_menu = None
        self.parent = parent
        self.search_filters = ["title", "id", "state"]

        self.initUI()
        self.init_handlers()

    def initUI(self):
        # Основная инициализация UI
        uic.loadUi("ui/projects_view.ui", self)
        self.setFixedSize(600, 350)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint)

        # Показ всех существующих проектов
        self.search()

    def init_handlers(self):
        self.requestEdit.textChanged.connect(self.search)
        self.openBtn.clicked.connect(self.open_project)

    def open_project(self):
        project = self.projectsList.currentItem()
        if project:
            project_id = project.text().split("\t")[0]
            with sqlite3.connect("data/toDev.db") as conn:
                cursor = conn.cursor()
                project_dir = cursor.execute(
                    "SELECT dir FROM projects WHERE id = ?", (project_id,)
                ).fetchone()
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

        with sqlite3.connect("data/toDev.db") as conn:
            cursor = conn.cursor()
            response = cursor.execute(query).fetchall()
        display_list = ["ID\tИмя\tСтатус\tПуть"]
        for project in response:
            project_id, title, path, state = project
            display_text = (
                f"{project_id}\t{title}\t{state if state else "Не указан"}"
                f"\t{path if len(path) <= 33 else path[:30] + '...'}"
            )
            display_list.append(display_text)
        self.projectsList.addItems(display_list)
        titles_item = self.projectsList.item(0)
        titles_item.setFlags(~Qt.ItemFlag.ItemIsEnabled)


class ProjectMenu(QMainWindow):
    def __init__(self, project_dir):
        with open(f"{project_dir}/data.json", "r") as f_data:
            self.params = json.load(f_data)
        self.is_saved = True
        self.window = None

        super().__init__()
        self.initUI()
        self.init_handlers()

    def initUI(self):
        # Основная инициализация UI
        uic.loadUi("ui/project_menu.ui", self)
        self.setWindowTitle(f"{self.params['title']} - {self.params['dir']}")

    def init_handlers(self):
        # Обработчики fileMenu
        for item in [self.createFileAct, self.createDirAct]:
            item.triggered.connect(self.create_data)
        for item in [self.copyFileAct, self.copyDirAct]:
            item.triggered.connect(self.copy)
        self.saveProjectAct.triggered.connect(self.save_project)
        self.exitMenuAct.triggered.connect(self.exit_menu)
        self.exitAct.triggered.connect(self.close)

        # Обработчики viewMenu
        self.projectInformationAct.triggered.connect(self.view_project_info)
        self.fileTreeAct.triggered.connect(self.view_files_tree)
        self.kanbanAct.triggered.connect(self.view_kanban)

        # Обработчики runMenu
        self.listOfTasksAct.triggered.connect(self.view_list_of_tasks)
        self.addTaskAct.triggered.connect(self.add_task)
        self.setDeadlineAct.triggered.connect(self.set_deadline)
        self.editDeadlineAct.triggered.connect(self.edit_deadline)
        self.delProjectAct.triggered.connect(self.del_project)

    def create_data(self):
        pass

    def copy(self):
        pass

    def save_project(self):
        with sqlite3.connect("data/toDev.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE projects SET title = ?, description = ?, dir = ?, logo = ?, state = ? WHERE dir = ?",
                (
                    self.params["title"],
                    self.params["description"],
                    self.params["dir"],
                    self.params["logo"],
                    self.params["state"],
                    self.params["dir"],
                ),
            )
        self.is_saved = True
        self.update_title()

    def exit_menu(self):
        self.close()
        self.window = MainMenu()
        self.window.show()

    def view_project_info(self):
        pass

    def view_files_tree(self):
        pass

    def view_kanban(self):
        pass

    def view_list_of_tasks(self):
        pass

    def add_task(self):
        pass

    def set_deadline(self):
        pass

    def edit_deadline(self):
        pass

    def del_project(self):
        response = QMessageBox.question(self,
                                        "Удалить проект",
                                        f"""Вы уверены, что хотите удалить проект "{self.params["title"]}"?""",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                        QMessageBox.StandardButton.No)
        if response == QMessageBox.StandardButton.Yes:
            self.is_saved = True
            shutil.rmtree(self.params["dir"])
            with sqlite3.connect("data/toDev.db") as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM tasks WHERE project_id = ?", (self.params["project_id"],))
                cursor.execute("DELETE FROM projects WHERE id = ?", (self.params["project_id"],))
                conn.commit()
            self.exit_menu()

    def update_title(self):
        prefix = "" if self.is_saved else "*"
        self.setWindowTitle(f"{prefix}{self.config['title']} - {self.config['dir']}")

    def keyPressEvent(self, event):
        if (
                event.key() == Qt.Key.Key_S
                and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
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
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
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


def init_db():
    if os.path.isfile("data/toDev.db"):
        return
    with sqlite3.connect("data/toDev.db") as conn:
        with open("scripts/init_db.sql", encoding="utf-8") as f_init_db:
            sql_script = f_init_db.read()
        cursor = conn.cursor()
        cursor.executescript(sql_script)


def init_app():
    # Инициализация программных файлов
    global MAIN_DIR, PROJECTS_DIR, PRODUCT_VER
    if not os.path.isfile("config.json"):
        with open("config.json", "w") as f_config:
            json.dump(
                {
                    "programDir": os.path.dirname(__file__).replace("\\", "/"),
                    "projectsDir": os.path.join(
                        os.path.dirname(__file__), "projects"
                    ).replace("\\", "/"),
                    "productVer": "alpha0.2"
                },
                f_config, indent=4
            )

    with open("config.json", "r") as f_config:
        config = json.load(f_config)
        MAIN_DIR, PROJECTS_DIR, PRODUCT_VER = config["programDir"], config["projectsDir"], config["productVer"]

    os.makedirs("projects", exist_ok=True)
    application = QApplication(sys.argv)
    application.setAttribute(Qt.ApplicationAttribute.AA_Use96Dpi)
    return application


if __name__ == "__main__":
    init_db()
    app = init_app()
    window = MainMenu()
    window.show()
    sys.exit(app.exec())
