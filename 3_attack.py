# 3_attack.py
import json
import os
from openai import OpenAI
import google.generativeai as genai
from tqdm import tqdm
import time
import config

# API 설정
openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
genai.configure(api_key=config.GOOGLE_API_KEY)

def get_gpt_response(prompt, model_name):
    try:
        response = openai_client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[Error] {str(e)}"

def get_gemini_response(prompt, model_name):
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        # Gemini는 간혹 안전 필터로 인해 response.text 접근이 안 될 수 있음
        return response.text
    except Exception as e:
        return f"[Blocked/Error] {str(e)}"

def is_refusal(text):
    """번역기가 번역을 거절했는지 판별하는 함수"""
    refusal_keywords = ["i'm sorry", "i am sorry", "cannot assist", "can't assist", "assist with that", "policy"]
    return any(kw in text.lower() for kw in refusal_keywords)

def main():
    input_file = "data/2_translated.json"
    output_file = "data/3_results.json"

    if not os.path.exists(input_file):
        print(f"[Error] {input_file} 파일이 없습니다. 2단계를 먼저 실행하세요.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    print(f"[Start] 공격 시작 (Target Models: {list(config.TARGET_MODELS.keys())})")

    for item in tqdm(dataset, desc="Attacking Models"):
        if "results" not in item:
            item["results"] = {}

        for lang, translated_prompt in item["translations"].items():
            # [핵심] 방법 A 적용: 번역기가 거절한 문구는 공격 대상에서 제외
            if is_refusal(translated_prompt):
                continue 

            if lang not in item["results"]:
                item["results"][lang] = {}

            for model_key, model_id in config.TARGET_MODELS.items():
                # 이미 공격한 결과가 있으면 스킵 (이어하기)
                if model_key in item["results"][lang]:
                    continue
                
                if "gpt" in model_key:
                    response = get_gpt_response(translated_prompt, model_id)
                elif "gemini" in model_key:
                    response = get_gemini_response(translated_prompt, model_id)
                    time.sleep(2) # Gemini Rate Limit 방지
                
                item["results"][lang][model_key] = response
        
        # 5개 아이템마다 중간 저장
        if item["id"] % 5 == 0:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, indent=4, ensure_ascii=False)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"[Success] 공격 완료! 결과 저장: {output_file}")

if __name__ == "__main__":
    main()