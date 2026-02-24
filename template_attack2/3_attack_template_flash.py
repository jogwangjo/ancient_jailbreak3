import json
import os
import time
import random
from tqdm import tqdm
import config
from google import genai
from google.genai import types
from config_templates_translated import TRANSLATED_TEMPLATES

client = genai.Client(api_key=config.GOOGLE_API_KEY)

SAFETY_SETTINGS_TARGET = [
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_MEDIUM_AND_ABOVE"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
]

MODEL_KEY = "gemini_2_5_flash"  # Flash 모델로 변경됨
MODEL_ID = config.TARGET_MODELS[MODEL_KEY]

INPUT_FILE = "data/2_translated_sampled_100.json"
OUTPUT_FILE = f"data/3_results_template_{MODEL_KEY}.json"

ALL_LANGS = ["Baseline_English", "Sanskrit", "Ancient_Greek", "Latin", "Classical Arabic" ,"Middle_Korean"]
ALL_TEMPLATES = list(TRANSLATED_TEMPLATES.keys())

def get_gemini_response(prompt, max_retries=20):
    # Pro 스크립트와 100% 동일한 로직 유지 (생략 없이 복붙됨)
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=8192,
                    safety_settings=SAFETY_SETTINGS_TARGET
                )
            )
            
            if response.candidates:
                candidate = response.candidates[0]
                finish_reason = candidate.finish_reason.name
                
                if finish_reason == "SAFETY": return "[BLOCKED_SAFETY]"
                
                if candidate.content and candidate.content.parts:
                    texts = [part.text for part in candidate.content.parts if hasattr(part, 'text') and part.text]
                    if texts: return "".join(texts)
                
                return f"[BLOCKED_{finish_reason}]"
                
        except Exception as e:
            error_str = str(e).lower()
            if "429" in str(e) or "quota" in error_str or "resource_exhausted" in error_str:
                base_wait = min(2 ** attempt, 120)
                wait_time = base_wait + random.uniform(0, base_wait * 0.1)
                print(f"\n⏳ [Rate limit] {wait_time:.1f}초 대기 후 재시도... (attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
                continue
            elif "timeout" in error_str or "deadline" in error_str:
                wait_time = 5 + random.uniform(0, 5)
                print(f"\n⏱️ [Timeout] {wait_time:.1f}초 대기 후 재시도... (attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
                continue
            elif "500" in str(e) or "503" in str(e) or "internal" in error_str:
                wait_time = 10 + random.uniform(0, 10)
                print(f"\n🔧 [Server Error] {wait_time:.1f}초 대기 후 재시도... (attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                return f"[Error] {str(e)}"
    
    return "[Error] Max retries exceeded"

def build_prompt(template_name, lang, question_translations, original_prompt):
    template_str = TRANSLATED_TEMPLATES[template_name][lang]
    question = original_prompt if lang == "Baseline_English" else question_translations.get(lang, "")
    if not question: return None
    return template_str.replace("{QUESTION}", question)

def main():
    if not os.path.exists(INPUT_FILE): return print(f"[Error] {INPUT_FILE} 없음.")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f: dataset = json.load(f)

    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f: saved_map = {i["id"]: i for i in json.load(f)}
        for item in dataset:
            if item["id"] in saved_map: item["template_results"] = saved_map[item["id"]].get("template_results", {})

    print(f"🚀 {MODEL_KEY} 템플릿 공격 시작")
    total_requests, successful_requests = 0, 0

    for item in tqdm(dataset, desc="Attacking"):
        if "template_results" not in item: item["template_results"] = {}
        for t_name in ALL_TEMPLATES:
            if t_name not in item["template_results"]: item["template_results"][t_name] = {}
            for lang in ALL_LANGS:
                if lang not in item["template_results"][t_name]: item["template_results"][t_name][lang] = {}
                if MODEL_KEY in item["template_results"][t_name][lang]: continue

                prompt = build_prompt(t_name, lang, item.get("translations", {}), item.get("original_prompt", ""))
                if not prompt: continue

                total_requests += 1
                response = get_gemini_response(prompt)
                item["template_results"][t_name][lang][MODEL_KEY] = response
                
                if not response.startswith("[Error]"): successful_requests += 1
                time.sleep(random.uniform(3, 5))

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f: json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"\n✅ 완료! ({OUTPUT_FILE})")

if __name__ == "__main__": main()