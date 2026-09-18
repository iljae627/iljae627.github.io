---
title: "[Mission #62] Threat Intelligence 시작하기 — Kimsuky와 Konni는 같은 조직일까"
date: 2026-09-18 01:00:00 +0900
categories: [CTF/Wargame, 리서치]
tags: [threat-intelligence, apt, kimsuky, konni, babyshark, osint, malware, attribution, 북한]
mermaid: true
---

## 1. 들어가며

이번 미션은 두 보안 보고서에 등장하는 공격자를 각각 찾아낸 뒤, 최초로 이름이 붙은 자료와 두 집단의 관계를 추적하는 위협 인텔리전스 입문 과제다.

- 자료 A: Huntress, [Targeted APT Activity: BABYSHARK Is Out for Blood](https://www.huntress.com/blog/targeted-apt-activity-babyshark-is-out-for-blood)
- 자료 B: AhnLab ASEC, [개인정보 유출 관련 내용으로 위장한 피싱 메일 유포 (Konni)](https://asec.ahnlab.com/ko/59625/)

처음 자료를 읽었을 때는 P를 **Kimsuky(김수키)**, Q를 **Konni(코니)**라고 적으면 끝날 줄 알았다. 그런데 원문을 다시 읽으니 그렇게 단정하기에는 문제가 있었다. 자료 A의 Huntress는 공격자를 Kimsuky라고 부르지 않고 **BABYSHARK를 사용하는 북한 국가 지원 행위자**라고만 적었다. 반면 자료 B의 ASEC은 Q를 **Konni 공격 그룹**이라고 명시한다. 결국 P의 정확한 세부 행위자명은 미확정이고, Kimsuky는 P를 설명하기 위해 검토할 수 있는 상위 분류 중 하나라고 정리했다.

이 차이를 놓치면 악성코드명, 캠페인명, 행위자명을 같은 것으로 취급하게 된다. KONNI도 처음부터 조직명이 아니었고, BABYSHARK 역시 행위자가 아니라 악성코드 이름이었다.

따라서 단순히 이름을 검색해 같은 그룹이라고 결론 내리지 않고 다음 순서로 자료를 확인했다.

```mermaid
flowchart LR
    A[자료 A·B 읽기] --> B[악성코드와 행위자 구분]
    B --> C[최초 명명 보고서 확인]
    C --> D[코드·TTP·표적 비교]
    D --> E[C2·운영 인프라 비교]
    E --> F[확신도와 미해결점 기록]
```

## 2. 자료 A의 공격자 P: BABYSHARK 사용 DPRK 행위자

![Huntress BABYSHARK 원문 확인](/assets/img/mission-62-threat-intelligence/04-huntress-babyshark.png)
_자료 A 원문. 북한 관련 싱크탱크를 겨냥한 BABYSHARK 침해사고를 다룬다._

Huntress가 조사한 사건은 핵·국가안보 관련 싱크탱크를 겨냥한 북한 연계 사이버 첩보 활동이다. 공격자는 실제 미국의소리(VOA) 관계자인 것처럼 접근해 먼저 대화를 나눴다. 신뢰를 얻은 뒤 “수정본”이라며 암호가 걸린 ZIP과 매크로 포함 Word 문서를 보냈다.

감염 후에는 다음 행위가 이어졌다.

- VBScript와 예약 작업으로 지속성 유지
- 레지스트리에 난독화된 스크립트 저장
- Google Drive와 OneDrive를 페이로드 전달에 악용
- `certutil`을 이용한 데이터 인코딩과 유출
- OneDrive의 `version.dll` 로딩을 이용한 DLL 하이재킹
- `johnbegin`과 `johnend` 사이에 암호화된 데이터를 저장
- 특정 사용자 이름에서만 실행되도록 제한

Huntress 원문은 행위자를 곧바로 Kimsuky라고 단정하지 않고 “북한 국가 지원 행위자”와 BABYSHARK 악성코드로 설명한다. BABYSHARK를 처음 공개한 [Palo Alto Networks Unit 42 보고서](https://unit42.paloaltonetworks.com/new-babyshark-malware-targets-u-s-national-security-think-tanks/)도 KimJongRAT·STOLEN PENCIL과의 연결 및 자원 공유 가능성을 제시했을 뿐, 당시 본문에서 Kimsuky라는 이름을 직접 쓰지는 않았다.

현재 [MITRE ATT&CK의 Kimsuky 항목](https://attack.mitre.org/groups/G0094/)은 BABYSHARK를 Kimsuky가 사용하는 소프트웨어로 분류한다. 이것은 P를 Kimsuky 맥락에서 살펴볼 근거는 되지만, MITRE의 소프트웨어 매핑만으로 Huntress가 본 2021년 침해의 세부 운영자까지 확정되는 것은 아니다. 그래서 이 글에서는 P를 **“BABYSHARK를 사용한 DPRK 연계 행위자”**로 두고, Kimsuky는 가능한 상위 활동 집합으로 다룬다.

![MITRE ATT&CK Kimsuky 그룹 항목](/assets/img/mission-62-threat-intelligence/07-mitre-kimsuky.png)
_MITRE ATT&CK은 Kimsuky를 G0094로 관리하며 여러 연구사의 별칭을 함께 제시한다._

## 3. P와 관련해 살펴본 Kimsuky 명명 계보

공개적으로 Kimsuky라는 이름을 사용한 초기 원전은 Kaspersky가 2013년 9월 11일 공개한 [The “Kimsuky” Operation: A North Korean APT?](https://securelist.com/the-kimsuky-operation-a-north-korean-apt/57915/)다.

![Kaspersky Kimsuky 최초 보고서](/assets/img/mission-62-threat-intelligence/01-kimsuky-first-report.png)
_2013년 Kaspersky의 최초 Kimsuky 보고서. 당시부터 한국의 싱크탱크가 핵심 표적이었다._

Kaspersky가 확인한 표적은 세종연구소, 한국국방연구원, 통일부, 현대상선과 통일 관련 단체 등이었다. 악성코드는 키로깅, 디렉터리 목록 수집, HWP 문서 탈취, 원격 제어 모듈 설치 기능을 갖췄다. C2 통신에는 불가리아 공개 메일 서비스인 `mail.bg`를 사용했으며, 변조한 TeamViewer도 원격 제어 도구로 이용했다.

이름의 직접적인 단서는 드롭박스용 Hotmail 계정 등록명이었다.

```text
iop110112@hotmail.com -> kimsukyang
rsh1213@hotmail.com   -> Kim asdfa
```

Kaspersky는 이 등록명이 실제 공격자 이름이라고 확신할 수 없으며, 조사자를 북한 방향으로 유도하기 위한 정보일 수도 있다고 명시했다. 즉 **Kimsuky라는 이름의 출발점과 북한 귀속 판단은 서로 다른 수준의 증거**다.

북한 연계 판단에는 다음 정보가 함께 사용됐다.

- 한국어가 포함된 컴파일 경로 `D:\rsh공격\UAC_dll(완성)\Release\test.pdb`
- 외교·국방·통일 정책과 관련된 한국 기관 중심의 피해자 구성
- 중국 지린성·랴오닝성 대역에서 관찰된 운영 IP 10개
- HWP 문서와 AhnLab 제품 등 한국 환경에 특화된 기능

최초 보고서가 등록명 하나로 배후를 확정하지 않고 반증 가능성까지 남긴 점이 인상적이었다.

## 4. 자료 B의 공격자 Q: Konni

![ASEC Konni 분석 원문](/assets/img/mission-62-threat-intelligence/05-asec-konni.png)
_자료 B 원문. 개인정보 유출 자료로 위장한 실행 파일을 Konni 그룹의 공격으로 분류했다._

ASEC은 개인정보 유출 관련 자료로 위장한 악성 EXE가 개인을 대상으로 유포된 사건을 **Konni 공격 그룹**의 활동으로 분류했다. 악성 파일을 실행하면 `.data` 섹션의 구성 요소가 `%ProgramData%` 아래에 생성된다. 이후 C2에서 난독화된 명령을 받아 XML 형식으로 실행하는 백도어로 동작한다.

당시에는 C2가 닫혀 있어 ASEC이 최종 행위까지 확인하지 못했다. 따라서 이 사례의 귀속은 공격 전 과정을 실시간으로 지켜본 결과라기보다 확보한 악성코드, 실행 흐름과 과거 Konni 지표를 비교해 같은 활동 묶음으로 판단한 결과로 이해했다.

## 5. KONNI라는 이름을 처음 붙인 자료

KONNI라는 이름을 처음 붙여 공개한 원전은 Cisco Talos가 2017년 5월 3일 작성한 [KONNI: A Malware Under The Radar For Years](https://blog.talosintelligence.com/konni-malware-under-radar-for-years/)다. 보고서에는 “Talos has named this malware KONNI”라고 명시되어 있다.

![Cisco Talos KONNI 최초 보고서](/assets/img/mission-62-threat-intelligence/03-konni-first-report.png)
_KONNI라는 이름을 붙인 2017년 Cisco Talos 보고서. 분류도 그룹이 아니라 RAT이다._

여기서 중요한 점은 **KONNI가 처음에는 공격 조직명이 아니라 RAT 악성코드 이름이었다**는 것이다. [MITRE ATT&CK도 KONNI를 그룹이 아닌 Software S0356](https://attack.mitre.org/software/S0356/)으로 등록하고 있다.

Talos는 2014년부터 2017년까지의 네 캠페인을 비교했다.

| 시기 | 관찰 내용 |
|---|---|
| 2014 | 키 입력, 클립보드, 브라우저 프로필·쿠키를 훔치는 정보 탈취 도구 |
| 2016 | EXE와 DLL로 구조가 분리되고 업로드·다운로드·명령 실행 기능 추가 |
| 2017 | 화면 캡처, 시스템 정보 수집을 포함한 RAT 기능 확장 |

공통적으로 이메일 첨부파일과 `.scr` 실행 유도, 미끼 문서 표시를 사용했다. 인프라는 무료 웹호스팅인 `000webhost`를 이용했고, 2017년 미끼 문서에는 UN·UNICEF·대사관 등 북한 관련 기관의 연락처가 들어 있었다.

Talos는 당시 운영자의 국가나 기존 APT 그룹을 확정하지 않았다. 이후 보안업체들이 KONNI 악성코드를 사용하는 캠페인과 운영자 클러스터를 “Konni Group”으로 부르면서 악성코드명과 행위자명이 겹치게 됐다.

## 6. P와 Q를 연결할 수 있을까

먼저 두 출발 보고서만 나란히 놓고 봤다. A의 C2는 `hodbeast[.]com`, `worldinfocontact[.]club`, `frebough[.]com` 등이었다. B는 분석 당시 C2가 닫혀 있어 최종 명령과 후속 인프라를 확인하지 못했다. **A와 B의 정확한 두 사건 사이에서 같은 도메인·IP·인증서가 재사용됐다는 공개 근거는 찾지 못했다.** 비슷한 피싱과 스크립트를 썼다는 이유만으로 같은 팀이라고 하기에는 부족했다.

그 다음 더 넓은 클러스터 관계를 확인했다. 이스트시큐리티 ESRC의 2019년 [APT 캠페인 'Konni' & 'Kimsuky' 조직의 공통점 발견](https://www.estsecurity.com/enterprise/security-center/notice/view/434)은 Konni와 Kimsuky로 분류한 여러 과거 캠페인의 중복을 비교한다. 다만 아래 근거들은 자료 A와 B의 해당 샘플을 직접 비교한 결과가 아니라, **더 넓은 Konni–Kimsuky 활동 집합에서 발견된 연결점**이다.

![ESRC Konni Kimsuky 연관성 보고서](/assets/img/mission-62-threat-intelligence/06-esrc-link-report.png)
_두 클러스터의 코드·도구·인프라 중복을 분석한 ESRC 보고서._

### 6.1 악성코드 구현의 중복

ESRC가 Konni와 Kimsuky의 Cobra Venom 계열 샘플을 비교했을 때 다음 항목이 겹쳤다.

| 구분 | 관찰된 연결점 | 판단 |
|---|---|---|
| 파일명 | `ChromSrch.dat` 동일 | 단독으로는 약한 증거 |
| 압축 | 암호화 압축과 설정 암호가 일치 | 강한 증거 |
| 바이너리 | `EngineDropperDll.dll` 익스포트명 일치 | 강한 증거 |
| 실행 인자 | `insrchmdl` 파라미터 일치 | 강한 증거 |
| 암호화 | 데이터 복호화 루틴 일치 | 매우 강한 증거 |
| 최종 페이로드 | `Gongstrong` 문자열의 커스텀 TeamViewer | 매우 강한 증거 |

파일명 하나는 누구나 복사할 수 있다. 그러나 같은 파일명과 압축 암호, 익스포트 함수, 인자, 복호화 구현, 최종 페이로드가 한꺼번에 겹친다면 우연일 가능성은 훨씬 낮아진다.

특히 커스텀 TeamViewer가 눈에 띄었다. 2013년 Kaspersky 보고서의 Kimsuky도 변조 TeamViewer를 사용했다. ESRC는 Konni 계열 Babyface RAT의 후속 단계와 Kimsuky HWP 공격에서 `Gongstrong` 문자열이 있는 같은 계열의 커스텀 TeamViewer가 사용됐고, 최종 페이로드 기능도 일치한다고 분석했다.

### 6.2 공격 방식과 표적의 중복

두 클러스터에서 반복된 특징은 다음과 같다.

- 표적형 이메일과 관계 형성형 사회공학
- 북한·통일·외교·국방·인권 분야 관계자 표적화
- 정상 문서를 보여 주면서 백그라운드에서 악성코드 실행
- Word·HWP·스크립트·DLL을 조합한 다단계 감염
- 탈취한 웹사이트 또는 무료 호스팅을 유포지와 C2로 사용
- 한국어 환경과 국내 웹 생태계에 대한 높은 이해
- 암호화폐 분야로 공격 범위 확대

표적과 TTP가 비슷하다는 사실만으로 같은 팀이라고 할 수는 없다. 같은 국가의 여러 팀이 임무나 교육 자료, 공개 도구를 공유할 수 있기 때문이다. 이 항목은 코드와 인프라 증거를 보조하는 정황으로 보았다.

### 6.3 인프라와 운영 흔적

ESRC 보고서에는 더 직접적인 연결점도 등장한다.

| Konni | Kimsuky | 연결 내용 |
|---|---|---|
| `naoei3-tosma.96[.]lt` | `naver-security-mail.96[.]lt` | 같은 무료 호스팅 계열과 유사 작명 |
| `naiei-aldiel.16mb[.]com` | `carolie-svr-v1.16mb[.]com` | 같은 호스팅 도메인 사용 |
| `upgradesrv.890m[.]com` | `oeks39402.890m[.]com` 등 | 같은 호스팅 계열 |
| `202.168.155[.]156` | `202.168.155[.]156` | 운영 IP가 정확히 일치 |

그 밖에도 Kimsuky C2에서 같은 `b374k` 웹셸, `victory` 계열 비밀번호와 PHP 메일 발송 도구가 반복됐다. Konni 문서에서 쓰인 `filer1.1apps[.]com` C2도 다른 연결 캠페인에서 재사용됐다.

IP 하나나 무료 호스팅 업체 하나가 겹치는 것은 공유 VPN, 감염 서버, 호스팅 재판매 때문에 생길 수 있다. 하지만 코드·암호·커스텀 도구·인프라가 동시에 겹친다면 동일 운영 생태계를 가리킬 가능성이 높다.

### 6.4 활동 시기와 분류 변화

```mermaid
timeline
    title Kimsuky·Konni 공개 활동 연표
    2013 : Kaspersky가 Kimsuky 작전 공개
    2014 : Talos가 나중에 KONNI로 묶은 첫 캠페인
    2017 : Talos가 RAT에 KONNI 이름 부여
    2018 : Konni·Kimsuky 관련 샘플과 인프라 중복 관찰
    2019 : ESRC가 두 클러스터의 공통점 공개
    2021 : ESRC가 Konni를 Thallium/Kimsuky로 통합 분류
    2023 : ASEC이 개인정보 유출 미끼 사건을 Konni로 분류
```

ESRC는 2021년 [코니(Konni)조직을 탈륨(Thallium)으로 통합 분류](https://direct.estsecurity.com/public/security-center/notice/view/14394?category-id=6)한다고 발표했다. Thallium은 당시 Microsoft가 사용한 Kimsuky 계열 명칭이다.

그러나 모든 연구기관이 완전히 같은 분류를 사용하지는 않는다. MITRE의 [KONNI 항목](https://attack.mitre.org/software/S0356/)은 북한 연계 캠페인과 NOKKI 코드 중복을 설명하면서 APT37 연결 가능성도 함께 남긴다. 같은 샘플을 어느 범위의 그룹으로 묶을지는 연구사가 가진 가시성과 분류 기준에 따라 달라질 수 있다.

### 6.5 Proofpoint의 TA406·TA427 분류

관계를 이해하는 데 가장 도움이 된 자료는 Proofpoint의 2021년 [Triple Threat: North Korea-Aligned TA406 Scams, Spies, and Steals](https://www.proofpoint.com/au/blog/threat-insight/triple-threat-north-korea-aligned-ta406-scams-spies-and-steals)였다. Proofpoint는 공개적으로 Kimsuky·Thallium·Konni Group이라고 불리는 넓은 활동을 하나로 뭉치지 않고 **TA406, TA408, TA427**로 나누어 추적한다.

- TA406은 공개 자료에서 Kimsuky·Thallium·Konni Group으로 추적되는 활동의 일부로 평가한다.
- TA406은 KONNI, SANNY, CARROTBAT/CARROTBALL뿐 아니라 BABYSHARK에도 접근한 것으로 본다.
- 그러나 Proofpoint는 TA406이 BABYSHARK의 최초 사용자는 아니라고 설명한다.
- TA427 역시 별도의 하위 행위자로서 BABYSHARK를 사용했다.

이 분류를 따르면 Konni로도 불리는 TA406과 BABYSHARK 사용이 관찰된 TA427은 넓은 Kimsuky 우산 아래 존재하지만, **서로 구분되는 행위자**다. 즉 도구 접근과 상위 생태계의 관계는 설명할 수 있어도, Huntress 사건의 P가 곧 TA406 또는 Konni라는 결론은 나오지 않는다.

Palo Alto Networks도 [The Fractured Statue Campaign](https://unit42.paloaltonetworks.com/the-fractured-statue-campaign-u-s-government-targeted-in-spear-phishing-attacks/)에서 Konni가 원래 RAT 이름이었으나, KONNI RAT 없이도 TTP가 겹치는 후속 활동이 나타나면서 연구자들이 운영자를 Konni Group이라고 부르게 됐다고 설명한다. 동시에 공개된 TTP를 모방한 복제나 false flag 가능성 때문에 해당 캠페인의 Konni 귀속을 **moderate confidence**로 제한했다. 이 대목 때문에 나도 코드와 전술이 비슷하다는 이유만으로 관계를 확정하지 않기로 했다.

## 7. 최종 판단

조사 초반에는 ESRC의 코드와 인프라 중복을 보고 “Konni는 Kimsuky의 하위 조직”이라고 결론을 내렸다. 하지만 A와 B의 정확한 두 사건을 다시 구분하고 Proofpoint와 MITRE의 분류까지 비교하니 그 문장은 너무 강했다.

수정한 결론은 다음과 같다.

> **P와 Q가 같은 조직이라고 확정할 근거는 부족하다. 둘 다 DPRK 연계 활동이라는 점은 강하게 뒷받침되며, Proofpoint의 분류를 채택하면 Kimsuky라는 넓은 생태계 안에서 도구와 개발 자원을 공유했을 가능성은 있다. 그러나 P의 정확한 하위 행위자는 미확정이고, A와 B 사이의 직접 인프라 재사용도 확인되지 않았다.**

확신도를 나누면 다음과 같다.

| 판단 | 확신도 | 이유 |
|---|---|---|
| 두 활동 모두 북한 연계 | 높음 | 장기간 반복된 표적·언어·작전 목적과 다수 기관 분석 |
| Proofpoint 분류를 전제로 한 상위 생태계 관계 | 중간 | TA406·TA427을 Kimsuky 아래 별도 행위자로 추적하며 BABYSHARK 접근도 관찰 |
| Huntress 사건 P의 정확한 세부 귀속 | 낮음/미확정 | Huntress는 Kimsuky·TA427·TA406 중 하나를 직접 명시하지 않음 |
| 자료 A와 B의 동일 세부 운영팀 | 낮음 | 동일 C2·IP·인증서 등 직접 인프라 연결을 확인하지 못함 |

따라서 `Kimsuky = Konni` 또는 `P = Kimsuky`라고 등호를 긋기보다, **벤더별로 경계가 다른 DPRK 연계 클러스터이며 일부 도구·개발 자원의 공유 가능성이 관찰된다**고 쓰는 편이 정확하다고 생각한다.

## 8. 조사하면서 새로 알게 된 점

### 악성코드명과 행위자명은 다르다

KONNI는 RAT 이름에서 출발했고, BABYSHARK 역시 악성코드 이름이다. 특정 악성코드가 발견됐다는 사실과 그 실행 주체를 확정하는 것은 별개의 분석 단계다.

### APT 이름은 고정된 주민등록번호가 아니다

Kimsuky, Thallium, Emerald Sleet, APT43 같은 이름은 연구기관이 자기 텔레메트리에서 본 활동을 묶은 라벨이다. 이름이 다르다고 반드시 다른 사람이 아니며, 이름이 같다고 모든 사건의 운영자가 같다는 보장도 없다.

### 단일 IOC보다 증거의 결합이 중요하다

미끼 주제와 표적은 쉽게 따라 할 수 있다. IP도 VPN이나 침해 서버일 수 있다. 반면 고유 코드 루틴, 커스텀 도구, 압축 암호, 인프라와 활동 시간이 함께 연결되면 귀속 판단은 훨씬 강해진다.

이번에는 반대로 **공통 IOC를 찾지 못한 것도 결과**라는 점을 알게 됐다. A와 B의 실제 사건에서 동일 C2를 찾지 못했다는 사실은 동일 행위자 결론을 약하게 만든다. 없는 근거를 비슷한 다른 캠페인의 IOC로 메우면 안 된다.

### 최초 보고서는 후대의 요약보다 신중했다

Kaspersky와 Talos는 당시 확인할 수 있는 사실과 추정을 분리했다. 시간이 지나 여러 업체의 관측이 쌓이면서 현재의 그룹 분류가 형성됐다. 위협 인텔리전스는 한 번의 검색 결과가 아니라 새로운 증거로 계속 수정되는 분석 과정이었다.

## 9. 아직 답을 찾지 못한 점

- Cisco Talos가 왜 `KONNI`라는 단어를 선택했는지는 최초 보고서에 설명되어 있지 않았다.
- Huntress가 본 2021년 침해의 운영자가 Proofpoint 체계에서 TA427인지, BABYSHARK에 접근한 다른 하위 행위자인지는 확인하지 못했다.
- 2023년 ASEC Konni 표본은 C2가 닫혀 있어 자료 A의 도메인·IP·인증서와 직접 비교하지 못했다.
- 겹친 코드와 인프라가 동일 운영자 때문인지, 북한 내 공용 개발팀·도구 공급망·인프라 관리 조직 때문인지는 공개 자료만으로 구분하기 어렵다.
- ESRC가 제시한 일부 연결은 원본 샘플과 전체 서버 로그가 공개되지 않아 모든 분석을 제3자가 독립적으로 재현하기 어렵다.
- Konni를 Kimsuky가 아닌 APT37 쪽과 연결하는 분류의 차이를 해소하려면 같은 기간의 원본 샘플, 피해자 중복, 도메인 등록·접속 이력을 더 비교해야 한다.

## 10. 마무리

이번 조사에서 가장 큰 교훈은 **위협 행위자를 찾는 일이 이름 맞히기가 아니라는 것**이었다. 보고서가 사용한 명칭이 악성코드인지, 캠페인인지, 운영자 클러스터인지 먼저 구분해야 했다. 그 다음 코드, TTP, 피해자, 인프라와 시간 정보를 함께 비교하고, 증거마다 신뢰도를 다르게 매겨야 했다.

Kimsuky와 Konni를 연결하는 공개 자료는 분명 존재한다. 하지만 그 자료가 곧바로 이번 A와 B의 두 사건을 같은 팀으로 만들어 주지는 않았다. 확인된 사실, 벤더의 분류, 내 추정을 따로 적고 답을 찾지 못한 부분을 남기는 것이 이번 미션에서 얻은 가장 큰 교훈이었다.

### 참고 자료

- Huntress, [Targeted APT Activity: BABYSHARK Is Out for Blood](https://www.huntress.com/blog/targeted-apt-activity-babyshark-is-out-for-blood)
- AhnLab ASEC, [개인정보 유출 관련 내용으로 위장한 피싱 메일 유포 (Konni)](https://asec.ahnlab.com/ko/59625/)
- Kaspersky Securelist, [The “Kimsuky” Operation: A North Korean APT?](https://securelist.com/the-kimsuky-operation-a-north-korean-apt/57915/)
- Cisco Talos, [KONNI: A Malware Under The Radar For Years](https://blog.talosintelligence.com/konni-malware-under-radar-for-years/)
- Palo Alto Networks Unit 42, [New BabyShark Malware Targets U.S. National Security Think Tanks](https://unit42.paloaltonetworks.com/new-babyshark-malware-targets-u-s-national-security-think-tanks/)
- ESTsecurity ESRC, [APT 캠페인 'Konni' & 'Kimsuky' 조직의 공통점 발견](https://www.estsecurity.com/enterprise/security-center/notice/view/434)
- ESTsecurity ESRC, [코니(Konni)조직을 탈륨(Thallium)으로 통합 분류](https://direct.estsecurity.com/public/security-center/notice/view/14394?category-id=6)
- Proofpoint, [Triple Threat: North Korea-Aligned TA406 Scams, Spies, and Steals](https://www.proofpoint.com/au/blog/threat-insight/triple-threat-north-korea-aligned-ta406-scams-spies-and-steals)
- Palo Alto Networks Unit 42, [The Fractured Statue Campaign](https://unit42.paloaltonetworks.com/the-fractured-statue-campaign-u-s-government-targeted-in-spear-phishing-attacks/)
- MITRE ATT&CK, [Kimsuky (G0094)](https://attack.mitre.org/groups/G0094/)
- MITRE ATT&CK, [KONNI (S0356)](https://attack.mitre.org/software/S0356/)
