import json
import os
import re
from tqdm import tqdm

# 💡 파일 경로 설정
INPUT_FILE = "data/3_translated_final2.json" 
OUTPUT_FILE = "data/3_translated_final_korean_cleaned.json" 

def clean_middle_korean_text(text):
    if not text:
        return text
    
    # 1. 괄호와 그 안의 내용(한자 등)을 정규식으로 제거
    # 예: "미국(美國)" -> "미국", "법(法)ᄅᆞᆯ" -> "법ᄅᆞᆯ"
    cleaned = re.sub(r'\([^)]*\)', '', text)
    cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
    
    # 2. 혹시 남을 수 있는 이중 공백 제거 및 앞뒤 공백 정리
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"[Error] {INPUT_FILE} 파일이 없습니다.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    print("🚀 중세 국어(Middle_Korean) 데이터에서 괄호 및 한자 제거 시작...")
    
    total_cleaned = 0

    for item in tqdm(dataset, desc="Cleaning Middle Korean"):
        if "translations" in item and "Middle_Korean" in item["translations"]:
            original_text = item["translations"]["Middle_Korean"]
            
            # [Error]가 아닌 정상 번역본에 대해서만 정제 수행
            if original_text and not original_text.startswith("[Error]"):
                cleaned_text = clean_middle_korean_text(original_text)
                
                if original_text != cleaned_text:
                    item["translations"]["Middle_Korean"] = cleaned_text
                    total_cleaned += 1

    # 결과 저장
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"\n🎉 작업 완료! 총 {total_cleaned}개의 중세 국어 데이터에서 괄호를 제거했습니다.")
    print(f"📁 결과 파일: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()