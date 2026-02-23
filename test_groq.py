import config
from openai import OpenAI
client = OpenAI(api_key=config.GROQ_API_KEY, base_url='https://api.groq.com/openai/v1')
print('API KEY:', repr(config.GROQ_API_KEY[:10]))
print('MODEL:', config.TARGET_MODELS['llama_3_1_8b'])
try:
    r = client.chat.completions.create(model=config.TARGET_MODELS['llama_3_1_8b'], messages=[{'role':'user','content':'hello'}], max_tokens=10, temperature=0)
    print('SUCCESS:', r.choices[0].message.content)
except Exception as e:
    print('ERROR:', repr(e))
