
import os
import pandas as pd
import torch

from typing import List

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline


BENCHMARK_PATH = "benchmark.csv"
RESULTS_PATH = "benchmark_results_clean.csv"

MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"


def build_rag_prompt(question: str, docs: List[Document]) -> str:
    context = "\n\n".join([
        d.page_content
        for d in docs
        if (d.page_content or "").strip()
    ])

    return f"""Ты — дружелюбный помощник, который должен правильно ответить на вопрос на основе предоставленной информации.
Вопрос:
{question}

Предоставленная информация:
{context}

Используй ТОЛЬКО информацию из документов. Отвечай максимально подробно.
Ответ:
"""


def main():
    df = pd.read_csv(BENCHMARK_PATH, sep=";", encoding="utf-8-sig")

    limit = os.getenv("BENCHMARK_LIMIT")
    if limit:
        df = df.head(int(limit))

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        device_map="auto",
        torch_dtype=torch.float16,
        trust_remote_code=True,
    )

    embeddings = HuggingFaceEmbeddings(
        model_name="Alibaba-NLP/gte-multilingual-base",
        model_kwargs={
            "device": "cuda" if torch.cuda.is_available() else "cpu",
            "trust_remote_code": True,
        },
        encode_kwargs={"normalize_embeddings": True},
    )

    vector_store = FAISS.load_local(
        "/content/vector_store",
        embeddings,
        allow_dangerous_deserialization=True,
    )

    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 5,
        },
    )

    llm = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=180,
        do_sample=False,
        repetition_penalty=1.2,
        return_full_text=False,
    )

    results = []

    for idx, row in df.iterrows():
        question = str(row["question"]).strip()
        print(f"[{len(results) + 1}/{len(df)}] {question}")

        try:
            docs = retriever.invoke(question)
            prompt = build_rag_prompt(question, docs)
            answer = llm(prompt)[0]["generated_text"].strip()

            retrieved_sources = []
            retrieved_chunks = []

            for d in docs:
                source = d.metadata.get("source", "")
                retrieved_sources.append(source)
                retrieved_chunks.append(
                    d.page_content[:700].replace("\n", " ")
                )

            results.append({
                "id": row.get("id", ""),
                "category": row.get("category", ""),
                "subtopic": row.get("subtopic", ""),
                "question": question,
                "expected_answer_summary": row.get("expected_answer_summary", ""),
                "source_doc": row.get("source_doc", ""),
                "must_contain": row.get("must_contain", ""),
                "should_not_contain": row.get("should_not_contain", ""),
                "model": MODEL_ID,
                "answer": answer,
                "retrieved_sources": " || ".join(retrieved_sources),
                "retrieved_chunks_preview": " || ".join(retrieved_chunks),
                "manual_score": "",
                "manual_comment": "",
            })

        except Exception as e:
            results.append({
                "id": row.get("id", ""),
                "category": row.get("category", ""),
                "subtopic": row.get("subtopic", ""),
                "question": question,
                "expected_answer_summary": row.get("expected_answer_summary", ""),
                "source_doc": row.get("source_doc", ""),
                "must_contain": row.get("must_contain", ""),
                "should_not_contain": row.get("should_not_contain", ""),
                "model": MODEL_ID,
                "answer": "",
                "retrieved_sources": "",
                "retrieved_chunks_preview": "",
                "manual_score": "",
                "manual_comment": f"ERROR: {e}",
            })

        pd.DataFrame(results).to_csv(
            RESULTS_PATH,
            index=False,
            encoding="utf-8-sig",
        )

    print(f"Done. Results saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
