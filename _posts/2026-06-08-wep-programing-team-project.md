---
title: "InfoSec Hub 개발 기록"
date: 2026-06-9 18:00:00 +0900
categories: [Project, Web]
tags: [HTML, CSS, JavaScript, Portfolio, Security, Frontend]
render_with_liquid: false
---


# InfoSec Hub: 정보보호 지식 아카이브 플랫폼 제작기


## 1. 프로젝트 아키텍처 기획 및 팀별 도메인 분업 구조


정보보호전공 과정에서 학습하는 지식은 범위가 방대합니다. 

이러한 지식들은 실무 환경에서 유기적으로 맞물려 돌아가지만, 학부 과정의 학습 노트는 파편화되기 쉬운 특성을 가지고 있습니다. 저희 팀(정일재, 권도영, 조하율)은 전공 역량을 한데 모으고, 언제든 꺼내 볼 수 있는 시각화된 전공 바이블을 구축하기 위해 **InfoSec Hub** 프로젝트를 출범했습니다.


중간고사 마일스톤의 핵심 목표는 **"동적 비즈니스 로직이 어떤 화면에서도 완벽하게 구동될 수 있도록 확장성 있는 프론트엔드 인프라와 정적 아카이브 뼈대를 완성하는 것"**이었습니다. 이를 위해 플랫폼을 구성하는 레이아웃과 서브페이지 아키텍처를 완전히 통일하고, 5대 보안 도메인을 설정하여 각 팀원의 강점에 맞춰 심화 마크업을 진행했습니다.


* **정일재 (Project Manager):** 프로젝트 전체 아키텍처 설계 및 UI/UX 인프라 스크립트 총괄. `index.html`(메인 대시보드), `forensics.html`(디지털 포렌식 수사 절차 및 윈도우 아티팩트 구조화), `pwnable.html`(시스템 해킹, x86/x64 메모리 구조 및 BOF/ROP 공격 기법 시각화) 마크업 및 콘텐츠 자산 빌드.
* **권도영 (UI/UX Designer):** 플랫폼 브랜드 아이덴티티(BI) 확립 및 전역 스타일 시트 가이드라인 제정. `:root` 커스텀 가상 클래스를 이용한 다크 테마 컬러 팔레트 및 반응형 글래스모피즘 네비게이션 설계. `reversing.html`(역공학 분석 기법 및 어셈블리어 구조화) 콘텐츠 구축.
* **조하율 (Web Publisher):** 미디어 쿼리 기반의 전역 모바일 뷰포트 적응형 레이아웃 검증 및 브라우저 크로스 체킹. `hardening.html`(리눅스 커널 보안 및 인프라 요새화), `network.html`(OSI 7계층 패킷 분석 및 트래픽 탐지 기법) 콘텐츠 구축.


이처럼 톱니바퀴처럼 맞물린 분업 구조 하에, 모든 HTML 파일이 하나의 공통 스타일 시트(`style.css`)와 자바스크립트(`script.js`)를 참조하도록 설계하여 유지보수성을 극대화했습니다.




---


## 2. HTML 시맨틱 마크업과 도메인별 특화 레이아웃 해부


웹 표준과 검색엔진 최적화, 그리고 스크린 리더 접근성을 보장하기 위해 전체 구조는 구조적 의미를 지닌 HTML5 시맨틱 태그로만 쪼개어 배정했습니다. 

각 페이지는 크게 상단 고정 헤더(`<header class="main-header">`), 모바일 전용 오프캔버스 드롭다운 메뉴(`<aside class="mobile-menu">`), 실제 전공 콘텐츠가 전개되는 본문 영역(`<main>`), 그리고 라이선스 및 학과 정보를 명시하는 최하단 영역(`<footer>`)의 4단 레이어로 일관되게 파싱됩니다.



### ① 메인 대시보드 (index.html) 구조 설계


메인 페이지는 플랫폼의 정체성을 한눈에 보여주는 공간입니다. 상단 히어로 섹션(`<section id="home" class="hero-section">`)은 텍스트 중심의 좌측 콘텐츠와 시각적 몰입감을 주는 우측의 둥근 보안 백그라운드 그래픽 에셋으로 배치했습니다. 

이어서 프로젝트의 당위성을 설명하는 About 섹션과, 본 플랫폼의 심장부인 5대 보안 도메인으로 즉시 라우팅되는 링킹 시스템인 Core Security Domains 영역(`<section id="domains" class="grid-section">`)이 유기적으로 연결됩니다.



### ② 포너블 서브 페이지 (pwnable.html)의 메모리 세그먼트 시각화


시스템 해킹을 다루는 포너블 페이지는 하드웨어 및 운영체제 레벨의 개념이 등장하므로 마크업 설계부터 컴포넌트 구조를 특화했습니다. 


