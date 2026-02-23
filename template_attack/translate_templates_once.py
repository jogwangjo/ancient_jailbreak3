"""
translate_templates_once.py

DAN / Developer Mode / AIM 템플릿을 5개 언어로 번역하여
config_templates_translated.py 에 하드코딩된 형태로 저장.

한 번만 실행하면 됨 — 결과는 config_templates_translated.py에 저장됨.
"""

import json
import time
import os
from openai import OpenAI
from google import genai
from google.genai import types
import config
from config_templates import TEMPLATES

openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
gemini_client = genai.Client(api_key=config.GOOGLE_API_KEY)
GEMINI_MODEL = "gemini-2.0-flash"

OUTPUT_FILE = "config_templates_translated.py"
CACHE_FILE = "data/template_translation_cache.json"

TARGET_LANGUAGES = {
    "Sanskrit": "Sanskrit",
    "Ancient_Greek": "Koine Greek",
    "Latin": "Classical Latin",
    "Classical Arabic": "Classical Arabic",
    "Middle_Korean": "15th Century Middle Korean",
}


def translate_gpt(text, lang_name, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o",  # 템플릿은 품질 중요하므로 4o 사용
                messages=[
                    {"role": "system", "content": config.TRANSLATION_SYSTEM_PROMPT.format(target_language=lang_name)},
                    {"role": "user", "content": f"Task: Dataset Localization\nTarget: {lang_name}\nInput String: {text}\nOutput Translation:"}
                ],
                temperature=0.1,
                max_tokens=4096,
                timeout=60
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"  [GPT Error] {e} (attempt {attempt+1})")
            time.sleep(5)
    return None


def translate_gemini(text, lang_name, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=f"Task: Dataset Localization\nTarget: {lang_name}\nInput String: {text}\nOutput Translation:",
                config=types.GenerateContentConfig(
                    system_instruction=config.TRANSLATION_SYSTEM_PROMPT.format(target_language=lang_name),
                    temperature=0.1,
                    max_output_tokens=4096,
                )
            )
            return response.text.strip() if response.text else None
        except Exception as e:
            print(f"  [Gemini Error] {e} (attempt {attempt+1})")
            time.sleep(5)
    return None


def translate(text, lang_key, lang_name):
    if lang_key == "Middle_Korean":
        return translate_gemini(text, lang_name)
    else:
        return translate_gpt(text, lang_name)


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_cache(cache):
    os.makedirs("data", exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def write_output(results):
    """results: {template_name: {lang_key: translated_text}}"""
    lines = []
    lines.append('# config_templates_translated.py')
    lines.append('# DAN, Developer Mode, AIM 템플릿 — 5개 언어 번역 (config_translation_prompt.py 스타일 적용)')
    lines.append('# translate_templates_once.py 로 자동 생성됨\n')

    var_names = {
        "DAN": "DAN_TEMPLATES",
        "Developer_Mode": "DEVELOPER_MODE_TEMPLATES",
        "AIM": "AIM_TEMPLATES",
    }

    lang_order = ["Baseline_English", "Sanskrit", "Ancient_Greek", "Latin", "Classical Arabic", "Middle_Korean"]

    for template_name, var_name in var_names.items():
        lines.append(f'{var_name} = {{')
        for lang_key in lang_order:
            if lang_key in results.get(template_name, {}):
                text = results[template_name][lang_key]
                # 텍스트 내 따옴표 이스케이프
                text_escaped = text.replace('\\', '\\\\').replace('"""', '\\"\\"\\"')
                lines.append(f'\n    "{lang_key}": """{text_escaped}""",\n')
        lines.append('}\n')

    lines.append('# ===========================================================================')
    lines.append('TRANSLATED_TEMPLATES = {')
    for template_name, var_name in var_names.items():
        lines.append(f'    "{template_name}": {var_name},')
    lines.append('}')

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"\n✅ {OUTPUT_FILE} 저장 완료")


def main():
    cache = load_cache()
    results = {}

    lang_order = ["Sanskrit", "Ancient_Greek", "Latin", "Classical Arabic", "Middle_Korean"]

    for template_name, template_str in TEMPLATES.items():
        print(f"\n{'='*60}")
        print(f"[{template_name}] 번역 시작")
        results[template_name] = {}

        # Baseline English는 그대로
        results[template_name]["Baseline_English"] = template_str

        for lang_key in lang_order:
            lang_name = TARGET_LANGUAGES[lang_key]
            cache_key = f"{template_name}_{lang_key}"

            if cache_key in cache:
                print(f"  [{lang_key}] 캐시 사용")
                results[template_name][lang_key] = cache[cache_key]
                continue

            print(f"  [{lang_key}] 번역 중... (모델: {'Gemini' if lang_key == 'Middle_Korean' else 'GPT-4o'})")
            translated = translate(template_str, lang_key, lang_name)

            if translated:
                results[template_name][lang_key] = translated
                cache[cache_key] = translated
                save_cache(cache)
                print(f"  [{lang_key}] ✓ 완료 ({len(translated)} chars)")
            else:
                print(f"  [{lang_key}] ✗ 실패")

            time.sleep(1)

    write_output(results)
    print("\n🎉 모든 번역 완료!")
    print(f"결과: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()