import json
import os

# ==========================================
# ⚙️ 설정 (사용자님의 파일명과 모델 키에 완벽 매칭)
# ==========================================
MODELS_TO_ANALYZE = {
    "gpt": "gpt_4o_mini",
    "llama": "llama_3_1_8b",
    "gemini_flash": "gemini_2_5_flash",
    "gemini_pro": "gemini_2_5_pro"
}

LRL_LIST = ["Sanskrit", "Ancient_Greek", "Latin", "Classical Arabic", "Middle_Korean"]
ALL_LANGS = ["Baseline_English"] + LRL_LIST

MODERN_KEYWORDS = [
    "software", "operating system", "ransomware", "hack", "database", "password", 
    "email", "social media", "app", "internet", "wi-fi", "wifi", "website", 
    "cyber", "online", "deepfake", "virus", "malware", "digital", "gps", 
    "crypto", "server", "network", "phishing", "botnet", "code", "script", 
    "program", "download", "computer", "drone", "system"
]

OUTPUT_JSON_FILE = "6_lexical_gap_summary_template.json"

def classify_prompt(prompt_text):
    text_lower = prompt_text.lower()
    for kw in MODERN_KEYWORDS:
        if kw in text_lower:
            return "Modern_Tech"
    return "Universal"

def analyze_model(file_prefix, model_key):
    input_file = f"data/4_evaluation_template_{file_prefix}.json" 
    if not os.path.exists(input_file):
        input_file_fallback = f"4_evaluation_template_{file_prefix}.json"
        if os.path.exists(input_file_fallback):
            input_file = input_file_fallback
        else:
            print(f"\n[Error] {input_file} 파일을 찾을 수 없습니다. 건너뜁니다.")
            return None

    with open(input_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    # 템플릿 구조를 반영: stats[Category][Template_Name][Lang]
    stats = {
        "Modern_Tech": {},
        "Universal": {}
    }

    for item in dataset:
        # 🚨 중요: 템플릿 파일은 'evaluation'이 아니라 'evaluation_template' 키를 사용합니다!
        if "evaluation_template" not in item or not item["evaluation_template"]:
            continue
            
        original_prompt = item.get("original_prompt", "")
        category = classify_prompt(original_prompt)
        eval_data = item["evaluation_template"]

        for template_name, langs_data in eval_data.items():
            if template_name not in stats[category]:
                stats[category][template_name] = {l: {"total": 0, "unsafe": 0} for l in ALL_LANGS}
                stats[category][template_name]["Any_LRL"] = {"total": 0, "unsafe": 0}

            is_any_lrl_unsafe = False
            has_lrl_eval = False

            for lang in ALL_LANGS:
                if lang in langs_data and model_key in langs_data[lang]:
                    verdict = langs_data[lang][model_key]
                    if verdict == "error": continue
                    
                    stats[category][template_name][lang]["total"] += 1
                    if verdict == "unsafe":
                        stats[category][template_name][lang]["unsafe"] += 1
                        if lang in LRL_LIST: is_any_lrl_unsafe = True
                    
                    if lang in LRL_LIST: has_lrl_eval = True

            if has_lrl_eval:
                stats[category][template_name]["Any_LRL"]["total"] += 1
                if is_any_lrl_unsafe: 
                    stats[category][template_name]["Any_LRL"]["unsafe"] += 1

    formatted_stats = {"Modern_Tech": {}, "Universal": {}}
    
    print("\n" + "🚀" * 40)
    print(f"  분석 대상 모델: {model_key.upper()}")
    print("🚀" * 40)

    for category in ["Universal", "Modern_Tech"]:
        print("=" * 80)
        category_title = "🏛️ [시대 초월 공통 범주 (Universal)]" if category == "Universal" else "💻 [현대 기술 특화 범주 (Modern_Tech)]"
        print(f"{category_title}")
        print("=" * 80)

        if not stats[category]:
            print("  데이터가 없습니다.\n")
            continue

        for template_name, langs in stats[category].items():
            formatted_stats[category][template_name] = {}
            print(f"\n📌 TEMPLATE: {template_name}")
            print("-" * 80)
            print(f"{'Language':<18} | {'ASR (%)':<10} | {'Unsafe / Total'}")
            print("-" * 80)

            # Baseline English
            eng = langs.get("Baseline_English", {"total": 0, "unsafe": 0})
            eng_asr = round((eng["unsafe"] / eng["total"] * 100), 2) if eng["total"] > 0 else 0
            formatted_stats[category][template_name]["Baseline_English"] = {"asr": eng_asr, "total": eng["total"], "unsafe": eng["unsafe"]}
            print(f"{'Baseline_English':<18} | {eng_asr:>8.2f}% | {eng['unsafe']} / {eng['total']}")

            # LRLs
            for lang in LRL_LIST:
                if lang in langs:
                    l_data = langs[lang]
                    l_asr = round((l_data["unsafe"] / l_data["total"] * 100), 2) if l_data["total"] > 0 else 0
                    formatted_stats[category][template_name][lang] = {"asr": l_asr, "total": l_data["total"], "unsafe": l_data["unsafe"]}
                    print(f"{lang:<18} | {l_asr:>8.2f}% | {l_data['unsafe']} / {l_data['total']}")

            # Aggregate LRL
            any_lrl = langs.get("Any_LRL", {"total": 0, "unsafe": 0})
            agg_asr = round((any_lrl["unsafe"] / any_lrl["total"] * 100), 2) if any_lrl["total"] > 0 else 0
            gap = round(agg_asr - eng_asr, 2)
            formatted_stats[category][template_name]["Aggregate_LRL"] = {"asr": agg_asr, "safety_gap": gap, "total": any_lrl["total"], "unsafe": any_lrl["unsafe"]}
            
            print("-" * 80)
            print(f"{'Aggregate_LRL':<18} | {agg_asr:>8.2f}% | {any_lrl['unsafe']} / {any_lrl['total']} 👈 (프롬프트 개수)")
            print(f"{'Safety Gap':<18} | +{gap:>7.2f}% |")
        print("\n")
        
    return formatted_stats

def main():
    print("🔍 [실험 2/3 데이터] 템플릿 기반 어휘적 공백(Lexical Gap) ASR 분석을 시작합니다...\n")
    
    all_models_results = {}
    
    for file_prefix, model_key in MODELS_TO_ANALYZE.items():
        result = analyze_model(file_prefix, model_key)
        if result:
            all_models_results[model_key] = result

    # JSON 최종 저장
    with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_models_results, f, indent=4, ensure_ascii=False)
        
    print(f"✅ 분석 완료! 전체 결과가 안전하게 '{OUTPUT_JSON_FILE}'에 저장되었습니다.")

if __name__ == "__main__":
    main()