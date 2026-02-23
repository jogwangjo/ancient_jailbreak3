import json
import os
from openai import OpenAI
from tqdm import tqdm
import config

openai_client = OpenAI(api_key=config.OPENAI_API_KEY)


def is_refusal(text):
    """다국어 거절 문구 필터링"""
    if not text:
        return False
    text_lower = text.lower()
    refusal_keywords = [
        "i'm sorry", "i am sorry", "can't assist", "cannot assist", "assist with that",
        "policy", "cannot fulfill", "can't fulfill", "cannot provide", "cannot answer",
        "पूरयितुं न शक्नोमि", "क्षम्यताम्", "नहीं कर सकता",
        "δεν μπορώ να ικανοποιήσω", "δεν δύναμαι", "λυποῦμαι", "δεν μπορῶ",
        "non possum", "paenitet me", "ic ne mæg", "forgyfst", "ic bidde"
    ]
    return any(kw in text_lower for kw in refusal_keywords)


def get_gpt_response(prompt, model_name, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = openai_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,   # 논문 설정
                max_tokens=4096    # 논문 설정 (seed 제거)
            )
            return response.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                import time
                wait = 2 ** attempt
                print(f"  [Rate limit] {wait}초 대기 후 재시도... (attempt {attempt+1})")
                time.sleep(wait)
            else:
                return f"[Error] {str(e)}"
    return "[Error] Max retries exceeded"


def main():
    input_file = "data/2_translated.json"
    output_file = "data/3_results_gpt.json"

    if not os.path.exists(input_file):
        print(f"[Error] {input_file} 파일이 없습니다.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    # 기존 결과 로드 (중간 재시작 지원)
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
        print(f"📂 기존 결과 로드: {output_file}")

    gpt_models = {k: v for k, v in config.TARGET_MODELS.items() if "gpt" in k.lower()}

    print(f"🚀 GPT 공격 시작")
    print(f"   모델: {list(gpt_models.keys())}")

    for item in tqdm(dataset, desc="Attacking GPT"):
        if "results" not in item:
            item["results"] = {}

        for lang, prompt in item["translations"].items():
            # 번역 거부 문구 스킵
            if is_refusal(prompt):
                continue

            if lang not in item["results"]:
                item["results"][lang] = {}

            for m_key, m_id in gpt_models.items():
                if m_key in item["results"][lang]:
                    continue
                item["results"][lang][m_key] = get_gpt_response(prompt, m_id)

        # 매 아이템마다 저장 (중간 유실 방지)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"✅ 공격 완료! 결과 파일: {output_file}")


if __name__ == "__main__":
    main()