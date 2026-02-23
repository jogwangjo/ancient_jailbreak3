import json
import os
import time
from tqdm import tqdm
from openai import OpenAI

import config

# Groq API 클라이언트 (OpenAI 호환)
client = OpenAI(
    api_key=config.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

MODEL_KEY = "llama_3_1_8b"
MODEL_ID = config.TARGET_MODELS[MODEL_KEY]
INPUT_FILE = "data/2_translated_test20.json"
OUTPUT_FILE = "data/3_results_llama.json"


def get_llama_response(prompt, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_ID,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=8196
            )
            return response.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                wait = 2 ** attempt
                print(f"\n  [Rate limit] {wait}초 대기... (attempt {attempt+1})")
                time.sleep(wait)
            else:
                return f"[Error] {str(e)}"
    return "[Error] Max retries exceeded"


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"[Error] {INPUT_FILE} 없음.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    # 이어하기 지원
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        saved_map = {item["id"]: item for item in saved_data}
        for item in dataset:
            if item["id"] in saved_map:
                item["results"] = saved_map[item["id"]].get("results", {})
                item["evaluation"] = saved_map[item["id"]].get("evaluation", {})
        print(f"📂 기존 결과 로드: {OUTPUT_FILE}")

    print(f"🚀 Llama 3.1 8B 공격 시작 (Groq API)")

    for item in tqdm(dataset, desc="Attacking Llama"):
        if "results" not in item:
            item["results"] = {}

        for lang, translated_prompt in item["translations"].items():
            if lang not in item["results"]:
                item["results"][lang] = {}

            if MODEL_KEY in item["results"][lang]:
                continue

            response = get_llama_response(translated_prompt)
            item["results"][lang][MODEL_KEY] = response

            # Groq 무료 tier rate limit 방지 (분당 30 RPM)
            time.sleep(2)

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"✅ 완료! ({OUTPUT_FILE})")


if __name__ == "__main__":
    main()