```html
<div class="memory-grid">
  <div class="memory-segment code-seg">
    <h3>Code (Text)</h3>
    <p>컴파일된 기계어 코드가 저장되며, 덮어쓰기를 막기 위해 Read/Execute 권한만 부여됩니다.</p>
  </div>
  <div class="memory-segment data-seg">
    <h3>Data / BSS</h3>
    <p>전역 변수와 정적 변수(Data) 및 초기화되지 않은 전역 변s(BSS)가 위치합니다.</p>
  </div>
  <div class="memory-segment heap-seg">
    <h3>Heap</h3>
    <p><code>malloc()</code>을 통해 동적으로 할당되는 영역으로, 낮은 주소에서 높은 주소로 확장됩니다.</p>
  </div>
  <div class="memory-segment stack-seg">
    <h3>Stack</h3>
    <p>지역 변수, 매개 변수, 반환 주소(Return Address)가 저장되며 높은 주소에서 낮은 주소로 확장됩니다.</p>
  </div>
</div>
```


가상 메모리 레이아웃을 직관적으로 이해할 수 있도록 `.memory-grid` 부모 컨테이너 내부에 각각의 메모리 구역(Code, Data, Heap, Stack)을 별도의 블록으로 분리했습니다. 

또한 취약 코드를 보여주기 위해 `<div class="code-box">` 컴포넌트를 설계하여, 상단 맥(Mac) 스타일의 3색 도트 장식(`red`, `yellow`, `green`)과 소스 파일명을 명시하는 `.filename` 레이어를 배치하고, 내부에는 가독성이 높은 고정폭 글꼴(Monospace) 기반의 `<pre><code>` 구문을 삽입하여 가독성을 확보했습니다.



### ③ 디지털 포렌식 서브 페이지 (forensics.html)의 수사 타임라인 컴포넌트


포렌식 도메인은 과학적 수사 절차와 연계보관성(Chain of Custody)의 순서가 핵심 마일스톤입니다. 이를 시각화하기 위해 수직형 흐름도인 `.process-timeline` 구조를 발굴하여 적용했습니다.


```html
<div class="process-timeline">
  <div class="process-step">
    <div class="step-number">01</div>
    <div class="step-content">
      <h3>사전 준비 (Preparation)</h3>
      <p>사건 발생 인지 후, 수사 권한을 확보하고 현장에 필요한 포렌식 장비와 분석 도구를 준비합니다.</p>
    </div>
  </div>
  </div>
```


의도적으로 부모 타임라인 컨테이너의 왼쪽 세로축에 CSS 가상 요소를 활용한 인프라 선을 그어두고, 각 수사 단계(`.process-step`)마다 절대 위치(`position: absolute`)로 배치된 동그란 순번 배지(`.step-number`)가 결합하여 스크롤 흐름에 따라 수사 단계를 직관적으로 읽어 내려갈 수 있는 수직적 레이아웃을 완성했습니다.



### ④ 팀 포트폴리오 (team.html)의 다차원 카드 컴포넌트


우리 팀의 기술적 스택과 비전을 투명하게 투영하기 위해 설계된 페이지입니다. `.team-profile-grid` 하위에 배치된 각 멤버의 프로필 카드(`.profile-card`)는 좌측의 인물 에셋 영역(`.profile-header`)과 우측의 서술형 커리어 레이어(`.profile-body`)로 완벽히 2분할됩니다. 


* **`.profile-header`:** 원형 크롭 처리된 프로필 이미지와 직책 배지(`<span class="leader-badge">`)가 결합되어 시각적 안정감을 부여합니다.
* **`.profile-body`:** 담당 분야의 타이틀, 연구 비전 에세이, 그리고 핵심 기술 스택을 토큰 형태로 쪼개어 보여주는 칩 형태의 레이아웃(`<div class="profile-skills">`)이 유기적으로 나열됩니다.
* **`.profile-footer`:** 우측 끝단 혹은 하단 래퍼에 개별 깃허브, 개발 블로그, 포트폴리오 링크를 아이콘 폰트와 결합하여 즉시 연결할 수 있도록 링크 인프라를 밀도 있게 집약했습니다.


---


## 3. CSS 디자인 시스템: 변수화 테마 및 고도화된 레이아웃 기술


본 플랫폼의 디자인 정체성은 '사이버 보안'이라는 차갑고 전문적인 감성을 프론트엔드 최신 표준 기술로 구현하는 데 있습니다. `style.css` 내부는 고정된 정적 수치를 배제하고, 철저히 전역 변수 시스템에 기반하여 컴포넌트 간 유기적 결합을 이끌어냈습니다.



### ① `:root` 커스텀 속성을 이용한 계층형 테마 아키텍처


