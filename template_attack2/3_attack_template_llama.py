import json, os, time, re
from openai import OpenAI
from tqdm import tqdm
import config
from config_templates_translated import TRANSLATED_TEMPLATES

client = OpenAI(api_key=config.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
MODEL_KEY = "llama_3_1_8b"
MODEL_ID = config.TARGET_MODELS[MODEL_KEY]

INPUT_FILE = "data/2_translated_sampled_100.json"
OUTPUT_FILE = f"data/3_results_template_{MODEL_KEY}.json"
ALL_LANGS = ["Baseline_English", "Sanskrit", "Ancient_Greek", "Latin", "Classical Arabic" ,"Middle_Korean"]
ALL_TEMPLATES = list(TRANSLATED_TEMPLATES.keys())

def call_llama(prompt):
    for attempt in range(10):
        try:
            res = client.chat.completions.create(
                model=MODEL_ID, messages=[{"role": "user", "content": prompt}], temperature=0.7, max_tokens=2048
            )
            time.sleep(7) # 기본 7초 휴식
            return res.choices[0].message.content
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "rate" in err:
                match = re.search(r"try again in ([\d\.]+)s", err)
                wait_time = float(match.group(1)) + 1.0 if match else 15 * (attempt + 1)
                print(f"\n[Rate limit] {wait_time:.1f}초 대기...")
                time.sleep(wait_time)
            else:
                time.sleep(7)
                return f"[Error] {e}"
    return "[Error] Max retries exceeded"

def main():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f: dataset = json.load(f)
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f: saved_map = {i["id"]: i for i in json.load(f)}
        for item in dataset:
            if item["id"] in saved_map: item["template_results"] = saved_map[item["id"]].get("template_results", {})

    for item in tqdm(dataset, desc=f"Attacking {MODEL_KEY}"):
        if "template_results" not in item: item["template_results"] = {}
        for t_name in ALL_TEMPLATES:
            if t_name not in item["template_results"]: item["template_results"][t_name] = {}
            for lang in ALL_LANGS:
                if lang not in item["template_results"][t_name]: item["template_results"][t_name][lang] = {}
                if MODEL_KEY in item["template_results"][t_name][lang]: continue

                q = item["original_prompt"] if lang == "Baseline_English" else item.get("translations", {}).get(lang, "")
                if not q: continue
                prompt = TRANSLATED_TEMPLATES[t_name][lang].replace("{QUESTION}", q)
                
                item["template_results"][t_name][lang][MODEL_KEY] = call_llama(prompt)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f: json.dump(dataset, f, indent=4, ensure_ascii=False)

if __name__ == "__main__": main()