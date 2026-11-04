import csv
import getpass
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests


API_URL = "https://apihub.kma.go.kr/api/typ01/url/kma_sfctm3.php"
BASE_DIR = Path(__file__).resolve().parent
RAW_OUTPUT_PATH = BASE_DIR / "weather_september_raw.txt"
CSV_OUTPUT_PATH = BASE_DIR / "weather_september.csv"
# APIHub's numbered output descriptions identify 1-based data-column positions.
EXPECTED_HEADER_POSITIONS = {"TM": 1, "WS": 4, "TA": 12, "HM": 14}
CSV_COLUMNS = [
    "datetime",
    "temperature_C",
    "humidity_pct",
    "wind_speed_ms",
]
HEADER_FIELD_PATTERN = re.compile(
    r"^\s*#\s*(\d+)\.\s*([A-Z][A-Z0-9_]*)\b"
)
TIMESTAMP_PATTERN = re.compile(r"^\d{12}$")
TEXT_MISSING_VALUES = {"", "-", "--", "NA", "N/A", "NULL", "NAN", "////"}
NUMERIC_MISSING_VALUES = {
    "-99",
    "-99.0",
    "-99.00",
    "-999",
    "-999.0",
    "-999.00",
    "-9999",
    "-9999.0",
    "-9999.00",
}


def redact_message(message: str, api_key: str) -> str:
    """오류 안내에서 인증키와 요청 URL을 가린다."""
    for secret in (api_key, quote(api_key, safe="")):
        if secret:
            message = message.replace(secret, "[인증키 숨김]")
    return re.sub(r"https?://[^\s\"'<>]+", "[요청 주소 숨김]", message)


def extract_error_message(body: str, api_key: str) -> str:
    """API 텍스트 응답에서 오류에 해당하는 설명 줄을 추린다."""
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines:
        return "응답 본문이 비어 있습니다."

    error_lines = [
        line
        for line in lines
        if re.search(r"error|오류|실패|인증|키", line, re.IGNORECASE)
    ]
    return redact_message(" ".join(error_lines or lines[:3]), api_key)


def save_raw_response(content: bytes) -> None:
    """응답 원본 바이트를 변형하지 않고 별도 파일로 보관한다."""
    RAW_OUTPUT_PATH.write_bytes(content)


def get_header_positions(lines: list[str]) -> dict[str, int]:
    """주석 형식의 공식 헤더 설명에서 변수 번호를 읽고 위치를 검증한다."""
    positions: dict[str, int] = {}
    for line in lines:
        if not line.lstrip().startswith("#"):
            continue
        match = HEADER_FIELD_PATTERN.match(line)
        if match:
            positions[match.group(2)] = int(match.group(1))

    missing = set(EXPECTED_HEADER_POSITIONS) - positions.keys()
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"응답 헤더 설명에서 변수 위치를 찾지 못했습니다: {names}")

    for name, expected_position in EXPECTED_HEADER_POSITIONS.items():
        actual_position = positions[name]
        if actual_position != expected_position:
            raise ValueError(
                f"응답 헤더의 {name} 위치가 예상과 다릅니다 "
                f"(예상 {expected_position}, 확인 {actual_position})."
            )
    return positions


def normalize_measurement(value: str, field: str) -> str:
    """결측 표시는 빈 문자열로 바꾸고 유효한 음수 기온은 보존한다."""
    stripped = value.strip()
    normalized = stripped.upper()
    if normalized in TEXT_MISSING_VALUES or stripped in NUMERIC_MISSING_VALUES:
        return ""

    try:
        numeric_value = float(stripped)
    except ValueError as exc:
        raise ValueError(f"{field} 값이 숫자가 아닙니다: {stripped}") from exc

    if not math.isfinite(numeric_value):
        return ""

    # 풍속과 습도는 음수가 될 수 없으므로 API의 -9 결측 표기를 비운다.
    # 기온의 -9는 실제 기온일 수 있어 결측으로 단정하지 않는다.
    if field in {"WS", "HM"} and numeric_value == -9:
        return ""
    return stripped


