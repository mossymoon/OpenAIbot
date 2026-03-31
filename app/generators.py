import base64
import io
import pathlib
from typing import Union

import aiofiles
import aiohttp
import certifi
import ssl
from openai import AsyncOpenAI
from config import AITOKEN

client = AsyncOpenAI(api_key=AITOKEN)

async def gpt_text(req, model):
    completion = await client.chat.completions.create(
        messages=[{"role": "user", "content": req}],
        model=model,
    )
    return {'response': completion.choices[0].message.content,
            'usage': completion.usage.total_tokens}


async def gpt_image(req, model):
    response = await client.images.generate(
        model=model,
        prompt=req,
        size="1024x1024",
        quality="medium",
        n=1
    )
    data = response.data[0]
    if getattr(data, "url", None):
        return {'response': data.url,
                'usage': 1}
    if getattr(data, "b64_json", None):
        image_bytes = base64.b64decode(data.b64_json)
        return {'response': image_bytes,
                'usage': 1}
    return {'response': None,
            'usage': 1}


async def encode_image(image_path):
    async with aiofiles.open(image_path, "rb") as image_file:
        return base64.b64encode(await image_file.read()).decode('utf-8')


async def gpt_vision(req, model, file):

    base64_image = await encode_image(file)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AITOKEN}",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ],
            }
        ],
        "max_completion_tokens": 300
    }

    if req is not None:
        payload["messages"][0]["content"].append({
            "type": "text",
            "text": req,
        })

    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=60)) as session:
        async with session.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload) as response:
            completion = await response.json()

    if "choices" not in completion:
        return {"response": None, "usage": 0, "error": completion}

    return {'response': completion['choices'][0]['message']['content'],
            'usage': completion.get('usage', {}).get('total_tokens', 0)}
