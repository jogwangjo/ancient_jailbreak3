import json
import os
import time
from tqdm import tqdm
from google import genai
from google.genai import types
from openai import OpenAI
import config

# 클라이언트 초기화
gemini_client = genai.Client(api_key=config.GOOGLE_API_KEY)
openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

LANG_KEY = "Middle_Korean"

SAFETY_SETTINGS_TARGET = [
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_MEDIUM_AND_ABOVE"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
]

# 공격 대상 모델 설정
ATTACK_TARGETS = {
    "gemini_2_5_flash": {
        "type": "gemini",
        "model_id": config.TARGET_MODELS["gemini_2_5_flash"],
        "result_file": "data/3_results_gemini_flash.json"
    }
}


def get_gemini_response(prompt, model_id, max_retries=10):
    for attempt in range(max_retries):
        try:
            response = gemini_client.models.generate_content(
                model=model_id,
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
                print(f"  [Rate limit] {wait}초 대기... (attempt {attempt+1})")
                time.sleep(wait)
            else:
                return f"[Error] {str(e)}"
    return "[Error] Max retries exceeded"

def attack_middle_korean(model_key, model_info, translated_data):
    """기존 result 파일에 Middle_Korean 결과만 추가"""
    result_file = model_info["result_file"]

    if not os.path.exists(result_file):
        print(f"[Error] {result_file} 없음. 해당 모델 스킵.")
        return

    with open(result_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    # translated_data를 id 기준으로 맵핑
    trans_map = {item["id"]: item for item in translated_data}

    print(f"\n🚀 {model_key} - Middle_Korean 공격 시작")

    for item in tqdm(dataset, desc=f"Attacking {model_key}"):
        item_id = item["id"]

        # 번역 데이터에서 Middle_Korean 프롬프트 가져오기
        if item_id not in trans_map:
            continue
        mk_prompt = trans_map[item_id].get("translations", {}).get(LANG_KEY)
        if not mk_prompt:
            continue

        # results 구조 초기화
        if "results" not in item:
            item["results"] = {}
        if LANG_KEY not in item["results"]:
            item["results"][LANG_KEY] = {}

        # 이미 결과 있으면 스킵
        if model_key in item["results"][LANG_KEY]:
            continue

        # 공격 실행
        if model_info["type"] == "gemini":
            response = get_gemini_response(mk_prompt, model_info["model_id"])

        item["results"][LANG_KEY][model_key] = response

        # 매 아이템마다 저장
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"✅ {model_key} Middle_Korean 공격 완료! ({result_file})")


def main():
    translated_file = "data/2_translated_test20.json"

    if not os.path.exists(translated_file):
        print(f"[Error] {translated_file} 파일이 없습니다.")
        return

    with open(translated_file, 'r', encoding='utf-8') as f:
        translated_data = json.load(f)

    # Middle_Korean 번역이 있는지 확인
    sample = translated_data[0].get("translations", {})
    if LANG_KEY not in sample:
        print(f"[Error] {translated_file}에 {LANG_KEY} 번역이 없습니다.")
        return

    print(f"📂 번역 데이터 로드 완료: {len(translated_data)}개 항목")

    for model_key, model_info in ATTACK_TARGETS.items():
        attack_middle_korean(model_key, model_info, translated_data)

    print("\n🎉 모든 모델 Middle_Korean 공격 완료!")


if __name__ == "__main__":
    main()