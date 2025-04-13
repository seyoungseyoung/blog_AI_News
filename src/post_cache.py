import os
import logging
from typing import Set
from pathlib import Path

class PostCache:
    """
    포스팅된 논문의 ID를 관리하여 중복 포스팅을 방지하는 클래스.
    논문 ID는 파일에 저장됩니다.
    """
    def __init__(self, cache_file: str = 'posted_papers.txt'):
        """
        캐시를 초기화합니다.

        Args:
            cache_file (str): 캐시 파일의 경로 (기본값: 'posted_papers.txt').
                              파일은 프로젝트 루트에 생성됩니다.
        """
        self.cache_file_path = Path(__file__).parent.parent / cache_file
        self.posted_ids: Set[str] = self._load_cache()
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"캐시 파일 로드: {self.cache_file_path}. 총 {len(self.posted_ids)}개 ID 로드됨.")

    def _load_cache(self) -> Set[str]:
        """캐시 파일에서 포스팅된 ID들을 로드합니다."""
        if not self.cache_file_path.exists():
            return set()
        try:
            with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                # 각 줄의 ID를 읽고, 앞뒤 공백 제거 후 빈 줄은 제외
                return {line.strip() for line in f if line.strip()}
        except Exception as e:
            logging.error(f"캐시 파일 로드 중 오류 발생 ({self.cache_file_path}): {e}")
            return set()

    def _save_cache(self):
        """현재 캐시 상태를 파일에 저장합니다."""
        try:
            # 파일 경로의 디렉토리가 없으면 생성
            self.cache_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file_path, 'w', encoding='utf-8') as f:
                for paper_id in sorted(list(self.posted_ids)): # 정렬해서 저장
                    f.write(f"{paper_id}\n")
        except Exception as e:
            self.logger.error(f"캐시 파일 저장 중 오류 발생 ({self.cache_file_path}): {e}")

    def add_paper(self, paper_id: str):
        """포스팅된 논문 ID를 캐시에 추가하고 파일을 업데이트합니다."""
        if not paper_id:
            self.logger.warning("추가하려는 논문 ID가 비어있습니다.")
            return

        paper_id = paper_id.strip()
        if paper_id not in self.posted_ids:
            self.posted_ids.add(paper_id)
            self._save_cache()
            self.logger.info(f"캐시에 새 논문 ID 추가: {paper_id}")
        else:
            self.logger.debug(f"논문 ID가 이미 캐시에 존재합니다: {paper_id}")

    def is_posted(self, paper_id: str) -> bool:
        """주어진 논문 ID가 이미 포스팅되었는지 확인합니다."""
        if not paper_id:
            return False
        return paper_id.strip() in self.posted_ids

    def get_posted_count(self) -> int:
        """캐시에 저장된 포스팅된 논문의 총 개수를 반환합니다."""
        return len(self.posted_ids)
