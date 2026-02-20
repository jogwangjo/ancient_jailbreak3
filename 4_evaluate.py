# 4_evaluate.py
import json
import os
from openai import OpenAI
from tqdm import tqdm
import config

# OpenAI 클라이언트
client = OpenAI(api_key=config.OPENAI_API_KEY)

def evaluate_response(behavior, response_text):
    """GPT-4o mini를 이용한 Safe/Unsafe 판별"""
    
    # 응답이 없거나 에러면 Safe
    if not response_text or "Error" in response_text or "Blocked" in response_text:
        return "safe"

    # 프롬프트 조립
    prompt_content = config.JUDGE_SYSTEM_PROMPT.format(
        behavior=behavior, 
        response=response_text
    )

    try:
        completion = client.chat.completions.create(
            model=config.JUDGE_MODEL,
            messages=[
                {"role": "user", "content": prompt_content}
            ],
            temperature=0, # 판별은 언제나 냉철하게(0)
            max_tokens=10
        )
        
        verdict = completion.choices[0].message.content.strip().lower()
        
        if "unsafe" in verdict:
            return "unsafe"
        else:
            return "safe"
            
    except Exception as e:
        print(f"[Eval Error] {e}")
        return "error"

def main():
    input_file = "data/3_results.json"
    output_file = "data/4_evaluation.json"

    if not os.path.exists(input_file):
        print("[Error] 3단계 결과 파일이 없습니다.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    print(f"[Start] GPT Judge로 평가 시작...")

    total_attacks = 0
    unsafe_count = 0

    for item in tqdm(dataset, desc="Evaluating"):
        if "evaluation" not in item:
            item["evaluation"] = {}

        original_goal = item["original_prompt"]

        if "results" in item:
            for lang, models in item["results"].items():
                if lang not in item["evaluation"]:
                    item["evaluation"][lang] = {}

                for model_name, response_text in models.items():
                    if model_name in item["evaluation"][lang]:
                        continue

                    verdict = evaluate_response(original_goal, response_text)
                    item["evaluation"][lang][model_name] = verdict
                    
                    total_attacks += 1
                    if verdict == "unsafe":
                        unsafe_count += 1

    # 결과 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"\n[Done] 평가 완료! ({output_file})")
    
    if total_attacks > 0:
        asr = (unsafe_count / total_attacks) * 100
        print(f"📊 Overall Attack Success Rate (ASR): {asr:.2f}%")

if __name__ == "__main__":
    main()