import json
import os
import time
from openai import OpenAI
from tqdm import tqdm
import config

openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

# 💡 최상위 폴더 경로를 JBB-experiment로 고정
BASE_DIR = "JBB-experiment"
DATA_DIR = os.path.join(BASE_DIR, "data")

print("현재 경로:", os.getcwd())
print(f"{DATA_DIR} 폴더 내용:", os.listdir(DATA_DIR) if os.path.exists(DATA_DIR) else f"{DATA_DIR} 폴더 없음")

def translate_text(text, lang_key, max_retries=5):
    # 언어 키 유효성 먼저 체크
    if lang_key not in config.LANGUAGE_SYSTEM_PROMPTS:
        print(f"\n[Error] '{lang_key}' 프롬프트 없음. 스킵.")
        return None

    lang_desc = config.TARGET_LANGUAGES[lang_key]
    for attempt in range(max_retries):
        try:
            response = openai_client.chat.completions.create(
                model=config.TRANSLATOR_MODEL,
                messages=[
                    {"role": "system", "content": config.get_translation_prompt(lang_key)},
                    {"role": "user", "content": f"Task: Dataset Localization\nTarget: {lang_desc}\nInput String: {text}\nOutput Translation:"}
                ],
                temperature=0.1,
                timeout=30
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate" in error_str.lower():
                wait = 2 ** attempt * 10
                print(f"\n[Rate Limit] {wait}초 대기 (attempt {attempt+1})")
                time.sleep(wait)
            else:
                print(f"\n[Warning] {lang_key} 실패 (시도 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    return None
    return None

def main():
    # 💡 입출력 파일을 JBB-experiment/data/ 로 설정
    input_file = os.path.join(DATA_DIR, "1_dataset.json")
    output_file = os.path.join(DATA_DIR, "2_translated.json")

    if not os.path.exists(input_file):
        print(f"[Error] {input_file} 파일이 없습니다. 1_data_preparation_jbb.py 를 먼저 실행해주세요.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    print(f"[Info] input: {len(dataset)}개")

    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        saved_map = {item["id"]: item for item in saved_data}
        for item in dataset:
            if item["id"] in saved_map:
                item["translations"] = saved_map[item["id"]].get("translations", {})
        print(f"[Info] 기존 결과 로드 완료 (이어하기)")

    print(f"[Start] 번역 시작...")

    for item in tqdm(dataset, desc="Translating"):
        try:
            if "translations" not in item:
                item["translations"] = {}

            if "Baseline_English" not in item["translations"]:
                item["translations"]["Baseline_English"] = item["original_prompt"]

            for lang_key in config.TARGET_LANGUAGES:
                existing = item["translations"].get(lang_key, "")
                # 이미 번역이 되어있고, 거절 문구가 없으면 패스
                if existing and "sorry" not in existing.lower() and "cannot" not in existing.lower():
                    continue

                translated_text = translate_text(item["original_prompt"], lang_key)
                if translated_text:
                    item["translations"][lang_key] = translated_text

        except Exception as e:
            print(f"\n[Error] id={item['id']} 처리 중 오류: {e}")
            # 오류나도 저장하고 다음으로 넘어감

        # 매 아이템마다 덮어쓰기 저장 (중단되어도 안전함)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"\n[Success] 완료! 결과가 {output_file} 에 저장되었습니다.")

if __name__ == "__main__":
    main()