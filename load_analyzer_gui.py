import csv
import math
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class MissingColumnsError(ValueError):
    pass


def read_valid_data(csv_path: Path) -> tuple[list[float], list[float], int]:
    times = []
    forces = []
    excluded_count = 0

    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required_fields = ("time_s", "force_N")
        missing_fields = [
            field for field in required_fields
            if field not in (reader.fieldnames or [])
        ]
        if missing_fields:
            raise MissingColumnsError(
                ", ".join(missing_fields)
            )

        for row in reader:
            values = []
            for field_name in required_fields:
                value = row.get(field_name, "")
                if value is None or value.strip() == "":
                    excluded_count += 1
                    break

                try:
                    values.append(float(value))
                except ValueError:
                    excluded_count += 1
                    break
            else:
                times.append(values[0])
                forces.append(values[1])

    return times, forces, excluded_count


SECTION_DIMENSIONS = {
    "사각형": (("b", "폭 b (mm)"), ("h", "높이 h (mm)")),
    "원형봉": (("d", "직경 d (mm)"),),
    "원형관": (("D", "외경 D (mm)"), ("t", "두께 t (mm)")),
    "사각형관": (
        ("B", "폭 B (mm)"),
        ("H", "높이 H (mm)"),
        ("t", "두께 t (mm)"),
    ),
    "H형강": (
        ("B", "폭 B (mm)"),
        ("H", "높이 H (mm)"),
        ("tw", "웨브 두께 tw (mm)"),
        ("tf", "플랜지 두께 tf (mm)"),
    ),
}


def calculate_area(section_type: str, dimensions: dict[str, float]) -> float:
    values = [dimensions[key] for key, _ in SECTION_DIMENSIONS[section_type]]
    if any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError("모든 치수는 0보다 큰 유한한 숫자여야 합니다.")

    if section_type == "사각형":
        area = dimensions["b"] * dimensions["h"]
    elif section_type == "원형봉":
        diameter = dimensions["d"]
        area = math.pi * diameter * diameter / 4
    elif section_type == "원형관":
        outer_diameter = dimensions["D"]
        thickness = dimensions["t"]
        if 2 * thickness >= outer_diameter:
            raise ValueError("원형관은 2t < D 조건을 만족해야 합니다.")
        inner_diameter = outer_diameter - 2 * thickness
        area = (
            math.pi
            * (outer_diameter * outer_diameter - inner_diameter * inner_diameter)
            / 4
        )
    elif section_type == "사각형관":
        width = dimensions["B"]
        height = dimensions["H"]
        thickness = dimensions["t"]
        if 2 * thickness >= width or 2 * thickness >= height:
            raise ValueError("사각형관은 2t < B 및 2t < H 조건을 만족해야 합니다.")
        area = width * height - (width - 2 * thickness) * (
            height - 2 * thickness
        )
    elif section_type == "H형강":
        width = dimensions["B"]
        height = dimensions["H"]
        web_thickness = dimensions["tw"]
        flange_thickness = dimensions["tf"]
        if 2 * flange_thickness >= height:
            raise ValueError("H형강은 2tf < H 조건을 만족해야 합니다.")
        if web_thickness >= width:
            raise ValueError("H형강은 tw < B 조건을 만족해야 합니다.")
        area = (
            2 * width * flange_thickness
            + (height - 2 * flange_thickness) * web_thickness
        )
    else:
        raise ValueError(f"지원하지 않는 단면 종류입니다: {section_type}")

    if not math.isfinite(area) or area <= 0:
        raise ValueError("계산된 단면적이 유효하지 않습니다.")
    return area


class LoadAnalyzerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("하중 데이터 그래프")
        self.root.geometry("900x680")
        self.root.minsize(600, 450)

        self.path_var = tk.StringVar()
        self.count_var = tk.StringVar(value="유효 데이터: -")
        self.section_type_var = tk.StringVar(value="사각형")
        self.area_var = tk.StringVar(value="단면적 A: 분석 전")
        self.max_stress_var = tk.StringVar(value="최대 응력: 분석 전")
        self.analysis_status_var = tk.StringVar(value="CSV 파일을 선택하세요.")
        self.dimension_vars: dict[str, tk.StringVar] = {}
        self.times: list[float] = []
        self.forces: list[float] = []

        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        controls = ttk.Frame(root, padding=10)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)

        browse_button = ttk.Button(
            controls,
            text="CSV 찾아보기",
            command=self.choose_csv,
        )
        browse_button.grid(row=0, column=0, padx=(0, 8))

        path_entry = ttk.Entry(
            controls,
            textvariable=self.path_var,
            state="readonly",
        )
        path_entry.grid(row=0, column=1, sticky="ew")

        count_label = ttk.Label(controls, textvariable=self.count_var)
        count_label.grid(row=0, column=2, padx=(12, 0))

        section_label = ttk.Label(controls, text="단면 종류")
        section_label.grid(row=1, column=0, sticky="w", pady=(12, 0))

        section_type = ttk.Combobox(
            controls,
            textvariable=self.section_type_var,
            values=tuple(SECTION_DIMENSIONS),
            state="readonly",
            width=14,
        )
        section_type.grid(row=1, column=1, sticky="w", pady=(12, 0))
        section_type.bind("<<ComboboxSelected>>", self.on_section_type_changed)

        self.dimensions_frame = ttk.Frame(controls)
        self.dimensions_frame.grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(8, 0),
        )

        analyze_button = ttk.Button(
            controls,
            text="분석",
            command=self.analyze,
        )
        analyze_button.grid(row=3, column=0, sticky="w", pady=(12, 0))

        area_label = ttk.Label(controls, textvariable=self.area_var)
        area_label.grid(row=3, column=1, sticky="w", padx=(12, 0), pady=(12, 0))

        max_stress_label = ttk.Label(
            controls,
            textvariable=self.max_stress_var,
        )
        max_stress_label.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="w",
            padx=(0, 0),
            pady=(12, 0),
        )

        status_label = ttk.Label(
            controls,
            textvariable=self.analysis_status_var,
        )
        status_label.grid(
            row=5,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(6, 0),
        )

        chart_frame = ttk.Frame(root, padding=(10, 0, 10, 10))
        chart_frame.grid(row=1, column=0, sticky="nsew")
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(0, weight=1)

        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.render_dimension_inputs()
        self.draw_chart([], [], "Select a CSV file, then click Analyze.")

    def choose_csv(self) -> None:
        selected_path = filedialog.askopenfilename(
            title="CSV 파일 선택",
            filetypes=(("CSV 파일", "*.csv"), ("모든 파일", "*.*")),
        )
        if not selected_path:
            return

        self.path_var.set(selected_path)
        self.count_var.set("유효 데이터: 읽는 중...")
        self.times = []
        self.forces = []
        self.invalidate_analysis("CSV 변경됨: 다시 분석 필요")

        try:
            self.times, self.forces, excluded_count = read_valid_data(
                Path(selected_path)
            )
        except MissingColumnsError as error:
            self.count_var.set("필수 열 누락")
            self.analysis_status_var.set("CSV 필수 열을 확인하세요.")
            messagebox.showerror(
                "필수 열 누락",
                f"CSV에 필요한 열이 없습니다: {error}",
                parent=self.root,
            )
            return
        except (OSError, UnicodeDecodeError, csv.Error) as error:
            self.count_var.set("유효 데이터: 읽기 실패")
            self.analysis_status_var.set(f"CSV 읽기 실패: {error}")
            messagebox.showerror(
                "CSV 읽기 오류",
                f"파일을 읽을 수 없습니다.\n{error}",
                parent=self.root,
            )
            return

        self.count_var.set(
            f"유효 데이터: {len(self.times)}개 (제외: {excluded_count}개)"
        )

    def on_section_type_changed(self, _event: tk.Event) -> None:
        self.section_type_var.set(_event.widget.get())
        self.render_dimension_inputs()
        self.invalidate_analysis("조건 변경됨: 다시 분석 필요")

    def render_dimension_inputs(self) -> None:
        for widget in self.dimensions_frame.winfo_children():
            widget.destroy()

        self.dimension_vars.clear()
        for column, (key, label_text) in enumerate(
            SECTION_DIMENSIONS[self.section_type_var.get()]
        ):
            field_frame = ttk.Frame(self.dimensions_frame)
            field_frame.grid(row=0, column=column, sticky="w", padx=(0, 12))
            ttk.Label(field_frame, text=label_text).grid(row=0, column=0, sticky="w")

            value_var = tk.StringVar()
            value_var.trace_add("write", self.on_dimensions_changed)
            self.dimension_vars[key] = value_var
            ttk.Entry(
                field_frame,
                textvariable=value_var,
                width=14,
            ).grid(row=1, column=0, sticky="w", pady=(4, 0))

    def on_dimensions_changed(self, *trace_info: str) -> None:
        if not trace_info or trace_info[-1] != "write":
            return
        self.invalidate_analysis("조건 변경됨: 다시 분석 필요")

    def invalidate_analysis(self, status: str) -> None:
        self.area_var.set("단면적 A: 무효")
        self.max_stress_var.set("최대 응력: 무효")
        self.analysis_status_var.set(status)
        self.draw_chart([], [], "Analysis results are unavailable.")

    def read_dimension_values(self) -> dict[str, float]:
        dimensions = {}
        for key, label in SECTION_DIMENSIONS[self.section_type_var.get()]:
            raw_value = self.dimension_vars[key].get().strip()
            if not raw_value:
                raise ValueError(f"{label} 값을 입력하세요.")
            try:
                dimensions[key] = float(raw_value)
            except ValueError as error:
                raise ValueError(f"{label}에 숫자를 입력하세요.") from error
        return dimensions

    def analyze(self) -> None:
        self.invalidate_analysis("분석 중...")

        if not self.path_var.get():
            self.analysis_status_var.set("분석 실패: CSV 파일을 선택하세요.")
            messagebox.showwarning(
                "CSV 파일 필요",
                "먼저 CSV 파일을 선택하세요.",
                parent=self.root,
            )
            return

        if not self.times:
            self.analysis_status_var.set("분석 실패: 유효한 CSV 데이터가 없습니다.")
            messagebox.showwarning(
                "유효 데이터 없음",
                "분석할 유효 데이터가 없습니다.",
                parent=self.root,
            )
            return

        try:
            dimensions = self.read_dimension_values()
            area_mm2 = calculate_area(self.section_type_var.get(), dimensions)
        except ValueError as error:
            self.analysis_status_var.set(f"분석 실패: {error}")
            messagebox.showwarning(
                "치수 입력 확인",
                str(error),
                parent=self.root,
            )
            return

        stresses = [force / area_mm2 for force in self.forces]
        max_index = stresses.index(max(stresses))
        max_stress = stresses[max_index]
        max_time = self.times[max_index]
        self.area_var.set(f"단면적 A: {area_mm2:.12g} mm²")
        self.max_stress_var.set(
            f"최대 응력: {max_stress:.3f} MPa    해당 시간: {max_time:g} s"
        )
        self.analysis_status_var.set("분석 완료")
        self.draw_chart(self.times, stresses)

    def draw_chart(
        self,
        times: list[float],
        values: list[float],
        empty_message: str = "CSV 파일을 선택하세요.",
    ) -> None:
        self.axes.clear()
        self.axes.set_xlabel("Time (s)")
        self.axes.set_ylabel("Stress (MPa)")
        self.axes.set_title("Time-Stress Curve")
        self.axes.grid(True, linestyle="--", alpha=0.5)

        if times:
            self.axes.plot(times, values, marker="o", linestyle="-", color="blue")
        else:
            self.axes.text(
                0.5,
                0.5,
                empty_message,
                ha="center",
                va="center",
                transform=self.axes.transAxes,
            )

        self.figure.tight_layout()
        self.canvas.draw()


def main() -> None:
    root = tk.Tk()
    LoadAnalyzerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
