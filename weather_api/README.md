# 기상청 ASOS 관측자료 수집 및 그래프

기상청 API허브의 ASOS 기간자료 API에서 서울 관측소(108)의 시간별 관측자료를 수집하고, 기온 그래프를 만듭니다.

## 구성

| 파일 | 설명 |
|---|---|
| `collect_weather.py` | API허브에서 자료를 받아 원본 응답과 정리된 CSV를 저장 |
| `plot_weather.py` | 수집 CSV를 읽어 시간별 기온 그래프를 저장하고 표시 |
| `requirements.txt` | `requests`, `matplotlib` 의존성 |

## 실행 환경 준비

Python 3.9 이상을 사용합니다. PowerShell에서 이 폴더로 이동해 의존성을 설치합니다.

```powershell
cd "$HOME\OneDrive\Desktop\코딩과응용\weather_api"
python -m pip install -r .\requirements.txt
```

## 자료 수집

```powershell
python .\collect_weather.py
```

실행 중 기상청 API허브에서 발급한 `authKey`를 입력합니다. 입력 문자는 보안상 화면에 표시되지 않습니다. 인증키를 코드나 채팅에 적거나 다른 사람과 공유하지 마세요.

요청 설정은 `collect_weather.py`의 `main()`에 있습니다.

- API: `https://apihub.kma.go.kr/api/typ01/url/kma_sfctm3.php`
- 기간: 2025년 9월 1일 00시부터 9월 7일 23시까지 (KST)
- 관측소: `108` (서울)
- 시간 초과: 30초

수집이 성공하면 다음 파일이 스크립트와 같은 폴더에 생성됩니다.

- `weather_september_raw.txt`: API가 반환한 원본 응답 바이트
- `weather_september.csv`: 분석에 사용할 정리된 자료

CSV의 열은 아래 순서입니다.

```text
datetime, temperature_C, humidity_pct, wind_speed_ms
```

날짜·시간은 `YYYY-MM-DD HH:MM` 형식이며 CSV는 `utf-8-sig`로 저장됩니다. 응답의 `#` 설명 줄에서 자료 열 번호를 확인하고, 공백으로 구분된 행에서 TM(1), WS(4), TA(12), HM(14)을 읽습니다. 자료는 시간순으로 정렬하고 중복 시각은 첫 행만 남깁니다. 결측값은 CSV에서 빈 값으로 둡니다. 풍속과 습도에서 `-9`는 결측으로 처리하지만, 기온의 음수는 정상 관측값일 수 있어 그대로 보존합니다.

## 기온 그래프

수집이 끝난 뒤 실행합니다.

```powershell
python .\plot_weather.py
```

이 스크립트는 API를 호출하지 않고 `weather_september.csv`만 읽습니다. 시각을 날짜·시간으로 변환해 정렬하고, 누락된 시각은 1시간 간격의 빈 자리로 추가합니다. 기온 결측과 누락 시각은 `NaN`으로 표시되어 그래프 선이 끊깁니다.

그래프 제목은 `Temperature over time`, 축 이름은 `Time (KST)`와 `Temperature (°C)`입니다. 그래프는 `temperature_september.png`로 저장한 뒤 화면에도 표시합니다.

## 오류 확인

- `SERVICE_KEY_IS_NOT_REGISTERED_ERROR` 또는 HTTP 403이 나오면 기상청 API허브에서 발급한 키인지, 해당 API 이용 신청이 승인되었는지 확인합니다. 공공데이터포털 키와 API허브 키는 서로 바꿔 쓸 수 없습니다.
- 터미널이 아닌 VS Code 출력 창이나 디버그 콘솔에서 실행하면 숨김 입력을 받을 수 없습니다. VS Code 터미널에서 위 명령을 실행합니다.
- 인증키가 채팅이나 공개된 위치에 노출되었다면 해당 키를 폐기하고 새 키를 발급받습니다.
- `weather_september.csv`가 없거나 열 이름이 맞지 않으면 먼저 수집 스크립트를 실행합니다.

스크립트 실행 중 HTTP 상태 코드와 오류 안내가 표시됩니다. 오류 메시지에도 인증키와 요청 URL은 출력하지 않도록 처리되어 있습니다.
