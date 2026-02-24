import json
import random

def sample_advbench(input_file, output_file, sample_size=100):
    with open(input_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    # 논문 재현성을 위해 시드 고정 (중요)
    random.seed(42)
    
    # 520개 중 100개 무작위 추출
    sampled_dataset = random.sample(dataset, sample_size)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sampled_dataset, f, indent=4, ensure_ascii=False)
        
    print(f"✅ {len(dataset)}개 중 {sample_size}개 추출 완료: {output_file}")

# 실행 예시 (맨 처음 번역된 2_translated.json에서 100개를 뽑아 새 파일로 만듭니다)
sample_advbench("data/2_translated.json", "data/2_translated_sampled_100.json")