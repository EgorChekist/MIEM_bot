
"""
!pip install -U langchain-community unstructured langchain-text-splitters langchain_huggingface torch
!pip install faiss-cpu langchain-community -q

Это файл с чанкингом и созданием векторной базы данных. В сам бот его всталвлять не надо, но все документы через него прогнать, а полученную vector_store уже скормить боту
Сейчас здесь допотопный, но быстрый чанкинг для быстрого тестирования. Потом заменю его на Semantic chunking по смыслу
Если что-то не будет работать пишите мне (Стелла)
"""



import os
import gc
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
import torch
import json

#работа с текстом, сплит, чанки
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    length_function=len,
)


all_chunks = []
folder_path = '/content/data/'

for root, dirs, files in os.walk(folder_path):
    for filename in files:
        if filename.endswith('.md'):
            filepath = os.path.join(root, filename)

            print(f"Обрабатываю: {filepath}")

            try:
                loader = TextLoader(filepath)
                docs = loader.load()

                chunks = splitter.split_documents(docs)
                all_chunks.extend(chunks)

                print(f"  Создано {len(chunks)} чанков")

                del docs, chunks
                gc.collect()

            except Exception as e:
                print(f"  Ошибка при обработке {filename}: {e}")

print(f"\nВсего обработано файлов: {len(all_chunks)} чанков")

#модель для эмбеддинга
embeddings = HuggingFaceEmbeddings(
    model_name="Alibaba-NLP/gte-multilingual-base",
    model_kwargs={
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "trust_remote_code": True
    },
    encode_kwargs={
        "normalize_embeddings": True,
    }
)

from langchain_community.vectorstores import FAISS

#готовим чанки
prepared_chunks = []

for chunk in all_chunks:
    prepared_chunks.append({
        "text": chunk.page_content,
        "source": chunk.metadata.get("source", "")
    })

#with open("data/chunks.json", "w", encoding="utf-8") as f:
#    json.dump(prepared_chunks, f, ensure_ascii=False, indent=2)

texts = [c["text"] for c in prepared_chunks]
metadatas = [{"source": c["source"]} for c in prepared_chunks]

vector_store = FAISS.from_texts(
    texts=texts,
    embedding=embeddings,
    metadatas=metadatas
)

vector_store.save_local("vector_store")

#vector_store.similarity_search("Вопрос для проверки",k=3)
