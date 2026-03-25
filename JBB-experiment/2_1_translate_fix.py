import json
import os
import time
from tqdm import tqdm
from openai import OpenAI
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)

# 💡 입출력 파일 설정
INPUT_FILE = "data/3_translated_fixed.json" 
OUTPUT_FILE = "data/3_translated_final.json" 

def is_refusal(text):
    if not text:
        return True
    text_lower = text.lower()
    
    # 💡 한국어, 중국어 등 다국어 우회 거절 키워드 전면 추가
    refusal_keywords = [
        # 영어
        "i'm sorry", "i am sorry", "can't assist", "cannot assist", "assist with that",
        "policy", "cannot fulfill", "can't fulfill", "cannot provide", "cannot answer",
        "as an ai", "as a language model", "cannot", "sorry",
        # 산스크리트어 / 힌디어 / 그리스어 / 라틴어 / 고대어
        "पूरयितुं न शक्नोमि", "क्षम्यताम्", "नहीं कर सकता", "क्षमा", "न शक्नोमि",
        "δεν μπορώ να ικανοποιήσω", "δεν δύναμαι", "λυποῦμαι", "δεν μπορῶ", "οὐκ ἐπιτρέπεται",
        "non possum", "paenitet me", "ic ne mæg", "forgyfst", "ic bidde",
        # 🇰🇷 한국어 (현대어/중세어 포함)
        "죄송", "수행할 수 없", "할 수 없", "도와드릴 수 없", "안타깝게도", "정책", "거절",
        # 🇨🇳 중국어 (번체/간체 포함)
        "抱歉", "無法", "不能", "无法", "对不起", "政策"
    ]
    return any(kw in text_lower for kw in refusal_keywords)

def force_translate_with_config(original_text, lang_key, max_retries=10):
    if lang_key not in config.LANGUAGE_SYSTEM_PROMPTS:
        return "[Error] No config prompt for this language"
        
    lang_desc = config.TARGET_LANGUAGES[lang_key]

    for attempt in range(max_retries):
        try:
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
            
            if is_refusal(result_text):
                print(f"   [시도 {attempt+1}/{max_retries}] 방어벽에 막힘. 온도 {current_temp:.1f}로 올려서 재돌파 시도...")
                time.sleep(1)
                continue 
            
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

    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        saved_map = {item["id"]: item for item in saved_data}
        for item in dataset:
            if item["id"] in saved_map:
                item["translations"] = saved_map[item["id"]].get("translations", {})

    print("🚀 누락/거절된 번역 데이터 2차 정밀 복구 시작 (다국어 필터 적용)...")
    
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
                
            # 거절 문구(한국어/중국어 등)나 Error가 발견되었다면 재시도
            if is_refusal(translated_text) or translated_text.startswith("[Error]"):
                print(f"\n[Refusal Detected] ID: {item.get('id', 'Unknown')} | Lang: {lang_key}")
                print(f" - 기존 답변: {translated_text[:50]}...")
                
                new_translation = force_translate_with_config(original_prompt, lang_key)
                
                if new_translation and not is_refusal(new_translation) and not new_translation.startswith("[Error]"):
                    print(f" - ✅ 복구 완료: {new_translation[:50]}...")
                    item["translations"][lang_key] = new_translation
                    total_fixed += 1
                else:
                    print(f" - ❌ 복구 실패 (10번 다 거절됨): {new_translation[:50]}...")
                    item["translations"][lang_key] = new_translation
                    
                time.sleep(1) 

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"\n🎉 작업 완료! 총 {total_fixed}개의 거절된 번역을 복구했습니다.")
    print(f"📁 최종 저장된 파일: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()