플랫폼의 UI 톤앤매너를 지배하는 색상 자산은 시스템의 명도와 신뢰도에 따라 엄격하게 쪼개어 관리됩니다.


```css
:root {
  /* 배경 계층화 시스템 */
  --bg-dark: #0b0d14;    /* 전체 바디의 베이스가 되는 다크 심해 네이비 */
  --bg-card: #151828;    /* 섹션 및 카드 컴포넌트의 가시 영역 배경 */
  --bg-lighter: #1f233a; /* 마우스 호버 및 입력 필드 활성용 강조 배경 */

  /* 타이포그래피 컬러 가이드 */
  --text-main: #f1f5f9;  /* 장시간 열람 시 눈의 피로를 최소화하는 Off-White */
  --text-muted: #94a3b8; /* 주석, 메타 정보, 서브 타이틀용 슬레이트 그레이 */

  /* 사이버네틱 액센트 시스템 */
  --accent-cyan: #00d4ff;   /* 핵심 네온 시안 (Offensive 및 메인 포인트) */
  --accent-blue: #3b82f6;   /* 그라데이션 보조용 일렉트릭 블루 */
  --accent-purple: #a855f7; /* 특화 및 하이라이트 컴포넌트용 퍼플 */
  --accent-green: #10b981;  /* 보안 안전 및 방어 기법용 그린 */
  --accent-red: #ef4444;    /* 메모리 오염 및 취약점 경고용 레드 */

  /* 인프라 수치 및 효과 */
  --border-color: rgba(255, 255, 255, 0.08);
  --glass-bg: rgba(11, 13, 20, 0.85);
  --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  --nav-height: 75px;
}
```


이러한 변수화 구조 덕분에 중간고사 시점에 구축된 약 1,000줄에 육박하는 스타일 시트는 기말고사의 대규모 모달, 폼, 결과 대시보드 컴포넌트가 추가되었을 때에도 단 하나의 스타일 충돌 없이 완벽한 정체성을 공유할 수 있었습니다.



### ② 동적 배경 연산: Radial-Gradient 기반의 bgShift 애니메이션


사용자가 웹사이트에 접속했을 때 정적인 정체 상태를 느끼지 않도록, 컴퓨터의 연산 리소스를 최소화하면서도 웅장한 분위기를 내는 실시간 배경 애니메이션 레이어를 배치했습니다.


```css
.bg-gradient-overlay {
  position: fixed;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background:
    radial-gradient(circle at 50% 50%, rgba(0, 212, 255, 0.03) 0%, transparent 60%),
    radial-gradient(circle at 80% 20%, rgba(168, 85, 247, 0.03) 0%, transparent 50%);
  z-index: -1;
  animation: bgShift 25s infinite alternate ease-in-out;
}

@keyframes bgShift {
  0% { transform: scale(1) rotate(0deg); }
  100% { transform: scale(1.1) rotate(5deg); }
}
```


전체 뷰포트의 2배에 달하는 거대한 가상 레이어를 브라우저 백그라운드에 배치하고, `radial-gradient`로 은은한 시안색과 보라색 광원을 투사한 뒤, `transform: scale`과 `rotate` 연산을 25초 주기로 부드러운 베지어 곡선(`ease-in-out`)에 태워 구동시켰습니다. 

브라우저의 리페인팅(Repainting) 부하를 막기 위해 하드웨어 가속이 작용하는 `transform` 속성만을 이용해 연산 스케줄링을 최적화했습니다.



### ③ Glassmorphism 헤더 및 반응형 뷰포트 분기점 (Breakpoint) 제어


상단 메인 헤더(`.main-header`)에는 투명도 `0.85`를 가진 반투명 레이어를 깔아두고 최신 웹 표준 기술인 `backdrop-filter: blur(12px)`를 적용했습니다. 이로 인해 본문 콘텐츠가 네비게이션 영역 하단으로 스크롤되어 지나갈 때, 실시간으로 픽셀들이 수학적으로 흐림 연산되어 지나가는 유려한 UI 효과를 연출했습니다.


또한 태블릿과 모바일 뷰포트 환경에서 레이아웃이 무너지지 않도록 다단계 미디어 쿼리 구조를 설계했습니다.


```css
/* 태블릿 이하 해상도 (1024px) 분기 제어 */
@media (max-width: 1024px) {
  .split-grid { grid-template-columns: 1fr; gap: 30px; }
  .about-container { flex-direction: column; }
  .about-stats { width: 100%; }
}

/* 스마트폰 해상도 (768px) 분기 제어 */
@media (max-width: 768px) {
  .desktop-nav { display: none; } /* PC 네비게이션 전면 소멸 */
  .hamburger { display: block; }  /* 햄버거 토글 버튼 출현 */
  .hero-section { flex-direction: column; text-align: center; }
  .portfolio-grid { grid-template-columns: 1fr; }
  .bg-darker { padding: 30px 20px; }
}
```


