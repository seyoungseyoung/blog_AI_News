import os
import logging
from dotenv import load_dotenv
from blog_poster import BlogPoster
from typing import Dict
from pathlib import Path

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('test_blog_posting.log'),
            logging.StreamHandler()
        ]
    )

def load_config() -> Dict:
    # .env 파일의 절대 경로를 찾습니다
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    
    config = {
        'DEEPSEEK_API_KEY': os.getenv('DEEPSEEK_API_KEY'),
        'NAVER_USERNAME': os.getenv('NAVER_USERNAME'),
        'NAVER_PASSWORD': os.getenv('NAVER_PASSWORD')
    }
    
    # 필수 환경 변수가 설정되었는지 확인
    required_vars = ['NAVER_USERNAME', 'NAVER_PASSWORD', 'DEEPSEEK_API_KEY']
    missing_vars = [var for var in required_vars if not config.get(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return config

def main():
    """테스트 메인 함수"""
    try:
        setup_logging()
        logging.info("Starting blog posting test...")
        
        # 설정 로드
        config = load_config()
        logging.info("Configuration loaded successfully")
        
        # 테스트용 포스트 데이터
        test_post = {
            "title": "Test Blog Post Title",
            "summary": "This is a test summary for the blog post.",
            "translation": "이것은 블로그 포스트를 위한 테스트 요약입니다.",
            "classification": "AI Research",
            "tags": ["Test", "AI", "Research"]
        }
        
        logging.info(f"Loaded test post: {test_post['title']}")
        
        # 블로그 포스터 초기화
        poster = BlogPoster(config)
        
        # 포스팅 시도
        result = poster.post_paper(test_post)
        
        if result:
            logging.info("Blog posting test completed successfully!")
        else:
            logging.error("Blog posting test failed!")
            
    except Exception as e:
        logging.error(f"Error during blog posting test: {str(e)}", exc_info=True)
    finally:
        if 'poster' in locals():
            poster.close()

if __name__ == "__main__":
    main() 