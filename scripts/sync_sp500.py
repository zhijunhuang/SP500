#!/usr/bin/env python3
"""
同步维基百科标普500成分股数据到数据库
支持历史变更记录
"""

import os
import sys
import datetime
import time
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from datetime import timezone, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.utils.db import SessionLocal, init_db
from app.models import SP500Constituent, SP500Meta


def parse_wikipedia_date(date_str: str) -> datetime.date:
    """将 'February 9, 2026' 转换为 date(2026, 2, 9)"""
    return datetime.datetime.strptime(date_str.strip(), "%B %d, %Y").date()


def fetch_wikipedia_data():
    """从维基百科获取当前成分股和历史变更数据"""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; SP500-Sync/1.0; +https://github.com/example/sp500)"
    }

    # Retry logic for network failures
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = httpx.get(url, timeout=30, headers=headers)
            response.raise_for_status()
            break
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"获取数据失败，已重试{max_retries}次: {e}")
                return None, []
            print(f"获取数据失败，重试中 ({attempt + 1}/{max_retries}): {e}")
            time.sleep(2)

    soup = BeautifulSoup(response.text, "html.parser")

    # 解析当前成分股表格
    current_constituents = []
    table = soup.find("table", {"id": "constituents"})
    if table:
        rows = table.find_all("tr")[1:]  # 跳过表头
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            ticker = cells[0].text.strip()
            company = cells[1].text.strip()
            sector = cells[2].text.strip()
            industry = cells[3].text.strip()
            if ticker and company:
                current_constituents.append({
                    "code": ticker,
                    "company_name": company,
                    "sector": sector,
                    "industry": industry
                })

    # 解析历史变更表格
    changes = []
    changes_table = soup.find("table", {"id": "changes"})
    if changes_table:
        rows = changes_table.find_all("tr")[2:]  # 跳过前两行表头
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            try:
                change_date = parse_wikipedia_date(cells[0].text.strip())
            except ValueError:
                print(f"警告: 无法解析日期 '{cells[0].text.strip()}'，跳过此行")
                continue

            added_ticker = cells[1].text.strip()
            added_company = cells[2].text.strip()
            removed_ticker = cells[3].text.strip()
            removed_company = cells[4].text.strip()

            change_record = {
                "date": change_date,
                "added": [],
                "removed": []
            }

            if added_ticker:
                change_record["added"].append((added_ticker, added_company))
            if removed_ticker:
                change_record["removed"].append((removed_ticker, removed_company))

            if change_record["added"] or change_record["removed"]:
                changes.append(change_record)

    return current_constituents, changes


