# -*- coding: utf-8 -*-
"""全局配置：作物映射、国家清单、厄尔尼诺年表、数据源注册。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW, VINTAGE, PROCESSED, WEB = (
    DATA / "raw",
    DATA / "vintage",
    DATA / "processed",
    DATA / "web",
)
import os

DB_PATH = Path(os.environ.get("MONITOR_DB", str(PROCESSED / "monitor_v2.duckdb")))
for d in (RAW, VINTAGE, PROCESSED, WEB, RAW / "usda", RAW / "noaa"):
    d.mkdir(parents=True, exist_ok=True)

# PSD Commodity_Description -> (英文 slug, 中文名)
CROPS = {
    "Wheat": ("wheat", "小麦"),
    "Corn": ("corn", "玉米"),
    "Oilseed, Soybean": ("soybean", "大豆"),
    "Rice, Milled": ("rice", "水稻(精米)"),
    "Sugar, Centrifugal": ("sugar", "糖(原糖)"),
}

from policy import POLICY

COUNTRIES = list(
    dict.fromkeys(
        country
        for members in POLICY["active_countries"].values()
        for country in members
    )
)

# 厄尔尼诺市场年度（ONI 弱及以上）
EL_NINO = {
    1982: "强",
    1986: "中",
    1987: "中",
    1991: "强",
    1994: "中",
    1997: "超强",
    2002: "中",
    2004: "弱",
    2006: "弱",
    2009: "中",
    2014: "弱",
    2015: "超强",
    2018: "弱",
    2023: "强",
}

PSD_URL = "https://apps.fas.usda.gov/psdonline/downloads/psd_alldata_csv.zip"
ONI_URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/"

# Registry contains only attributable sources. Missing integrations stay visible.
SOURCES = {
    "usda_psd": dict(
        name="USDA PSD", url=PSD_URL, freq="monthly", script="fetch_usda.py"
    ),
    "usda_wasde": dict(
        name="USDA WASDE",
        url="https://www.usda.gov/about-usda/general-information/staff-offices/office-chief-economist/commodity-markets/wasde-report/historical-wasde-report-data",
        freq="monthly",
        script="fetch_wasde.py",
    ),
    "noaa_oni": dict(
        name="NOAA CPC ONI", url=ONI_URL, freq="monthly", script="fetch_noaa.py"
    ),
    "noaa_nino34": dict(
        name="NOAA CPC Nino 3.4",
        url="https://www.cpc.ncep.noaa.gov/data/indices/sstoi.indices",
        freq="monthly",
        script="fetch_noaa.py",
    ),
    "cropwatch": dict(
        name="CropWatch",
        url="http://cloud.cropwatch.com.cn/web/report",
        freq="quarterly",
        script="fetch_cropwatch.py",
    ),
    "china_outlook": dict(
        name="中国农业展望报告",
        url="https://aoc.caas.cn/",
        freq="annual",
        script="fetch_china_outlook.py",
    ),
    "worldbank": dict(
        name="World Bank Pink Sheet",
        url="https://www.worldbank.org/en/research/commodity-markets",
        freq="monthly",
        script="fetch_prices.py",
    ),
    "nbs": dict(
        name="国家统计局实产公告",
        url="https://www.stats.gov.cn/",
        freq="annual",
        script="fetch_nbs.py",
    ),
    "china_prices": dict(
        name="NBS 国内现货调查",
        url="https://www.stats.gov.cn/",
        freq="ten-day",
        script="fetch_nbs.py",
    ),
}
CURRENT_FORECAST_YEAR = __import__("datetime").date.today().year
STALE_DAYS = {
    "usda_psd": 45,
    "usda_wasde": 45,
    "noaa_oni": 65,
    "noaa_nino34": 65,
    "worldbank": 65,
    "cropwatch": 150,
    "china_outlook": 400,
    "nbs": 400,
    "china_prices": 45,
}
BASIS = {
    "wheat": "grain",
    "corn": "grain",
    "soybean": "oilseed",
    "rice": "milled",
    "sugar": "centrifugal_raw_value",
}
from futures_config import CONTRACTS

for contract in CONTRACTS.values():
    SOURCES[contract["source"]] = dict(
        name=contract["label"] + " · 新浪",
        url=contract["source_url"],
        freq="daily",
        script="fetch_futures.py",
    )
    STALE_DAYS[contract["source"]] = 7
