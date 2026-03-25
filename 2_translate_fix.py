import json
import os
import time
from tqdm import tqdm
from openai import OpenAI
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)

INPUT_FILE = "data/2_translated_fixed2.json"
OUTPUT_FILE = "data/2_translated_fixed3.json" 

def is_refusal(text):
    if not text:
        return True
    text_lower = text.lower()
    refusal_keywords = [
        "i'm sorry", "i am sorry", "can't assist", "cannot assist", "assist with that",
        "policy", "cannot fulfill", "can't fulfill", "cannot provide", "cannot answer",
        "पूरयितुं न शक्नोमि", "क्षम्यताम्", "नहीं कर सकता",
        "δεν μπορώ να ικανοποιήσω", "δεν δύναμαι", "λυποῦμαι", "δεν μπορῶ",
        "non possum", "paenitet me", "ic ne mæg", "forgyfst", "ic bidde",
        "as an ai", "as a language model"
    ]
    return any(kw in text_lower for kw in refusal_keywords)

# 💡 수정된 부분: max_retries=10 으로 변경
def force_translate_with_config(original_text, lang_key, max_retries=10):
    """
    거절(I'm sorry) 당하면, 온도를 조금씩 올려가며 최대 10번까지 악착같이 다시 시도합니다.
    """
    if lang_key not in config.LANGUAGE_SYSTEM_PROMPTS:
        return "[Error] No config prompt for this language"
        
    lang_desc = config.TARGET_LANGUAGES[lang_key]

    for attempt in range(max_retries):
        try:
            # 시도 횟수가 늘어날수록 온도를 올려서(0.1 -> 0.9) 다른 방식의 답변을 유도
            current_temp = min(0.1 + (attempt * 0.1), 0.9) 
            
            response = client.chat.completions.create(
                model=config.TRANSLATOR_MODEL,
                messages=[
                    {"role": "system", "content": config.get_translation_prompt(lang_key)},
                    {"role": "user", "content": f"Task: Dataset Localization\nTarget: {lang_desc}\nInput String: {original_text}\nOutput Translation:"}
                ],
                temperature=current_temp, 
                timeout=30
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # [핵심 수정] 응답이 왔는데 그게 거절 문구(I'm sorry 등)라면?
            if is_refusal(result_text):
                print(f"   [시도 {attempt+1}/{max_retries}] 방어벽에 막힘. 온도 {current_temp:.1f}로 올려서 재돌파 시도...")
                time.sleep(1)
                continue # 리턴하지 않고 다음 시도로 넘어갑니다!
            
            # 거절 문구가 없으면 진짜로 성공한 것!
            return result_text
            
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate" in error_str:
                wait = 2 ** attempt * 5
                print(f"\n   [Rate Limit] {wait}초 대기 (attempt {attempt+1})")
                time.sleep(wait)
            else:
                print(f"\n   [Warning] 통신 에러 (시도 {attempt+1}/{max_retries}): {e}")
                time.sleep(5)
                
    return "[Error] Translation failed (10번 모두 거절당함)"

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"[Error] {INPUT_FILE} 파일이 없습니다.")
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
                item["translations"] = saved_map[item["id"]].get("translations", {})

    print("🚀 누락/거절된 번역 데이터 순정 복구 시작 (최대 10회 재시도)...")
    
    total_fixed = 0

    for item in tqdm(dataset, desc="Fixing Translations"):
        original_prompt = item.get("original_prompt", "")
        
        if not original_prompt:
            continue

        if "translations" not in item:
            item["translations"] = {}

        for lang_key, translated_text in list(item["translations"].items()):
            if lang_key == "Baseline_English":
                continue
                
            # 거절 문구가 발견되었다면 재시도
            if is_refusal(translated_text):
                print(f"\n[Refusal Detected] ID: {item.get('id', 'Unknown')} | Lang: {lang_key}")
                print(f" - 기존 답변: {translated_text[:50]}...")
                
                # 최대 10번 재시도하는 함수 호출
                new_translation = force_translate_with_config(original_prompt, lang_key)
                
                if new_translation and not is_refusal(new_translation) and not new_translation.startswith("[Error]"):
                    print(f" - 복구 완료: {new_translation[:50]}...")
                    item["translations"][lang_key] = new_translation
                    total_fixed += 1
                else:
                    print(f" - 복구 실패 (10번 다 거절됨): {new_translation[:50]}...")
                    
                time.sleep(1) 

        # 덮어쓰기 저장
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"\n✅ 작업 완료! 총 {total_fixed}개의 거절된 번역을 복구했습니다.")
    print(f"📁 저장된 파일: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()