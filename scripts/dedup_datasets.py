#!/usr/bin/env python3
"""
Dataset Deduplication Script

SHA-1/256 Hash → Exact Match 제거 → Near-Dup (LSH + Levenshtein < 0.2) 필터로
Deepeval·Evalchemy 양측 데이터셋 중복 제거를 수행합니다.
"""

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml
from datasketch import MinHash, MinHashLSH
from Levenshtein import distance as levenshtein_distance
from tqdm import tqdm

# Constants
DEFAULT_LSH_THRESHOLD = 0.8
DEFAULT_LEVENSHTEIN_THRESHOLD = 0.2
DEFAULT_NUM_PERM = 128
MIN_TEXT_LENGTH = 3
NGRAM_SIZE = 3

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DatasetDeduplicator:
    """데이터셋 중복 제거 클래스."""

    def __init__(
        self,
        lsh_threshold: float = DEFAULT_LSH_THRESHOLD,
        levenshtein_threshold: float = DEFAULT_LEVENSHTEIN_THRESHOLD,
        num_perm: int = DEFAULT_NUM_PERM,
    ):
        """
        Args:
            lsh_threshold: LSH 유사도 임계값 (0.0-1.0)
            levenshtein_threshold: Levenshtein 거리 임계값 (0.0-1.0)
            num_perm: MinHash permutation 수
        """
        self.lsh_threshold = lsh_threshold
        self.levenshtein_threshold = levenshtein_threshold
        self.num_perm = num_perm
        self.lsh = MinHashLSH(threshold=lsh_threshold, num_perm=num_perm)

    def _normalize_text(self, text: str) -> str:
        """텍스트 정규화."""
        return text.lower().strip()

    def _calculate_hash(self, text: str) -> str:
        """SHA-256 해시 계산."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _create_minhash(self, text: str) -> MinHash:
        """텍스트에서 MinHash 생성."""
        minhash = MinHash(num_perm=self.num_perm)
        # 문자 단위 n-gram 생성
        ngrams = [text[i : i + NGRAM_SIZE] for i in range(len(text) - NGRAM_SIZE + 1)]
        for ngram in ngrams:
            minhash.update(ngram.encode("utf8"))
        return minhash

    def _calculate_levenshtein_similarity(self, text1: str, text2: str) -> float:
        """Levenshtein 유사도 계산 (0.0-1.0)."""
        max_len = max(len(text1), len(text2))
        if max_len == 0:
            return 1.0
        dist = levenshtein_distance(text1, text2)
        return 1.0 - (dist / max_len)

    def _extract_text_content(self, sample: dict) -> str:
        """샘플에서 텍스트 내용 추출."""
        # 다양한 데이터셋 형식 지원
        text_fields = ["question", "query", "text", "prompt", "input", "context"]

        content_parts = []
        for field in text_fields:
            if field in sample:
                content_parts.append(str(sample[field]))

        # choices 필드 처리 (ARC 등)
        if "choices" in sample and isinstance(sample["choices"], list):
            content_parts.extend([str(choice) for choice in sample["choices"]])

        return " ".join(content_parts)

    def deduplicate_exact(self, dataset: list[dict]) -> tuple[list[dict], set[str]]:
        """정확한 중복 제거 (SHA-256 기반)."""
        logger.info("정확한 중복 제거 시작...")

        seen_hashes = set()
        deduplicated = []
        duplicates = set()

        for i, sample in enumerate(tqdm(dataset, desc="정확한 중복 검사")):
            text_content = self._extract_text_content(sample)
            normalized_text = self._normalize_text(text_content)
            text_hash = self._calculate_hash(normalized_text)

            if text_hash not in seen_hashes:
                seen_hashes.add(text_hash)
                deduplicated.append(sample)
            else:
                duplicates.add(i)

        logger.info(f"정확한 중복 {len(duplicates)}개 제거됨")
        return deduplicated, duplicates

    def deduplicate_near(self, dataset: list[dict]) -> tuple[list[dict], set[int]]:
        """근사 중복 제거 (LSH + Levenshtein)."""
        logger.info("근사 중복 제거 시작...")

        # LSH 인덱스 구축
        minhashes = {}
        texts = {}

        for i, sample in enumerate(tqdm(dataset, desc="MinHash 계산")):
            text_content = self._extract_text_content(sample)
            normalized_text = self._normalize_text(text_content)

            if len(normalized_text) < MIN_TEXT_LENGTH:  # 너무 짧은 텍스트 스킵
                continue

            minhash = self._create_minhash(normalized_text)
            minhashes[i] = minhash
            texts[i] = normalized_text
            self.lsh.insert(i, minhash)

        # 중복 후보 찾기
        duplicates = set()
        checked_pairs = set()

        for i in tqdm(range(len(dataset)), desc="근사 중복 검사"):
            if i not in minhashes or i in duplicates:
                continue

            # LSH로 후보 찾기
            candidates = self.lsh.query(minhashes[i])

            for candidate in candidates:
                if candidate == i or candidate in duplicates:
                    continue

                # 이미 확인한 쌍 스킵
                pair = tuple(sorted([i, candidate]))
                if pair in checked_pairs:
                    continue
                checked_pairs.add(pair)

                # Levenshtein 거리로 정밀 검사
                similarity = self._calculate_levenshtein_similarity(texts[i], texts[candidate])

                if similarity > (1.0 - self.levenshtein_threshold):
                    # 더 긴 텍스트를 유지 (더 완전한 데이터로 간주)
                    if len(texts[candidate]) > len(texts[i]):
                        duplicates.add(i)
                    else:
                        duplicates.add(candidate)

        # 중복 제거된 데이터셋 생성
        deduplicated = [sample for i, sample in enumerate(dataset) if i not in duplicates]

        logger.info(f"근사 중복 {len(duplicates)}개 제거됨")
        return deduplicated, duplicates

    def deduplicate(self, dataset: list[dict]) -> dict:
        """전체 중복 제거 프로세스."""
        logger.info(f"중복 제거 시작: 원본 크기 {len(dataset)}")
        original_size = len(dataset)

        # 1단계: 정확한 중복 제거
        dataset_exact, exact_duplicates = self.deduplicate_exact(dataset)

        # 2단계: 근사 중복 제거
        dataset_final, near_duplicates = self.deduplicate_near(dataset_exact)

        # 결과 통계
        total_duplicates = len(exact_duplicates) + len(near_duplicates)
        final_size = len(dataset_final)

        result = {
            "original_size": original_size,
            "exact_duplicates": len(exact_duplicates),
            "near_duplicates": len(near_duplicates),
            "total_duplicates": total_duplicates,
            "final_size": final_size,
            "deduplication_rate": (total_duplicates / original_size) * 100,
            "dataset": dataset_final,
            "processed_at": datetime.utcnow().isoformat(),
        }

        logger.info("중복 제거 완료:")
        logger.info(f"  원본 크기: {original_size}")
        logger.info(f"  정확한 중복: {len(exact_duplicates)}")
        logger.info(f"  근사 중복: {len(near_duplicates)}")
        logger.info(f"  최종 크기: {final_size}")
        logger.info(f"  중복 제거율: {result['deduplication_rate']:.2f}%")

        return result


def load_dataset_from_manifest(manifest_path: str) -> tuple[list[dict], dict]:
    """매니페스트 파일에서 데이터셋 로드."""
    logger.info(f"매니페스트 로드: {manifest_path}")

    manifest_file = Path(manifest_path)
    manifest = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))

    # MinIO/S3에서 데이터 로드 (실제 구현에서는 boto3 등 사용)
    storage_info = manifest["spec"]["storage"]
    bucket = storage_info["bucket"]
    path = storage_info["path"]

    # 로컬 개발용: 로컬 파일에서 로드
    local_path = Path(f"data/{bucket}/{path}/data.json")

    if local_path.exists():
        logger.info(f"로컬 파일에서 로드: {local_path}")
        if storage_info.get("format") == "jsonl":
            dataset = [
                json.loads(line) for line in local_path.read_text(encoding="utf-8").splitlines()
            ]
        else:
            dataset = json.loads(local_path.read_text(encoding="utf-8"))
    else:
        logger.warning(f"데이터 파일을 찾을 수 없음: {local_path}")
        logger.info("샘플 데이터로 테스트...")
        # 테스트용 샘플 데이터
        dataset = [
            {"question": "What is AI?", "choices": ["A", "B", "C", "D"], "answer": "A"},
            {
                "question": "What is AI?",
                "choices": ["A", "B", "C", "D"],
                "answer": "A",
            },  # 정확한 중복
            {
                "question": "What is artificial intelligence?",
                "choices": ["A", "B", "C", "D"],
                "answer": "A",
            },  # 근사 중복
            {"question": "Define machine learning", "choices": ["X", "Y", "Z"], "answer": "X"},
        ]

    return dataset, manifest


def update_manifest(manifest_path: str, dedup_result: dict) -> None:
    """매니페스트 파일에 중복 제거 결과 업데이트."""
    logger.info(f"매니페스트 업데이트: {manifest_path}")

    manifest_file = Path(manifest_path)
    manifest = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))

    # 중복 제거 정보 추가
    manifest["spec"]["size"] = dedup_result["final_size"]
    manifest["spec"]["deduplication"] = {
        "method": "minhash-lsh",
        "threshold": 0.2,
        "processed_at": dedup_result["processed_at"],
        "original_size": dedup_result["original_size"],
        "deduplicated_size": dedup_result["final_size"],
        "exact_duplicates": dedup_result["exact_duplicates"],
        "near_duplicates": dedup_result["near_duplicates"],
        "deduplication_rate": round(dedup_result["deduplication_rate"], 2),
    }

    # 백업 생성
    backup_path = Path(f"{manifest_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    manifest_file.rename(backup_path)
    logger.info(f"원본 매니페스트 백업: {backup_path}")

    # 업데이트된 매니페스트 저장
    manifest_file.write_text(
        yaml.dump(manifest, default_flow_style=False, allow_unicode=True), encoding="utf-8"
    )


def save_deduplicated_dataset(dataset: list[dict], output_path: str) -> None:
    """중복 제거된 데이터셋 저장."""
    logger.info(f"중복 제거된 데이터셋 저장: {output_path}")

    # 디렉토리 생성
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    output_file.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    """메인 함수."""
    parser = argparse.ArgumentParser(description="데이터셋 중복 제거")
    parser.add_argument("--input-manifest", required=True, help="입력 매니페스트 파일 경로")
    parser.add_argument(
        "--output-dir",
        default="output/deduplicated",
        help="출력 디렉토리 (기본값: output/deduplicated)",
    )
    parser.add_argument(
        "--lsh-threshold", type=float, default=0.8, help="LSH 유사도 임계값 (기본값: 0.8)"
    )
    parser.add_argument(
        "--levenshtein-threshold",
        type=float,
        default=0.2,
        help="Levenshtein 거리 임계값 (기본값: 0.2)",
    )
    parser.add_argument("--dry-run", action="store_true", help="실제 파일 수정 없이 결과만 출력")

    args = parser.parse_args()

    try:
        # 데이터셋 로드
        dataset, manifest = load_dataset_from_manifest(args.input_manifest)

        # 중복 제거 수행
        deduplicator = DatasetDeduplicator(
            lsh_threshold=args.lsh_threshold, levenshtein_threshold=args.levenshtein_threshold
        )

        result = deduplicator.deduplicate(dataset)

        if not args.dry_run:
            # 중복 제거된 데이터셋 저장
            dataset_name = manifest["metadata"]["name"]
            output_path = f"{args.output_dir}/{dataset_name}_deduplicated.json"
            save_deduplicated_dataset(result["dataset"], output_path)

            # 매니페스트 업데이트
            update_manifest(args.input_manifest, result)

            logger.info("중복 제거 완료!")
        else:
            logger.info("Dry-run 모드: 파일이 수정되지 않았습니다.")

    except Exception as e:
        logger.error(f"중복 제거 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
