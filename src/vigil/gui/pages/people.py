"""People page: names, notes, photo import, and a gallery rebuild."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .base import Page


class PeoplePage(Page):
    def __init__(self, context, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "People",
            "No people yet",
            "Add a person, then import a clear photo of their face.",
            "Add person",
            parent,
        )
        self.context = context
        self.store = getattr(context, "people_store", None)
        self._selected_id: Optional[int] = None

        split = QHBoxLayout()
        split.setSpacing(12)

        left = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(240)
        self.list_widget.currentItemChanged.connect(self._on_selected)
        left.addWidget(self.list_widget, 1)
        add_button = QPushButton("Add person")
        add_button.clicked.connect(self.add_person)
        left.addWidget(add_button)
        split.addLayout(left, 1)

        editor = QWidget()
        editor.setObjectName("Panel")
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(14, 14, 14, 14)
        editor_layout.setSpacing(8)
        heading = QLabel("Person")
        heading.setObjectName("SectionTitle")
        editor_layout.addWidget(heading)

        editor_layout.addWidget(QLabel("Name"))
        self.name_edit = QLineEdit()
        self.name_edit.setAccessibleName("Name")
        editor_layout.addWidget(self.name_edit)

        editor_layout.addWidget(QLabel("Notes"))
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setAccessibleName("Notes")
        self.notes_edit.setPlaceholderText("Optional notes about this person")
        self.notes_edit.setFixedHeight(72)
        editor_layout.addWidget(self.notes_edit)

        self.enabled_box = QCheckBox("Include this person in matching")
        self.enabled_box.setChecked(True)
        editor_layout.addWidget(self.enabled_box)

        self.photos_label = QLabel("No photos yet")
        self.photos_label.setObjectName("Muted")
        editor_layout.addWidget(self.photos_label)

        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")
        self.status_label.setWordWrap(True)
        editor_layout.addWidget(self.status_label)
        editor_layout.addStretch(1)

        buttons = QHBoxLayout()
        self.import_button = QPushButton("Import photo")
        self.import_button.clicked.connect(self.import_photo)
        self.rebuild_button = QPushButton("Rebuild embeddings")
        self.rebuild_button.clicked.connect(self.rebuild_gallery)
        self.delete_button = QPushButton("Delete person")
        self.delete_button.setObjectName("Danger")
        self.delete_button.clicked.connect(self.delete_person)
        self.save_button = QPushButton("Save person")
        self.save_button.setObjectName("Primary")
        self.save_button.clicked.connect(self.save_person)
        buttons.addWidget(self.import_button)
        buttons.addWidget(self.rebuild_button)
        buttons.addWidget(self.delete_button)
        buttons.addStretch(1)
        buttons.addWidget(self.save_button)
        editor_layout.addLayout(buttons)
        split.addWidget(editor, 2)

        self.body_layout.addLayout(split, 1)
        self.view.set_retry(self.refresh)
        self.view.empty.action_clicked.connect(self.add_person)
        self.refresh()

    def refresh(self) -> None:
        try:
            people = self.context.reader.people()
        except Exception as err:
            self.show_error("Could not read people: %s" % err)
            return
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for person in people:
            item = QListWidgetItem(person["name"])
            item.setData(Qt.UserRole, int(person["id"]))
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)
        if not people:
            self.show_empty()
            self._set_editor_enabled(False)
            return
        self.show_content()
        self._set_editor_enabled(True)
        if self._selected_id is None:
            self.list_widget.setCurrentRow(0)
        else:
            self._select(self._selected_id)

    def _set_editor_enabled(self, enabled: bool) -> None:
        for widget in (
            self.name_edit,
            self.notes_edit,
            self.enabled_box,
            self.import_button,
            self.rebuild_button,
            self.delete_button,
            self.save_button,
        ):
            widget.setEnabled(enabled)

    def _on_selected(self, current: Optional[QListWidgetItem], _previous=None) -> None:
        if current is None:
            self._selected_id = None
            return
        person_id = int(current.data(Qt.UserRole))
        self._selected_id = person_id
        try:
            people = {int(row["id"]): row for row in self.context.reader.people()}
        except Exception as err:
            self._report(False, "Could not read the person: %s" % err)
            return
        person = people.get(person_id)
        if person is None:
            return
        self.name_edit.setText(person.get("name") or "")
        self.notes_edit.setPlainText(person.get("notes") or "")
        self.enabled_box.setChecked(bool(person.get("enabled")))
        try:
            count = self.store.count_images(person_id) if self.store else 0
        except Exception:
            count = 0
        self.photos_label.setText(
            "No photos yet" if count == 0 else "%d photo(s) on file" % count
        )
        self.status_label.setText("")

    def add_person(self) -> None:
        if self.store is None:
            self._report(False, "The people store is not available.")
            return
        try:
            person_id = self.store.add("New person")
        except Exception as err:
            self._report(False, "Could not add the person: %s" % err)
            return
        self._selected_id = person_id
        self._remember(person_id, "New person")
        self.refresh()
        self._report(True, "Added a new person. Give them a name and a photo.")

    def delete_person(self) -> None:
        if self.store is None or self._selected_id is None:
            return
        person_id = self._selected_id
        answer = QMessageBox.question(
            self,
            "Delete person",
            "Delete this person and every photo and embedding stored for them?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self.store.delete(person_id)
        except Exception as err:
            self._report(False, "Could not delete the person: %s" % err)
            return
        self._selected_id = None
        self._remember(person_id, None)
        self._rebuild()
        self.refresh()
        self._report(True, "Person deleted.")

    def save_person(self) -> None:
        if self.store is None or self._selected_id is None:
            return
        name = self.name_edit.text().strip()
        if not name:
            self._report(False, "A person needs a name.")
            return
        person_id = self._selected_id
        try:
            self.store.update(
                person_id,
                name,
                self.notes_edit.toPlainText().strip() or None,
                self.enabled_box.isChecked(),
            )
        except Exception as err:
            self._report(False, "Could not save the person: %s" % err)
            return
        self._remember(person_id, name)
        rebuilt = self._rebuild()
        self.refresh()
        current = self.list_widget.currentItem()
        if current is not None:
            current.setText(name)
        if rebuilt:
            self._report(True, "Saved. The gallery was rebuilt from the database.")

    def _remember(self, person_id: int, name) -> None:
        remember = getattr(self.context, "remember_person", None)
        if callable(remember):
            remember(person_id, name)

    def _rebuild(self) -> bool:
        rebuild = getattr(self.context, "rebuild_gallery", None)
        if not callable(rebuild):
            return True
        try:
            rebuild()
        except Exception as err:
            self._report(False, "The gallery was not rebuilt: %s" % err)
            return False
        return True

    def import_photo(self) -> None:
        if self._selected_id is None:
            return
        path, _filter = QFileDialog.getOpenFileName(
            self, "Import a face photo", "", "Images (*.jpg *.jpeg *.png)"
        )
        if not path:
            return
        action = getattr(self.context, "add_person_photo", None)
        if action is None:
            self._report(False, "Photo import needs a running app context.")
            return
        try:
            ok, message = action(self._selected_id, Path(path))
        except Exception as err:
            self._report(False, "Could not import the photo: %s" % err)
            return
        self._report(ok, message)
        self.refresh()

    def rebuild_gallery(self) -> None:
        action = getattr(self.context, "rebuild_gallery", None)
        if action is None:
            self._report(False, "Gallery rebuild needs a running app context.")
            return
        try:
            count = action()
        except Exception as err:
            self._report(False, "Could not rebuild the gallery: %s" % err)
            return
        self._report(True, "Gallery rebuilt from %d person(s)." % int(count))

    def _report(self, ok: bool, message: str) -> None:
        self.status_label.setObjectName("Muted" if ok else "Danger")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.status_label.setText(message)

    def _select(self, person_id: int) -> None:
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if int(item.data(Qt.UserRole)) == person_id:
                self.list_widget.setCurrentRow(index)
                return
