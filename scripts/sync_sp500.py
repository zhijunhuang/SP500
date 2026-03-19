#!/usr/bin/env python3
"""
同步维基百科标普500成分股数据到数据库
"""

import os
import sys
import datetime
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.utils.db import SessionLocal, init_db
from app.models import SP500Constituent, SP500Meta

def fetch_wikipedia_sp500():
    """从维基百科获取标普500成分股数据"""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    
    try:
        response = httpx.get(url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"获取数据失败: {e}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"id": "constituents"})
    
    if not table:
        print("未找到成分股表格")
        return []
    
    constituents = []
    rows = table.find_all("tr")[1:]  # 跳过表头
    
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        
        # 提取数据
        ticker = cells[0].text.strip()
        company = cells[1].text.strip()
        sector = cells[2].text.strip()
        industry = cells[3].text.strip()
        
        constituents.append({
            "code": ticker,
            "company_name": company,
            "sector": sector,
            "industry": industry
        })
    
    return constituents

def update_sp500_constituents(db: Session, constituents):
    """更新标普500成分股数据到数据库"""
    # 获取当前日期
    today = datetime.date.today()
    
    # 获取数据库中现有的成分股
    existing_constituents = db.query(SP500Constituent).filter(
        SP500Constituent.effective_to.is_(None)
    ).all()
    
    # 创建现有成分股的字典，用于快速查找
    existing_dict = {c.code: c for c in existing_constituents}
    
    # 处理新的成分股
    new_codes = set([c["code"] for c in constituents])
    existing_codes = set(existing_dict.keys())
    
    # 需要添加的成分股
    to_add = new_codes - existing_codes
    # 需要移除的成分股
    to_remove = existing_codes - new_codes
    # 需要更新的成分股（保持不变的）
    to_keep = existing_codes & new_codes
    
    print(f"现有成分股: {len(existing_codes)}")
    print(f"新成分股: {len(new_codes)}")
    print(f"需要添加: {len(to_add)}")
    print(f"需要移除: {len(to_remove)}")
    print(f"保持不变: {len(to_keep)}")
    
    # 标记需要移除的成分股
    for code in to_remove:
        constituent = existing_dict[code]
        constituent.effective_to = today
        db.add(constituent)
    
    # 添加新的成分股
    for constituent_data in constituents:
        if constituent_data["code"] in to_add:
            new_constituent = SP500Constituent(
                code=constituent_data["code"],
                company_name=constituent_data["company_name"],
                sector=constituent_data["sector"],
                industry=constituent_data["industry"],
                effective_from=today
            )
            db.add(new_constituent)
    
    # 更新元数据
    update_metadata(db)
    
    db.commit()
    print(f"同步完成: {today}")

def update_metadata(db: Session):
    """更新元数据"""
    # 检查是否已有元数据
    meta_info = db.query(SP500Meta).filter(
        SP500Meta.key == "data_source"
    ).first()
    
    if not meta_info:
        meta_info = SP500Meta(
            key="data_source",
            value="Wikipedia"
        )
        db.add(meta_info)
    
    # 更新最后同步时间
    last_sync_meta = db.query(SP500Meta).filter(
        SP500Meta.key == "last_sync"
    ).first()
    
    if not last_sync_meta:
        last_sync_meta = SP500Meta(
            key="last_sync",
            value=datetime.datetime.utcnow().isoformat()
        )
        db.add(last_sync_meta)
    else:
        last_sync_meta.value = datetime.datetime.utcnow().isoformat()
        db.add(last_sync_meta)

def main():
    """主函数"""
    print("开始同步标普500成分股数据...")
    
    # 初始化数据库
    init_db()
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 获取数据
        constituents = fetch_wikipedia_sp500()
        
        if not constituents:
            print("未获取到数据，同步失败")
            return
        
        # 更新数据
        update_sp500_constituents(db, constituents)
        print("同步成功！")
    except Exception as e:
        print(f"同步失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
