import json
import logging
import math
from datetime import datetime
from typing import Any, Dict, List

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_PROFILES: Dict[str, Dict[str, Any]] = {
    "conservative": {
        "risk_tolerance": "LOW",
        "preferred_sectors": ["Technology"],
        "min_quality_score": 90.0,
        "max_volatility": 0.15,
    },
    "moderate": {
        "risk_tolerance": "MEDIUM",
        "preferred_sectors": ["Technology", "Consumer Discretionary"],
        "min_quality_score": 80.0,
        "max_volatility": 0.25,
    },
    "aggressive": {
        "risk_tolerance": "HIGH",
        "preferred_sectors": ["Technology", "Consumer Discretionary"],
        "min_quality_score": 70.0,
        "max_volatility": 0.40,
    },
}


def score_ticker_for_profile(
    ticker: str,
    profile: Dict[str, Any],
    ticker_metrics: Dict[str, Any],
) -> float:
    score = 0.0

    quality = float(str(ticker_metrics.get("quality_score", 0.0)))
    min_quality = float(str(profile.get("min_quality_score", 80.0)))
    if quality >= min_quality:
        score += 40.0 * min(quality / 100.0, 1.0)

    volatility = float(str(ticker_metrics.get("volatility", 1.0)))
    max_vol = float(str(profile.get("max_volatility", 0.25)))
    if volatility <= max_vol:
        score += 30.0 * (1.0 - volatility / max_vol)

    sector = str(ticker_metrics.get("sector", ""))
    preferred = [str(s) for s in profile.get("preferred_sectors", [])]
    if sector in preferred:
        score += 20.0

    sentiment = float(str(ticker_metrics.get("sentiment", 0.0)))
    score += 10.0 * max(0.0, min(sentiment, 1.0))

    score = max(0.0, min(score, 100.0))
    logger.info(f"Score for {ticker} ({profile.get('risk_tolerance')}): {score:.2f}")
    return score


def get_recommendations(
    profile_name: str,
    ticker_metrics: Dict[str, Dict[str, Any]],
    top_n: int = 3,
) -> List[Dict[str, Any]]:
    profile = USER_PROFILES.get(profile_name, USER_PROFILES["moderate"])
    scored: List[Dict[str, Any]] = []

    for ticker, metrics in ticker_metrics.items():
        score = score_ticker_for_profile(ticker, profile, metrics)
        reasons: List[str] = []

        quality = float(str(metrics.get("quality_score", 0.0)))
        min_q = float(str(profile.get("min_quality_score", 80.0)))
        if quality >= min_q:
            reasons.append(f"Quality score {quality:.0f}% meets {min_q:.0f}% threshold")

        volatility = float(str(metrics.get("volatility", 1.0)))
        max_vol = float(str(profile.get("max_volatility", 0.25)))
        if volatility <= max_vol:
            reasons.append(f"Volatility {volatility:.0%} within {max_vol:.0%} limit")

        sector = str(metrics.get("sector", ""))
        preferred = [str(s) for s in profile.get("preferred_sectors", [])]
        if sector in preferred:
            reasons.append(f"{sector} sector matches profile preference")

        scored.append({"ticker": ticker, "score": score, "reasons": reasons})

    scored.sort(key=lambda x: float(str(x["score"])), reverse=True)
    recommendations = scored[:top_n]
    logger.info(f"Generated {len(recommendations)} recommendations for {profile_name}")
    return recommendations


def explain_recommendation(
    ticker: str,
    profile_name: str,
    ticker_metrics: Dict[str, Any],
) -> str:
    profile = USER_PROFILES.get(profile_name, USER_PROFILES["moderate"])
    lines: List[str] = [f"{ticker} recommended for {profile_name} profile because:"]

    quality = float(str(ticker_metrics.get("quality_score", 0.0)))
    min_q = float(str(profile.get("min_quality_score", 80.0)))
    lines.append(f"  - Quality score {quality:.0f}% (above {min_q:.0f}% threshold)")

    volatility = float(str(ticker_metrics.get("volatility", 0.0)))
    max_vol = float(str(profile.get("max_volatility", 0.25)))
    lines.append(f"  - Volatility {volatility:.0%} (below {max_vol:.0%} threshold)")

    sector = str(ticker_metrics.get("sector", "Unknown"))
    preferred = [str(s) for s in profile.get("preferred_sectors", [])]
    if sector in preferred:
        lines.append(f"  - {sector} sector matches preference")

    explanation = "\n".join(lines)
    logger.info(f"Explanation generated for {ticker}/{profile_name}")
    return explanation


def find_similar_tickers(
    ticker: str,
    all_metrics: Dict[str, Dict[str, Any]],
    top_n: int = 2,
) -> List[str]:
    if ticker not in all_metrics:
        return []

    ref = all_metrics[ticker]
    ref_quality = float(str(ref.get("quality_score", 0.0)))
    ref_vol = float(str(ref.get("volatility", 0.0)))
    ref_sent = float(str(ref.get("sentiment", 0.0)))

    distances: List[Dict[str, Any]] = []
    for other, metrics in all_metrics.items():
        if other == ticker:
            continue
        q = float(str(metrics.get("quality_score", 0.0)))
        v = float(str(metrics.get("volatility", 0.0)))
        s = float(str(metrics.get("sentiment", 0.0)))
        dist = math.sqrt(
            ((ref_quality - q) / 100.0) ** 2 + (ref_vol - v) ** 2 + (ref_sent - s) ** 2
        )
        distances.append({"ticker": other, "distance": dist})

    distances.sort(key=lambda x: float(str(x["distance"])))
    similar = [str(d["ticker"]) for d in distances[:top_n]]
    logger.info(f"Found {len(similar)} tickers similar to {ticker}: {similar}")
    return similar


def run_recommendation_engine(
    profile_name: str,
    bucket: str,
) -> Dict[str, Any]:
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    ticker_metrics: Dict[str, Dict[str, Any]] = {}

    for ticker in tickers:
        metrics: Dict[str, Any] = {}
        if bucket:
            try:
                s3 = boto3.client("s3")
                key = f"monitoring/metrics/{ticker}_latest.json"
                obj = s3.get_object(Bucket=bucket, Key=key)
                metrics = json.loads(obj["Body"].read().decode("utf-8"))
            except Exception:
                metrics = {}
        ticker_metrics[ticker] = metrics

    recommendations = get_recommendations(profile_name, ticker_metrics, top_n=3)

    if bucket:
        try:
            s3 = boto3.client("s3")
            now = datetime.utcnow()
            key = (
                f"reports/recommendations"
                f"/{now.year}/{now.month:02d}/{now.day:02d}/{profile_name}.json"
            )
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(recommendations),
                ContentType="application/json",
            )
        except Exception as e:
            logger.warning(f"Could not save recommendations to S3: {e}")

    result: Dict[str, Any] = {
        "profile": profile_name,
        "recommendations": recommendations,
        "generated_at": datetime.utcnow().isoformat(),
    }
    logger.info("Recommendation Engine Complete")
    return result


if __name__ == "__main__":
    pass
