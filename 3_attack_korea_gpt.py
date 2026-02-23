import json
import os
import time
from tqdm import tqdm
from openai import OpenAI
import config

openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

LANG_KEY = "Middle_Korean"
MODEL_KEY = "gpt_4o_mini"
MODEL_ID = config.TARGET_MODELS[MODEL_KEY]
RESULT_FILE = "data/3_results_gpt.json"
TRANSLATED_FILE = "data/2_translated_test20.json"


def get_gpt_response(prompt, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = openai_client.chat.completions.create(
                model=MODEL_ID,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=8192
            )
            return response.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                wait = 2 ** attempt
                print(f"  [Rate limit] {wait}초 대기... (attempt {attempt+1})")
                time.sleep(wait)
            else:
                return f"[Error] {str(e)}"
    return "[Error] Max retries exceeded"


def main():
    if not os.path.exists(TRANSLATED_FILE):
        print(f"[Error] {TRANSLATED_FILE} 없음.")
        return
    if not os.path.exists(RESULT_FILE):
        print(f"[Error] {RESULT_FILE} 없음.")
        return

    with open(TRANSLATED_FILE, 'r', encoding='utf-8') as f:
        translated_data = json.load(f)
    with open(RESULT_FILE, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    trans_map = {item["id"]: item for item in translated_data}

    print(f"🚀 GPT-4o-mini Middle_Korean 공격 시작")

    for item in tqdm(dataset, desc="Attacking GPT"):
        item_id = item["id"]
        trans_item = trans_map.get(item_id, {})

        # original_prompt는 스킵 여부와 관계없이 항상 채워넣기
        if not item.get("original_prompt"):
            item["original_prompt"] = trans_item.get("original_prompt", "")

        mk_prompt = trans_item.get("translations", {}).get(LANG_KEY)
        if not mk_prompt:
            continue

        if "results" not in item:
            item["results"] = {}
        if LANG_KEY not in item["results"]:
            item["results"][LANG_KEY] = {}

        if MODEL_KEY in item["results"][LANG_KEY]:
            continue

        item["results"][LANG_KEY][MODEL_KEY] = get_gpt_response(mk_prompt)

        with open(RESULT_FILE, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"✅ 완료! ({RESULT_FILE})")


if __name__ == "__main__":
    main()