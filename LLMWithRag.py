import os
import re
import glob
import torch

import numpy as np
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from langchain_community.document_loaders import TextLoader
from transformers import AutoTokenizer, AutoModelForCausalLM
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

class SemanticChunkerSelf:
    """Semantic chunking: разбивка по семантическим границам"""
    def __init__(self, embedding_model_name: str = "BAAI/bge-m3", threshold_percentile: int = 90,max_chunk_size=1000,
        min_chunk_size=200,
        device="cuda"):

        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.threshold_percentile = threshold_percentile
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size

    def chunk_text(self, text: str) -> List[str]:
        """Semantic chunking"""

        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 1:
            return [text]

        if len(sentences) <= 1:
            return sentences

        embeddings = self.embedding_model.encode(
            sentences,
            convert_to_numpy=True,
            batch_size=32,
            show_progress_bar=False
        )

        similarities = cosine_similarity(embeddings[:-1], embeddings[1:])
        similarities = np.diag(similarities)

        chunks = []
        current_chunk = sentences[0]

        for i in range(1, len(sentences)):
            sentence = sentences[i]
            similarity = similarities[i - 1]

            threshold = np.percentile(similarities, self.threshold_percentile)
            semantic_split = similarity < threshold

            size_split = len(current_chunk) + len(sentence) > self.max_chunk_size

            if semantic_split or size_split:
                if len(current_chunk) < self.min_chunk_size and chunks:
                    chunks[-1] += " " + current_chunk
                else:
                    chunks.append(current_chunk)

                current_chunk = sentence
            else:
                current_chunk += " " + sentence

        if len(current_chunk) < self.min_chunk_size and chunks:
            chunks[-1] += " " + current_chunk
        else:
            chunks.append(current_chunk)

        return chunks

#Функция для генерации ответа на поставленный промпт
def generate_amswer(prompt):
  messages = [
    {
        "role": "system",
        "content": """
         Внимательно прочитай вопрос студента.
         Выбери самое подходящее объяснение исходя ТОЛЬКО из предоставленного контекста.
         Не додумывай никакую информацию.
         Если ты не знаешь что ответить, то пиши `Я не обладаю подобной информациейЮ, рекомендую вам обратиться в учебный офис.`"""
    },
    {
        "role": "user",
        "content": prompt
    }
  ]

  inputs = tokenizer.apply_chat_template(
    messages,
    do_sample=False,
    add_generation_prompt=True,
    tokenize=True,
    return_dict=True,
    return_tensors="pt",
  ).to(model.device)

  outputs = model.generate(
      **inputs,
      max_new_tokens=300,
      temperature=0.0,
      do_sample=False)

  return tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:])




#Если хотите, тут можно менять модели
model_id = "Qwen/Qwen2.5-7B-Instruct"

# Загрузка с 4-битным квантованием (нужно для Colab)
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",
    torch_dtype=torch.float16,  # Используем float16
    load_in_4bit=True,  # 4-битное квантование
    low_cpu_mem_usage=True,
)


#Тут наш текст разбивается непосредственно на чанки.
# Если уже есть векторная разбитая база, оно нам не нужно



files  = glob.glob("/content/dataset/**/*.txt", recursive=True)
main_doc = []
chunker = SemanticChunkerSelf()
for file in files:
  text_loader = TextLoader(file)
  text = text_loader.load()[0].page_content

  #print(text)

  chunks = chunker.chunk_text(text)

  for idx, chunk in enumerate(chunks):
    main_doc.append(Document(page_content = chunk,
                    metadata = {
                        "chunk_id":idx,
                        "source":file
                    }))

# Тут мы начинаем создавать веткорную базу из наших разбитых текстов


os.environ["HF_TOKEN"] = "ТОКЕН HF"

emb = HuggingFaceEmbeddings(model_name="sentence-transformers/distiluse-base-multilingual-cased-v2",
    model_kwargs={
        "device": "cuda",
    },
    encode_kwargs={
        "batch_size": 128,  # Увеличиваем батч для GPU
        "normalize_embeddings": True,  # Нормализация для cosine similarity
    })


# Сохранение полученных чанков в векторную  базу.

# from langchain_community.vectorstores import FAISS  # UPDATED
#
# vector_storeF1 = FAISS.from_documents(
#     main_doc, emb
# )
#
# vector_storeF1.save_local("vector_storeF1")

#Если есть уже векторная база, можно просто загрузить её из файла
# vector_storeF1 = FAISS.load_local(
#     "/content/vector_storeF1",  # папка с сохраненным индексом
#     emb,
#     allow_dangerous_deserialization=True  # необходимо в новых версиях LangChain
# )



texts = [doc.page_content for doc in main_doc]
meta = [doc.metadata for doc in main_doc]

vector_store = None

batch_size = 64
for i in range(0, len(text), batch_size):
  batch_text = texts[i:i+batch_size]
  batch_meta = meta[i:i+batch_size]

  batch_emb = emb.embed_documents(batch_text)

  if vector_store is None:
    vector_store = FAISS.from_embeddings(
      text_embeddings=list(zip(batch_text, batch_emb)),
      embedding=emb,
      metadatas=batch_meta
    )
  else:
    vector_store.add_embeddings(
      text_embeddings=list(zip(batch_text, batch_emb)),
      metadatas=batch_meta
    )


vector_store.save_local("vector_store")

#Можно выделить их в отудб\льную функцию чтобы он брат отсюда информаицю из текстов
# вставлять полученне чанки как контекст в системный промпт и давать ответ по этому контекста
vector_store.max_marginal_relevance_search(
      "Вопрос нашего студента",
      k=10, #Сколько самых подходящих чанков он вернёт
      filter={"book_ru": "ИУП"} # Тут можно указать фильтр по метаданным.
  )









