import json
import os
import time
from openai import OpenAI
from tqdm import tqdm
import config
from config_templates_translated import TRANSLATED_TEMPLATES

client = OpenAI(
    api_key=config.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

MODEL_KEY = "llama_3_1_8b"
MODEL_ID = config.TARGET_MODELS[MODEL_KEY]

INPUT_FILE = "data/2_translated_test20.json"
OUTPUT_FILE = "data/3_results_template_llama.json"

ALL_LANGS = ["Baseline_English", "Sanskrit", "Ancient_Greek", "Latin", "Classical Arabic", "Middle_Korean"]
ALL_TEMPLATES = list(TRANSLATED_TEMPLATES.keys())

GROQ_SLEEP = 2  # 30 RPM 제한


def call_llama(prompt, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_ID,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=8196
            )
            time.sleep(GROQ_SLEEP)
            return response.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                wait = 2 ** attempt
                print(f"\n  [Rate limit] {wait}초 대기...")
                time.sleep(wait)
            else:
                time.sleep(GROQ_SLEEP)
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

    total = len(dataset) * len(ALL_TEMPLATES) * len(ALL_LANGS)
    print(f"🚀 Llama 3.1 8B (Groq) 템플릿 공격 시작")
    print(f"   모델: {MODEL_ID}")
    print(f"   템플릿: {ALL_TEMPLATES}")
    print(f"   언어: {ALL_LANGS}")
    print(f"   총 요청 수 (최대): {total} | 예상 소요: {total * GROQ_SLEEP // 60}분")

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

                response = call_llama(prompt)
                item["template_results"][template_name][lang][MODEL_KEY] = response

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"✅ 완료! ({OUTPUT_FILE})")


if __name__ == "__main__":
    main()