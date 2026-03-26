import json
import os
import time
from openai import OpenAI
from tqdm import tqdm
import config

openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

# 💡 JBB-experiment 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

MODEL_KEY = "gpt_4o"
MODEL_ID = "gpt-4o"

def get_gpt_response(prompt, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = openai_client.chat.completions.create(
                model=MODEL_ID,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=512
            )
            return response.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                wait = 2 ** attempt * 10
                print(f"\n  [Rate limit] {wait}초 대기 (attempt {attempt+1})")
                time.sleep(wait)
            else:
                return f"[Error] {str(e)}"
    return "[Error] Max retries exceeded"

def main():
    # 💡 Fix 완료된 버전을 최우선으로 찾고, 없으면 일반 번역본 사용
    input_file = os.path.join(DATA_DIR, "3_translated_final2.json")

    output_file = os.path.join(DATA_DIR, "4_results_gpt4o.json")

    if not os.path.exists(input_file):
        print(f"[Error] {input_file} 파일이 없습니다. 번역을 먼저 진행해주세요.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        saved_map = {item["id"]: item for item in saved}
        for item in dataset:
            if item["id"] in saved_map:
                item["results"] = saved_map[item["id"]].get("results", {})
        print(f"📂 기존 결과 로드 완료 (이어하기 가능): {output_file}")

    print(f"🚀 GPT-4o 공격 시작")
    print(f"   모델: {MODEL_ID}")

    for item in tqdm(dataset, desc="Attacking GPT-4o"):
        if "results" not in item:
            item["results"] = {}

        for lang, translated_prompt in item.get("translations", {}).items():
            if lang not in item["results"]:
                item["results"][lang] = {}

            if MODEL_KEY in item["results"][lang]:
                continue

            response = get_gpt_response(translated_prompt)
            item["results"][lang][MODEL_KEY] = response

            time.sleep(0.5) # 안전장치

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"✅ 공격 완료! 결과 파일: {output_file}")

if __name__ == "__main__":
    main()