1024px 구간에서는 좌우로 배치되던 레이아웃(`split-grid`)과 통계 박스들을 수직 정렬 축으로 변경하여 시선의 분산을 막았고, 768px 모바일 바운더리에 도달하면 상단 PC 내비게이션 바를 화면에서 완전히 소거하는 대신 우측 오프캔버스 사이드바 메뉴 인터페이스로 전환되도록 설계했습니다.


---


## 4. 자바스크립트 인프라 코어: DOM 제어 및 브라우저 최적화 메커니즘


중간고사 기간 동안 작성된 `script.js` 코어 로직은 사이트 전역의 사용성 편의(UX) 증대와 스크롤 연산 최적화에 모든 초점이 맞춰져 있습니다. 브라우저의 가용한 메인 스레드 리소스를 낭비하지 않기 위해 고성능 비동기 API들을 정교하게 결합했습니다.



### ① 오프캔버스 모바일 메뉴 제어와 이벤트 버블링 차단 알고리즘


모바일 환경에서 햄버거 버튼을 누르면 우측 숨겨진 공간에서 슬라이딩으로 메뉴판이 튀어나오고, 메뉴 영역 외부의 어두운 빈 공간을 터치하면 알아서 제자리로 돌아가는 '오프캔버스(Off-canvas)' 인터페이스 로직입니다.


```javascript
const hamburgerBtn = document.getElementById('hamburger-btn');
const closeBtn = document.getElementById('close-btn');
const mobileMenu = document.getElementById('mobile-menu');

if (hamburgerBtn && closeBtn && mobileMenu) {
  // 1. 메뉴 활성화 레이어 전개
  hamburgerBtn.addEventListener('click', (e) => {
    e.stopPropagation(); // 핵심: 이벤트 캡처링/버블링 전파를 물리적으로 단절
    mobileMenu.classList.add('active');
  });

  // 2. X 버튼 터치 시 비활성화
  closeBtn.addEventListener('click', () => {
    mobileMenu.classList.remove('active');
  });

  // 3. 이벤트 타겟 분석을 통한 외부 영역 선택 해제 (Dimmer dismiss)
  document.addEventListener('click', (e) => {
    if (
      mobileMenu.classList.contains('active') &&
      !mobileMenu.contains(e.target) &&   /* 클릭된 점이 메뉴 내부 노드가 아니고 */
      !hamburgerBtn.contains(e.target)    /* 클릭된 점이 햄버거 토글 버튼도 아닐 때 */
    ) {
      mobileMenu.classList.remove('active');
    }
  });
}
```


사용자가 햄버거 버튼을 클릭하는 순간 발생하는 클릭 이벤트는 DOM 트리를 타고 최상위 `document` 객체까지 올라갑니다(Event Bubbling). 만약 전파를 막지 않으면 버튼을 누르자마자 3번에 명시된 `document` 전역 리스너가 동시에 발동하여 메뉴가 열리자마자 다시 닫히는 심각한 UI 오동작이 발생합니다. 

이를 방지하기 위해 `e.stopPropagation()`으로 버블링 통로를 완전히 잠그고, 문서 전체 클릭 시에는 `contains` 메서드를 통해 실제 사용자의 터치 좌표가 모바일 메뉴 돔 트리 내부에 속해 있는지 수학적으로 논리 판별하여 외부 영역 클릭 시에만 안전하게 메뉴를 닫도록 설계했습니다.



### ② 현재 경로 자동 파싱 및 글로벌 내비게이션 바(GNB) 활성화


여러 개의 서브 페이지를 넘나들 때 사용자가 현재 자신이 머무는 학습 도메인을 직관적으로 알 수 있도록 상단 메뉴 탭에 실시간으로 빛을 주입하는 자동화 모듈입니다.


```javascript
// 현재 브라우저가 위치한 URL 세그먼트의 최하단 파일명 추출
const currentPath = window.location.pathname.split('/').pop();
const navLinks = document.querySelectorAll('.desktop-nav a, .mobile-nav-links a');

navLinks.forEach((link) => {
  const linkPath = link.getAttribute('href');
  if (!linkPath || linkPath.startsWith('#')) return; // 내부 페이지 앵커 링크 필터링

  link.classList.remove('active'); // 기존 주입된 active 클래스 소멸

  // 현재 브라우저 파일명과 HTML 메뉴 href 경로 매칭 연산
  if (currentPath === linkPath || (currentPath === '' && linkPath === 'index.html')) {
    link.classList.add('active');

    // 계층형 드롭다운 메뉴 내부에 속한 서브 링크인 경우
    const parentDropdown = link.closest('.dropdown');
    if (parentDropdown) {
      // 상위 최상위 부모 탭(예: 'Study') 요소도 동시에 찾아 active 클래스 강제 주입
      const parentLink = parentDropdown.querySelector('a');
      if (parentLink) parentLink.classList.add('active');
    }
  }
});
```


