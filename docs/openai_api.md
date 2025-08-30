```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

completion = client.chat.completions.create(
    model=os.getenv("OPENAI_COMPATIBLE_MODEL"),
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "Explain to me how AI works"
        },
    ],
)

print(completion.choices[0].message.content)
```