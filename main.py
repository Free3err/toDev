import json
import shutil
import sqlite3
import sys
import os

from PyQt6 import uic
from PyQt6.QtCore import Qt, QSize, QDir
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog, QMessageBox, QLabel, QLineEdit, QTextEdit, \
    QInputDialog
from PyQt6.QtGui import QIcon, QPixmap, QFileSystemModel


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
        self.verLabel.setText(f"Версия: {PRODUCT_VER}")

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
                    "INSERT INTO projects (title, dir, state) VALUES (?, ?, 5)",
                    (
                        self.nameEdit.text(),
                        project_dir,
                    ),
                )
                response = cursor.execute(
                    "SELECT * FROM projects WHERE dir = ?", (project_dir,)
                ).fetchone()
                project_id, title, project_dir, state = response
            with open(f"{project_dir}/data.json", "w") as f_data:
                json.dump(
                    {
                        "project_id": project_id,
                        "title": title,
                        "description": None,
                        "dir": project_dir,
                        "logo": None,
                        "state": state,
                    },
                    f_data, indent=4
                )
        except sqlite3.IntegrityError:
            return
        except Exception:
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
                f"{project_id}\t{title}\t{STATES[state - 1][1]}"
                f"\t{path}"
            )
            display_list.append(display_text)
        self.projectsList.addItems(display_list)
        titles_item = self.projectsList.item(0)
        titles_item.setFlags(~Qt.ItemFlag.ItemIsEnabled)
        for i in range(self.projectsList.count()):
            item = self.projectsList.item(i)
            item.setSizeHint(QSize(self.projectsList.width(), 30))