모든 HTML 페이지마다 일일이 클래스를 하드코딩해 두면, 메뉴 구조가 바뀌거나 파일명이 변경될 때 수십 개의 문서를 다 뜯어고쳐야 하는 재앙이 발생합니다. 

이 로직은 브라우저 런타임에 주소창의 물리 경로를 슬래시(`/`) 단위로 쪼개어 마지막 원소(예: `pwnable.html`)만 추출한 뒤, 페이지 내 존재하는 모든 앵커 태그들과 대조 연산을 수행합니다. 

특히 `closest('.dropdown')` 메서드를 사용해 현재 활성화된 페이지가 서브 카테고리 내부에 은닉되어 있다면, 상위 부모 메뉴판까지 역으로 추적하여 동시에 불을 켜 주도록 설계되어 고도의 레이아웃 편의성을 증명합니다.



### ③ Intersection Observer API 기반의 고성능 스크롤 페이드인 효과


플랫폼 전반의 콘텐츠 블록과 카드 컴포넌트들이 스크롤 흐름에 따라 순차적으로 위로 솟아오르며 페이드인되는 가속 애니메이션 엔진입니다. 


```javascript
const animatedElements = document.querySelectorAll(
  '.content-block, .grid-card, .profile-card, .tool-item, .memory-segment'
);

// 하드웨어 가속 트랜스폼 및 투명도 초기 상태 인라인 주입
animatedElements.forEach((el) => {
  el.style.opacity = '0';
  el.style.transform = 'translateY(40px)';
  el.style.transition = 'all 0.8s cubic-bezier(0.4, 0, 0.2, 1)';
});

const observerOptions = {
  threshold: 0.15,               /* 감시 대상 요소가 뷰포트에 15% 노출될 때 작동 */
  rootMargin: '0px 0px -50px 0px' /* 하단 마진을 50px 줄여 스크롤이 확실히 내려왔을 때 트리거 */
};

const scrollObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      // 뷰포트 교차 감지 시 투명도 및 위치 원상 복구로 애니메이션 트리거
      entry.target.style.opacity = '1';
      entry.target.style.transform = 'translateY(0)';
      
      // 쓰레기 메모리 누수 방지 및 리소스 확보를 위해 해당 요소 감시 즉시 종료
      scrollObserver.unobserve(entry.target);
    }
  });
}, observerOptions);

animatedElements.forEach((el) => scrollObserver.observe(el));
```


만약 과거의 방식대로 `window.addEventListener('scroll')` 루프 내부에서 전체 요소의 위치를 실시간 연산했다면, 스크롤 휠 작동 시 초당 수백 번의 메인 스레드 연산 오버헤드가 발생하여 모바일 기기에서 심한 버벅거림을 유발했을 것입니다. 

비동기 감지 엔진인 `IntersectionObserver`를 도입하여, 브라우저가 화면 렌더링 스케줄링을 자체 최적화하도록 유도했고, 애니메이션이 발동된 카드 요소는 `unobserve()`를 통해 감시 대상 목록에서 물리적으로 제거해 가비지 컬렉션(GC) 효율을 극대화했습니다.



### ④ requestAnimationFrame 기반의 초당 60프레임 동적 수치 카운트업


메인 페이지 통계 대시보드(`.about-stats`)가 스크롤에 의해 화면에 포착되는 시점에, 숫자가 0부터 부드럽게 증가하여 타겟 수치에 도달하는 정밀 프레임 제어 엔진입니다.


