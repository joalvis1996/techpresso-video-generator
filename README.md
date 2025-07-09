# techpresso-video-generator

1. 뉴스레터 메일 수집 및 파싱 자동화 - GAS (Google Apps Script) 활용

“외부 뉴스 콘텐츠를 자동으로 가져와서 필요 없는 것 쳐내고, 딱 쓰기 좋은 JSON으로 만들어 자동화 파이프라인에 연결해주는 역할”

- 메일을 직접 열지 않고 'techpresso' 발신자 키워드로 메일 찾음. 스케줄러 기능을 통해 하루 단위로 자동 실행.
- 메일 본문(HTML)에서 핵심 내용만 파싱 (제목, 상세 내용, 관련 이모지)
- 파싱된 기사 내용을 '제목', '본문', '원문링크' 형태의 JSON 배열로 정리
- UrlFetchApp.fetch() 사용하여 Make에서 생성한 Webhook URL로 POST 요청 (Make 시나리오 시작을 위함)

2. Make 시나리오 시작 및 중복 체크

- Custom Webhook 모듈이 JSON 수신
- 이미 저장한 기사인지 체크 (Supabase REST API를 GET 방식으로 호출)
- Query string은 bundle 데이터 중 subject 항목을 이용 
![중복 체크](./assets/img/supabase_check_duplicate.png)

- true이면 기존에 저장된 row 반환 (중복이므로 시나리오 종료)
- false이면 빈 배열 [] 반환 (다음 모듈 실행)
- Router 모듈 사용하여 true, false 분기
![분기](./assets/img/supabase_duplicate_router.png)