class ProjectMenu(QMainWindow):
    def __init__(self, project_dir):
        with open(f"{project_dir}/data.json", "r") as f_data:
            self.params = json.load(f_data)
        self.tasks_list = self.get_tasks()
        self.is_saved = True
        self.window = None

        super().__init__()
        self.initUI()

        self.editable_objects = {
            "name": self.nameEdit,
            "desc": self.descEdit,
        }

        self.init_handlers()

    def initUI(self):
        # Основная инициализация UI
        uic.loadUi("ui/project_menu.ui", self)
        self.setWindowTitle(f"{self.params['title']} - {self.params['dir']}")

        # Инициализация иконок
        self.setImageBtn.setIcon(QIcon("svg/create_icon.svg"))
        self.setImageBtn.setFixedSize(80, 80)

        # Инициализация фото
        self.init_logo()

        # Инициализация данных проекта
        self.nameEdit.setText(self.params["title"])
        self.descEdit.setText(self.params["description"])
        self.update_list_of_tasks()
        self.statusbar.showMessage(f"Статус: {STATES[self.params["state"] - 1][1]}")
        self.update_files_tree()

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
        self.setStatusAct.triggered.connect(self.change_status)
        self.delProjectAct.triggered.connect(self.del_project)

        # Другое
        for obj in self.editable_objects.values():
            if isinstance(obj, QTextEdit):
                obj.textChanged.connect(self.mark_unsaved)
            elif isinstance(obj, QLineEdit):
                obj.textChanged.connect(self.mark_unsaved)

        self.setImageBtn.clicked.connect(self.set_image)
        self.tasksList.doubleClicked.connect(self.open_task)
        self.treeFilesView.doubleClicked.connect(self.open_file)

    def change_status(self):
        self.window = ChangeStatus(self)
        self.window.show()

    def init_logo(self):
        if self.params["logo"]:
            self.setImageBtn.hide()
            logo_pixmap = QPixmap(self.params["logo"])
            img_label = QLabel()
            img_label.setPixmap(logo_pixmap)
            img_label.setScaledContents(True)
            img_label.setFixedSize(96, 96)
            self.mainLayout.addWidget(img_label, 1, 1)

    def get_tasks(self):
        with sqlite3.connect("data/toDev.db") as conn:
            cursor = conn.cursor()
            response = cursor.execute(f"SELECT id, title, description, state FROM tasks WHERE project_id = ?",
                                      (self.params["project_id"],)).fetchall()
        tasks_list = {task[0]: {"task_id": task[0], "title": task[1], "desc": task[2], "state": task[3]} for task in
                      response}
        return tasks_list

    def open_file(self, index):
        file_path = self.files_model.filePath(index)
        if os.path.isfile(file_path):
            os.startfile(file_path)
        elif os.path.isdir(file_path):
            pass

    def mark_unsaved(self):
        self.is_saved = False
        self.update_title()

    def update_files_tree(self):
        root_path = os.path.join(self.params["dir"], "files")
        self.files_model = QFileSystemModel()
        self.files_model.setRootPath(root_path)
        self.files_model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

        self.treeFilesView.setModel(self.files_model)
        self.treeFilesView.setRootIndex(self.files_model.index(root_path))

    def update_list_of_tasks(self):
        self.tasksList.clear()
        self.tasksList.addItem("ID\tНазвание\t\tСтатус")

        tasks = []
        for task_data in self.tasks_list.values():
            task_id = task_data.get("task_id")
            title = task_data.get("title")
            state = STATES[task_data.get("state") - 1][1]
            text = f"{task_id}\t{title if len(title) < 20 else title[0:17] + '...'}\t{state}"
            tasks.append(text)

        self.tasksList.addItems(tasks)
        titles_item = self.tasksList.item(0)
        titles_item.setFlags(titles_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        for i in range(self.tasksList.count()):
            item = self.tasksList.item(i)
            item.setSizeHint(QSize(self.tasksList.width(), 35))

    def set_image(self):
        response = QFileDialog.getOpenFileName(self, "Выберите изображение", "",
                                               "Изображения (*.png *.jpg *.jpeg *.bmp *.gif, *.svg)")
        if response[0]:
            with open(self.params['dir'] + "/data.json", "w") as f_data:
                self.params["logo"] = response[0]
                json.dump(self.params, f_data, indent=4)
            self.init_logo()

    def open_task(self):
        self.window = TaskMenu(self.tasks_list[int(self.tasksList.currentItem().text().split("\t")[0])], self)
        self.window.show()

    def exit_menu(self):
        self.close()
        self.window = MainMenu()
        self.window.show()

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

    def save_project(self):
        try:
            for key, obj in self.editable_objects.items():
                if key == "name":
                    self.params[key] = obj.text()
                elif key == "desc":
                    self.params["description"] = obj.toPlainText()
            with open(f"{self.params['dir']}/data.json", "w") as f_data:
                json.dump(self.params, f_data, indent=4)

            with sqlite3.connect("data/toDev.db") as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE projects SET title = ?, state = ? WHERE id = ?",
                               (self.params["title"], self.params["state"], self.params["project_id"]))

            self.is_saved = True
            self.update_title()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", f"Не удалось сохранить проект:\n{e}")

    def view_kanban(self):
        self.window = KanBan(self)
        self.window.show()

    def add_task(self):
        task_name, ok = QInputDialog.getText(self, "Добавить задачу", "Название задачи:")
        if ok:
            desc, ok = QInputDialog.getText(self, "Добавить задачу", "Описание задачи:")
            if ok:
                task_id = max(self.tasks_list.keys(), default=0) + 1
                self.tasks_list[task_id] = {"task_id": task_id, "title": task_name or "Без названия",
                                            "desc": desc, "state": None}
                with sqlite3.connect("data/toDev.db") as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO tasks (project_id, title, description,  state) VALUES (?, ?, ?, 5)",
                                   (self.params["project_id"], task_name or "Без названия", desc))
                self.update_list_of_tasks()

    def view_list_of_tasks(self):
        """Будет переписано"""
        pass

    def view_project_info(self):
        """ Будет переписано"""
        pass

    def view_files_tree(self):
        """ Будет переписано"""
        pass

    def create_data(self):
        current_index = self.treeFilesView.selectedIndexes()
        if not current_index:
            current_dir = os.path.join(self.params["dir"], "files")
        else:
            current_dir = self.files_model.filePath(current_index[0])

        if not os.path.isdir(current_dir):
            current_dir = os.path.dirname(current_dir)

        if self.sender() == self.createFileAct:
            response, ok = QInputDialog.getText(self, "Создать файл", "Введите название файла (с расширением):")
            if response and ok:
                file_path = os.path.join(current_dir, response)
                try:
                    if not os.path.isfile(file_path):
                        with open(file_path, "w"):
                            pass
                        QMessageBox.information(self, "Создание файла", f'Файл "{response}" успешно создан!')
                        self.update_files_tree()
                    else:
                        QMessageBox.information(self, "Ошибка", "Файл с таким именем уже существует!")
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось создать файл: {e}")
            else:
                QMessageBox.information(self, "Не удалось создать файл", "Название файла не может быть пустым!")

        elif self.sender() == self.createDirAct:
            response, ok = QInputDialog.getText(self, "Создать директорию", "Введите название директории:")
            if response and ok:
                dir_path = os.path.join(current_dir, response)
                try:
                    if not os.path.isdir(dir_path):
                        os.mkdir(dir_path)
                        QMessageBox.information(self, "Создание директории",
                                                f'Директория "{response}" успешно создана!')
                    else:
                        QMessageBox.information(self, "Ошибка", "Директория с таким именем уже существует!")
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось создать директорию: {e}")
            else:
                QMessageBox.information(self, "Не удалось создать директорию",
                                        "Название директории не может быть пустым!")

        self.update_files_tree()

    def copy(self):
        current_index = self.treeFilesView.selectedIndexes()
        if not current_index:
            current_dir = os.path.join(self.params["dir"], "files")
        else:
            current_dir = self.files_model.filePath(current_index[0])

        if not os.path.isdir(current_dir):
            current_dir = os.path.dirname(current_dir)

        if self.sender() == self.copyFileAct:
            response, ok = QFileDialog.getOpenFileName(self, "Выберите файл", "", "Все файлы (*.*)")
            if response and ok:
                try:
                    dest_path = os.path.join(current_dir, os.path.basename(response))
                    if os.path.isfile(dest_path):
                        QMessageBox.information(self, "Ошибка копирования", "Файл с таким названием уже существует!")
                    else:
                        shutil.copy2(response, current_dir)
                        QMessageBox.information(self, "Успех", "Файл успешно скопирован!")
                        self.update_files_tree()
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось скопировать файл:\n{e}")

        elif self.sender() == self.copyDirAct:
            response = QFileDialog.getExistingDirectory(self, "Выберите папку", "")
            if response:
                try:
                    dest_dir = os.path.join(current_dir, os.path.basename(response))
                    if os.path.isdir(dest_dir):
                        QMessageBox.information(self, "Ошибка копирования",
                                                "Директория с таким названием уже существует!")
                    else:
                        shutil.copytree(response, dest_dir)
                        QMessageBox.information(self, "Успех", "Директория успешно скопирована!")
                        self.update_files_tree()
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось скопировать директорию:\n{e}")

    def update_title(self):
        prefix = "" if self.is_saved else "*"
        self.setWindowTitle(f"{prefix}{self.params['title']} - {self.params['dir']}")

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
                f"""Вы хотите сохранить проект "{self.params['title']}"?""",
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