```javascript
const stats = document.querySelectorAll('.stat-num');
const statsContainer = document.querySelector('.about-stats');
let hasCounted = false; // 플래그 연산을 통한 중복 실행 차단

if (statsContainer && stats.length > 0) {
  const statObserver = new IntersectionObserver((entries) => {
    // 통계 컨테이너가 화면에 50% 이상 노출되었고, 아직 카운팅이 안 가동되었을 때
    if (entries[0].isIntersecting && !hasCounted) {
      stats.forEach((stat) => {
        const targetText = stat.innerText;
        const isPercentage = targetText.includes('%');
        const targetNumber = parseInt(targetText.replace(/[^0-9]/g, '')); // 숫자 자산만 추출
        
        let currentCount = 0;
        const duration = 2000; // 정확히 2000ms(2초) 동안 가동
        const increment = targetNumber / (duration / 16.6); // 60fps 기준 프레임당 정밀 증가분 산출

        // 디스플레이 주사율과 완벽히 스케줄링되는 재귀 카운트 루프
        const updateCount = () => {
          currentCount += increment;
          if (currentCount < targetNumber) {
            stat.innerText = Math.ceil(currentCount) + (isPercentage ? '%' : '');
            requestAnimationFrame(updateCount); // 브라우저가 다음 프레임을 그릴 준비가 되었을 때 재귀 호출
          } else {
            stat.innerText = targetNumber + (isPercentage ? '%' : ''); // 최종 수치 강제 고정
          }
        };
        updateCount();
      });
      hasCounted = true; // 무한 스크롤 시 재트리거 방지용 락킹
    }
  }, { threshold: 0.5 }); // 50% 임계값 설정

  statObserver.observe(statsContainer);
}
```


자바스크립트의 표준 타이머인 `setInterval`이나 `setTimeout`은 자바스크립트 엔진의 이벤트 루프(Task Queue) 구조상 지연 시간이 누적되므로 프레임이 밀리거나 뚝뚝 끊기는 결함이 존재합니다. 

디스플레이 주사율 타임라인에 맞춰 콜백 함수를 실행해 주는 브라우저 원형 API인 `requestAnimationFrame`을 사용하고, 증가분을 초당 60프레임 기준 수식(`duration / 16.6`)으로 정밀 분할 연산하여, 어떠한 사양의 디바이스에서도 눈이 편안한 부드러운 숫자 애니메이션을 구현해 냈습니다.


---


## 5. 프로젝트 종합 회고 및 기말고사 고도화 엔진으로의 링킹 구조


이번 중간고사 마일스톤은 프론트엔드의 이론적 최적화 기법들과 시맨틱 구조 설계를 실전 웹 빌드 프로세스에 투영해 볼 수 있었던 매우 뜻깊은 이정표였습니다. 

특히 5대 보안 도메인의 방대한 지식을 훼손하지 않으면서도, 다크 테마와 글래스모피즘 시스템 하에 일관된 컴포넌트로 녹여내는 퍼블리싱 과정은 웹 프론트엔드 아키텍처에 대한 이해도를 한 단계 격상시켰습니다.


성능 최적화 관점에서도 브라우저의 연산 레이어 구조를 명확히 파악하고 `IntersectionObserver` 및 `requestAnimationFrame` 같은 고성능 브라우저 API를 적재적소에 배치하여, 화려한 시각적 인터랙션을 양산하면서도 메모리 누수와 메인 스레드 낭비를 완벽히 제어해 낸 점은 큰 기술적 성과입니다.


이렇게 구축된 견고하고 정밀한 프론트엔드 인프라가 존재했기에, 이어지는 기말고사 기간에 탑재된 **"LocalStorage 기반의 독립형 회원 세션 관리 인프라"**, **"fflate와 DecompressionStream 바이너리 버퍼 파서를 이용한 클라이언트 사이드 옵시디언 볼트(ZIP) 분석 엔진"**, 그리고 **"XSS 인젝션 위협을 원천 방어하는 가상 DOM 마크다운 시큐어 렌더러"**와 같은 복잡하고 딥(Deep)한 자바스크립트 비즈니스 로직들이 단 하나의 아키텍처 수정 없이 완벽하게 탑재되어 구동될 수 있었습니다. 

InfoSec Hub는 단순한 학부 과제 결과물을 넘어, 웹 프론트엔드 엔지니어링과 사이버 보안 전공 지식이 완벽하게 결합된 하나의 실전형 웹 아카이브 솔루션으로 진화해 나갈 것입니다.

## 6. 기말고사 (Phase 2): 브라우저 엔진 기반의 고급 동적 로직 탑재


중간고사 마일스톤을 통해 어떤 환경에서도 레이아웃이 무너지지 않는 견고한 'UI/UX 도화지'를 완성했다면, 기말고사 기간에는 브라우저 자체의 잠재력을 한계까지 끌어올려 별도의 서버 없이도 독립적으로 구동되는 **'고급 동적 웹 비즈니스 로직'**을 연동하는 데 모든 전력을 다했습니다. 

보안 전공자들이 지식 관리를 위해 가장 애용하는 **옵시디언(Obsidian) 볼트 데이터**를 외부 서버로 단 1바이트도 전송하지 않고, 브라우저 샌드박스 내부에서 고속 해제하여 지식 통계를 다차원 대시보드로 산출해 주는 지능형 모듈을 포함해, 기말고사 기간에 새롭게 탑재된 3가지 핵심 기능의 설계 아키텍처와 시큐어 코딩 명세를 상세히 해부합니다.



