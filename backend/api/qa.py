import os
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional

from backend.config import settings

router = APIRouter()

class QARequest(BaseModel):
    city: str = Field(..., example="武汉")
    question: str = Field(..., example="武汉有什么好吃的？")

def mock_qa(city: str, question: str) -> tuple[str, List[str]]:
    # Simple keyword matching mock QA
    if "吃" in question or "美食" in question or "特色" in question:
        if city == "武汉":
            ans = "武汉的美食极具特色，首推蔡林记热干面、老通城三鲜豆皮、四季美汤包和谈炎记水饺。此外，万松园的油焖大虾、户部巷的各类街头小吃以及吉庆街的宵夜文化也是极佳体验。"
            ref = ["《武汉美食地标指南》", "《马蜂窝·武汉寻味之旅》"]
        elif city == "西安":
            ans = "西安是著名的美食之都，必吃美食包括：回民街的肉夹馍、羊肉泡馍、凉皮、冰峰汽水（俗称‘三秦套餐’），还有biangbiang面、水盆羊肉和甑糕。"
            ref = ["《三秦美食宝典》", "《携程·西安本地食客推荐》"]
        elif city == "成都":
            ans = "成都美食以川味麻辣著称，推荐品尝：锦里或宽窄巷子的抄手、伤心凉粉、担担面，必吃正宗的成都火锅、串串香以及钵钵鸡，甜品推荐红糖冰粉。"
            ref = ["《成都美食地图·火锅篇》", "《大众点评·必吃榜成都分册》"]
        else:
            ans = f"{city}拥有丰富的地方特产和美食文化。建议您前往当地老城区或者特色步行街，品尝本地人常去的特色餐饮和百年老店。"
            ref = [f"《{city}城市生活指南》"]
            
    elif "住" in question or "酒店" in question or "民宿" in question:
        if city == "武汉":
            ans = "在武汉住宿，推荐选择江汉路/循礼门附近，出行极为方便且靠近商业街；或者选择武昌的街道口/光谷附近，适合高校游和东湖游。若预算充足，可选择江滩附近的江景酒店。"
            ref = ["《武汉酒店住宿分布与交通指南》"]
        else:
            ans = f"在{city}旅游，建议选择市中心商业区或者轨道交通枢纽附近的酒店/民宿。这样可以最大化节省出行交通时间，并方便体验城市夜生活。"
            ref = [f"《{city}自由行住宿攻略》"]
            
    else:
        ans = f"针对您关于{city}旅行的提问：“{question}”。建议合理规划出行时间，避开节假日高峰，并提前通过官方小程序或公众号预约景点门票。您可以参考当地官方旅游局发布的最新指南。"
        ref = [f"《{city}文化与旅游局官方手册》"]
        
    return ans, ref

@router.post("/qa")
def city_qa(req: QARequest):
    if settings.USE_MOCK:
        answer, references = mock_qa(req.city, req.question)
        return {
            "success": True,
            "answer": answer,
            "references": references
        }
        
    # Non-mock logic: Collaborate with Member C's RAG retriever
    try:
        # Assuming retriever or loader provides a query interface
        # We try to import retrieve or call_rag from backend.rag
        from backend.rag.retriever import retrieve_answer
        answer, references = retrieve_answer(req.city, req.question)
        return {
            "success": True,
            "answer": answer,
            "references": references
        }
    except Exception as e:
        # Fallback
        answer, references = mock_qa(req.city, req.question)
        return {
            "success": True,
            "answer": answer,
            "references": references,
            "warning": f"RAG query failed, fallback used. Error: {str(e)}"
        }
