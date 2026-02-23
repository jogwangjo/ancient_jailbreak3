import json
import os
import time
from openai import OpenAI
from tqdm import tqdm
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)


def back_translate(text, source_lang, max_retries=3):
    """고대어 → 영어 역번역 (gpt-4o-mini)"""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are an expert translator of {source_lang}. "
                            "Translate the following {source_lang} text into modern English. "
                            "Output ONLY the translated English text, nothing else."
                        )
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0.1,
                timeout=15
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"\n[Warning] 역번역 실패 (시도 {attempt+1}/3): {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                return None


def get_embedding(text, max_retries=3):
    """OpenAI text-embedding-3-small 임베딩"""
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            print(f"\n[Warning] 임베딩 실패 (시도 {attempt+1}/3): {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                return None


def compute_similarity(emb1, emb2):
    """코사인 유사도 계산"""
    return float(cosine_similarity(emb1.reshape(1, -1), emb2.reshape(1, -1))[0][0])


def main():
    input_file = "data/2_translated.json"
    output_file = "data/2_backtranslation_similarity.json"

    if not os.path.exists(input_file):
        print(f"[Error] {input_file} 파일이 없습니다.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    # 이어하기 지원
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        saved_map = {item["id"]: item for item in saved}
        print(f"📂 기존 결과 로드: {output_file}")
    else:
        saved_map = {}

    results = []

    lang_map = {
        "Sanskrit": "Sanskrit",
        "Ancient_Greek": "Koine Greek",
        "Latin": "Classical Latin",
        "Old_English": "Anglo-Saxon English",
        "Baseline_English": "English"
    }

    print("🔄 역번역 + 유사도 측정 시작 (gpt-4o-mini + text-embedding-3-small)")

    for item in tqdm(dataset, desc="Back-translating"):
        item_id = item["id"]

        # 이어하기: 이미 처리된 항목 스킵
        if item_id in saved_map:
            results.append(saved_map[item_id])
            continue

        original = item["original_prompt"]
        original_emb = get_embedding(original)
        if original_emb is None:
            continue

        result = {
            "id": item_id,
            "original_prompt": original,
            "back_translations": {},
            "similarities": {}
        }

        for lang_key, lang_name in lang_map.items():
            translated = item.get("translations", {}).get(lang_key)
            if not translated:
                continue

            # Baseline_English는 역번역 불필요 (동일 언어)
            if lang_key == "Baseline_English":
                back_translated = translated
            else:
                back_translated = back_translate(translated, lang_name)
                if back_translated is None:
                    continue

            back_emb = get_embedding(back_translated)
            if back_emb is None:
                continue

            similarity = compute_similarity(original_emb, back_emb)

            result["back_translations"][lang_key] = back_translated
            result["similarities"][lang_key] = round(similarity, 4)

        results.append(result)

        # 매 아이템마다 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4, ensure_ascii=False)

    # 최종 통계 출력
    print("\n📊 언어별 평균 코사인 유사도:")
    lang_scores = {lang: [] for lang in lang_map}
    for r in results:
        for lang, score in r.get("similarities", {}).items():
            if lang in lang_scores:
                lang_scores[lang].append(score)

    for lang, scores in lang_scores.items():
        if scores:
            print(f"  {lang:20s}: {np.mean(scores):.4f} (n={len(scores)})")

    print(f"\n✅ 완료! 결과 파일: {output_file}")


if __name__ == "__main__":
    main()