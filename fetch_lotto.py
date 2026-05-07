try:
    import requests
except ImportError:
    print("requests 라이브러리가 필요합니다. 아래 명령어를 실행해주세요:")
    print("pip install -r requirements.txt")
    exit(1)

import json
import re
import sys
from pathlib import Path

API_URL = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={drw_no}"
DATA_FILE = Path(__file__).with_name("lotto_data.json")
LOTTO_FIELDS = [
    "drwNo",
    "drwNoDate",
    "drwtNo1",
    "drwtNo2",
    "drwtNo3",
    "drwtNo4",
    "drwtNo5",
    "drwtNo6",
    "bnusNo",
]


def load_existing_data():
    if not DATA_FILE.exists():
        return []

    try:
        with DATA_FILE.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        print(f"lotto_data.json을 읽을 수 없습니다: {error}")
        sys.exit(1)

    if not isinstance(data, list):
        print("lotto_data.json 형식이 올바르지 않습니다. JSON 배열이어야 합니다.")
        sys.exit(1)

    return data


def normalize_round(raw_round):
    return {field: raw_round[field] for field in LOTTO_FIELDS}


def parse_api_response(response_text):
    text = response_text.strip()
    jsonp_match = re.fullmatch(r"[A-Za-z_$][\w$]*\((.*)\)\s*;?", text, re.DOTALL)
    if jsonp_match:
        text = jsonp_match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        print("API 응답 파싱에 실패했습니다. 응답 내용:")
        print(response_text)
        raise RuntimeError(f"API 응답을 JSON으로 해석할 수 없습니다: {error}") from error


def fetch_round(session, drw_no):
    max_retries = 2
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = session.get(
                API_URL.format(drw_no=drw_no),
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            response.raise_for_status()
            break
        except requests.RequestException as error:
            last_error = error
            if attempt < max_retries:
                print(f"요청 실패, 재시도 {attempt + 1}/{max_retries}...", end=" ", flush=True)
                continue

            raise RuntimeError(f"인터넷 연결 또는 API 요청에 실패했습니다: {last_error}") from last_error

    data = parse_api_response(response.text)

    if data.get("returnValue") == "fail":
        return None

    missing_fields = [field for field in LOTTO_FIELDS if field not in data]
    if missing_fields:
        raise RuntimeError(f"{drw_no}회차 응답에 필수 필드가 없습니다: {', '.join(missing_fields)}")

    return normalize_round(data)


def save_data(rounds):
    sorted_rounds = sorted(rounds, key=lambda item: item["drwNo"])
    with DATA_FILE.open("w", encoding="utf-8-sig") as file:
        json.dump(sorted_rounds, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main():
    existing_data = load_existing_data()
    existing_by_round = {
        item["drwNo"]: item
        for item in existing_data
        if isinstance(item, dict) and isinstance(item.get("drwNo"), int)
    }

    next_round = max(existing_by_round, default=0) + 1
    collected = []

    with requests.Session() as session:
        while True:
            print(f"{next_round}회차 수집 중...", end=" ", flush=True)
            try:
                round_data = fetch_round(session, next_round)
            except RuntimeError as error:
                print("실패")
                print(error)
                print("기존 lotto_data.json 파일은 변경하지 않았습니다.")
                sys.exit(1)

            if round_data is None:
                print("최신 회차까지 수집 완료")
                break

            print("완료")
            collected.append(round_data)
            next_round += 1

    if not collected:
        print("추가할 신규 회차가 없습니다.")
        return

    for round_data in collected:
        existing_by_round[round_data["drwNo"]] = round_data

    save_data(list(existing_by_round.values()))
    print(f"총 {len(collected)}개 회차를 추가했습니다.")


if __name__ == "__main__":
    main()



