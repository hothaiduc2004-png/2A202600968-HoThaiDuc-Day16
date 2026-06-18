import os
import json
import time
from typing import Tuple
from openai import OpenAI
from dotenv import load_dotenv

from .schemas import QAExample, JudgeResult, ReflectionEntry
from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM

load_dotenv()

def get_client() -> OpenAI:
    api_key = os.getenv("OPEN_ROUTER_API") or os.getenv("OPENROUTER_API_KEY") or ""
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

def call_llm(messages: list, model: str = "meta-llama/llama-3-8b-instruct") -> Tuple[str, int, int]:
    client = get_client()
    start_time = time.time()
    completion = client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": "http://localhost:8000",
            "X-OpenRouter-Title": "Reflexion Lab",
        },
        extra_body={},
        model=model,
        messages=messages,
    )
    latency_ms = int((time.time() - start_time) * 1000)
    content = completion.choices[0].message.content
    tokens = 0
    if completion.usage:
        tokens = completion.usage.total_tokens
    if tokens == 0:
        # Rough estimate if no usage returned
        tokens = int(len(str(messages)) / 4) + int(len(content) / 4)
    return content, tokens, latency_ms

def actor_answer(example: QAExample, attempt_id: int, agent_type: str, reflection_memory: list[str]) -> Tuple[str, int, int]:
    context_str = "\n".join([f"[{c.title}] {c.text}" for c in example.context])
    user_msg = f"Question: {example.question}\n\nContext:\n{context_str}"
    
    if reflection_memory:
        reflections_str = "\n".join([f"- {r}" for r in reflection_memory])
        user_msg += f"\n\nReflections from previous attempts:\n{reflections_str}"
        
    messages = [
        {"role": "system", "content": ACTOR_SYSTEM},
        {"role": "user", "content": user_msg}
    ]
    
    answer, tokens, latency = call_llm(messages)
    return answer.strip(), tokens, latency

def evaluator(example: QAExample, answer: str) -> Tuple[JudgeResult, int, int]:
    user_msg = f"Question: {example.question}\nExpected Gold Answer: {example.gold_answer}\nPredicted Answer: {answer}"
    messages = [
        {"role": "system", "content": EVALUATOR_SYSTEM},
        {"role": "user", "content": user_msg}
    ]
    
    response_text, tokens, latency = call_llm(messages)
    try:
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(response_text)
        return JudgeResult(score=int(data.get("score", 0)), reason=data.get("reason", "No reason provided.")), tokens, latency
    except Exception as e:
        score = 1 if "score\": 1" in response_text or "\"score\":1" in response_text or "\"score\": 1" in response_text else 0
        return JudgeResult(score=score, reason=f"Failed to parse JSON. Raw response: {response_text}"), tokens, latency

def reflector(example: QAExample, attempt_id: int, judge: JudgeResult, answer: str) -> Tuple[ReflectionEntry, int, int]:
    context_str = "\n".join([f"[{c.title}] {c.text}" for c in example.context])
    user_msg = f"Question: {example.question}\nContext:\n{context_str}\nGold Answer: {example.gold_answer}\nPredicted Answer: {answer}\nEvaluator Reason: {judge.reason}"
    messages = [
        {"role": "system", "content": REFLECTOR_SYSTEM},
        {"role": "user", "content": user_msg}
    ]
    
    response_text, tokens, latency = call_llm(messages)
    try:
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(response_text)
        return ReflectionEntry(
            attempt_id=attempt_id,
            failure_reason=data.get("failure_reason", "unknown"),
            lesson=data.get("lesson", "unknown"),
            next_strategy=data.get("next_strategy", "Try again.")
        ), tokens, latency
    except Exception as e:
        return ReflectionEntry(
            attempt_id=attempt_id,
            failure_reason="parse error",
            lesson="parse error",
            next_strategy="Try to read carefully."
        ), tokens, latency
