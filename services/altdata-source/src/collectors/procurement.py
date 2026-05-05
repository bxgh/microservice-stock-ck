import logging
import asyncio
import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import httpx
from bs4 import BeautifulSoup

from src.models.hardware import HardwareProcurementTender

logger = logging.getLogger(__name__)

class ProcurementCollector:
    """
    政企招投标数据采集器 (中国政府采购网 CCGP)
    实现对 AI 算力、GPU 服务器、智算中心等关键词的标讯监控与 NLP 数据提取。
    """
    
    def __init__(self):
        self.base_url = "http://search.ccgp.gov.cn/bxsearch"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Referer": "http://search.ccgp.gov.cn/bxsearch"
        }

    async def collect_tenders(self, keywords: List[str]) -> List[HardwareProcurementTender]:
        """
        根据关键词列表从 CCGP 采集招投标公告。
        """
        all_tenders = []
        for kw in keywords:
            logger.info(f"Searching for procurement tenders with keyword: {kw}")
            tenders = await self._search_keyword(kw)
            all_tenders.extend(tenders)
            # 搜索间隔，防爬
            await asyncio.sleep(2.0)
            
        return all_tenders

    async def _search_keyword(self, keyword: str) -> List[HardwareProcurementTender]:
        """
        单个关键词搜索并解析结果页。
        """
        params = {
            "searchtype": "1", # 默认搜索中标公告
            "page_index": "1",
            "bidSort": "0",
            "buyerName": "",
            "projectId": "",
            "pinMu": "",
            "bidType": "7", # 中标公告分类
            "dbtype": "1",
            "kw": keyword,
            "start_time": (datetime.now() - timedelta(days=30)).strftime("%Y:%m:%d"),
            "end_time": datetime.now().strftime("%Y:%m:%d"),
            "timeType": "2", # 扩大搜索范围以确保采集到真实数据样本
            "displayZone": "",
            "zoneId": "",
            "pppStatus": "0",
            "agentName": ""
        }
        
        tenders = []
        try:
            # 真实抓取中国政府采购网 (CCGP)
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    self.base_url, 
                    params=params, 
                    headers=self.headers
                )
                
            if response.status_code == 200:
                # 1. 解析结果列表页，获取基础信息和 URL
                basic_infos = self._parse_ccgp_html(response.text, keyword)
                
                # 2. 遍历基础信息，抓取详情页补充数据 (带间隔防封)
                for info in basic_infos[:10]: # 限制单次搜索处理前 10 条，避免过久
                    try:
                        detail_data = await self._fetch_tender_amount_and_winner(info["url"])
                        
                        # 合并数据
                        raw_data = {
                            **info,
                            "winner": detail_data["winner"],
                            "content": detail_data["full_content"] # 用于 _parse_tender_detail 中的硬件识别
                        }
                        
                        tender = self._parse_tender_detail(raw_data)
                        if tender:
                            tender.amount = detail_data["amount"] # 覆盖金额
                            tenders.append(tender)
                            
                        # 详情页抓取间隔
                        await asyncio.sleep(3.0)
                    except Exception as detail_err:
                        logger.warning(f"Failed to process detail for {info['title']}: {detail_err}")
            else:
                logger.error(f"CCGP search failed with status {response.status_code}")
                
            logger.info(f"Successfully processed {len(tenders)} real tenders for keyword '{keyword}'")
            
        except Exception as e:
            logger.error(f"Failed to search keyword '{keyword}': {e}")
            
        return tenders

    @property
    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _parse_ccgp_html(self, html: str, keyword: str) -> List[Dict]:
        """解析 CCGP 搜索结果 HTML，返回基础信息列表"""
        soup = BeautifulSoup(html, "html.parser")
        results = []
        
        # CCGP 中标公告列表容器的真实选择器 (通过实际请求确认)
        items = soup.select("ul.vT-srch-result-list-bid li")
        if not items:
            logger.warning(f"No items found in CCGP response for '{keyword}'. HTML snippet: {html[:200]}")
        
        for item in items:
            try:
                a_tag = item.select_one("a")
                if not a_tag:
                    continue
                    
                title = a_tag.get_text(strip=True)
                detail_url = a_tag.get("href")
                if not detail_url.startswith("http"):
                    detail_url = "http://www.ccgp.gov.cn" + detail_url
                
                info_text = item.select_one("span").get_text(strip=True) if item.select_one("span") else ""
                
                # 解析日期
                date_match = re.search(r"(\d{4})[./年](\d{2})[./月](\d{2})", info_text)
                tender_date = self._now
                if date_match:
                    tender_date = datetime(
                        int(date_match.group(1)), 
                        int(date_match.group(2)), 
                        int(date_match.group(3))
                    )
                
                # 提取采购人 (从列表页获取初步信息)
                purchaser = "Unknown"
                purchaser_match = re.search(r"采购人：([^|]+)", info_text)
                if purchaser_match:
                    purchaser = purchaser_match.group(1).strip()

                results.append({
                    "title": title,
                    "url": detail_url,
                    "date": tender_date,
                    "purchaser": purchaser,
                    "region": "China" # 默认，后续可从 info_text 解析
                })
            except Exception as e:
                logger.warning(f"Failed to parse tender item in list: {e}")
                
        return results

    async def _fetch_tender_amount_and_winner(self, url: str) -> Dict[str, Any]:
        """抓取详情页并提取金额与中标人"""
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    content = resp.text
                    soup = BeautifulSoup(content, "html.parser")
                    text_content = soup.get_text(separator=" ", strip=True)
                    
                    amount = 0.0
                    # 1. CCGP 专用金额标签（该字段单位固定为元）
                    amt_tag = soup.select_one(".bookmark-item.numeric-input-box-cls")
                    if amt_tag:
                        try:
                            amount = float(amt_tag.get_text(strip=True).replace(",", "")) / 10000.0
                        except ValueError:
                            pass
                    
                    if amount == 0.0:
                        # 2. 正则表达式从全文提取（附带单位换算）
                        match = re.search(r"(?:中标金额|总成交金额|合同金额|中标成交金额)[^\d]{0,20}?([\d,.]+)\s*(万元|元)", text_content)
                        if match:
                            try:
                                amount = float(match.group(1).replace(",", ""))
                                if match.group(2) == "元":
                                    amount /= 10000.0
                            except ValueError:
                                pass
                    
                    # 2. 提取中标人
                    winner = "Multiple/See Detail"
                    # 匹配模式：中标供应商/中标人 + (名称)
                    # 排除掉一些常见干扰词
                    winner_match = re.search(r"(?:中标供应商|成交供应商|中标人)[:：\s]*([\u4e00-\u9fa5\w\(\)（）]{4,40})", text_content)
                    if winner_match:
                        winner = winner_match.group(1).strip()
                        # 过滤：包含这些词说明正则匹配到了非供应商段落
                        _invalid_tokens = ["得分", "排序", "满意度", "附件", "公示", "通知书", "领取", "可登录", "未中标"]
                        if any(x in winner for x in _invalid_tokens):
                            winner = "See Detail"

                    return {"amount": amount, "winner": winner, "full_content": text_content}
        except Exception as e:
            logger.error(f"Failed to fetch detail from {url}: {e}")
            
        return {"amount": 0.0, "winner": "Unknown", "full_content": ""}

    def _parse_tender_detail(self, raw_data: dict) -> Optional[HardwareProcurementTender]:
        """
        从合并数据（列表页 + 详情页全文）中构造 HardwareProcurementTender 对象。
        amount 字段不在此处解析，由调用方通过 _fetch_tender_amount_and_winner 覆盖。
        """
        title = raw_data.get("title", "")
        content = raw_data.get("content", "")
        
        # 2. 识别硬件类型 (综合标题与全文内容)
        hw_type = "Unknown"
        combined_text = (title + content).upper()
        
        if any(w in combined_text for w in ["昇腾", "ASCEND", "910B", "910C", "华为算力"]):
            hw_type = "Ascend"
        elif any(w in combined_text for w in ["NVIDIA", "英伟达", "H100", "A100", "4090", "H800", "B20", "B200"]):
            hw_type = "NVIDIA"
        elif any(w in combined_text for w in ["沐曦", "METAX", "曦云", "曦思", "C500", "N100"]):
            hw_type = "MetaX"
        elif any(w in combined_text for w in ["海光", "HYGON", "DCU", "深算"]):
            hw_type = "Hygon"
        elif any(w in combined_text for w in ["算力中心", "智算中心", "超算", "服务器"]):
            hw_type = "ComputeCenter"
            
        return HardwareProcurementTender(
            date=raw_data.get("date", self._now),
            title=title,
            purchaser=raw_data.get("purchaser", "Unknown"),
            winner=raw_data.get("winner", "Unknown"),
            hardware_type=hw_type,
            amount=0.0,  # 由调用方通过 tender.amount = detail_data["amount"] 覆盖
            region=raw_data.get("region", "China"),
            collect_time=self._now
        )