class TaskMenu(QWidget):
    def __init__(self, task_data, parent):
        self.params = task_data
        self.parent = parent

        super().__init__()
        self.initUI()
        self.init_handlers()

    def initUI(self):
        # Инициализация основного UI
        uic.loadUi("ui/task_menu.ui", self)
        self.setFixedSize(620, 400)

        self.titleEdit.setText(self.params["title"])
        self.descEdit.setText(self.params["desc"])
        self.statusParameter.setCurrentIndex(self.params["state"] - 1)

    def init_handlers(self):
        self.cancelBtn.clicked.connect(self.close)
        self.saveBtn.clicked.connect(self.save_task)
        self.delTaskBtn.clicked.connect(self.delete)

    def delete(self):
        response = QMessageBox.question(self, "Удалить задачу", "Вы уверены что хотите удалить задачу?")
        if response == QMessageBox.StandardButton.Yes:
            self.close()
            with sqlite3.connect("data/toDev.db") as conn:
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM tasks WHERE id = {self.params['task_id']};")
                conn.commit()

            if isinstance(self.parent, KanBan):
                self.parent.update_list_of_tasks()
            elif isinstance(self.parent, ProjectMenu):
                self.parent.tasks_list = self.parent.get_tasks()
                self.parent.update_list_of_tasks()
            QMessageBox.information(self, "Удалить задачу", "Задача была удалена!")

    def save_task(self):
        with sqlite3.connect("data/toDev.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET title = ?, description = ?, state = ? WHERE id = ?",
                           (self.titleEdit.text(), self.descEdit.toPlainText(), self.statusParameter.currentIndex() + 1,
                            self.params["task_id"]))
            conn.commit()

        if isinstance(self.parent, KanBan):
            self.parent.update_list_of_tasks()
        elif isinstance(self.parent, ProjectMenu):
            self.parent.tasks_list = self.parent.get_tasks()
            self.parent.update_list_of_tasks()
        QMessageBox.information(self, "Сохранение", "Задача успешно сохранена!")
        self.close()

    def keyPressEvent(self, event):
        if (
                event.key() == Qt.Key.Key_S
                and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self.save_task()
            event.accept()
        else:
            super().keyPressEvent(event)


class KanBan(QWidget):
    def __init__(self, parent):
        self.parent = parent
        super().__init__()
        self.initUI()
        self.init_handlers()

    def initUI(self):
        uic.loadUi("ui/kanban.ui", self)
        self.update_list_of_tasks()

    def update_list_of_tasks(self):
        self.parent.tasks_list = self.parent.get_tasks()
        self.parent.update_list_of_tasks()
        self.tasks_list = self.parent.tasks_list
        for list_widget in [self.completeList, self.cancelledList, self.expiredList, self.inProcessList,
                            self.nonStateList]:
            list_widget.clear()
            list_widget.addItem("ID\tНазвание")
            titles_item = list_widget.item(0)
            titles_item.setFlags(~Qt.ItemFlag.ItemIsEnabled)

        for task in self.tasks_list.values():
            match task["state"]:
                case 1:
                    self.completeList.addItem(
                        f"{task['task_id']}\t{task['title'] if len(task["title"]) < 25 else task["title"][:22] + '...'}")
                case 2:
                    self.inProcessList.addItem(
                        f"{task['task_id']}\t{task['title'] if len(task["title"]) < 25 else task["title"][:22] + '...'}")
                case 3:
                    self.cancelledList.addItem(
                        f"{task['task_id']}\t{task['title'] if len(task["title"]) < 25 else task["title"][:22] + '...'}")
                case 4:
                    self.expiredList.addItem(
                        f"{task['task_id']}\t{task['title'] if len(task["title"]) < 25 else task["title"][:22] + '...'}")
                case 5:
                    self.nonStateList.addItem(
                        f"{task['task_id']}\t{task['title'] if len(task["title"]) < 25 else task["title"][:22] + '...'}")

        for list_widget in [self.completeList, self.cancelledList, self.expiredList, self.inProcessList,
                            self.nonStateList]:
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                item.setSizeHint(QSize(list_widget.width(), 30))

    def init_handlers(self):
        for item in [self.completeList, self.cancelledList, self.expiredList, self.inProcessList, self.nonStateList]:
            item.doubleClicked.connect(self.open_task)

    def open_task(self):
        sender = self.sender()
        selected_item = sender.currentItem()
        if selected_item and sender.row(selected_item) > 0:
            task_id = int(selected_item.text().split("\t")[0])
            task_data = self.tasks_list.get(task_id)

            if task_data:
                self.window = TaskMenu(task_data, self)
                self.window.show()


class ChangeStatus(QWidget):
    def __init__(self, parent):
        self.parent = parent
        super().__init__()
        self.initUI()
        self.init_handlers()

    def init_handlers(self):
        self.cancelBtn.clicked.connect(self.close)
        self.saveBtn.clicked.connect(self.save_status)

    def initUI(self):
        uic.loadUi("ui/change_status.ui", self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint)
        self.setFixedSize(200, 150)
        self.statusParameter.setCurrentIndex(self.parent.params["state"] - 1)

    def save_status(self):
        state = self.statusParameter.currentIndex()
        self.parent.params["state"] = state + 1
        self.parent.mark_unsaved()
        self.parent.statusbar.showMessage(f"Статус: {STATES[self.parent.params["state"] - 1][1]}")
        self.close()

    def keyPressEvent(self, event):
        if (
                event.key() == Qt.Key.Key_S
                and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self.save_task()
            event.accept()
        else:
            super().keyPressEvent(event)


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
    global MAIN_DIR, PROJECTS_DIR, PRODUCT_VER, STATES

    with sqlite3.connect("data/toDev.db") as conn:
        cursor = conn.cursor()
        response = cursor.execute("SELECT * FROM states").fetchall()
        STATES = response

    if not os.path.isfile("config.json"):
        with open("config.json", "w") as f_config:
            json.dump(
                {
                    "programDir": os.path.dirname(__file__).replace("\\", "/"),
                    "projectsDir": os.path.join(
                        os.path.dirname(__file__), "projects"
                    ).replace("\\", "/"),
                    "productVer": "release1.0"
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
