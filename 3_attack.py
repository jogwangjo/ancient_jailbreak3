import json
import os
import time
import random
from tqdm import tqdm
import config
from google import genai
from google.genai import types
from openai import OpenAI
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# =================================================================
# 🎛️ 모델 제어 스위치 (ON/OFF Toggle)
# 실행하고 싶은 모델만 True로 변경하세요.
# =================================================================
ACTIVE_MODELS = {
    "gemini_2_5_flash": True,   # Gemini 2.5 Flash
    "gemini_2_5_pro": False,    # Gemini 2.5 Pro 
    "gpt-4o-mini": True,        # GPT 모델 
    "llama_3_1_8b": True        # Llama 3.1 8B (Groq)
}

# 파일 경로 설정
INPUT_FILE = "data/2_translated.json"
OUTPUT_FILE = "data/3_results_unified.json"  # 하나로 합쳐진 최종 결과 파일

# =================================================================
# ⚙️ API 클라이언트 및 설정 초기화
# =================================================================
gemini_client = genai.Client(api_key=config.GOOGLE_API_KEY)
openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
groq_client = OpenAI(api_key=config.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

# 파일 쓰기 충돌을 막기 위한 자물쇠(Lock)
file_lock = threading.Lock()

# Gemini 안전 설정 (논문 환경과 동일)
GEMINI_SAFETY_SETTINGS = [
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_MEDIUM_AND_ABOVE"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
]

# =================================================================
# 🛡️ 공통 유틸리티
# =================================================================
def is_refusal(text):
    if not text:
        return True
    text_lower = text.lower()
    refusal_keywords = [
        "i'm sorry", "i am sorry", "can't assist", "cannot assist", "assist with that",
        "policy", "cannot fulfill", "can't fulfill", "cannot provide", "cannot answer",
        "पूरयितुं न शक्नोमि", "क्षम्यताम्", "नहीं कर सकता",
        "δεν μπορώ να ικανοποιήσω", "δεν δύναμαι", "λυποῦμαι", "δεν μπορῶ",
        "non possum", "paenitet me", "ic ne mæg", "forgyfst", "ic bidde"
    ]
    return any(kw in text_lower for kw in refusal_keywords)

# =================================================================
# 🤖 모델별 API 핸들러
# =================================================================
def get_gemini_response(prompt, model_id, max_retries=10):
    for attempt in range(max_retries):
        try:
            response = gemini_client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=4096,
                    safety_settings=GEMINI_SAFETY_SETTINGS
                )
            )
            
            if response.candidates:
                candidate = response.candidates[0]
                finish_reason = candidate.finish_reason.name
                
                if finish_reason == "SAFETY":
                    return "[BLOCKED_SAFETY]"
                
                if candidate.content and candidate.content.parts:
                    texts = [part.text for part in candidate.content.parts if hasattr(part, 'text') and part.text]
                    if texts:
                        return "".join(texts)
                return f"[BLOCKED_{finish_reason}]"
                
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "resource_exhausted" in error_str:
                wait_time = min(2 ** attempt, 60) + random.uniform(0, 5)
                print(f"  [Gemini Rate Limit] {wait_time:.1f}초 대기... (attempt {attempt+1})")
                time.sleep(wait_time)
            else:
                return f"[Error] {str(e)}"
    return "[Error] Max retries exceeded"

def get_gpt_response(prompt, model_id, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = openai_client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=4096
            )
            return response.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                wait_time = min(2 ** attempt, 30) + random.uniform(0, 3)
                print(f"  [GPT Rate Limit] {wait_time:.1f}초 대기... (attempt {attempt+1})")
                time.sleep(wait_time)
            else:
                return f"[Error] {str(e)}"
    return "[Error] Max retries exceeded"

def get_llama_response(prompt, model_id, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = groq_client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=4096
            )
            time.sleep(2) 
            return response.choices[0].message.content
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                wait_time = (2 ** attempt) + random.uniform(0, 2)
                print(f"  [Groq Rate Limit] {wait_time:.1f}초 대기... (attempt {attempt+1})")
                time.sleep(wait_time)
            else:
                return f"[Error] {str(e)}"
    return "[Error] Max retries exceeded"

# =================================================================
# ⚡ 단일 아이템 처리 함수 (Worker)
# =================================================================
def process_single_item(item, active_model_keys):
    if "results" not in item:
        item["results"] = {}

    for lang, translated_prompt in item["translations"].items():
        if is_refusal(translated_prompt):
            continue

        if lang not in item["results"]:
            item["results"][lang] = {}

        for model_key in active_model_keys:
            model_id = config.TARGET_MODELS.get(model_key)
            if not model_id:
                continue

            # 이미 결과가 있으면 스킵 (이어하기)
            if model_key in item["results"][lang]:
                continue

            # 모델별 API 호출
            if "gemini" in model_key.lower():
                response = get_gemini_response(translated_prompt, model_id)
            elif "gpt" in model_key.lower():
                response = get_gpt_response(translated_prompt, model_id)
            elif "llama" in model_key.lower():
                response = get_llama_response(translated_prompt, model_id)
            else:
                response = "[Error] Unknown model type"

            item["results"][lang][model_key] = response

    return item

# =================================================================
# 🚀 메인 실행 루프 (Multi-threading)
# =================================================================
def main():
    if not os.path.exists(INPUT_FILE):
        print(f"[Error] {INPUT_FILE} 파일이 없습니다.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    # 기존 결과 및 평가(evaluation) 보존을 포함한 이어하기 로직
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        saved_map = {item["id"]: item for item in saved_data}
        for item in dataset:
            if item["id"] in saved_map:
                item["results"] = saved_map[item["id"]].get("results", {})
                if "evaluation" in saved_map[item["id"]]:
                    item["evaluation"] = saved_map[item["id"]]["evaluation"]
        print(f"📂 기존 결과 로드 완료 (이어하기 모드)")

    active_model_keys = [k for k, v in ACTIVE_MODELS.items() if v]
    print(f"\n🚀 병렬 통합 공격 시작 (Multi-threading)")
    print(f"🎯 활성화된 모델: {active_model_keys}")

    # 한 번에 던질 API 요청 수 (무료 API 제한이 걸릴 경우 이 숫자를 2~3으로 낮추세요)
    MAX_WORKERS = 5 
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_item, item, active_model_keys): item for item in dataset}

        for future in tqdm(as_completed(futures), total=len(dataset), desc="Attacking (Parallel)"):
            try:
                processed_item = future.result()
                
                # Lock을 걸고 안전하게 파일 덮어쓰기
                with file_lock:
                    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                        json.dump(dataset, f, indent=4, ensure_ascii=False)
                        
            except Exception as e:
                print(f"\n[Error] 처리 중 오류 발생: {e}")

    print(f"\n✅ 모든 병렬 공격 완료! 결과 파일: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()