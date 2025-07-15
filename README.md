# techpresso-video-generator

1. 뉴스레터 메일 수집 및 파싱 자동화 - GAS (Google Apps Script) 활용

“외부 뉴스 콘텐츠를 자동으로 가져와서 필요 없는 것 쳐내고, 딱 쓰기 좋은 JSON으로 만들어 자동화 파이프라인에 연결해주는 역할”

- 메일을 직접 열지 않고 'techpresso' 발신자 키워드로 메일 찾음. 스케줄러 기능을 통해 하루 단위로 자동 실행.
- 메일 본문(HTML)에서 핵심 내용만 파싱 (제목, 상세 내용, 관련 이모지)
- 파싱된 기사 내용을 '제목', '본문', '원문링크' 형태의 JSON 배열로 정리
- UrlFetchApp.fetch() 사용하여 Make에서 생성한 Webhook URL로 POST 요청 (Make 시나리오 시작을 위함)
![스크립트 실행 예시](./assets/img/apps_script_fetch.png)

2. Make 시나리오 시작 및 중복 체크

- Custom Webhook 모듈이 JSON 수신
- 이미 저장한 기사인지 체크 (Supabase REST API - GET 요청)
- Query string은 bundle 데이터 중 subject 항목을 이용 
![중복 체크](./assets/img/supabase_check_duplicate.png)

- true이면 기존에 저장된 row 반환 (중복이므로 시나리오 종료)
- false이면 빈 배열 [] 반환 (다음 모듈 실행)
- Router 모듈 사용하여 true, false 분기
![분기](./assets/img/supabase_duplicate_router.png)

3. 기사 번역 및 내용 가공 (Gemini API)

- 영어에서 한국어로 기사 내용 번역
- 뉴스 대본 형식으로 내용 가공 
![프롬프트](./assets/img/gemini_prompt_translate.png)

- Gemini 응답값 정제
    - 불필요한 따옴표, 이스케이프 문자 제거 (Text Parser 모듈 사용)
    - 문자열 JSON 으로 변환 (JSON 모듈 사용)
    - 전 단계에서 출력된 다수의 레코드들을 하나의 배열로 합침(Array Aggregator 모듈 사용)

    ex. 번역 결과가 3개인 경우
    ```
    {title: "...", news_style_content: "..."}
    {title: "...", news_style_content: "..."}
    {title: "...", news_style_content: "..."}
    ```
    위 형식을 아래 배열로 변환
    ```
    [
        { "title": "...", "news_style_content": "..." },
        { "title": "...", "news_style_content": "..." },
        { "title": "...", "news_style_content": "..." }
    ]
    ```
    - 배열에 저장된 원소를 하나씩 꺼내서 반복 실행 (Iterator 모듈 사용)
    - DB에 기사 제목, 내용, 뉴스 형식 대본 등을 저장 (HTTP 모듈 사용, Supabase REST API - PATCH 요청)

    ![기사 저장](./assets/img/supabase_save_news.png)

