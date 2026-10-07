import csv
from pathlib import Path

import matplotlib.pyplot as plt


AREA_MM2 = 100.0


def main():
    input_path = Path(__file__).with_name("load_data.csv")
    output_path = Path(__file__).with_name("load_result.csv")
    plot_path = Path(__file__).with_name("stress_plot.png")

    with input_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    if not rows:
        print("CSV 파일에 데이터가 없습니다.")
        return

    valid_rows = []
    excluded_count = 0

    for row_number, row in enumerate(rows, start=2):
        for field_name in ("time_s", "force_N"):
            value = row.get(field_name, "")
            if value is None or value.strip() == "":
                print(
                    f"제외된 행 {row_number}: {field_name} 값이 비어 있습니다."
                )
                excluded_count += 1
                break

            try:
                float(value)
            except ValueError:
                print(
                    f"제외된 행 {row_number}: {field_name} 값이 숫자가 아닙니다. "
                    f"문제값: {value!r}"
                )
                excluded_count += 1
                break
        else:
            valid_rows.append(row)

    valid_count = len(valid_rows)
    if valid_count == 0:
        print("유효한 데이터가 없습니다. 계산을 중단합니다.")
        return

    print(f"제외된 행 수: {excluded_count}")
    print(f"유효한 데이터 수: {valid_count}")

    for row in valid_rows:
        force_n = float(row["force_N"])
        row["stress_MPa"] = str(force_n / AREA_MM2)

    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        fieldnames = ["time_s", "force_N", "stress_MPa"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(valid_rows)

    max_force = max(float(row["force_N"]) for row in valid_rows)
    max_time = next(
        row["time_s"] for row in valid_rows
        if float(row["force_N"]) == max_force
    )
    max_stress = max(float(row["stress_MPa"]) for row in valid_rows)
    max_stress_time = next(
        row["time_s"] for row in valid_rows
        if float(row["stress_MPa"]) == max_stress
    )

    print(f"데이터 개수: {valid_count}")
    print(f"최대 하중: {max_force:.0f} N")
    print(f"최대 하중의 시간: {max_time} s")
    print(f"최대 응력: {max_stress:.1f} MPa")
    print(f"최대 응력의 시간: {max_stress_time} s")

    stress_above_6 = sum(
        1 for row in valid_rows if float(row["stress_MPa"]) > 6.0
    )
    print(f"기준 응력 6 MPa를 초과한 데이터 개수: {stress_above_6}")

    times = [float(row["time_s"]) for row in valid_rows]
    stresses = [float(row["stress_MPa"]) for row in valid_rows]

    plt.figure(figsize=(8, 5))
    plt.plot(times, stresses, marker="o", linestyle="-", color="blue")
    plt.scatter(
        max_time, max_stress,
        color="red", s=50, zorder=3,
    )
    plt.annotate(
        f"Max: {max_stress:.1f} MPa",
        (max_time, max_stress),
        xytext=(8, 8),
        textcoords="offset points",
        color="red",
        fontsize=10,
    )
    plt.xlabel("Time (s)")
    plt.ylabel("Stress (MPa)")
    plt.title("Time-Stress Curve")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(plot_path, dpi=300)
    plt.close()

    print(f"그래프 저장: {plot_path.name}")


if __name__ == "__main__":
    main()
