import datetime
import json
import logging
import os  # noqa: F401
from typing import Any, Dict, List, Optional  # noqa: F401

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECTOR_MAP: Dict[str, str] = {
    "AAPL": "Technology",
    "MSFT": "Technology",
    "GOOGL": "Communication Services",
    "AMZN": "Consumer Discretionary",
    "TSLA": "Consumer Discretionary",
}

SECTOR_BENCHMARKS: Dict[str, float] = {
    "Technology": 0.15,
    "Communication Services": 0.12,
    "Consumer Discretionary": 0.10,
}


def calculate_sector_returns(
    ticker_returns: Dict[str, float],
) -> Dict[str, float]:
    sector_buckets: Dict[str, List[float]] = {}
    for ticker, ret in ticker_returns.items():
        sector = SECTOR_MAP.get(str(ticker), "Other")
        sector_buckets.setdefault(sector, []).append(float(str(ret)))

    sector_returns: Dict[str, float] = {}
    for sector, returns in sector_buckets.items():
        avg = sum(returns) / len(returns) if returns else 0.0
        sector_returns[sector] = round(avg, 4)

    logger.info("Sector returns: %s", sector_returns)
    return sector_returns


def identify_sector_leaders(
    ticker_returns: Dict[str, float],
) -> Dict[str, str]:
    sector_best: Dict[str, tuple] = {}
    for ticker, ret in ticker_returns.items():
        sector = SECTOR_MAP.get(str(ticker), "Other")
        ret_val = float(str(ret))
        if sector not in sector_best or ret_val > sector_best[sector][1]:
            sector_best[sector] = (str(ticker), ret_val)

    leaders: Dict[str, str] = {sector: info[0] for sector, info in sector_best.items()}
    logger.info("Sector leaders: %s", leaders)
    return leaders


def calculate_sector_rotation(
    current_returns: Dict[str, float],
    previous_returns: Dict[str, float],
) -> Dict[str, Any]:
    current_sector = calculate_sector_returns(current_returns)
    previous_sector = calculate_sector_returns(previous_returns)

    gaining: List[str] = []
    losing: List[str] = []
    stable: List[str] = []

    all_sectors = set(list(current_sector.keys()) + list(previous_sector.keys()))
    for sector in all_sectors:
        cur = float(str(current_sector.get(sector, 0.0)))
        prev = float(str(previous_sector.get(sector, 0.0)))
        diff = cur - prev
        if diff > 0.005:
            gaining.append(sector)
        elif diff < -0.005:
            losing.append(sector)
        else:
            stable.append(sector)

    result: Dict[str, Any] = {
        "gaining": sorted(gaining),
        "losing": sorted(losing),
        "stable": sorted(stable),
    }
    logger.info("Sector rotation — gaining: %s, losing: %s", gaining, losing)
    return result


def compare_to_benchmark(
    sector_returns: Dict[str, float],
) -> Dict[str, Any]:
    comparison: Dict[str, Any] = {}
    for sector, ret in sector_returns.items():
        ret_val = float(str(ret))
        benchmark = float(str(SECTOR_BENCHMARKS.get(sector, 0.0)))
        alpha = round(ret_val - benchmark, 4)
        comparison[sector] = {
            "return": ret_val,
            "benchmark": benchmark,
            "alpha": alpha,
        }
    logger.info("Benchmark comparison complete for %d sectors", len(comparison))
    return comparison


def run_sector_analysis(
    ticker_prices: Dict[str, List[float]],
    bucket: str,
) -> Dict[str, Any]:
    ticker_returns: Dict[str, float] = {}
    for ticker, prices in ticker_prices.items():
        if len(prices) >= 2:
            first = float(str(prices[0]))
            last = float(str(prices[-1]))
            ret = (last - first) / first if first != 0 else 0.0
        else:
            ret = 0.0
        ticker_returns[str(ticker)] = round(ret, 6)

    sector_returns = calculate_sector_returns(ticker_returns)
    sector_leaders = identify_sector_leaders(ticker_returns)
    benchmark_comparison = compare_to_benchmark(sector_returns)

    result: Dict[str, Any] = {
        "ticker_returns": ticker_returns,
        "sector_returns": sector_returns,
        "sector_leaders": sector_leaders,
        "benchmark_comparison": benchmark_comparison,
        "analyzed_at": datetime.datetime.utcnow().isoformat(),
    }

    now = datetime.datetime.utcnow()
    s3_key = "processed/sector_analysis/{}/{}/{}/analysis.json".format(
        now.strftime("%Y"),
        now.strftime("%m"),
        now.strftime("%d"),
    )

    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=json.dumps(result),
            ContentType="application/json",
        )
        logger.info("Saved sector analysis to s3://%s/%s", bucket, s3_key)
    except Exception as e:
        logger.warning("S3 upload skipped: %s", str(e))

    logger.info("Sector Analysis Complete")
    return result


if __name__ == "__main__":
    pass
