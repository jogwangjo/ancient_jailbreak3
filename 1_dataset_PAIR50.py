# 1_data_preparation.py
import pandas as pd
import json
import os

# PAIR 논문 공식 50개 데이터셋
PAIR_URL = "https://raw.githubusercontent.com/patrickrchao/JailbreakingLLMs/main/data/harmful_behaviors_custom.csv"

def main():
    data_dir = "data"
    input_file = os.path.join(data_dir, "pair_50.csv")
    output_file = os.path.join(data_dir, "1_dataset.json")

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # 다운로드
    if not os.path.exists(input_file):
        print(f"[System] PAIR 50개 데이터 다운로드 중...")
        try:
            df_download = pd.read_csv(PAIR_URL)
            df_download.to_csv(input_file, index=False)
            print(f"[Success] 다운로드 완료! ({len(df_download)}개)")
        except Exception as e:
            print(f"[Error] 다운로드 실패: {e}")
            return

    df = pd.read_csv(input_file)
    print(f"[Info] 컬럼: {df.columns.tolist()}")
    print(f"[Info] 총 {len(df)}개 로드")

    # PAIR CSV는 'goal' 컬럼 사용 (AdvBench와 동일)
    if 'goal' not in df.columns:
        print("[Error] 'goal' 컬럼이 없습니다.")
        print(f"실제 컬럼명: {df.columns.tolist()}")
        return

    goals = df['goal'].tolist()

    dataset = []
    for idx, goal in enumerate(goals, start=1):
        dataset.append({
            "id": idx,
            "original_prompt": goal,
            "translations": {},
            "results": {},
            "evaluation": {}
        })

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=4, ensure_ascii=False)

    print(f"[Success] 저장 완료: {output_file} ({len(dataset)}개)")

if __name__ == "__main__":
    main()