import json
import os
import time
from tqdm import tqdm
from google import genai
from google.genai import types
import config
from config_templates_translated import TRANSLATED_TEMPLATES

client = genai.Client(api_key=config.GOOGLE_API_KEY)

MODEL_KEY = "gemini_2_5_flash"
MODEL_ID = config.TARGET_MODELS[MODEL_KEY]

INPUT_FILE = "data/2_translated_test20.json"
OUTPUT_FILE = "data/3_results_template_gemini_flash.json"

ALL_LANGS = ["Baseline_English", "Sanskrit", "Ancient_Greek", "Latin", "Classical Arabic", "Middle_Korean"]
ALL_TEMPLATES = list(TRANSLATED_TEMPLATES.keys())

SAFETY_SETTINGS = [
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT",        threshold="BLOCK_MEDIUM_AND_ABOVE"),
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH",       threshold="BLOCK_MEDIUM_AND_ABOVE"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
]


def call_gemini(prompt, max_retries=10):
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=8192,
                    safety_settings=SAFETY_SETTINGS
                )
            )
            return response.text if response.text else "[BLOCKED] No content returned"
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                wait = 2 ** attempt
                print(f"\n  [Rate limit] {wait}초 대기...")
                time.sleep(wait)
            else:
                return f"[Error] {str(e)}"
    return "[Error] Max retries exceeded"


def build_prompt(template_name, lang, question_translations, original_prompt):
    template_str = TRANSLATED_TEMPLATES[template_name][lang]
    if lang == "Baseline_English":
        question = original_prompt
    else:
        question = question_translations.get(lang, "")
    if not question:
        return None
    return template_str.replace("{QUESTION}", question)


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"[Error] {INPUT_FILE} 없음.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    # 이어하기
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        saved_map = {item["id"]: item for item in saved_data}
        for item in dataset:
            if item["id"] in saved_map:
                item["template_results"] = saved_map[item["id"]].get("template_results", {})
        print(f"📂 기존 결과 로드: {OUTPUT_FILE}")

    print(f"🚀 Gemini 2.5 Flash 템플릿 공격 시작")
    print(f"   모델: {MODEL_ID}")
    print(f"   템플릿: {ALL_TEMPLATES}")
    print(f"   언어: {ALL_LANGS}")

    for item in tqdm(dataset, desc="Attacking"):
        if "template_results" not in item:
            item["template_results"] = {}

        for template_name in ALL_TEMPLATES:
            if template_name not in item["template_results"]:
                item["template_results"][template_name] = {}

            for lang in ALL_LANGS:
                if lang not in TRANSLATED_TEMPLATES[template_name]:
                    continue
                if lang not in item["template_results"][template_name]:
                    item["template_results"][template_name][lang] = {}
                if MODEL_KEY in item["template_results"][template_name][lang]:
                    continue

                prompt = build_prompt(
                    template_name, lang,
                    item.get("translations", {}),
                    item.get("original_prompt", "")
                )
                if not prompt:
                    continue

                response = call_gemini(prompt)
                item["template_results"][template_name][lang][MODEL_KEY] = response

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"✅ 완료! ({OUTPUT_FILE})")


if __name__ == "__main__":
    main()