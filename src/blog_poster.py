import os
import json
from typing import List, Dict, Any
import logging
from datetime import datetime
import frontmatter
import yaml
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import requests
from selenium.webdriver.common.action_chains import ActionChains
from pathlib import Path
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
import re

class BlogPoster:
    def __init__(self, config: Dict):
        self.config = config
        self.username = config.get('NAVER_USERNAME')
        self.password = config.get('NAVER_PASSWORD')
        self.api_key = config.get('DEEPSEEK_API_KEY')
        
        self.naver_blog_url = "https://blog.naver.com"
        self.driver = None
        self.logger = logging.getLogger(__name__)
        
        if not self.username or not self.password:
            self.logger.error("Naver credentials not found in config")
            raise ValueError("네이버 로그인 정보가 설정에 없습니다.")
        if not self.api_key:
             raise ValueError("DEEPSEEK_API_KEY not found in config")

        self.api_url = config.get('DEEPSEEK_API_URL', "https://api.deepseek.com/chat/completions")
        self.posts_dir = 'content/posts'
        self.images_dir = 'static/images'
        self.cookies_file = Path(__file__).parent.parent / 'config' / 'naver_cookies.pkl'
        
        self._setup_driver()

    def _setup_driver(self) -> bool:
        """WebDriver 설정"""
        try:
            print("- WebDriver 설정 시작...")
            
            # Chrome 옵션 설정
            options = webdriver.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--start-maximized')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # User-Agent 설정
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36')
            
            print("- Chrome 옵션 설정 완료")
            
            try:
                # webdriver_manager를 사용하여 ChromeDriver 자동 설치
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
                print("✓ ChromeDriver 자동 설치 및 설정 완료")
            except Exception as e:
                print(f"✗ ChromeDriver 자동 설치 실패: {e}")
                print("- 수동 설치된 ChromeDriver 사용 시도...")
                
                # 수동 설치된 ChromeDriver 사용 시도
                chromedriver_path = Path(__file__).parent / 'chromedriver' / 'chromedriver.exe'
                if not chromedriver_path.exists():
                    print("✗ ChromeDriver를 찾을 수 없습니다.")
                    return False
                    
                service = Service(executable_path=str(chromedriver_path))
                self.driver = webdriver.Chrome(service=service, options=options)
                print("✓ 수동 설치된 ChromeDriver 설정 완료")
            
            # 페이지 로드 타임아웃 설정
            self.driver.set_page_load_timeout(30)
            
            # JavaScript 코드 실행하여 웹드라이버 감지 방지
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            
            print("✓ WebDriver 설정 완료")
            return True
            
        except Exception as e:
            print(f"✗ 웹드라이버 설정 실패: {e}")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            return False

    def login(self):
        """네이버에 로그인합니다."""
        try:
            print("- 네이버 로그인 시작...")
            
            # 네이버 로그인 페이지로 이동
            self.driver.get('https://nid.naver.com/nidlogin.login')
            time.sleep(2)
            
            # JavaScript를 통한 로그인 정보 입력
            self.driver.execute_script(
                f"document.getElementsByName('id')[0].value='{self.username}'")
            time.sleep(0.5)
            
            self.driver.execute_script(
                f"document.getElementsByName('pw')[0].value='{self.password}'")
            time.sleep(0.5)
            
            # 로그인 버튼 클릭
            login_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, 'btn_login'))
            )
            login_button.click()
            
            # 로그인 성공 확인
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda d: 'nid.naver.com/nidlogin.login' not in d.current_url
                )
                print(f"✓ 네이버 로그인 성공. 현재 URL: {self.driver.current_url}")
                return True
            except TimeoutException:
                print("✗ 로그인 실패: 아이디 또는 비밀번호를 확인해주세요.")
                return False
                
        except Exception as e:
            self.logger.error(f"Login failed: {e}", exc_info=True)
            print(f"✗ 로그인 실패: {str(e)}")
            return False

    def check_login_status(self):
        """현재 로그인 상태를 확인합니다."""
        try:
            self.driver.get('https://blog.naver.com/gongnyangi')
            time.sleep(2)
            
            # 로그인 버튼이 있는지 확인
            login_buttons = self.driver.find_elements(By.CLASS_NAME, 'log_btn')
            return len(login_buttons) == 0
            
        except Exception:
            return False

    def _call_api(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.error(f"API call failed: {str(e)}")
            raise

    def _generate_blog_content(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """LLM을 호출하여 블로그 포스트 제목, 내용, 태그를 생성합니다."""
        # LLM에 전달할 정보 준비
        title_orig = paper.get('title', 'N/A')
        url_orig = paper.get('url', 'URL 정보 없음') 
        abstract_orig = paper.get('abstract', '초록 정보 없음') # 원본 초록 추가
        classification = paper.get('classification', 'AI Research') # 분류 정보는 참고용
        summary = paper.get('summary', '요약 정보 없음') # 요약 정보도 참고용
        translation = paper.get('translation', '번역 정보 없음') # 번역 정보도 참고용
        
        prompt = f"""다음 논문 정보를 바탕으로, **깊이 있고 통찰력 있는** 블로그 포스트와 관련 태그를 생성해주세요.

**원본 논문 정보:**
*   제목: {title_orig}
*   URL: {url_orig}
*   분류: {classification}
*   초록 (Abstract): {abstract_orig} 

**요청 사항:**
1.  **블로그 제목:**
    *   논문 내용을 쉽고 흥미롭게 전달하는 **새로운 한글 제목** 생성 (10~30자 내외)
2.  **블로그 본문 (매우 중요 - 깊이 있는 내용):**
    *   **서론:** 연구 배경, 문제 제기, 이 연구가 왜 중요한지 설명.
    *   **본론:** 
        *   **핵심 아이디어/방법론:** 논문에서 제안하는 주요 방법이나 모델을 **일반인이 이해할 수 있도록 쉽게 설명**.
        *   **주요 결과/성능:** 어떤 실험을 통해 무엇을 발견했는지, 기존 연구 대비 어떤 점이 개선되었는지 **구체적인 결과** 언급 (필요시).
        *   **의의/시사점:** 이 연구 결과가 가지는 의미나 시사점 분석.
    *   **결론:** 연구 요약, 한계점 (있다면), 향후 전망.
    *   **참고 정보:** 제공된 '초록(Abstract)' 내용을 **적극 활용**하여 깊이 있는 분석을 담아주세요.
    *   **가독성:** 친절하고 이해하기 쉬운 한글로 작성. 전문 용어는 (영어 원문) 병기.
    *   **형식:** 마크다운 사용. 원본 논문 제목 본문 내 언급. 댓글 유도 금지.
    *   **★출처 명시★:** 본문 맨 마지막 줄에 다음 형식으로 원본 논문 출처 명시:
        ```
        --- 
        원본 논문: [{title_orig}]({url_orig})
        ```
3.  **블로그 태그:**
    *   논문의 핵심 내용(주제, 방법론, 주요 결과 등)을 가장 잘 나타내는 **관련성 높은 태그 15~20개**를 생성해주세요.
    *   **태그는 반드시 한글, 영어 알파벳, 숫자, 공백만 포함해야 합니다. (특수문자 절대 사용 금지)**
    *   너무 일반적이거나 광범위한 태그보다는 구체적인 키워드를 사용해주세요.

**응답 형식 (JSON):**
```json
{{
  "blog_title": "[생성된 한글 제목]",
  "blog_content": "[생성된 깊이 있는 마크다운 본문 (출처 포함)]",
  "blog_tags": ["태그1", "태그2", ..., "태그15"] 
}}
```
"""
        try:
            raw_response = self._call_api(prompt)
            print("--- LLM Raw Response ---")
            print(raw_response)
            print("-------------------------")
            
            # JSON 응답 파싱 시도
            try:
                json_match = re.search(r'```json\n({.*?})\n```', raw_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    parsed_data = json.loads(json_str)
                    
                    required_keys = ['blog_title', 'blog_content', 'blog_tags']
                    if all(key in parsed_data for key in required_keys) and isinstance(parsed_data['blog_tags'], list):
                        print("✓ LLM 응답 JSON 파싱 성공 (제목, 본문, 태그)")
                        
                        # --- 태그 클리닝 --- 
                        raw_tags = parsed_data['blog_tags']
                        cleaned_tags = []
                        seen_tags = set() # 중복 체크용 (소문자 기준)
                        for tag in raw_tags:
                            # 1. 허용 문자(한글,영문,숫자,공백) 외 제거
                            cleaned_tag = re.sub(r'[^a-zA-Z0-9가-힣\s]', '', str(tag))
                            # 2. 양끝 공백 제거 및 연속 공백 하나로
                            cleaned_tag = ' '.join(cleaned_tag.split()).strip()
                            # 3. 빈 태그 및 중복 태그 방지 (소문자 비교)
                            if cleaned_tag and cleaned_tag.lower() not in seen_tags:
                                cleaned_tags.append(cleaned_tag)
                                seen_tags.add(cleaned_tag.lower())
                                
                        # 최대 30개로 제한
                        final_tags = cleaned_tags[:30]
                        print(f"- 클리닝 후 최종 태그 ({len(final_tags)}개): {final_tags}")
                        # --------------------
                        
                        return {
                            "title": parsed_data['blog_title'].strip(),
                            "content": parsed_data['blog_content'].strip(),
                            "tags": final_tags # 클리닝된 태그 사용
                        }
                    else:
                        missing = [k for k in required_keys if k not in parsed_data]
                        type_error = "blog_tags가 리스트가 아님" if 'blog_tags' in parsed_data and not isinstance(parsed_data['blog_tags'], list) else ""
                        print(f"✗ LLM 응답 JSON 형식 오류 (누락 키: {missing}, 타입 오류: {type_error})")
                        raise ValueError("LLM 응답 JSON 형식 오류")
                else:
                    print("✗ LLM 응답에서 JSON 블록을 찾을 수 없음")
                    raise ValueError("LLM 응답 JSON 형식 오류 (JSON 블록 부재)")
                    
            except (json.JSONDecodeError, ValueError) as e:
                print(f"✗ LLM 응답 파싱 실패: {e}. 기본 내용 사용 시도.")
                return {
                    "title": f"[요약] {title_orig}", 
                    "content": f"# {title_orig}\n\n{summary}\n\n(LLM 콘텐츠 생성 실패)",
                    "tags": ['AI', '논문', '기술'] # 기본 태그
                }
                
        except Exception as e:
            self.logger.error(f"Error generating blog content: {str(e)}", exc_info=True)
            print(f"✗ 블로그 콘텐츠 생성 중 오류 발생: {e}")
            return {
                "title": f"[오류] {title_orig}",
                "content": f"# {title_orig}\n\n블로그 콘텐츠 생성 중 오류가 발생했습니다.\n\n오류: {e}",
                "tags": ['오류', 'AI', '논문'] # 오류 시 기본 태그
            }

    def create_post(self, title: str, content: str, tags: List[str]) -> bool:
        """네이버 블로그에 글을 포스팅합니다. (이전 코드 참고, iframe 처리 제거)"""
        if not self.driver:
            self.logger.error("WebDriver가 초기화되지 않았습니다.")
            return False

        try:
            # 1. 글쓰기 페이지로 직접 이동 (이전 코드 방식)
            write_url = f"https://blog.naver.com/{self.username}/postwrite"
            print(f"- 글쓰기 페이지로 직접 이동 시도: {write_url}")
            self.driver.get(write_url)
            print("- 페이지 로딩 대기 (5초)...") # 대기 시간 5초로 수정
            time.sleep(5) 
            current_url = self.driver.current_url
            print(f"- 현재 URL: {current_url}")

            if "postwrite" not in current_url.lower():
                 print(f"✗ 글쓰기 페이지로 이동 실패. 예상 URL과 다름: {current_url}")
                 return False

            # 2. 이전 글 작성 확인 팝업 처리 (이전 코드 참고)
            try:
                print("- 이전 글 팝업 확인 중...")
                WebDriverWait(self.driver, 5).until(
                     EC.presence_of_element_located((By.CLASS_NAME, 'se-popup-button-text'))
                )
                cancel_buttons = self.driver.find_elements(By.CLASS_NAME, 'se-popup-button-text')
                if cancel_buttons:
                    for button in cancel_buttons:
                        if '취소' in button.text or 'cancel' in button.text.lower():
                            button.click()
                            time.sleep(3) # 팝업 닫히는 시간
                            print("- 이전 글 '취소' 처리 완료")
                            break
            except TimeoutException:
                 print("- 이전 글 팝업 없음 - 계속 진행")
            except Exception as e:
                print(f"- 이전 글 팝업 처리 중 오류 (무시하고 계속): {e}")

            # 3. 도움말 닫기 버튼 처리 (이전 코드 참고)
            time.sleep(2)
            try:
                print("- 도움말 팝업 확인 중...")
                help_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), '닫기') or contains(@class, 'close')]")
                for button in help_buttons:
                     try:
                         if button.is_displayed() and button.is_enabled():
                             print("- 도움말 닫기 버튼 클릭 시도...")
                             button.click()
                             time.sleep(2)
                             print("- 도움말 닫기 완료")
                             break
                     except Exception as inner_e: # StaleElementReference 등 예외 처리
                         print(f"-- 도움말 버튼 처리 중 내부 오류 (무시): {inner_e}")
                         continue
            except Exception as e:
                print(f"- 도움말 팝업 처리 중 오류 (무시하고 계속): {e}")

            # 4. 제목 입력 (기본 content)
            try:
                print("- 제목 영역 찾는 중 (기본 content)...")
                title_area = None
                # 제목 영역 선택자 (더 관대한 방식)
                title_selectors = [
                    'span.se-placeholder.__se_placeholder', 
                    'span.se-ff-nanumgothic.se-fs32.__se-node',
                    '[contenteditable="true"][aria-label*="제목"]' # 접근성 속성 활용
                ]
                for i, selector in enumerate(title_selectors):
                    try:
                        title_area = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        print(f"- 제목 영역 찾음 (선택자 {i+1}: {selector})")
                        break # 찾으면 루프 종료
                    except TimeoutException:
                        if i == len(title_selectors) - 1: # 마지막 시도였으면
                           print("✗ 제목 영역을 찾을 수 없습니다.")
                           return False
                        else:
                           print(f"- 제목 영역 선택자 {i+1} 실패, 다음 시도...")
               
                # 제목 입력 수정: 클릭 -> 지우기 -> 새 제목 입력 -> Enter (이전 코드 참고)
                title_area.click()
                time.sleep(0.5)
                # Ctrl+A, Delete
                if os.name == 'nt': ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
                else: ActionChains(self.driver).key_down(Keys.COMMAND).send_keys('a').key_up(Keys.COMMAND).perform()
                time.sleep(0.2)
                ActionChains(self.driver).send_keys(Keys.DELETE).perform()
                time.sleep(0.2)
                # 새 제목 입력
                actions = ActionChains(self.driver) # 제목 입력을 위한 ActionChains
                actions.send_keys(title)
                time.sleep(0.5)
                # Enter 키 추가 (이전 코드 참고)
                actions.send_keys(Keys.ENTER).perform()
                print("- 제목 입력 및 Enter 완료")
                time.sleep(1.5) # Enter 후 본문 활성화 대기 시간 증가 (1.0 -> 1.5)
                
                # --- 본문 영역으로 포커스 이동 (클릭 방식 변경) --- 
                print("- 본문 영역으로 포커스 이동 시도 (JavaScript 클릭)...")
                # 본문 영역 선택자 (더 관대한 방식)
                body_selectors = [
                    'div.se-component-content p.se-text-paragraph', # 이전 코드 주 사용 선택자
                    'div.se-main-container .se-component[contenteditable="true"]',
                    '[contenteditable="true"][aria-label*="내용"]'
                ]
                editor_element = None
                clicked_body = False
                for i, selector in enumerate(body_selectors):
                    try:
                         # 요소를 먼저 찾음
                         editor_element = WebDriverWait(self.driver, 3).until(
                             EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                         )
                         print(f"- 본문 영역 찾음 (선택자 {i+1}: {selector})")
                         # JavaScript로 클릭 시도 (이전 코드 방식)
                         try:
                             self.driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", editor_element)
                             print("- 본문 영역 JavaScript 클릭 성공 (포커스 이동)")
                             time.sleep(1.0) # 클릭 후 대기 시간 유지
                             clicked_body = True
                             break # 성공 시 루프 종료
                         except Exception as click_e:
                             print(f"- 본문 영역 JavaScript 클릭 실패 (선택자 {i+1}): {click_e}, 다음 시도...")
                             if i == len(body_selectors) - 1: # 마지막 시도였으면
                                 print("✗ 모든 본문 영역 클릭 실패")
                                 return False
                    except TimeoutException:
                        if i == len(body_selectors) - 1:
                            print("✗ 본문 영역을 찾을 수 없습니다.")
                            return False
                        else:
                            print(f"- 본문 영역 선택자 {i+1} 실패, 다음 시도...")
                
                if not clicked_body:
                     print("✗ 본문 영역 클릭에 최종 실패했습니다.")
                     return False

            except Exception as e:
                print(f"✗ 제목 입력 또는 본문 포커스 이동 실패: {e}")
                return False

            # 5. 본문 입력 (기본 content, 포커스 이동 후)
            try:
                print("- 본문 내용 입력 시작...")
                time.sleep(0.5) # 본문 입력 시작 전 추가 대기
                actions = ActionChains(self.driver) # 본문 입력을 위한 ActionChains 새로 생성
                cleaned_content = content.strip()
                total_chars = len(cleaned_content)
                print(f"- 총 {total_chars} 문자 입력 예정")

                for i, char in enumerate(cleaned_content):
                    if char == '\n':
                        actions.send_keys(Keys.ENTER)
                    else:
                        actions.send_keys(char)
                    actions.perform()
                    time.sleep(0.01) # 이전 커밋에서 주석 처리됨

                    if (i + 1) % 100 == 0 or (i + 1) == total_chars:
                        print(f"  ... {i+1}/{total_chars} 문자 입력 완료")

                print("- 모든 본문 문자 입력 완료.")
                time.sleep(1)

            except Exception as e:
                print(f"✗ 본문 입력 실패: {e}")
                return False

            # 6. 1단계 발행 버튼 클릭 (JavaScript 우선, 이전 코드 참고)
            try:
                print("- 1단계 발행 버튼 클릭 시도 (JavaScript)... ")
                publish_script = "document.querySelector('button.publish_btn__m9KHH').click(); return true;"
                try:
                    self.driver.execute_script(publish_script)
                    print("- 1단계 발행 버튼 클릭 완료 (JavaScript). 발행 설정 창 대기 (5초)...")
                    time.sleep(5)
                except Exception as js_e:
                    print(f"- JavaScript 클릭 실패 ({js_e}), Selenium 클릭 시도...")
                    publish_button_selector = 'button.publish_btn__m9KHH'
                    publish_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, publish_button_selector))
                    )
                    publish_button.click()
                    print("- 1단계 발행 버튼 클릭 완료 (Selenium). 발행 설정 창 대기 (5초)...")
                    time.sleep(5)
            except Exception as e:
                print(f"✗ 1단계 발행 버튼 클릭 실패: {e}")
                return False

            # 7. 카테고리 선택 (이전 코드 참고, 실패 시 무시)
            try:
                print("- 카테고리 선택 중...")
                category_button_selector = 'button.selectbox_button__jb1Dt'
                category_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, category_button_selector))
                )
                category_button.click()
                time.sleep(1)
                
                # 카테고리명 확인 필요! 'AI 연구뉴스'가 맞는지 확인하세요.
                # 주의: for 속성값 '18'은 동적으로 변할 수 있음. 텍스트 기반이 더 나을 수 있음.
                category_text_xpath = "//label[contains(., 'AI 연구뉴스')]"
                try:
                    category_label = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, category_text_xpath))
                    )
                except TimeoutException:
                    # 카테고리 ID '18' 시도 (Fallback)
                    category_label_selector = 'label[for="category-18"]'
                    print(f"- 카테고리 텍스트 선택자 실패, ID({category_label_selector}) 기반 시도...")
                    category_label = WebDriverWait(self.driver, 5).until(
                         EC.element_to_be_clickable((By.CSS_SELECTOR, category_label_selector))
                    )

                category_label.click()
                print("✓ 카테고리 선택 완료")
                time.sleep(1)
            except Exception as e:
                print(f"✗ 카테고리 선택 실패 (무시하고 진행): {e}")

            # 8. 태그 입력 (이전 코드 참고, 실패 시 무시)
            if tags:
                try:
                    print("- 태그 입력 시작...")
                    tag_input_selector = 'input#tag-input.tag_input__rvUB5'
                    tag_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, tag_input_selector))
                    )
                    for tag in tags:
                        tag_input.clear()
                        time.sleep(0.1)
                        tag_input.send_keys(tag)
                        time.sleep(0.5)
                        tag_input.send_keys(Keys.ENTER)
                        time.sleep(1)
                    print("- 모든 태그 입력 완료")
                except Exception as e:
                    print(f"✗ 태그 입력 실패 (무시하고 진행): {e}")
            else:
                print("- 입력할 태그 없음")

            # 9. 2단계 최종 발행 버튼 클릭 (JavaScript 우선, 이전 코드 참고)
            try:
                print("- 2단계 최종 발행 버튼 클릭 시도 (JavaScript)... ")
                final_publish_script = "document.querySelector('button.confirm_btn__WEaBq[data-testid=\"seOnePublishBtn\"]\').click(); return true;"
                try:
                    self.driver.execute_script(final_publish_script)
                    print("- 2단계 최종 발행 버튼 클릭 완료 (JavaScript). 포스팅 완료 대기 (7초)...")
                    time.sleep(7)
                except Exception as js_e:
                    print(f"- JavaScript 클릭 실패 ({js_e}), Selenium 클릭 시도...")
                    final_publish_button_selector = 'button.confirm_btn__WEaBq[data-testid=\"seOnePublishBtn\"]\''
                    final_publish_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, final_publish_button_selector))
                    )
                    final_publish_button.click()
                    print("- 2단계 최종 발행 버튼 클릭 완료 (Selenium). 포스팅 완료 대기 (7초)...")
                    time.sleep(7)
                
                if "postwrite" not in self.driver.current_url.lower():
                     print("✓ 블로그 포스팅 성공!")
                     return True
                else:
                     print(f"✗ 포스팅 실패 또는 확인 불가: 현재 URL이 여전히 postwrite 페이지입니다 ({self.driver.current_url})")
                     return False

            except Exception as e:
                print(f"✗ 2단계 최종 발행 버튼 클릭 실패: {e}")
                return False

        except Exception as e:
            self.logger.error(f"Error creating post: {str(e)}", exc_info=True)
            print(f"✗ 포스팅 생성 중 예외 발생: {e}")
            # 오류 시 스크린샷 저장
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f'error_screenshot_{timestamp}.png'
                self.driver.save_screenshot(screenshot_path)
                print(f"- 오류 발생 시점 스크린샷 저장: {screenshot_path}")
            except Exception as ss_e:
                print(f"- 스크린샷 저장 실패: {ss_e}")
            return False

    def post_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """논문을 블로그에 포스팅합니다."""
        original_title = paper.get('title', 'N/A')
        self.logger.info(f"Posting paper (Original Title): {original_title}")

        try:
            # LLM 호출하여 새로운 한글 제목, 내용, 태그 생성
            generated_post = self._generate_blog_content(paper)
            blog_title = generated_post['title']
            blog_content = generated_post['content']
            tags = generated_post['tags'] # LLM이 생성한 태그 사용
            self.logger.info(f"Generated Blog Title: {blog_title}")
            self.logger.info(f"Generated Tags: {tags}")

            # 분류 정보는 가져오기 (필요시)
            classification = paper.get('classification', paper.get('categories', ['AI Research'])[0])
            
            # 블로그에 포스팅 (생성된 제목, 내용, 태그 사용)
            if not self.driver:
                if not self._setup_driver():
                    raise Exception("Failed to setup WebDriver")

            if not self.login():
                raise Exception("Failed to login")

            if not self.create_post(blog_title, blog_content, tags):
                 print(f"✗ 포스팅 생성 실패 (Title: {blog_title})")
                 raise Exception("Failed to create post")

            self.logger.info(f"Successfully posted paper: {original_title} (as: {blog_title})")

            # 결과 반환 (생성된 제목, 태그 포함)
            return {
                "paper_id": paper.get("paper_id", "N/A"),
                "original_title": original_title,
                "blog_title": blog_title, 
                "classification": classification, 
                "tags": tags, # LLM 생성 태그
                "content": blog_content 
            }
        except Exception as e:
            self.logger.error(f"Error posting paper {original_title}: {str(e)}", exc_info=True)
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f'error_post_paper_{timestamp}.png'
                if self.driver: self.driver.save_screenshot(screenshot_path)
                print(f"- 오류 발생 시점 스크린샷 저장: {screenshot_path}")
            except Exception as ss_e:
                print(f"- 스크린샷 저장 실패: {ss_e}")
            raise

    def save_post_to_file(self, content: str, paper: Dict[str, Any]) -> bool:
        """
        생성된 내용을 개별 파일로 저장합니다.
        """
        try:
            # 디렉토리 생성
            os.makedirs(self.posts_dir, exist_ok=True)
            os.makedirs(self.images_dir, exist_ok=True)

            # 파일명 생성 (날짜와 논문 ID 사용)
            date_str = datetime.now().strftime('%Y-%m-%d')
            # 논문 ID에서 특수문자 제거
            paper_id = ''.join(c for c in paper.get('paper_id', 'unknown_paper') if c.isalnum() or c in ('-', '_'))
            filename = os.path.join(self.posts_dir, f'{date_str}_{paper_id}.md')

            # 파일에 내용 저장
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)

            self.logger.info(f"Successfully saved post to {filename}")

            # 이미지 파일 복사 (필요한 경우)
            self._copy_featured_image()

            return True

        except Exception as e:
            self.logger.error(f"Error while saving post to file: {str(e)}")
            return False

    def _copy_featured_image(self):
        """
        피처드 이미지를 복사합니다.
        """
        try:
            source_image = 'assets/images/ai_research.jpg'
            target_image = os.path.join(self.images_dir, 'ai_research.jpg')

            if os.path.exists(source_image):
                import shutil
                shutil.copy2(source_image, target_image)
                self.logger.info(f"Successfully copied featured image to {target_image}")
        except Exception as e:
            self.logger.error(f"Error while copying featured image: {str(e)}")

    def update_index(self):
        """
        블로그 인덱스를 업데이트합니다.
        """
        try:
            index_file = 'content/_index.md'
            if os.path.exists(index_file):
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_content = f.read()

                # 인덱스 업데이트 로직 추가
                # ...

                self.logger.info("Successfully updated blog index")
        except Exception as e:
            self.logger.error(f"Error while updating index: {str(e)}")

    def generate_rss(self):
        """
        RSS 피드를 생성합니다.
        """
        try:
            rss_file = 'static/rss.xml'
            # RSS 생성 로직 추가
            # ...

            self.logger.info("Successfully generated RSS feed")
        except Exception as e:
            self.logger.error(f"Error while generating RSS: {str(e)}")

    def close(self):
        """WebDriver를 종료합니다."""
        if self.driver:
            try:
                print("- WebDriver 종료 중...")
                self.driver.quit()
                self.driver = None
                print("✓ WebDriver 종료 완료")
            except Exception as e:
                print(f"✗ WebDriver 종료 중 오류 발생: {e}")
                self.driver = None # 오류 발생 시에도 None으로 설정 