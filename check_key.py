import os
import sys
from openai import OpenAI
import google.generativeai as genai

def test_openai():
    print("\n" + "="*40)
    print("🤖 1. OpenAI (GPT) 연결 테스트")
    print("="*40)

    api_key = os.getenv("OPENAI_API_KEY")
    
    # 1. 환경 변수 확인
    if not api_key:
        print("❌ [실패] 시스템 환경 변수에서 'OPENAI_API_KEY'를 찾을 수 없습니다.")
        return

    print(f"✅ 키 감지됨: {api_key[:8]}...{api_key[-4:]} (길이: {len(api_key)})")

    # 2. 실제 호출 테스트
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello! Just say 'OK'."}],
            max_tokens=10
        )
        print(f"✅ [성공] 응답 수신: \"{response.choices[0].message.content}\"")
    except Exception as e:
        print(f"❌ [에러] 호출 실패: {e}")

def test_gemini():
    print("\n" + "="*40)
    print("✨ 2. Google (Gemini) 연결 테스트")
    print("="*40)

    api_key = os.getenv("GOOGLE_API_KEY")

    # 1. 환경 변수 확인
    if not api_key:
        print("❌ [실패] 시스템 환경 변수에서 'GOOGLE_API_KEY'를 찾을 수 없습니다.")
        return

    print(f"✅ 키 감지됨: {api_key[:8]}...{api_key[-4:]} (길이: {len(api_key)})")

    # 2. 실제 호출 테스트
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content("Hello! Just say 'OK'.")
        print(f"✅ [성공] 응답 수신: \"{response.text.strip()}\"")
    except Exception as e:
        print(f"❌ [에러] 호출 실패: {e}")

if __name__ == "__main__":
    print("🔍 API Key System Check...")
    test_openai()
    test_gemini()
    print("\n" + "="*40)
    print("🏁 테스트 종료")