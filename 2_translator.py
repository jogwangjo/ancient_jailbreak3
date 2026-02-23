import json
import os
import time
from openai import OpenAI
from tqdm import tqdm
from google import genai
from google.genai import types
import config

# GPT 클라이언트 (기존 언어용)
openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

# Gemini 클라이언트 (Middle Korean 전용)
gemini_client = genai.Client(api_key=config.GOOGLE_API_KEY)
GEMINI_TRANSLATOR_MODEL = "gemini-2.0-flash"


def translate_text_gpt(text, lang_name, max_retries=3):
    """GPT-4o-mini: 기존 언어 번역"""
    for attempt in range(max_retries):
        try:
            response = openai_client.chat.completions.create(
                model=config.TRANSLATOR_MODEL,
                messages=[
                    {"role": "system", "content": config.TRANSLATION_SYSTEM_PROMPT.format(target_language=lang_name)},
                    {"role": "user", "content": f"Task: Dataset Localization\nTarget: {lang_name}\nInput String: {text}\nOutput Translation:"}
                ],
                temperature=0.1,
                timeout=15
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"\n[Warning] GPT {lang_name} 번역 실패 (시도 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                return None


def translate_text_gemini(text, lang_name, max_retries=3):
    """Gemini 2.0 Flash: Middle Korean 전용 번역"""
    for attempt in range(max_retries):
        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_TRANSLATOR_MODEL,
                contents=f"Task: Dataset Localization\nTarget: {lang_name}\nInput String: {text}\nOutput Translation:",
                config=types.GenerateContentConfig(
                    system_instruction=config.TRANSLATION_SYSTEM_PROMPT.format(target_language=lang_name),
                    temperature=0.1,
                    max_output_tokens=512,
                )
            )
            return response.text.strip() if response.text else None
        except Exception as e:
            print(f"\n[Warning] Gemini {lang_name} 번역 실패 (시도 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                return None


def main():
    input_file = "data/1_dataset.json"
    output_file = "data/2_translated_test20.json"

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

    print(f"[Start] 번역 시작... (GPT-4o-mini: 기타 언어 / Gemini 2.0 Flash: Middle Korean)")

    for item in tqdm(dataset, desc="Translating"):
        if "translations" not in item:
            item["translations"] = {}

        # 1. Baseline English
        if "Baseline_English" not in item["translations"]:
            item["translations"]["Baseline_English"] = item["original_prompt"]

        # 2. 언어별 번역
        for lang_key, lang_desc in config.TARGET_LANGUAGES.items():
            if lang_key in item["translations"] and item["translations"][lang_key]:
                continue

            if lang_key == "Middle_Korean":
                # Gemini 2.0 Flash로 번역
                translated_text = translate_text_gemini(item["original_prompt"], lang_desc)
            else:
                # GPT-4o-mini로 번역
                translated_text = translate_text_gpt(item["original_prompt"], lang_desc)

            if translated_text:
                item["translations"][lang_key] = translated_text

        # 중간 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"[Success] 번역 완료! ({output_file})")


if __name__ == "__main__":
    main()