def parse_weather_records(body: str) -> tuple[list[dict[str, str]], int]:
    """주석 헤더를 확인하고 공백 구분 자료를 정리·정렬·중복 제거한다."""
    lines = body.splitlines()
    positions = get_header_positions(lines)
    records_by_time: dict[datetime, dict[str, str]] = {}
    duplicate_count = 0

    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split()
        if not fields or not TIMESTAMP_PATTERN.fullmatch(fields[0]):
            continue

        required_position = max(EXPECTED_HEADER_POSITIONS.values())
        if len(fields) < required_position:
            raise ValueError("자료 행의 열 수가 헤더 설명보다 적습니다.")

        observed_at = datetime.strptime(
            fields[positions["TM"] - 1], "%Y%m%d%H%M"
        )
        record = {
            "datetime": observed_at.strftime("%Y-%m-%d %H:%M"),
            "temperature_C": normalize_measurement(
                fields[positions["TA"] - 1], "TA"
            ),
            "humidity_pct": normalize_measurement(
                fields[positions["HM"] - 1], "HM"
            ),
            "wind_speed_ms": normalize_measurement(
                fields[positions["WS"] - 1], "WS"
            ),
        }
        if observed_at in records_by_time:
            duplicate_count += 1
            continue
        records_by_time[observed_at] = record

    ordered_times = sorted(records_by_time)
    records = [records_by_time[observed_at] for observed_at in ordered_times]
    return records, duplicate_count


def save_weather_csv(records: list[dict[str, str]]) -> None:
    """정해진 열 순서와 UTF-8 BOM으로 CSV를 저장한다."""
    with CSV_OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(records)


def main() -> int:
    """API허브 응답을 원본 보관하고 정리한 관측자료 CSV를 생성한다."""
    print("기상청 API허브에서 발급받은 authKey를 입력한 뒤 Enter를 누르세요.")
    print("보안을 위해 입력 중에는 글자가 화면에 표시되지 않습니다.")
    try:
        api_key = getpass.getpass("authKey: ").strip()
    except (EOFError, OSError):
        print("터미널에서 인증키를 입력할 수 없습니다.")
        print("VS Code 터미널에서 `python .\\collect_weather.py`로 실행해 주세요.")
        return 1

    if not api_key:
        print("인증키가 비어 있습니다.")
        return 1

    params = {
        "tm1": "202509010000",
        "tm2": "202509072300",
        "stn": "108",
        "disp": "0",
        "help": "1",
        "authKey": api_key,
    }

    try:
        response = requests.get(API_URL, params=params, timeout=30)
    except requests.RequestException:
        print("API 요청에 실패했습니다(네트워크 오류 또는 시간 초과).")
        return 1

    print(f"HTTP 상태 코드: {response.status_code}")
    try:
        save_raw_response(response.content)
    except OSError as exc:
        print(f"원본 응답 파일을 저장하지 못했습니다: {exc}")
        return 1

    content_type = response.headers.get("Content-Type", "")
    charset_match = re.search(
        r"charset\s*=\s*[\"']?([^;\s\"']+)",
        content_type,
        re.IGNORECASE,
    )
    charset = (
        charset_match.group(1)
        if charset_match
        else response.apparent_encoding or response.encoding or "utf-8"
    )
    try:
        body = response.content.decode(charset, errors="replace")
    except LookupError:
        print("응답의 문자 인코딩을 처리할 수 없습니다.")
        return 1

    if not response.ok:
        print(f"요청 실패: {extract_error_message(body, api_key)}")
        return 1

    try:
        positions = get_header_positions(body.splitlines())
        records, duplicate_count = parse_weather_records(body)
    except ValueError as exc:
        print(f"응답 자료 처리 실패: {exc}")
        return 1

    if not records:
        print(f"요청 실패: {extract_error_message(body, api_key)}")
        return 1

    try:
        save_weather_csv(records)
    except OSError as exc:
        print(f"CSV 파일을 저장하지 못했습니다: {exc}")
        return 1

    print("\n헤더 번호 확인:")
    for name in ("TM", "WS", "TA", "HM"):
        print(f"{name}({positions[name]})")

    missing_counts = {
        column: sum(record[column] == "" for record in records)
        for column in CSV_COLUMNS
    }
    print(f"\n행 수: {len(records)}")
    print(f"중복 시각 제거 수: {duplicate_count}")
    print("열별 결측 수:")
    for column, count in missing_counts.items():
        print(f"  {column}: {count}")
    print(f"첫 시각: {records[0]['datetime']}")
    print(f"마지막 시각: {records[-1]['datetime']}")
    print(f"CSV 저장 위치: {CSV_OUTPUT_PATH}")
    print(f"원본 응답 저장 위치: {RAW_OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
