# 배포 안내 (팀 GitHub 계정으로 직접 진행)

목표: **소스 = GitHub 저장소**, **메인 실행 링크 = Streamlit Community Cloud**, **예비 링크 = GitHub Pages**, **최종 보험 = 시연 녹화본**.
모두 무료이고, 심사위원에게 가입이나 API 키를 요구하지 않습니다.

## 0. 올리기 전 확인 (중요)

- [ ] 설문 원자료(구글폼 응답 CSV·엑셀)가 폴더에 **없는지** 확인. 집계 결과만 보고서에 사용
- [ ] `data/bookings.db` 파일이 있으면 삭제 (실행할 때 자동으로 다시 생김)
- [ ] 비밀번호·API 키·개인 이메일이 코드에 없는지 확인 (현재 코드에는 없음)

## 1. GitHub 저장소 만들기 (약 5분)

1. github.com 로그인 → 오른쪽 위 **+** → **New repository**
2. Repository name: `maeum-bridge` (원하는 이름 가능)
3. **Public** 선택 (무료 계정에서 GitHub Pages를 쓰려면 공개 저장소여야 함)
4. "Add a README" 체크는 **하지 않음** → **Create repository**
5. 새 저장소 화면에서 **uploading an existing file** 링크 클릭
6. 압축을 푼 `maeum-bridge` 폴더 **안의 내용 전부**(app.py, core, data, docs, tests, validation, README.md, requirements.txt, DEPLOY.md, .gitignore)를 끌어다 놓기
   - 폴더째 끌어 놓으면 구조가 유지됩니다 (크롬 권장)
   - `.gitignore`처럼 점으로 시작하는 파일이 안 보이면 따로 한 번 더 올리기
7. 아래 **Commit changes** 클릭
8. 확인: 저장소 첫 화면에 `app.py`, `core/`, `docs/`가 맨 위 단계에 보여야 함 (`maeum-bridge/app.py`처럼 한 단계 안에 들어가 있으면 잘못 올린 것)

## 2. 메인 링크: Streamlit Community Cloud (약 5분)

1. share.streamlit.io 접속 → **Continue with GitHub**로 로그인 → GitHub 접근 권한 승인
2. 오른쪽 위 **Create app** → "Do you already have an app?" 에서 **Yup, I have an app**
3. 입력
   - Repository: `팀계정/maeum-bridge`
   - Branch: `main`
   - Main file path: `app.py`
   - App URL: 원하는 주소 (예: `maeum-bridge-팀명`) → `https://maeum-bridge-팀명.streamlit.app`
4. **Deploy** → 1~3분 기다리면 앱이 열림
5. 확인: 동의 → 검진 → 결과 → 예약 → 조회까지 한 번 눌러 보기

주의: 무료 앱은 **12시간 동안 접속이 없으면 잠듭니다.** 잠든 앱은 처음 연 사람이 깨우기 버튼을 눌러야 하고 잠깐 기다려야 합니다.
→ 심사 기간에는 **하루 2번(아침·저녁) 팀원이 접속**해 깨워 두기. 담당자를 정해 두세요.

## 3. 예비 링크: GitHub Pages (약 3분)

`docs/` 폴더의 웹 버전을 올립니다. 정적 사이트라 잠들지 않습니다.

1. 저장소 → **Settings** → 왼쪽 **Pages**
2. Build and deployment → Source: **Deploy from a branch**
3. Branch: **main**, 폴더: **/docs** → **Save**
4. 1~2분 뒤 같은 화면 위쪽에 주소가 나타남: `https://팀계정.github.io/maeum-bridge/`
5. 확인: 휴대폰에서 열어 '시연용 예시 응답 채우기' → S3 → 위기 배너가 뜨는지 보기

## 4. 접속 점검 (제출 전날)

- [ ] 두 링크를 **로그인하지 않은 시크릿 창**과 **휴대폰**에서 열어 보기
- [ ] 다른 팀원 기기에서도 열어 보기
- [ ] 시연 녹화본(5분 이내) 저장

## 5. 보고서에 넣을 문구 (부록 예시)

> **실행 방법**
> - 실행 링크: https://maeum-bridge-팀명.streamlit.app (Python·Streamlit, 12시간 미접속 시 대기 화면이 나오면 깨우기 버튼을 눌러 주세요)
> - 예비 링크: https://팀계정.github.io/maeum-bridge/ (같은 규칙의 웹 버전, 예약은 각 브라우저에만 저장)
> - 소스 코드: https://github.com/팀계정/maeum-bridge
> - 로컬 실행: `pip install -r requirements.txt` → `streamlit run app.py` (Python 3.10 이상, 유료 서비스·API 키 불필요)
> - 예시 입력: README 1장의 S1·S2·S3, 또는 웹 화면의 '시연용 예시 응답 채우기' 버튼
> - 공개 범위: 코드·화면 공개 가능 / 교내 설문 원자료 비공개

## 6. 나중에 코드를 고치면

- GitHub에서 파일을 수정·업로드해 커밋하면 Streamlit 앱과 GitHub Pages가 **자동으로 갱신**됩니다.
- 제출 후 수정했다면 바뀐 내용을 기록해 두세요 (요강: 기존 제출 대비 변경 내용 명시).
