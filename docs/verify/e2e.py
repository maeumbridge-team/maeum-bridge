"""웹 버전 E2E: 실제 Chrome으로 화면을 클릭하며 흐름 전체를 확인한다."""
import sys, pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path(sys.argv[1]).resolve().as_uri()
out = pathlib.Path(sys.argv[2]); out.mkdir(exist_ok=True)
errors, results = [], []
def check(name, cond): results.append((name, bool(cond)))
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 390, "height": 844})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(url); pg.wait_for_timeout(300)
    check("동의 전 시작 버튼 비활성", pg.is_disabled("#start"))
    pg.screenshot(path=out / "m1_intro.png", full_page=True)
    pg.check("#agree"); pg.click("#start")
    pg.click("#submit")
    check("미응답 경고 16문항", "GAD-7 7" in pg.text_content("#missing") and pg.locator("fieldset.missing").count() == 16)
    for ex, lvl, flag in [("S1", "1단계", False), ("S2", "2단계", True), ("S3", "3단계", True)]:
        if ex != "S1":
            pg.click("#restart"); pg.check("#agree"); pg.click("#start")
        pg.click(f"[data-ex={ex}]")
        check(f"{ex} 진행률 16/16", pg.text_content("#ptext") == "응답 16 / 16")
        pg.click("#submit")
        check(f"{ex} 판정 {lvl}", lvl in pg.text_content(".level .tag"))
        check(f"{ex} 위기 배너 {'있음' if ex=='S3' else '없음'}", (pg.locator(".alert.crit").count() == 1) == (ex == "S3"))
        check(f"{ex} 예약 폼 {'바로 표시' if flag else '버튼 뒤'}", (pg.locator("#book").count() == 1) == flag)
        if ex == "S3":
            pg.screenshot(path=out / "m2_result_S3.png", full_page=True)
    # 선호 방식 필터: 채팅만
    for m in ["대면", "화상", "전화"]:
        pg.click(f"[data-mode={m}]")
    check("채팅만 선택 시 예약 채널 1개", pg.locator("#ch option").count() == 1 and "채팅" in pg.text_content("#ch"))
    pg.click("[data-mode=대면]")
    first_slot = pg.input_value("#slot")
    pg.click("#book")
    code = pg.text_content("#code")
    check("예약 코드 형식", code.startswith("MB-") and len(code) == 12)
    pg.screenshot(path=out / "m3_done.png", full_page=True)
    pg.click("#home")
    pg.click("#lookup summary"); pg.fill("#lookup-code", code.lower()); pg.click("#lookup-btn")
    check("조회(소문자 입력)", "·" in pg.text_content("#lookup-msg") and "ok" in pg.get_attribute("#lookup-msg", "class"))
    # 같은 시간 중복 예약 방지: 다시 S3로 들어가 같은 채널 슬롯 목록에서 빠졌는지
    pg.check("#agree"); pg.click("#start"); pg.click("[data-ex=S3]"); pg.click("#submit")
    pg.select_option("#ch", "campus_chat")
    check("예약된 시간은 목록에서 제외", first_slot not in [o.get_attribute("value") for o in pg.locator("#slot option").all()])
    pg.click("#lookup summary"); pg.fill("#lookup-code", code); pg.click("#cancel-btn")
    check("취소", "취소했습니다" in pg.text_content("#lookup-msg"))
    pg.click("#lookup-btn"); check("취소 후 조회 없음", "없습니다" in pg.text_content("#lookup-msg"))
    # 다크 모드 · 데스크톱 폭
    pg2 = b.new_page(viewport={"width": 1100, "height": 900}, color_scheme="dark")
    pg2.on("pageerror", lambda e: errors.append(str(e)))
    pg2.goto(url); pg2.check("#agree"); pg2.click("#start"); pg2.click("[data-ex=S2]"); pg2.click("#submit")
    pg2.screenshot(path=out / "d1_result_S2_dark.png", full_page=True)
    sw = pg.evaluate("document.documentElement.scrollWidth"); check(f"모바일 가로 스크롤 없음 (scrollWidth={sw})", sw <= 390)
    b.close()
for n, ok in results: print(("PASS " if ok else "FAIL ") + n)
print("JS 오류:", errors or "없음")
sys.exit(0 if all(ok for _, ok in results) and not errors else 1)