def update_sp500_constituents(db: Session, current_constituents, changes):
    """更新标普500成分股数据到数据库，包含历史变更"""
    today = datetime.date.today()
    earliest_date = datetime.date(1976, 1, 1)

    print(f"当前成分股: {len(current_constituents)}")
    print(f"历史变更记录: {len(changes)}")

    # 构建当前成分股字典（用于获取sector/industry信息）
    current_info = {c["code"]: c for c in current_constituents}

    try:
        # Step 1: 清空所有现有数据，重新构建
        db.query(SP500Constituent).delete()
        db.commit()
        print("已清空现有数据")

        # Step 2: 处理历史变更（从旧到新）
        # 按日期排序确保顺序正确
        changes_sorted = sorted(changes, key=lambda x: x["date"])

        # 用字典维护当前有效的记录
        active_records = {}  # code -> record with effective_to = NULL

        # 跟踪已创建过earliest_date记录的ticker（用于处理同一ticker多次removed的情况）
        created_earliest_record = set()

        for change in changes_sorted:
            change_date = change["date"]

            # 处理被移除的股票
            for removed_ticker, removed_company in change["removed"]:
                if removed_ticker in active_records:
                    # 该ticker当前有效，标记为移除
                    active_records[removed_ticker].effective_to = change_date
                    del active_records[removed_ticker]
                else:
                    # 该ticker不在活动记录中
                    # 如果该ticker从未在"added"列出现过且从未创建过earliest记录，才创建
                    info = current_info.get(removed_ticker, {})

                    if removed_ticker not in created_earliest_record:
                        # 第一次看到这个ticker被移除（它从未被追踪添加过）
                        old_record = SP500Constituent(
                            code=removed_ticker,
                            company_name=removed_company or info.get("company_name", removed_ticker),
                            sector=info.get("sector", ""),
                            industry=info.get("industry", ""),
                            effective_from=earliest_date,
                            effective_to=change_date
                        )
                        db.add(old_record)
                        created_earliest_record.add(removed_ticker)
                    # else: 该ticker已经被处理过（曾在earliest_date被移除又重新加入），忽略

            # 处理新加入的股票
            for added_ticker, added_company in change["added"]:
                info = current_info.get(added_ticker, {})

                # 如果该ticker已经在active_records中，说明它之前被添加过但没有被移除的记录
                # 先关闭之前的记录
                if added_ticker in active_records:
                    active_records[added_ticker].effective_to = change_date
                    del active_records[added_ticker]

                new_record = SP500Constituent(
                    code=added_ticker,
                    company_name=added_company or info.get("company_name", added_ticker),
                    sector=info.get("sector", ""),
                    industry=info.get("industry", ""),
                    effective_from=change_date,
                    effective_to=None
                )
                db.add(new_record)
                active_records[added_ticker] = new_record

        db.commit()
        print(f"已处理 {len(changes_sorted)} 条历史变更")
        print(f"变更后有效记录: {len(active_records)}")

        # Step 3: 添加当前成分股中未被变更追踪的（1976年之前加入且从未离开的）
        # 这些ticker从未出现在changes表的added列
        never_changed = []
        for code, info in current_info.items():
            if code not in active_records:
                # 从未在active_records中，说明从未被添加过（1976年之前加入且从未离开）
                # 但要检查是否已经有该code的记录（可能只有移除记录没有添加记录）
                existing_count = db.query(SP500Constituent).filter(
                    SP500Constituent.code == code
                ).count()

                if existing_count == 0:
                    # 完全没有记录，才创建新记录
                    never_changed.append(code)
                    new_record = SP500Constituent(
                        code=code,
                        company_name=info["company_name"],
                        sector=info["sector"],
                        industry=info["industry"],
                        effective_from=earliest_date,
                        effective_to=None
                    )
                    db.add(new_record)
                    active_records[code] = new_record

        db.commit()
        print(f"已添加 {len(never_changed)} 只1976年前加入且从未离开的股票")

        # 验证
        total_records = db.query(SP500Constituent).count()
        active_count = db.query(SP500Constituent).filter(
            SP500Constituent.effective_to.is_(None)
        ).count()
        print(f"总记录数: {total_records}, 当前有效: {active_count}")

        # 更新元数据
        update_metadata(db)

        print(f"同步完成: {today}")
    except Exception as e:
        db.rollback()
        raise e


def update_metadata(db: Session):
    """更新元数据"""
    meta_info = db.query(SP500Meta).filter(
        SP500Meta.key == "data_source"
    ).first()

    if not meta_info:
        meta_info = SP500Meta(
            key="data_source",
            value="Wikipedia"
        )
        db.add(meta_info)

    last_sync_meta = db.query(SP500Meta).filter(
        SP500Meta.key == "last_sync"
    ).first()

    if not last_sync_meta:
        last_sync_meta = SP500Meta(
            key="last_sync",
            value=datetime.datetime.now(timezone.utc).isoformat()
        )
        db.add(last_sync_meta)
    else:
        last_sync_meta.value = datetime.datetime.now(timezone.utc).isoformat()
        db.add(last_sync_meta)


def main():
    """主函数"""
    print("开始同步标普500成分股数据（含历史变更）...")

    # 初始化数据库
    init_db()

    # 创建数据库会话
    db = SessionLocal()

    try:
        # 获取数据
        current_constituents, changes = fetch_wikipedia_data()

        if current_constituents is None:
            print("获取数据失败，同步终止")
            return

        if not current_constituents:
            print("未获取到当前成分股数据，同步失败")
            return

        print(f"获取到 {len(current_constituents)} 个当前成分股")
        print(f"获取到 {len(changes)} 条历史变更记录")

        # 更新数据
        update_sp500_constituents(db, current_constituents, changes)
        print("同步成功！")
    except Exception as e:
        print(f"同步失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