### ① LocalStorage 기반의 독립형 회원가입 및 로그인 인증 시스템


기존의 아카이브는 누구나 접근하여 모든 서브 페이지를 열람할 수 있는 정적 구조였습니다. 하지만 각 사용자별로 자신의 옵시디언 볼트 파일을 업로드하고 개인 맞춤형 지식 분석 흐름(Workflow)을 연동하기 위해서는, 사용자별 세션을 격리하여 화면을 제어할 필요성이 대두되었습니다. 

별도의 백엔드 데이터베이스 없이도 완벽한 독립형 인증 경험을 구현하기 위해, 브라우저의 영속성 저장소인 `localStorage`를 가상 데이터베이스 레이어로 활용하여 사용자 계정 정보를 안전하게 관리하는 아키텍처를 구축했습니다.


```javascript
// script.js - 회원가입 및 로그인 데이터 관리 코어
const authKey = 'infosecHubUser';   /* 현재 세션의 활성 로그인 유저 키 */
const usersKey = 'infosecHubUsers'; /* 로컬 가입자 가상 DB 풀 키 */

// 가입자 풀 배열 로드 함수
const getStoredUsers = () => {
  try {
    const users = JSON.parse(localStorage.getItem(usersKey));
    return Array.isArray(users) ? users : [];
  } catch {
    return [];
  }
};
```


인증 상태의 변화에 따른 UI 가시성 제어는 `updateAuthUi()` 함수를 핵심 거점으로 삼아 돔 트리(DOM Tree) 전체를 실시간 동기화하도록 설계했습니다. 

사용자가 로그인하지 않은 상태일 경우, 메인화면의 업로드 드롭존 컨테이너(`.upload-panel`)에 `.locked` 클래스를 부여하여 시각적인 블러 및 비활성화 효과를 적용하고, 실제 파일 인젝션 노드인 `<input type="file" id="vault-upload">`에 `disabled` 속성을 강제 주입하여 로그인 전 물리적인 파일 입력을 원천적으로 차단합니다. 


```javascript
// script.js - 로그인 세션 상태와 UI 가시성 동적 동기화 로직
const updateAuthUi = () => {
  const user = getUser();
  const isLoggedIn = Boolean(user?.name);

  if (authStatus) {
    authStatus.classList.toggle('logged-in', isLoggedIn);
    authStatus.innerHTML = isLoggedIn
      ? `<i class="fas fa-user-check"></i><span>${escapeHtml(user.name)}님 로그인됨</span>`
      : '<i class="fas fa-user-lock"></i><span>로그인이 필요합니다</span>';
  }

  // 세션 유무에 따라 파일 업로드 패널의 하드웨어 잠금/해제 동적 제어
  if (uploadPanel && vaultUpload && uploadMessage) {
    uploadPanel.classList.toggle('locked', !isLoggedIn);
    vaultUpload.disabled = !isLoggedIn;
    uploadMessage.textContent = isLoggedIn
      ? 'ZIP 파일을 선택하거나 드롭존을 눌러 업로드하세요.'
      : '로그인하면 업로드가 활성화됩니다.';
  }
};
```


로그인에 성공하면 사용자의 입력 문자열을 안전하게 이스케이프(`escapeHtml`) 처리한 후 세션 상태 배지에 동적으로 바인딩하며 대시보드의 잠금을 해제합니다. 인증 모드 전환 시에는 비밀번호 확인 필드 노드를 감지하여 `required = true` 속성을 유동적으로 주입·제거하는 돔 제어 설계를 통해 사용자 편의성을 확보했습니다.



### ② 클라이언트 사이드 Obsidian Vault ZIP 업로드 및 지식 분석 엔진


기말 프로젝트의 기술적 집약체로, 사용자가 자신의 전체 옵시디언 노트를 패키징한 ZIP 파일을 업로드하면 자바스크립트가 비동기 Promise 파이프라인을 전개하여 실시간 통계를 도출합니다.




```javascript
// script.js - 바이너리 압축 해제 메커니즘 (fflate & Native Fallback 이중 구조)
async function parseMarkdownFilesFromZip(file) {
  const buffer = await file.arrayBuffer(); /* 파일 스트림을 바이너리 ArrayBuffer로 변환 */

  // 1순위: fflate 고속 인메모리 디컴프레션 파서 가동
  if (window.fflate?.unzipSync) {
    const decoder = new TextDecoder('utf-8');
    const files = window.fflate.unzipSync(new Uint8Array(buffer));
    return Object.entries(files)
      .filter(([path]) => path.toLowerCase().endsWith('.md'))
      .map(([path, bytes]) => ({
        path: path.replace(/\\/g, '/'),
        name: path.split('/').pop(),
        text: decoder.decode(bytes),
      }));
  }

  // 2순위 Fallback: 브라우저 API 기반 수동 센트럴 디렉터리 바이트 파싱
  const entries = readZipCentralDirectory(buffer).filter(
    (entry) => !entry.isDirectory && entry.name.toLowerCase().endsWith('.md')
  );
  // ... DecompressionStream('deflate-raw')를 이용한 청크 바이너리 해제
}
```


