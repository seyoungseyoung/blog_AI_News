import logging
import os
from typing import Dict
from dotenv import load_dotenv
from paper_crawler import PaperCrawler
from blog_poster import BlogPoster
from post_cache import PostCache
import json
import time
import schedule # 스케줄 라이브러리 import
import pytz # 시간대 처리 라이브러리 import
from datetime import datetime # datetime import 추가

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('ai_news_blog.log'),
            logging.StreamHandler()
        ]
    )

def load_config() -> Dict:
    load_dotenv()
    return {
        'DEEPSEEK_API_KEY': os.getenv('DEEPSEEK_API_KEY'),
        'NAVER_USERNAME': os.getenv('NAVER_USERNAME'),
        'NAVER_PASSWORD': os.getenv('NAVER_PASSWORD'),
        # NAVER_ID, NAVER_PW는 현재 BlogPoster에서 사용 안 함
    }

def run_posting_job(use_cache: bool = True):
    """논문 포스팅 작업을 수행하는 함수"""
    logger = logging.getLogger(__name__)
    logger.info("=== 논문 포스팅 작업 시작 ===")
    
    try:
        # 설정 로드
        logger.info("설정 로드 중...")
        config = load_config()
        logger.info("설정 로드 완료.")
        
        # 포스트 캐시 초기화
        logger.info("포스트 캐시 초기화 중...")
        cache = PostCache()
        logger.info("포스트 캐시 초기화 완료.")
        
        # 논문 크롤러 초기화
        logger.info("논문 크롤러 초기화 중...")
        crawler = PaperCrawler(config)
        logger.info("논문 크롤러 초기화 완료.")
        
        # 최근 상위 논문 가져오기
        logger.info("최근 상위 논문 검색 시작...")
        papers = crawler.get_daily_papers() 
        if not papers:
            logger.warning("크롤링할 논문이 없습니다.")
            logger.info("=== 논문 포스팅 작업 종료 (크롤링 결과 없음) ===")
            return
        logger.info(f"상위 {len(papers)}개 논문 검색 완료.")
            
        # 블로그 포스터 초기화
        logger.info("블로그 포스터 초기화 중...")
        poster = BlogPoster(config)
        logger.info("블로그 포스터 초기화 완료.")
        
        # 포스팅할 논문 찾기 및 최대 10개 포스팅
        posted_count = 0
        max_posts = 10 
        processed_papers = 0 
        
        logger.info(f"새 논문 포스팅 시작 (최대 {max_posts}개 목표)...")
        for paper in papers:
            processed_papers += 1
            if posted_count >= max_posts:
                logger.info(f"목표 포스팅 개수({max_posts}개)에 도달하여 종료합니다.")
                break 
                
            paper_id = paper.get('url') 
            if not paper_id:
                logger.warning(f"논문 ID(URL) 없음 (순위: {processed_papers}): {paper.get('title')}")
                continue 
                
            if use_cache and cache.is_posted(paper_id):
                logger.info(f"이미 포스팅됨 (순위: {processed_papers}, ID: {paper_id}): {paper.get('title')}")
                continue 
            
            logger.info(f"포스팅 시도 (순위: {processed_papers}, 목표: {posted_count + 1}/{max_posts}): {paper.get('title')} (ID: {paper_id})")
            try:
                result = poster.post_paper(paper)
                if result:
                    logger.info(f"✓ 포스팅 성공 ({posted_count + 1}/{max_posts}): {paper.get('title')}")
                    if use_cache:
                        cache.add_paper(paper_id)
                    posted_count += 1 
                    logger.info("성공 후 10초 대기...")
                    time.sleep(10) 
                else:
                    logger.error(f"✗ 포스팅 실패: {paper.get('title')}")
            except Exception as e:
                logger.error(f"✗ 포스팅 중 예외 발생 ({paper.get('title')}): {str(e)}", exc_info=True)
                
        logger.info(f"총 {processed_papers}개 논문 처리, {posted_count}개 신규 포스팅 완료.")
        if processed_papers == len(papers) and posted_count < max_posts:
             logger.warning(f"가져온 모든 논문을 확인했지만 목표({max_posts}개)보다 적게 포스팅했습니다.")
                
    except Exception as e:
        logger.critical(f"✗ 작업 실행 중 치명적 오류 발생: {str(e)}", exc_info=True)
    finally:
        if 'poster' in locals() and hasattr(poster, 'driver') and poster.driver:
            logger.info("블로그 포스터 리소스 정리 중...")
            poster.close()
            logger.info("블로그 포스터 리소스 정리 완료.")
        logger.info("=== 논문 포스팅 작업 종료 ===")

# --- 스케줄링 관련 함수 및 실행 로직 --- 
def main(use_cache: bool = True):
    """스케줄러를 설정하고 실행합니다."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    kst = pytz.timezone('Asia/Seoul')
    schedule_time_str = "20:25"
    
    logger.info(f"스케줄러 시작. 매일 한국 시간 {schedule_time_str}에 작업 실행 예정.")
    
    # 스케줄 설정: 매일 KST 03:05에 run_posting_job 실행
    schedule.every().day.at(schedule_time_str, kst).do(run_posting_job, use_cache=use_cache)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    # --- 실행 모드 선택 ---
    TEST_MODE = False  # True: 테스트 모드, False: 실제 운영 모드
    
    if TEST_MODE:
        # 테스트 모드: 즉시 1회 실행
        print("--- 테스트 모드: run_posting_job() 즉시 실행 ---")
        setup_logging()
        run_posting_job(use_cache=False)  # 테스트 시 캐시 사용 안 함
        print("--- run_posting_job() 실행 완료 ---")
    else:
        # 실제 운영 모드: 스케줄러 실행
        print("--- 운영 모드: 스케줄러 시작 ---")
        main(use_cache=True)  # 실제 운영 시 캐시 사용 