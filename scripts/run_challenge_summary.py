import logging
import os

from ingestion.challenge_summary import run_challenge_summary

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    bucket = os.getenv("AWS_BUCKET_NAME", "")
    result = run_challenge_summary(bucket)
    cert = result["certificate"]
    stats = result["stats"]
    print("🎉 90-Day Challenge Complete!")
    print(f"Certificate ID: {cert['certificate_id']}")
    print(f"Builder: {cert['builder']}")
    print(f"Completion Date: {cert['completion_date']}")
    print(f"Modules: {stats['total_modules']}")
    print(f"Tests: {stats['total_tests']}")
    print(f"ADRs: {stats['total_adrs']}")
    print(f"MLOps Stages: {stats['mlops_stages']}")
    print("Achievements:")
    for achievement in cert["achievements"]:
        print(f"  ✅ {achievement}")
    logger.info("🎉 Challenge complete! Certificate generated.")
