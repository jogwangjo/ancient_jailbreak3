# 1_data_preparation.py
import pandas as pd
import json
import os

# AdvBench 공식 데이터 URL (LLM Attacks Repository)
ADVBENCH_URL = "https://raw.githubusercontent.com/llm-attacks/llm-attacks/main/data/advbench/harmful_behaviors.csv"

def main():
    # 경로 설정
    data_dir = "data"
    input_file = os.path.join(data_dir, "advbench.csv")
    output_file = os.path.join(data_dir, "1_dataset.json")

    # 1. 데이터 폴더 생성
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # 2. AdvBench 파일 확인 및 다운로드
    if not os.path.exists(input_file):
        print(f"[System] '{input_file}' 파일이 없습니다. 공식 저장소에서 다운로드합니다...")
        try:
            # URL에서 바로 읽어서 CSV로 저장
            df_download = pd.read_csv(ADVBENCH_URL)
            df_download.to_csv(input_file, index=False)
            print(f"[Success] 다운로드 완료! ({len(df_download)}개 데이터)")
        except Exception as e:
            print(f"[Error] 다운로드 실패: {e}")
            return

    # 3. 데이터 로드 및 샘플링
    df = pd.read_csv(input_file)
    
    # AdvBench는 'goal'이라는 컬럼에 질문이 있습니다.
    if 'goal' not in df.columns:
        print("[Error] CSV 파일에 'goal' 컬럼이 없습니다.")
        return

    # 랜덤으로 20개만 추출 (실험 속도를 위해)
    # random_state=42로 고정하여 언제 실행해도 같은 20개가 뽑히도록 함
    # df_sample = df.sample(n=20, random_state=42)
    goals = df['goal'].tolist()
    
    print(f"[Info] '{input_file}'에서 랜덤하게 20개의 데이터를 추출했습니다.")

    # 4. JSON 변환 (ID는 1부터 시작)
    dataset = []
    for idx, goal in enumerate(goals, start=1):  # start=1 로 변경
        dataset.append({
            "id": idx,
            "original_prompt": goal,
            "translations": {},
            "results": {},
            "evaluation": {} 
        })

    # 5. 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=4, ensure_ascii=False)
    
    print(f"[Success] 데이터 준비 완료: {output_file}")
    print(f"         (총 {len(dataset)}개의 질문이 저장되었습니다.)")

if __name__ == "__main__":
    main()