import openai
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# ✅ 최신 버전(1.0.0+) 방식의 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_gpt_response(prompt):
    try:
        # ✅ 최신 방식의 API 호출
        response = client.chat.completions.create(
            model="gpt-4o-mini", # 또는 "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": "너는 전문 번역가야. 입력된 문장을 지정된 언어로 자연스럽게 번역해줘."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"GPT API 에러 발생: {e}")
        return prompt  # 에러 발생 시 원문 반환

# #기본 테스트
# if __name__ == "__main__":
#     stt_output = "졸업할 수 있겠지?"
#     answer = get_gpt_response(stt_output)
#     print("🙋 나:" , stt_output)
#     print("🤖 GPT 응답:", answer)
#     print("-" * 40)

# #여러 문장을 한꺼번에 테스트
# questions = [
#     "안녕, 반가워.",
#     "오늘 할 일 추천해줘!",
#     "오늘 서울에서 벚꽃 보러갈 만한 곳이 어디 있을까?",
#     "서울에서 10000원으로 장보고 싶은데 어떤 걸 구매할까?",
# ]

# for q in questions:
#     print(f"🙋 사용자: {q}")
#     print(f"🤖 나만의 음성 비서: {get_gpt_response(q)}")
#     print("-" * 40)