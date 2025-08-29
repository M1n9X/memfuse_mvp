请求代码如下
```python
import requests

url = 'https://api.jina.ai/v1/embeddings'
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer $JINA_API_KEY'
}

data = {
    "model": "jina-embeddings-v3",
    "task": "text-matching",
    "input": [
        "Organic skincare for sensitive skin with aloe vera and chamomile: Imagine the soothing embrace of nature with our organic skincare range, crafted specifically for sensitive skin. Infused with the calming properties of aloe vera and chamomile, each product provides gentle nourishment and protection. Say goodbye to irritation and hello to a glowing, healthy complexion.",
        "Bio-Hautpflege für empfindliche Haut mit Aloe Vera und Kamille: Erleben Sie die wohltuende Wirkung unserer Bio-Hautpflege, speziell für empfindliche Haut entwickelt. Mit den beruhigenden Eigenschaften von Aloe Vera und Kamille pflegen und schützen unsere Produkte Ihre Haut auf natürliche Weise. Verabschieden Sie sich von Hautirritationen und genießen Sie einen strahlenden Teint.",
        "Cuidado de la piel orgánico para piel sensible con aloe vera y manzanilla: Descubre el poder de la naturaleza con nuestra línea de cuidado de la piel orgánico, diseñada especialmente para pieles sensibles. Enriquecidos con aloe vera y manzanilla, estos productos ofrecen una hidratación y protección suave. Despídete de las irritaciones y saluda a una piel radiante y saludable.",
        "针对敏感肌专门设计的天然有机护肤产品：体验由芦荟和洋甘菊提取物带来的自然呵护。我们的护肤产品特别为敏感肌设计，温和滋润，保护您的肌肤不受刺激。让您的肌肤告别不适，迎来健康光彩。",
        "新しいメイクのトレンドは鮮やかな色と革新的な技術に焦点を当てています: 今シーズンのメイクアップトレンドは、大胆な色彩と革新的な技術に注目しています。ネオンアイライナーからホログラフィックハイライターまで、クリエイティビティを解き放ち、毎回ユニークなルックを演出しましょう。"
    ]
}

response = requests.post(url, headers=headers, json=data)

print(response.json())

```

生成的 Response 格式如下
```json
{
  "model": "jina-embeddings-v3",
  "object": "list",
  "usage": {
    "total_tokens": 410,
    "prompt_tokens": 410
  },
  "data": [
    {
      "object": "embedding",
      "index": 0,
      "embedding": [
        0.00935378,
        0.10311876,
        0.0494107,
        -0.09084168,
        0.0366438,
        ...
      ]
    },
    {
      "object": "embedding",
      "index": 1,
      "embedding": [
        -0.01723192,
        0.1117066,
        0.02701169,
        -0.05835238,
        0.03986514,
        ...
      ]
    },
    {
      "object": "embedding",
      "index": 2,
      "embedding": [
        -0.04895958,
        0.11686841,
        0.02536866,
        -0.07984079,
        0.01114604,
        ...
      ]
    },
    {
      "object": "embedding",
      "index": 3,
      "embedding": [
        0.05991271,
        0.04280833,
        0.02183173,
        -0.05791361,
        0.1084869,
        ...
      ]
    },
    {
      "object": "embedding",
      "index": 4,
      "embedding": [
        0.16196127,
        0.0252948,
        -0.01550297,
        -0.02532643,
        0.0385848,
        ...
      ]
    }
  ]
}
```