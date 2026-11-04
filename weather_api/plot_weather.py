import csv
import math
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "weather_september.csv"
PLOT_PATH = BASE_DIR / "temperature_september.png"
DATETIME_FORMAT = "%Y-%m-%d %H:%M"
HOUR = timedelta(hours=1)


def load_temperature_records() -> dict[datetime, float]:
    """weather_september.csv를 읽어 시각별 기온을 숫자로 변환한다."""
    records: dict[datetime, float] = {}
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required_columns = {"datetime", "temperature_C"}
        if reader.fieldnames is None or not required_columns.issubset(
            reader.fieldnames
        ):
            raise ValueError(
                "weather.csv에 datetime, temperature_C 열이 필요합니다."
            )

        for row_number, row in enumerate(reader, start=2):
            try:
                observed_at = datetime.strptime(
                    row["datetime"].strip(), DATETIME_FORMAT
                )
            except (AttributeError, ValueError) as exc:
                raise ValueError(
                    f"{row_number}행 datetime을 읽을 수 없습니다."
                ) from exc

            if observed_at in records:
                raise ValueError(
                    f"weather.csv에 중복 시각이 있습니다: "
                    f"{observed_at.strftime(DATETIME_FORMAT)}"
                )

            raw_temperature = (row.get("temperature_C") or "").strip()
            if not raw_temperature:
                temperature = math.nan
            else:
                try:
                    temperature = float(raw_temperature)
                except ValueError as exc:
                    raise ValueError(
                        f"{row_number}행 temperature_C가 숫자가 아닙니다."
                    ) from exc
                if not math.isfinite(temperature):
                    temperature = math.nan
            records[observed_at] = temperature

    if not records:
        raise ValueError("weather.csv에 그릴 데이터가 없습니다.")
    return records


def create_hourly_series(
    records: dict[datetime, float],
) -> tuple[list[datetime], list[float], list[datetime]]:
    """정렬된 관측값을 1시간 시간축에 맞추고 누락 시각을 NaN으로 채운다."""
    sorted_times = sorted(records)
    if any(
        observed_at.minute != 0 or observed_at.second != 0
        for observed_at in sorted_times
    ):
        raise ValueError("datetime 값은 정각 단위의 시간 자료여야 합니다.")

    times: list[datetime] = []
    temperatures: list[float] = []
    missing_times: list[datetime] = []
    observed_at = sorted_times[0]
    last_observed_at = sorted_times[-1]

    while observed_at <= last_observed_at:
        times.append(observed_at)
        if observed_at in records:
            temperatures.append(records[observed_at])
        else:
            temperatures.append(math.nan)
            missing_times.append(observed_at)
        observed_at += HOUR

    return times, temperatures, missing_times


def save_and_show_plot(
    times: list[datetime], temperatures: list[float]
) -> None:
    """기온 선 그래프를 PNG로 저장하고 화면에 표시한다."""
    figure, axis = plt.subplots(figsize=(11, 5))
    axis.plot(times, temperatures, color="tab:red", linewidth=1.5)
    axis.set_title("Temperature over time")
    axis.set_xlabel("Time (KST)")
    axis.set_ylabel("Temperature (°C)")
    axis.grid(True, alpha=0.3)
    figure.autofmt_xdate()
    figure.tight_layout()
    figure.savefig(PLOT_PATH, dpi=150)
    plt.show()


def main() -> int:
    """CSV를 읽어 누락 시각을 출력하고 기온 그래프를 만든다."""
    try:
        records = load_temperature_records()
        times, temperatures, missing_times = create_hourly_series(records)
        save_and_show_plot(times, temperatures)
    except (OSError, ValueError) as exc:
        print(f"그래프 생성 실패: {exc}")
        return 1

    print(f"누락 시각 수: {len(missing_times)}")
    if missing_times:
        print("누락 시각:")
        for missing_at in missing_times:
            print(missing_at.strftime(DATETIME_FORMAT))
    print(f"그래프 저장 위치: {PLOT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
