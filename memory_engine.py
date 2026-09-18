from math import exp, log
from datetime import datetime
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings

EDGE_THRESHOLD  = 1.2
MAX_MENTION = 100

class MemoryEngine:
    def __init__(self,persist_dir:str="./memory_db",model_name:str="BAAI/bge-small-zh-v1.5"):
        self.persist_dir=persist_dir
        self.model_name=model_name

        self.embeddings=HuggingFaceEmbeddings(model_name=self.model_name)
        self.vector_db=Chroma(
            collection_name="agent_memory",
            embedding_function=self.embeddings,
            persist_directory=persist_dir
        )

    def save(
        self,
        concept:str,
        content:str,
        tags:list[str],
    )->str:
        existing = self.vector_db.get(where={'concept':concept})

        if existing and existing["ids"]:
            concept_id=existing["ids"][0]
            concept_content=existing["documents"][0]
            concept_metadatas=existing["metadatas"][0]

            msg=(
                f"当前认知已存在,"
                f"认知id为[{concept_id}],"
                f"认知内容[{concept_content}]\n"
                f"认知元数据metadatas[{concept_metadatas}]"
            )
            return msg
        else:
            concept_tags=",".join(tags)
            new_metadatas={
                "concept":concept,
                "tags":concept_tags,
                "mention_count":1,
                "created_at":datetime.now().isoformat(),
                "last_mentioned_at":datetime.now().isoformat()
            }
            page_content=f"{concept}:{content}"
            doc=Document(page_content=page_content,metadata=new_metadatas)
            self.vector_db.add_documents([doc])
            msg=f"认知[{concept}]已存入记忆区."
            return msg

    def update_by_id(
            self,
            concept_id:str,
            new_content:str,
            new_concept_name:str|None=None,
            new_tags:list[str]|None=None,
            )->str:
        existing=self.vector_db.get(ids=[concept_id])

        if existing and existing["ids"]:
            old_meta=existing["metadatas"][0]
            if new_tags is not None:
                tags_str = ','.join(new_tags)
            else:
                tags_str = old_meta.get("tags", "")  
           
            if new_concept_name is None:
                new_concept_name=old_meta.get("concept","concept")
            new_mention_count=old_meta.get("mention_count",1)+1
            created_at=old_meta.get("created_at",old_meta.get("last_mentioned_at"))
            new_metadatas={
                "concept":new_concept_name,
                "tags":tags_str,
                "mention_count":new_mention_count,
                "created_at":created_at,
                "last_mentioned_at":datetime.now().isoformat()
            }
            page_content=f"{new_concept_name}:{new_content}"
            doc=Document(page_content=page_content,metadata=new_metadatas)
            self.vector_db.update_document(concept_id,doc)
            msg=f"更新成功:id[{concept_id}]概念[{new_concept_name}]更新完成"
            return msg
        else :
            msg=f"更新失败:没有找到id[{concept_id}]的实体"
            return msg

    def search(
            self,
            query:str,
            top_k:int=8
    )->list[dict]:
        results = self.vector_db.similarity_search_with_score(query=query,k=top_k)

        scored_results = []

        for doc,L2_distance in results:
            if L2_distance > EDGE_THRESHOLD:
                continue

            #近因性
            try:
                last_time=datetime.fromisoformat(doc.metadata.get("last_mentioned_at", ""))
                hours_elapsed = (datetime.now() - last_time).total_seconds() / 3600.0
                recency=exp(-log(2) * hours_elapsed / 24.0)
            except (ValueError,TypeError):
                recency=0.0

            #重要性
            mention_count=doc.metadata.get("mention_count", 1)
            familiarity = log(1 + mention_count) / log(1 + MAX_MENTION)

            #相关性
            relevance=max(0.0, 1.0 - L2_distance /EDGE_THRESHOLD)


            final_score = 0.30*recency+0.25*familiarity+0.45*relevance

            scored_results.append((doc,L2_distance,final_score))

        scored_results.sort(key=lambda x: x[2],reverse=True)

        final_results=[]

        for result in scored_results:
            doc=result[0]
            concept=doc.metadata.get("concept","")

            existing = self.vector_db.get(where={'concept':concept})
            concept_id = "未知"
            if existing and existing["ids"]:
                concept_id=existing["ids"][0]

            tags=doc.metadata.get("tags","")
            mention_count=doc.metadata.get("mention_count",1)
            created_at=doc.metadata.get("created_at","")
            last_mentioned_at=doc.metadata.get("last_mentioned_at","")
            content=doc.page_content

            final_results.append({
                "concept_id":concept_id,
                "concept":concept,
                "content":content,
                "tags":tags,
                "mention_count":mention_count,  
                "created_at":created_at,
                "last_mentioned_at":last_mentioned_at,
                })


        return final_results





