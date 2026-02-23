import json
import os
import time
from tqdm import tqdm
import config
from google import genai
from google.genai import types

client = genai.Client(api_key=config.GOOGLE_API_KEY)

# Chain-of-Thought Hijacking 논문과 동일한 Target 설정
SAFETY_SETTINGS_TARGET = [
    types.SafetySetting(
        category="HARM_CATEGORY_HARASSMENT",
        threshold="BLOCK_MEDIUM_AND_ABOVE"
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_HATE_SPEECH",
        threshold="BLOCK_MEDIUM_AND_ABOVE"
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
        threshold="BLOCK_MEDIUM_AND_ABOVE"
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_DANGEROUS_CONTENT",
        threshold="BLOCK_MEDIUM_AND_ABOVE"
    ),
]

MODEL_KEY = "gemini_2_5_pro"
MODEL_ID = config.TARGET_MODELS[MODEL_KEY]


def get_gemini_response(prompt, max_retries=10):
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

                if finish_reason == "SAFETY":
                    return "[BLOCKED_SAFETY]"

                # MAX_TOKENS 포함 모든 경우 parts에서 텍스트 추출
                if candidate.content and candidate.content.parts:
                    texts = []
                    for part in candidate.content.parts:
                        try:
                            if part.text:
                                texts.append(part.text)
                        except AttributeError:
                            pass
                    if texts:
                        return "".join(texts)

                return f"[BLOCKED_{finish_reason}]"
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                wait = 2 ** attempt
                print(f"  [Rate limit] {wait}초 대기 후 재시도... (attempt {attempt+1})")
                time.sleep(wait)
            else:
                return f"[Error] {str(e)}"
    return "[Error] Max retries exceeded"


def main():
    input_file = "data/2_translated_test20.json"
    output_file = "data/3_results_gemini_pro.json"

    if not os.path.exists(input_file):
        print(f"[Error] {input_file} 파일이 없습니다.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    # 기존 결과 로드 (중간 재시작 지원)
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            saved_map = {item["id"]: item for item in saved_data}
            for item in dataset:
                if item["id"] in saved_map:
                    item["results"] = saved_map[item["id"]].get("results", {})
                    item["evaluation"] = saved_map[item["id"]].get("evaluation", {})
            print(f"📂 기존 결과 로드: {output_file}")

    print(f"🚀 Gemini 2.5 Pro 공격 시작 (Sync 모드)")
    print(f"   모델: {MODEL_ID}")

    for item in tqdm(dataset, desc="Attacking"):
        if "results" not in item:
            item["results"] = {}

        for lang, translated_prompt in item["translations"].items():
            if lang not in item["results"]:
                item["results"][lang] = {}

            # 이미 결과 있으면 스킵 (이어하기)
            if MODEL_KEY in item["results"][lang]:
                continue

            # API 호출
            response = get_gemini_response(translated_prompt)
            item["results"][lang][MODEL_KEY] = response

            # [핵심 추가] 질문 하나 던지고 무조건 3초 대기! 
            # (1분에 약 20회 요청 속도로 조절하여 429 에러 원천 차단)
            time.sleep(3)

        # 매 아이템마다 저장 (중간 유실 방지)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"✅ 공격 완료! 결과 파일: {output_file}")


if __name__ == "__main__":
    main()