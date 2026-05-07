try:
    import requests
except ImportError:
    print("requests 라이브러리가 필요합니다. 아래 명령어를 실행해주세요:")
    print("pip install -r requirements.txt")
    exit(1)

import json
import sys
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/smok95/lotto/master/lotto.json"
DATA_FILE = Path(__file__).with_name("lotto_data.json")


def download_lotto_data():
    try:
        response = requests.get(
            SOURCE_URL,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        raise RuntimeError(f"로또 데이터를 다운로드하지 못했습니다: {error}") from error
    except ValueError as error:
        raise RuntimeError(f"다운로드한 데이터를 JSON으로 해석할 수 없습니다: {error}") from error

    if not isinstance(data, list):
        raise RuntimeError("다운로드한 JSON 형식이 올바르지 않습니다. 배열이어야 합니다.")

    return data


def convert_round(raw_round):
    draw_no = raw_round.get("draw_no")
    numbers = raw_round.get("numbers")
    bonus_no = raw_round.get("bonus_no")

    if not isinstance(draw_no, int):
        raise ValueError("draw_no가 없거나 정수가 아닙니다.")
    if not isinstance(numbers, list) or len(numbers) != 6:
        raise ValueError(f"{draw_no}회차 numbers는 6개 번호 배열이어야 합니다.")
    if not all(isinstance(number, int) for number in numbers):
        raise ValueError(f"{draw_no}회차 numbers에 정수가 아닌 값이 있습니다.")
    if not isinstance(bonus_no, int):
        raise ValueError(f"{draw_no}회차 bonus_no가 없거나 정수가 아닙니다.")

    return {
        "drwNo": draw_no,
        "drwNoDate": "",
        "drwtNo1": numbers[0],
        "drwtNo2": numbers[1],
        "drwtNo3": numbers[2],
        "drwtNo4": numbers[3],
        "drwtNo5": numbers[4],
        "drwtNo6": numbers[5],
        "bnusNo": bonus_no,
    }


def convert_data(raw_data):
    converted = []
    seen_rounds = set()

    for raw_round in raw_data:
        if not isinstance(raw_round, dict):
            raise RuntimeError("회차 데이터 항목은 객체여야 합니다.")

        try:
            converted_round = convert_round(raw_round)
        except ValueError as error:
            raise RuntimeError(f"회차 데이터 변환 실패: {error}") from error

        draw_no = converted_round["drwNo"]
        if draw_no in seen_rounds:
            continue

        seen_rounds.add(draw_no)
        converted.append(converted_round)

    return sorted(converted, key=lambda item: item["drwNo"])


def save_data(lotto_data):
    with DATA_FILE.open("w", encoding="utf-8-sig") as file:
        json.dump(lotto_data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main():
    try:
        raw_data = download_lotto_data()
        lotto_data = convert_data(raw_data)
        save_data(lotto_data)
    except RuntimeError as error:
        print(error)
        print("기존 lotto_data.json 파일은 변경하지 않았습니다.")
        sys.exit(1)

    print(f"총 {len(lotto_data)}회차 데이터 저장 완료")


if __name__ == "__main__":
    main()
