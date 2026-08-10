"""Interface gráfica PySide6 para o conversor PDF → livro (booklet)."""

from __future__ import annotations

import sys

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from pypdf import PdfReader

from booklet_maker import PipelineError, build_booklet, is_path_under_script_dir


class Worker(QObject):
    progress = Signal(str)
    finished = Signal(object)

    def __init__(
        self,
        input_pdf: str,
        output_pdf: str,
        part_size: int,
        extract_start: int,
        extract_end: int,
        rotate_even: bool,
        number_start: int | None,
        number_end: int | None,
        impose_margin: float,
        page_number_position: float,
    ) -> None:
        super().__init__()
        self._input_pdf = input_pdf
        self._output_pdf = output_pdf
        self._part_size = part_size
        self._extract_start = extract_start
        self._extract_end = extract_end
        self._rotate_even = rotate_even
        self._number_start = number_start
        self._number_end = number_end
        self._impose_margin = impose_margin
        self._page_number_position = page_number_position

    @Slot()
    def run(self) -> None:
        try:
            result = build_booklet(
                input_pdf=self._input_pdf,
                output_pdf=self._output_pdf,
                part_size=self._part_size,
                extract_start=self._extract_start,
                extract_end=self._extract_end,
                rotate_even=self._rotate_even,
                number_start=self._number_start,
                number_end=self._number_end,
                impose_margin=self._impose_margin,
                page_number_position=self._page_number_position,
                on_progress=lambda msg: self.progress.emit(msg),
            )
            self.finished.emit(result)
        except Exception as exc:
            self.finished.emit(exc)


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Conversor PDF para livro")
        self._total_pages = 0
        self._thread: QThread | None = None
        self._worker: Worker | None = None
        self._form_widgets: list[QWidget] = []

        self._input_edit = QLineEdit()
        self._input_browse = QPushButton("Procurar…")
        self._input_browse.clicked.connect(self._browse_input)

        self._page_count_label = QLabel("Total de páginas: —")

        self._output_dir_edit = QLineEdit()
        self._output_dir_browse = QPushButton("Procurar…")
        self._output_dir_browse.clicked.connect(self._browse_output_dir)

        self._output_name_edit = QLineEdit()
        self._output_name_edit.setText("livro.pdf")

        self._start_spin = QSpinBox()
        self._start_spin.setMinimum(1)
        self._start_spin.setMaximum(1)
        self._start_spin.setValue(1)
        self._start_spin.valueChanged.connect(self._sync_page_range)

        self._end_spin = QSpinBox()
        self._end_spin.setMinimum(1)
        self._end_spin.setMaximum(1)
        self._end_spin.setValue(1)
        self._end_spin.valueChanged.connect(self._update_numbering_limits)

        self._part_size_spin = QSpinBox()
        self._part_size_spin.setMinimum(1)
        self._part_size_spin.setMaximum(9999)
        self._part_size_spin.setValue(28)

        self._margin_spin = QSpinBox()
        self._margin_spin.setMinimum(0)
        self._margin_spin.setMaximum(100)
        self._margin_spin.setValue(0)

        self._page_number_position_spin = QSpinBox()
        self._page_number_position_spin.setMinimum(0)
        self._page_number_position_spin.setMaximum(100)
        self._page_number_position_spin.setValue(5)

        self._rotate_check = QCheckBox("Rodar páginas pares")

        self._number_check = QCheckBox("Numerar páginas")
        self._number_check.toggled.connect(self._toggle_numbering_fields)

        self._number_start_spin = QSpinBox()
        self._number_start_spin.setMinimum(1)
        self._number_start_spin.setMaximum(1)
        self._number_start_spin.setValue(1)

        self._number_end_spin = QSpinBox()
        self._number_end_spin.setMinimum(1)
        self._number_end_spin.setMaximum(1)
        self._number_end_spin.setValue(1)

        self._number_start_label = QLabel("Primeira página a numerar")
        self._number_end_label = QLabel("Última página a numerar")

        self._convert_button = QPushButton("Converter")
        self._convert_button.clicked.connect(self._start_conversion)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setVisible(False)

        self._status_label = QLabel("Pronto.")

        form = QFormLayout()
        form.addRow("PDF de entrada", self._input_row())
        form.addRow("", self._page_count_label)
        form.addRow("Pasta de saída", self._output_dir_row())
        form.addRow("Nome do PDF final", self._output_name_edit)
        form.addRow("Página inicial", self._start_spin)
        form.addRow("Página final", self._end_spin)
        form.addRow("Páginas por parte", self._part_size_spin)
        form.addRow("Margem", self._margin_spin)
        form.addRow("Posição do número da página", self._page_number_position_spin)
        form.addRow("", self._rotate_check)
        form.addRow("", self._number_check)
        form.addRow(self._number_start_label, self._number_start_spin)
        form.addRow(self._number_end_label, self._number_end_spin)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._convert_button)
        layout.addWidget(self._progress_bar)
        layout.addWidget(self._status_label)

        self._form_widgets = [
            self._input_edit,
            self._input_browse,
            self._output_dir_edit,
            self._output_dir_browse,
            self._output_name_edit,
            self._start_spin,
            self._end_spin,
            self._part_size_spin,
            self._margin_spin,
            self._page_number_position_spin,
            self._rotate_check,
            self._number_check,
            self._number_start_spin,
            self._number_end_spin,
        ]

        self._toggle_numbering_fields(False)

    def _input_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._input_edit)
        layout.addWidget(self._input_browse)
        return row

    def _output_dir_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._output_dir_edit)
        layout.addWidget(self._output_dir_browse)
        return row

    def _browse_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar PDF de entrada",
            "",
            "PDF (*.pdf)",
        )
        if not path:
            return

        self._input_edit.setText(path)
        try:
            total = len(PdfReader(path).pages)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "PDF inválido",
                f"Não foi possível ler o PDF:\n{exc}",
            )
            self._total_pages = 0
            self._page_count_label.setText("Total de páginas: —")
            return

        self._total_pages = total
        self._page_count_label.setText(f"Total de páginas: {total}")
        self._start_spin.setMaximum(total)
        self._end_spin.setMaximum(total)
        self._end_spin.setValue(total)
        self._update_numbering_limits()

    def _browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Selecionar pasta de saída",
            "",
        )
        if not path:
            return
        self._output_dir_edit.setText(path)

    def _extracted_page_count(self) -> int:
        return self._end_spin.value() - self._start_spin.value() + 1

    def _sync_page_range(self) -> None:
        if self._end_spin.value() < self._start_spin.value():
            self._end_spin.setValue(self._start_spin.value())
        self._update_numbering_limits()

    def _update_numbering_limits(self) -> None:
        extracted = max(1, self._extracted_page_count())
        self._number_start_spin.setMaximum(extracted)
        self._number_end_spin.setMaximum(extracted)
        if self._number_start_spin.value() > extracted:
            self._number_start_spin.setValue(extracted)
        if self._number_end_spin.value() > extracted:
            self._number_end_spin.setValue(extracted)
        if self._number_end_spin.value() < self._number_start_spin.value():
            self._number_end_spin.setValue(self._number_start_spin.value())

    def _toggle_numbering_fields(self, checked: bool) -> None:
        self._number_start_spin.setEnabled(checked)
        self._number_end_spin.setEnabled(checked)

    def _set_form_enabled(self, enabled: bool) -> None:
        for widget in self._form_widgets:
            widget.setEnabled(enabled)
        if enabled:
            self._toggle_numbering_fields(self._number_check.isChecked())

    def _reset_form(self) -> None:
        self._input_edit.clear()
        self._output_dir_edit.clear()
        self._output_name_edit.setText("livro.pdf")
        self._total_pages = 0
        self._page_count_label.setText("Total de páginas: —")
        self._start_spin.setMinimum(1)
        self._start_spin.setMaximum(1)
        self._start_spin.setValue(1)
        self._end_spin.setMinimum(1)
        self._end_spin.setMaximum(1)
        self._end_spin.setValue(1)
        self._part_size_spin.setValue(28)
        self._margin_spin.setValue(0)
        self._page_number_position_spin.setValue(5)
        self._rotate_check.setChecked(False)
        self._number_check.setChecked(False)
        self._number_start_spin.setMinimum(1)
        self._number_start_spin.setMaximum(1)
        self._number_start_spin.setValue(1)
        self._number_end_spin.setMinimum(1)
        self._number_end_spin.setMaximum(1)
        self._number_end_spin.setValue(1)
        self._progress_bar.setVisible(False)
        self._status_label.setText("Pronto.")

    def _validate(self) -> bool:
        input_path = self._input_edit.text().strip()
        output_dir = self._output_dir_edit.text().strip()
        output_name = self._output_name_edit.text().strip()

        if not input_path:
            QMessageBox.warning(self, "Validação", "Indique o PDF de entrada.")
            return False

        if not output_dir:
            QMessageBox.warning(self, "Validação", "Indique a pasta de saída.")
            return False

        if not output_name:
            QMessageBox.warning(self, "Validação", "Indique o nome do PDF final.")
            return False

        if not output_name.lower().endswith(".pdf"):
            QMessageBox.warning(self, "Validação", "O PDF final deve terminar em .pdf.")
            return False

        output_dir_path = Path(output_dir).expanduser()
        if not output_dir_path.is_dir():
            QMessageBox.warning(self, "Validação", "A pasta de saída não existe.")
            return False

        if is_path_under_script_dir(output_dir_path):
            QMessageBox.warning(
                self,
                "Validação",
                "A pasta de saída não pode ser a pasta do programa nem uma subpasta dela.",
            )
            return False

        if self._total_pages <= 0:
            QMessageBox.warning(self, "Validação", "Selecione um PDF de entrada válido.")
            return False

        extract_start = self._start_spin.value()
        extract_end = self._end_spin.value()

        if extract_start > extract_end:
            QMessageBox.warning(
                self,
                "Validação",
                "A página inicial deve ser menor ou igual à página final.",
            )
            return False

        if extract_end > self._total_pages:
            QMessageBox.warning(
                self,
                "Validação",
                f"A página final não pode exceder {self._total_pages}.",
            )
            return False

        if self._number_check.isChecked():
            number_start = self._number_start_spin.value()
            number_end = self._number_end_spin.value()
            extracted = extract_end - extract_start + 1

            if number_start > number_end:
                QMessageBox.warning(
                    self,
                    "Validação",
                    "A primeira página a numerar deve ser menor ou igual à última.",
                )
                return False

            if number_end > extracted:
                QMessageBox.warning(
                    self,
                    "Validação",
                    f"A última página a numerar não pode exceder {extracted}.",
                )
                return False

        return True

    def _start_conversion(self) -> None:
        if not self._validate():
            return

        number_start: int | None = None
        number_end: int | None = None
        if self._number_check.isChecked():
            number_start = self._number_start_spin.value()
            number_end = self._number_end_spin.value()

        self._set_form_enabled(False)
        self._convert_button.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._status_label.setText("A converter, aguarde…")

        self._thread = QThread()
        output_pdf = Path(self._output_dir_edit.text().strip()) / self._output_name_edit.text().strip()
        self._worker = Worker(
            input_pdf=self._input_edit.text().strip(),
            output_pdf=str(output_pdf),
            part_size=self._part_size_spin.value(),
            extract_start=self._start_spin.value(),
            extract_end=self._end_spin.value(),
            rotate_even=self._rotate_check.isChecked(),
            number_start=number_start,
            number_end=number_end,
            impose_margin=self._margin_spin.value(),
            page_number_position=self._page_number_position_spin.value(),
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    @Slot()
    def _on_thread_finished(self) -> None:
        self._thread = None
        self._worker = None

    @Slot(object)
    def _on_finished(self, result: object) -> None:
        self._progress_bar.setVisible(False)
        self._set_form_enabled(True)
        self._convert_button.setEnabled(True)

        if isinstance(result, Exception):
            if isinstance(result, PipelineError):
                QMessageBox.critical(self, "Erro", str(result))
            else:
                QMessageBox.critical(self, "Erro", str(result))
            self._status_label.setText("Pronto.")
            return

        path = Path(result)
        QMessageBox.information(self, "Concluído", f"Concluído: {path}")
        self._reset_form()

    def closeEvent(self, event) -> None:
        if self._thread is not None and self._thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Conversão em curso",
                "Uma conversão está a decorrer. Deseja cancelar e fechar na mesma?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
            self._thread.quit()
            self._thread.wait(5000)
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(520, 360)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
