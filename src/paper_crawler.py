import arxiv
import datetime
from typing import List, Dict, Any
import pytz
import time
import os
import logging
import re

class PaperCrawler:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def get_daily_papers(self) -> List[Dict[str, Any]]:
        """최근 72시간 내의 논문을 크롤링하고 랭킹을 매깁니다."""
        try:
            print("- arXiv API에서 논문 검색 중...")
            # 최근 72시간 내의 AI 논문 검색
            search = arxiv.Search(
                query='cat:cs.AI',
                max_results=100,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            
            papers = []
            time_periods = [24, 48, 72]  # 검색할 시간대 (시간 단위)
            current_period = 0
            
            while current_period < len(time_periods) and not papers:
                hours_ago = time_periods[current_period]
                time_ago = datetime.datetime.now(pytz.UTC) - datetime.timedelta(hours=hours_ago)
                print(f"- 최근 {hours_ago}시간 내 논문 검색 중...")
                
                for result in search.results():
                    # 현재 설정된 시간대 내의 논문만 필터링
                    if result.published < time_ago:
                        continue
                        
                    paper = {
                        'title': result.title,
                        'authors': [author.name for author in result.authors],
                        'abstract': result.summary,
                        'url': result.entry_id,
                        'pdf_url': result.pdf_url,
                        'published': result.published.strftime('%Y-%m-%d %H:%M:%S'),
                        'categories': result.categories,
                        'doi': result.doi,
                        'comment': result.comment,
                        'score': 0  # 랭킹 점수 초기화
                    }
                    papers.append(paper)
                
                if not papers:
                    current_period += 1
                else:
                    print(f"✓ 최근 {hours_ago}시간 내 {len(papers)}개의 논문을 찾았습니다.")
            
            if not papers:
                print("✗ 최근 72시간 내 제출된 논문이 없습니다.")
                return []
            
            # 랭킹 점수 계산
            for paper in papers:
                # 1. 최신성 점수 (최근일수록 높은 점수)
                hours_old = (datetime.datetime.now(pytz.UTC) - datetime.datetime.strptime(paper['published'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.UTC)).total_seconds() / 3600
                paper['score'] += max(0, 72 - hours_old) * 2  # 72시간 기준으로 점수 계산
                
                # 2. 저자 수 점수 (저자가 많을수록 높은 점수)
                paper['score'] += min(len(paper['authors']), 5)
                
                # 3. 제목 길이 점수 (적절한 길이의 제목에 높은 점수)
                title_length = len(paper['title'])
                if 30 <= title_length <= 100:
                    paper['score'] += 3
                elif 20 <= title_length < 30 or 100 < title_length <= 150:
                    paper['score'] += 2
                else:
                    paper['score'] += 1
                
                # 4. 초록 길이 점수 (적절한 길이의 초록에 높은 점수)
                abstract_length = len(paper['abstract'])
                if 500 <= abstract_length <= 2000:
                    paper['score'] += 3
                elif 300 <= abstract_length < 500 or 2000 < abstract_length <= 3000:
                    paper['score'] += 2
                else:
                    paper['score'] += 1
                
                # 5. 키워드 점수 (AI 관련 키워드가 많을수록 높은 점수)
                keywords = ['artificial intelligence', 'machine learning', 'deep learning', 'neural network', 'transformer', 'llm', 'gpt']
                title_lower = paper['title'].lower()
                abstract_lower = paper['abstract'].lower()
                keyword_count = sum(1 for keyword in keywords if keyword in title_lower or keyword in abstract_lower)
                paper['score'] += keyword_count
            
            # 점수순으로 정렬
            papers.sort(key=lambda x: x['score'], reverse=True)
            
            # 상위 10개 논문 출력 (로깅용)
            print("\n=== 상위 10개 논문 ===")
            for i, paper in enumerate(papers[:10], 1):
                print(f"{i}위: {paper['title']} (점수: {paper['score']:.2f})") # 점수 소수점 표시
            
            # 상위 N개 논문 반환 (캐시 확인 및 다중 포스팅 위해 여러 개 반환)
            top_papers_count = 20 # 반환 개수 증가 (예: 20)
            print(f"- 상위 {top_papers_count}개 논문을 반환합니다.")
            return papers[:top_papers_count]
            
        except Exception as e:
            print(f"✗ 논문 크롤링 중 오류 발생: {str(e)}")
            self.logger.error(f"Error during paper crawling: {e}", exc_info=True) # 로깅 추가
            return []
            
    def filter_papers(self, papers: List[Dict]) -> List[Dict]:
        """
        수집된 논문들을 필터링합니다.
        """
        filtered_papers = []
        for paper in papers:
            # AI 관련 카테고리 필터링
            if any(cat.startswith('cs.AI') or cat.startswith('cs.LG') for cat in paper['categories']):
                filtered_papers.append(paper)
                
        self.logger.info(f"Filtered {len(filtered_papers)} AI-related papers")
        return filtered_papers 