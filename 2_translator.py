# 2_translate.py
import json
import os
from openai import OpenAI
from tqdm import tqdm
import config

# OpenAI 클라이언트 (환경 변수에서 키 자동 인식)
client = OpenAI(api_key=config.OPENAI_API_KEY)

def translate_text(text, lang_name):
    """GPT-4o mini를 이용한 고대어 번역"""
    try:
        response = client.chat.completions.create(
            model=config.TRANSLATOR_MODEL,
            messages=[
                {"role": "system", "content": config.TRANSLATION_SYSTEM_PROMPT.format(target_language=lang_name)},
                {"role": "user", "content": f"Task: Dataset Localization\nTarget: {lang_name}\nInput String: {text}\nOutput Translation:"}
            ],
            temperature=0.1 # 번역 일관성
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"\n[Error] Translation failed: {e}")
        return None

def main():
    input_file = "data/1_dataset.json"
    output_file = "data/2_translated.json"

    with open(input_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    # 이어하기 기능
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            saved_map = {item["id"]: item for item in saved_data}
            for item in dataset:
                if item["id"] in saved_map:
                    item["translations"] = saved_map[item["id"]].get("translations", {})

    print(f"[Start] GPT({config.TRANSLATOR_MODEL})로 번역 시작...")

    for item in tqdm(dataset, desc="Translating"):
        # 1. Baseline English (비교군) 추가
        if "Baseline_English" not in item["translations"]:
            item["translations"]["Baseline_English"] = item["original_prompt"]

        # 2. 고대어 번역
        for lang_key, lang_desc in config.TARGET_LANGUAGES.items():
            if lang_key in item["translations"] and item["translations"][lang_key]:
                continue
            
            translated_text = translate_text(item["original_prompt"], lang_desc)
            
            if translated_text:
                item["translations"][lang_key] = translated_text
        
        # 중간 저장
        if item["id"] % 5 == 0:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, indent=4, ensure_ascii=False)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=4, ensure_ascii=False)
    
    print(f"[Success] 번역 완료! ({output_file})")

if __name__ == "__main__":
    main()