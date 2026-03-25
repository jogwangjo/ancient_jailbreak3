import json
import os
import time
from tqdm import tqdm
import config
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

genai.configure(api_key=config.GOOGLE_API_KEY)

# 💡 JBB-experiment 경로 설정
BASE_DIR = "JBB-experiment"
DATA_DIR = os.path.join(BASE_DIR, "data")

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

MODEL_KEY = "gemini_2_5_flash"
# config에 타겟 모델이 있다면 가져오고, 없다면 하드코딩된 이름 사용
MODEL_ID = config.TARGET_MODELS.get(MODEL_KEY, "gemini-2.5-flash")

model = genai.GenerativeModel(
    model_name=MODEL_ID,
    safety_settings=SAFETY_SETTINGS,
    generation_config=genai.GenerationConfig(
        temperature=0.7,
        max_output_tokens=512,
    )
)

def get_gemini_response(prompt, max_retries=10):
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)

            if response.candidates:
                candidate = response.candidates[0]
                finish_reason = candidate.finish_reason.name

                if finish_reason == "SAFETY":
                    return "[BLOCKED_SAFETY]"

                if candidate.content and candidate.content.parts:
                    texts = [p.text for p in candidate.content.parts if hasattr(p, 'text') and p.text]
                    if texts:
                        return "".join(texts)

                return f"[BLOCKED_{finish_reason}]"

            return "[BLOCKED_NO_CANDIDATE]"

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                wait = 2 ** attempt
                print(f"\n  [Rate limit] {wait}초 대기 (attempt {attempt+1})")
                time.sleep(wait)
            else:
                return f"[Error] {error_str}"

    return "[Error] Max retries exceeded"

def main():
    # 💡 Fix 완료된 버전을 최우선으로 찾고, 없으면 일반 번역본 사용
    input_file = os.path.join(DATA_DIR, "3_translated_final2.json")
        
    output_file = os.path.join(DATA_DIR, "4_results_gemini.json")

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

    print(f"🚀 Gemini 2.5 Flash 공격 시작")
    print(f"   모델: {MODEL_ID}")

    for item in tqdm(dataset, desc="Attacking Gemini"):
        if "results" not in item:
            item["results"] = {}

        for lang, translated_prompt in item.get("translations", {}).items():
            if lang not in item["results"]:
                item["results"][lang] = {}

            if MODEL_KEY in item["results"][lang]:
                continue

            response = get_gemini_response(translated_prompt)
            item["results"][lang][MODEL_KEY] = response

            time.sleep(1) # 안전장치: 요청 간 1초 대기

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"✅ 공격 완료! 결과 파일: {output_file}")

if __name__ == "__main__":
    main()