네트워크 단절이나 라이브러리 로드가 실패하더라도 시스템이 마비되지 않도록, 브라우저 원형 API를 결합한 자체 2순위 폴백 구조를 설계했습니다. 

ZIP 포맷 최하단의 EOCD 매직 시그니처(`0x06054b50`)를 역추적하여 파일 헤더들의 오프셋을 계산한 뒤, 브라우저 내장 스트림인 `DecompressionStream('deflate-raw')`에 밀어 넣어 순수 자바스크립트만으로 원형 바이트를 성공적으로 복원해 냅니다. 추출된 스트림은 `TextDecoder('utf-8')`을 거쳐 마크다운 텍스트 노트 배열로 최종 변환됩니다.


분석 알고리즘인 `scoreCategories`는 각 보안 분야의 핵심 키워드를 기반으로 텍스트의 연관성을 도출합니다. 


```javascript
// script.js - 가중치 기반 학습 분야 자동 분류 알고리즘
const scoreCategories = (text) => {
  const lowerText = text.toLowerCase();

  const scored = Object.entries(categoryKeywords).map(([name, words]) => {
    const score = words.reduce((sum, word) => {
      const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const matches = lowerText.match(new RegExp(escaped, 'gi'));
      return sum + (matches ? matches.length : 0);
    }, 0);
    return { name, score };
  });

  const maxScore = Math.max(...scored.map((item) => item.score), 1);
  return scored
    .map((item) => ({ ...item, percent: Math.round((item.score / maxScore) * 100) }))
    .sort((a, b) => b.score - a.score); /* 최다 출현 카테고리 정렬 */
};
```


마지막으로, 미리보기 패널에 렌더링할 때는 XSS 방어를 위해 `document.createElement('template')` 샌드박스 내부에서 유해 태그를 소거하고 모든 `on*` 이벤트 핸들러를 삭제하는 브라우저 인메모리 트리 새니타이저를 거치도록 하였습니다.



### ③ 고속 지능형 스크롤 제어 내비게이션 콘솔


전체 페이지 깊이가 깊어짐에 따라, 사용자가 신속하게 원하는 지점으로 이동할 수 있는 스마트 플로팅 컨트롤러를 설계했습니다.


```javascript
// script.js - 글로벌 하강 스크롤 컨트롤 엔진
const updateScrollDownBtn = () => {
  const scrollBottom = window.scrollY + window.innerHeight;
  const pageHeight = document.documentElement.scrollHeight;

  // 디스플레이 하단이 푸터 근처에 도달하면 버튼 숨김
  scrollDownBtn.classList.toggle('is-hidden', scrollBottom >= pageHeight - 120);
};

window.addEventListener('scroll', updateScrollDownBtn);
```


이 컨트롤러는 현재 스크롤 위치(`window.scrollY`)와 창의 높이(`window.innerHeight`)를 연산하여 가시 화면 최하단 좌표를 실시간으로 추적합니다. 문서의 전체 높이(`scrollHeight`)와 비교하여 사용자가 하단에 도달했음을 감지하면 버튼의 투명도를 조정하고, `pointer-events: none`을 통해 UI 간섭을 논리적으로 차단합니다. 

상향 스크롤 버튼 또한 상단에서 300px 이상 진입 시 등장하도록 설계하고, 클릭 시 `window.scrollTo({ behavior: 'smooth' })`를 사용하여 부드러운 화면 전환을 제공합니다.



---


## 7. 학기말 최종 개발 회고


이번 프로젝트는 **중간고사 기간 동안 다져놓은 견고한 마크업 및 스타일 시스템 설계가, 기말고사의 고밀도 자바스크립트 로직과 결합할 때 얼마나 큰 시너지를 내는지** 증명한 여정이었습니다.

중간고사 단계에서 CSS 변수 모델을 철저히 모듈화하고 최적화 구조를 안착시켜 놓았기에, 기말고사 기간에는 바이너리 스트림 처리, 다중 압축 해제 폴백 알고리즘, 그리고 XSS 방어를 위한 돔 트리밍 처리라는 고부하 비즈니스 로직 연동에만 모든 개발 화력을 집중할 수 있었습니다. 

우리가 완성한 InfoSec Hub 플랫폼은 훌륭한 허브가 된것같습니다. 앞으로 더욱 진화된 보안 관제 아카이브로 발전시켜 나갈 것입니다.