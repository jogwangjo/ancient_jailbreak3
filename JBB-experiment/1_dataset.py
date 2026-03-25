import pandas as pd
import json
import os

# JailbreakBench (JBB-Behaviors) 공식 데이터 URL
JBB_URL = "https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors/raw/main/data/harmful-behaviors.csv"

def main():
    # 💡 최상위 실험 폴더 설정
    base_dir = "JBB-experiment"
    data_dir = os.path.join(base_dir, "data")
    input_file = os.path.join(data_dir, "jbb_behaviors.csv")
    output_file = os.path.join(data_dir, "1_dataset.json")

    # 1. JBB-experiment 및 내부 data 폴더 생성
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"[System] '{data_dir}' 폴더를 생성했습니다.")

    # 2. JailbreakBench 파일 확인 및 다운로드
    if not os.path.exists(input_file):
        print(f"[System] '{input_file}' 파일이 없습니다. 공식 저장소에서 다운로드합니다...")
        try:
            df_download = pd.read_csv(JBB_URL)
            df_download.to_csv(input_file, index=False)
            print(f"[Success] 다운로드 완료! ({len(df_download)}개 데이터)")
        except Exception as e:
            print(f"[Error] 다운로드 실패: {e}")
            return

    # 3. 데이터 로드
    df = pd.read_csv(input_file)
    
    # JBB-Behaviors는 'Goal' 컬럼에 질문이 있습니다.
    if 'Goal' not in df.columns:
        print("[Error] CSV 파일에 'Goal' 컬럼이 없습니다.")
        return

    goals = df['Goal'].tolist()
    print(f"[Info] '{input_file}'에서 데이터를 추출했습니다. (총 {len(goals)}개)")

    # 4. JSON 변환 (ID는 1부터 시작)
    dataset = []
    for idx, goal in enumerate(goals, start=1):
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