---
title: "Ethernaut Level 0–40 올클리어: Solidity 취약점 41개 실전 정리"
date: 2026-10-02 10:00:00 +0900
categories: [CTF/Wargame]
tags: [Ethernaut, Solidity, Web3, Smart-Contract, EVM, CTF, Write-up, OpenZeppelin, 미션11]
mermaid: true
---

## 1. 시작하며

이번 미션은 OpenZeppelin의 Web3 워게임 **Ethernaut**를 처음부터 끝까지 풀며 Solidity와 EVM 보안 개념을 익히는 것이었다. 예전 라이트업 대부분은 Level 0~30 전후에서 끝나지만, 2026년 10월 2일 공식 저장소의 목록은 **Level 0부터 40까지 총 41개**다.

![Ethernaut 공식 페이지](/assets/img/ethernaut-all-clear/01-ethernaut-home.png)
_Ethernaut 공식 페이지. 실제 레벨 목록과 난이도를 먼저 확인했다._

브라우저 콘솔만으로 한 번씩 호출하는 데 그치지 않고 공식 저장소를 받아 Foundry 테스트로 공격 전·후 상태와 `validateInstance()` 결과를 확인했다. 기준 커밋은 `d05643a40aa98c45d66247c69ffceab8f44dd8cb`, 실행 환경은 Forge 1.8.4와 Prague EVM이다.

```text
공식 소스 분석 → 공격 가설 수립 → Foundry 로컬 재현
→ validateInstance() 확인 → 취약점 원인과 대응책 정리
```

공식 테스트 42개 스위트의 98개 테스트가 모두 통과했다. 공식 테스트가 아직 없는 Level 38·39는 별도 테스트를 작성해 각각 EIP-7702 재진입과 EIP-2098 서명 재사용을 재현했다. Level 40은 독립 PoC 테스트로 함수 선택자 충돌과 마지막 배열 원소가 해시에서 빠지는 결함을 확인했다.

![Foundry 전체 테스트 통과](/assets/img/ethernaut-all-clear/02-all-tests.png)
_공식 Foundry 테스트 실행 결과. 42개 스위트, 98개 테스트, 실패 0._

> 이 글의 화면은 Sepolia 거래를 성공한 것처럼 꾸민 이미지가 아니다. 공식 소스를 로컬 EVM에서 실행한 결과를 읽기 좋게 재구성한 캡처다. Motorbike처럼 하드포크 이후 공개 네트워크 판정이 깨진 레벨도 있어, 재현 가능한 로컬 검증을 기준으로 삼았다.

## 2. 먼저 익힌 Solidity와 EVM 문법

Ethernaut 풀이에 반복해서 쓰인 요소는 다음과 같다.

| 문법·개념 | 보안상 의미 |
|---|---|
| `msg.sender`, `tx.origin` | 직접 호출자와 거래 최초 발신자는 다르다 |
| `call`, `delegatecall` | 외부 코드 실행, 재진입, 호출 문맥과 저장소 공유 |
| `fallback`, `receive` | 함수 선택자가 없거나 ETH를 받을 때 실행되는 진입점 |
| storage slot | `private`도 숨겨지지 않으며 프록시에서는 충돌 위험이 있다 |
| `abi.encode*`, selector | calldata 레이아웃과 앞 4바이트 함수 식별자 |
| `CREATE`, `CREATE2` | 배포 주소가 발신자·nonce 또는 salt로 결정된다 |
| ERC-20/721 콜백 | 토큰 이동도 외부 코드 실행을 유발할 수 있다 |
| ECDSA | 메시지 도메인, nonce, 정규화가 빠지면 서명 재사용이 가능하다 |
| EIP-7702 | EOA도 위임 코드를 실행할 수 있어 EOA/컨트랙트 이분법이 깨진다 |

`private`은 접근 제어가 아니라 Solidity 코드 수준의 가시성일 뿐이고, 블록 값은 비밀 난수가 아니며, 외부 호출 한 번은 제어권을 상대에게 넘기는 행위라는 세 문장이 전체 미션을 관통했다.

## 3. Level 0–7: 호출 문맥과 기본 함정

### Level 0 — Hello Ethernaut

브라우저 개발자 콘솔에서 `contract.info()`, `info1()`, `info2("hello")`처럼 반환값을 따라가 최종 `password()`를 얻고 `authenticate(password)`를 호출한다. ABI를 통해 컨트랙트의 `view` 함수와 트랜잭션 함수를 구분하는 튜토리얼이다.

### Level 1 — Fallback

`contribute()`에 0.001 ETH보다 작은 값을 보내 기여 기록을 만든 뒤, 빈 calldata와 ETH를 보내 `receive()`를 실행한다. 조건을 만족하면 `owner = msg.sender`가 되고 `withdraw()`가 열린다.

```solidity
target.contribute{value: 1 wei}();
(bool ok,) = address(target).call{value: 1 wei}("");
require(ok);
target.withdraw();
```

권한 변경을 입금용 fallback에 섞지 말고, 소유권 변경에는 명시적인 접근 제어를 사용해야 한다.

### Level 2 — Fallout

생성자여야 했던 함수 이름이 `Fal1out()`으로 오타가 나 일반 공개 함수가 되었다. 이를 호출하면 바로 소유자가 된다. 최신 Solidity의 `constructor` 키워드가 왜 필요한지 보여 준다.

### Level 3 — Coin Flip

컨트랙트가 `blockhash(block.number - 1)`을 상수로 나눈 값을 동전 결과로 쓴다. 같은 트랜잭션 안의 공격 컨트랙트도 똑같은 블록 값을 보므로 결과를 미리 계산해 10번 연속 맞힌다. 온체인 값만으로 만든 난수는 검증자와 공격자에게 모두 보인다.

### Level 4 — Telephone

`tx.origin != msg.sender` 조건은 중간 공격 컨트랙트를 한 번 거치면 만족한다. 인증에 `tx.origin`을 쓰지 말고 역할 기반 접근 제어와 `msg.sender`를 사용해야 한다.

### Level 5 — Token

구버전 Solidity에서 잔고 20인 계정이 21을 전송하면 `20 - 21`이 언더플로되어 매우 큰 정수가 된다. Solidity 0.8+의 checked arithmetic이나 SafeMath가 방어책이다.

### Level 6 — Delegation

프록시의 fallback에 `pwn()` 선택자 `abi.encodeWithSignature("pwn()")`를 보낸다. `delegatecall`은 Delegate의 코드를 실행하지만 저장소와 `msg.sender`는 Delegation의 문맥을 유지하므로 슬롯 0의 owner가 바뀐다.

### Level 7 — Force

대상에는 payable 함수가 없지만, ETH를 가진 보조 컨트랙트가 `selfdestruct(payable(target))`를 실행하면 대상의 동의 없이 잔고가 생긴다. 컨트랙트 잔고가 내부 회계와 항상 같다고 가정하면 안 된다.

## 4. Level 8–13: 저장소, DoS, 재진입

### Level 8 — Vault

`password`가 `private`이어도 storage slot 1을 `eth_getStorageAt` 또는 `vm.load`로 읽을 수 있다. 블록체인의 상태는 공개되어 있으므로 비밀값 원문을 온체인에 저장하지 않는다.

### Level 9 — King

현재 king보다 많은 ETH를 보내 왕이 된 뒤, ETH 수신 시 항상 revert하는 공격 컨트랙트를 왕으로 만든다. 다음 참가자에게 환불하는 `transfer`가 실패하면서 왕 교체 전체가 막힌다. push payment 대신 사용자가 직접 찾아가는 pull payment가 안전하다.

### Level 10 — Re-entrancy

`withdraw()`가 잔고를 줄이기 전에 `msg.sender.call{value: ...}`로 외부 호출한다. 공격 컨트랙트의 `receive()`에서 다시 `withdraw()`를 호출해 잔고가 갱신되기 전 반복 출금했다.

![Re-entrancy 로컬 재현](/assets/img/ethernaut-all-clear/03-reentrancy.png)
_Checks-Effects-Interactions 순서가 뒤집힌 지점을 공격 컨트랙트로 재현했다._

대응은 상태를 먼저 갱신하는 CEI 패턴과 `ReentrancyGuard`다. 단, 가드만 붙이는 것보다 불변식이 외부 호출 전 성립하도록 설계하는 편이 중요하다.

### Level 11 — Elevator

대상은 호출자가 구현한 `isLastFloor()`를 두 번 호출하고 결과가 항상 같다고 가정한다. 공격 구현은 첫 호출에 false, 두 번째 호출에 true를 반환한다. 외부 `view` 인터페이스라도 상대 상태에 따라 다른 값을 낼 수 있다.

### Level 12 — Privacy

storage packing을 계산하면 `locked`가 slot 0, 정수들이 slot 1, `data[0..2]`가 slot 3~5에 놓인다. slot 5의 앞 16바이트를 `bytes16`으로 잘라 `unlock()`에 전달한다.

### Level 13 — Gatekeeper One

세 관문을 맞춘다. 공격 컨트랙트를 경유해 `msg.sender != tx.origin`, `tx.origin` 하위 16비트에 맞는 `bytes8` 키, 그리고 `gasleft() % 8191 == 0`이 되도록 가스를 탐색한다. 가스 잔량은 인증 수단이 아니다.

## 5. Level 14–21: 생성 시점, allowance, 주소와 바이트코드

### Level 14 — Gatekeeper Two

공격 컨트랙트 생성자 안에서 호출하면 런타임 코드가 아직 배치되지 않아 `extcodesize(caller()) == 0`이다. 키는 `keccak256(msg.sender)`와 XOR했을 때 `uint64.max`가 되도록 반전한다. 코드 크기로 EOA 여부를 판별하는 방법은 생성자와 EIP-7702 앞에서 깨진다.

### Level 15 — Naught Coin

`transfer()`만 시간 잠금으로 막혀 있고 ERC-20의 `approve()`와 `transferFrom()`은 살아 있다. 자신 또는 공격 컨트랙트에 allowance를 주고 전체 잔고를 이동한다. 토큰 제약은 모든 이동 경로에 같은 정책을 적용해야 한다.

### Level 16 — Preservation

라이브러리 호출이 `delegatecall`인데 대상과 라이브러리의 storage layout이 다르다. 첫 호출로 slot 0의 라이브러리 주소를 공격 라이브러리로 바꾸고, 두 번째 호출로 slot 2의 owner를 덮는다.

### Level 17 — Recovery

잃어버린 SimpleToken 주소를 생성자 주소와 nonce로 다시 계산한다. 첫 `CREATE`라면 `keccak256(rlp.encode([creator, 1]))`의 마지막 20바이트다. 주소를 찾은 뒤 `destroy(player)`로 ETH를 회수한다.

### Level 18 — MagicNumber

Solidity 없이 10바이트 이하의 runtime bytecode가 42를 반환해야 한다. `602a60005260206000f3`는 42를 메모리 0에 저장하고 32바이트를 반환한다. 이 runtime을 돌려주는 creation bytecode로 solver를 배포한다.

### Level 19 — Alien Codex

구버전 배열 길이를 언더플로시켜 전체 storage를 배열처럼 접근한다. 동적 배열 시작점 `keccak256(slot)`에서 slot 0까지 되감는 인덱스를 계산해 owner가 들어 있는 packed slot을 덮는다.

### Level 20 — Denial

withdraw 과정에서 partner에게 모든 가스를 넘긴다. partner를 무한 루프나 과도한 가스 소비 컨트랙트로 지정하면 owner 지급까지 도달하지 못한다. 신뢰하지 않는 외부 호출 실패가 핵심 로직을 막지 않게 해야 한다.

### Level 21 — Shop

구매자가 구현한 `price()`를 상태 변경 전후 두 번 호출한다. 첫 호출에는 100, `isSold`가 true가 된 두 번째 호출에는 0을 반환해 100 미만 가격으로 판매되게 한다. Elevator와 마찬가지로 외부 조회 결과의 일관성을 가정한 문제다.

## 6. Level 22–27: AMM, 프록시, 탐지 봇

### Level 22 — Dex

가격식이 현재 두 토큰 잔고의 단순 비율이다.

```solidity
return (amount * IERC20(to).balanceOf(address(this))) /
       IERC20(from).balanceOf(address(this));
```

토큰 1과 2를 번갈아 전량 스왑하면 반올림과 변하는 현물 비율 때문에 한쪽 준비금이 0이 된다. 외부 조작이 쉬운 spot balance만 가격 오라클처럼 쓰면 안 된다.

### Level 23 — Dex Two

허용 토큰인지 검사하지 않아 직접 만든 토큰도 스왑 입력으로 받는다. 가짜 토큰을 Dex에 조금 보내 가격식을 만든 뒤 두 정상 토큰을 각각 전부 빼냈다.

![Dex와 Dex Two 풀이](/assets/img/ethernaut-all-clear/04-dex.png)
_Dex는 가격식, Dex Two는 자산 allowlist가 깨진 문제였다._

### Level 24 — Puzzle Wallet

프록시와 구현체의 슬롯이 충돌한다. `pendingAdmin`과 `owner`가 slot 0, `admin`과 `maxBalance`가 slot 1을 함께 쓴다. `proposeNewAdmin(player)`로 wallet owner가 되고, 중첩 `multicall`로 같은 `msg.value`를 두 번 입금 처리해 잔고를 비운 다음 `setMaxBalance(uint160(player))`로 admin을 덮는다.

### Level 25 — Motorbike

프록시가 아닌 구현 컨트랙트 Engine을 직접 찾아 초기화하고 upgrader가 된다. 악성 구현으로 업그레이드하면서 과거에는 `selfdestruct`로 코드를 제거했다. 다만 Dencun의 EIP-6780 이후 이전 트랜잭션에서 만든 컨트랙트의 코드는 지워지지 않아 Sepolia 판정이 깨질 수 있다. 로컬 테스트가 통과하더라도 현재 체인 규칙과 레벨 검증식의 불일치를 별도로 확인해야 한다.

![프록시 저장소 공격 재현](/assets/img/ethernaut-all-clear/05-proxy.png)
_Puzzle Wallet과 Motorbike를 통해 proxy storage layout과 implementation 초기화의 위험을 확인했다._

### Level 26 — DoubleEntryPoint

LegacyToken의 `delegateTransfer()` 경로로 underlying DET가 빠져나가는 것을 Forta bot으로 감지한다. `msgData`에서 원래 송신자를 디코딩하고 vault에서 시작된 delegate transfer면 `raiseAlert(user)`를 호출한다. 래퍼 토큰은 실제 자산 이동 경로까지 감시해야 한다.

### Level 27 — Good Samaritan

공격자의 `notify(uint256)`가 10 토큰을 받을 때만 `NotEnoughBalance()` custom error를 발생시킨다. Wallet은 이 에러 선택자를 잔고 부족으로 오인해 `transferRemainder()`를 실행한다. 외부 컨트랙트가 낸 에러의 출처를 확인하지 않고 제어 흐름에 사용하면 안 된다.

## 7. Level 28–37: calldata, 회계, 서명과 비트 패킹

### Level 28 — Gatekeeper Three

`construct0r()`로 owner가 되고, SimpleTrick을 만든 뒤 storage에서 password를 읽어 `getAllowance()`를 통과한다. 공격 컨트랙트는 `receive()`에서 revert하도록 하고 대상에 0.001 ETH보다 조금 넘게 강제 전송한 뒤 `enter()`를 호출한다.

### Level 29 — Switch

함수는 calldata 고정 오프셋의 selector만 검사하지만 실제 ABI 디코더는 공격자가 지정한 동적 배열 offset을 따른다. 허용된 `turnSwitchOff()`를 검사 위치에 두고, 실제 실행 데이터 위치에는 `turnSwitchOn()`을 놓은 raw calldata를 보낸다. 검증 대상과 실행 대상은 반드시 같은 디코딩 결과여야 한다.

### Level 30 — HigherOrder

`registerTreasury(uint8)` ABI를 정상 인코딩하지 않고 selector 뒤에 256비트 값 256을 직접 붙인다. assembly의 `calldataload(4)`는 전체 32바이트를 읽으므로 `uint8` 의도와 다르게 treasury가 256이 되고 commander를 획득한다.

### Level 31 — Stake

외부 WETH `transferFrom()`의 반환값을 확인하지 않은 채 내부 `totalStaked`와 사용자 잔고를 올린다. 이후 ETH stake/unstake를 조합해 내부 회계와 실제 ETH 잔고를 어긋나게 한다. 토큰 호출은 성공 bool, 실제 수령량, fee-on-transfer 가능성까지 검증해야 한다.

### Level 32 — Impersonator

ECDSA에서 `(r, s, v)`와 `(r, n-s, flipped-v)`가 같은 signer를 복구할 수 있는 가변성을 이용한다. 원본 서명에서 `s' = secp256k1n - s`, `v' = 28`을 만들어 controller를 바꾼다. low-s 정규화와 OpenZeppelin ECDSA 구현을 사용해야 한다.

### Level 33 — Magic Animal Carousel

동물 이름, owner, crate ID가 한 storage word에 비트 패킹되어 있다. `changeAnimal()`에 비표준 길이의 raw calldata를 넣어 마스킹 밖의 비트까지 영향을 주고, 다음 spin에서 `currentCrateId`를 `uint16.max`로 만든다. assembly/비트 연산은 필드별 마스크와 범위를 명시해야 한다.

### Level 34 — Bet House

Pool과 BetHouse 사이 토큰·ETH 회계 순서와 외부 상호작용을 공격 컨트랙트로 엮는다. 소량의 PoolToken을 공격 컨트랙트에 넘기고 0.001 ETH로 공격을 시작해 인스턴스의 종료 조건을 만든다. 여러 컨트랙트의 합성 상태를 하나의 불변식으로 검사해야 한다.

### Level 35 — Elliptic Token

잘못 구성된 타원곡선 서명 검증으로 Alice의 permit 서명을 위조하고, 플레이어의 acceptance 서명을 결합한다. 승인량을 크게 설정한 뒤 `transferFrom(ALICE, player, INITIAL_AMOUNT)`로 잔고를 비운다. 서명 대상에는 체인 ID, 컨트랙트 주소, nonce, 만료시간을 포함한 명확한 도메인이 필요하다.

### Level 36 — Cashback

생성·런타임 바이트코드를 직접 변형한 공격 컨트랙트와 EIP-7702 위임을 함께 사용한다. 코드 자체를 검사하는 로직을 우회한 뒤 플레이어 EOA에 nonce 변경 코드를 위임해 보상 조건을 조작한다. `extcodehash`, 코드 prefix, EOA 가정만으로 신뢰를 정하면 안 된다.

### Level 37 — Impersonator Two

서명 검증에 함수 목적과 상태를 구분하는 도메인이 충분히 결합되지 않았다. 같은 `r`을 갖도록 만든 두 서명으로 `setAdmin()`과 `switchLock()`을 통과하고 `withdraw()`한다. 한 서명이 다른 기능이나 컨트랙트에서 재사용되지 않도록 EIP-712 domain과 함수별 nonce를 사용해야 한다.

![최근 추가 레벨 테스트](/assets/img/ethernaut-all-clear/06-recent-levels.png)
_Level 32~37의 공식 solve 경로도 모두 로컬에서 통과했다._

## 8. Level 38–40: EIP-7702와 최신 공격 표면

### Level 38 — UniqueNFT

목표는 한 주소가 NFT를 두 개 이상 갖게 만드는 것이다. 컨트랙트는 `tx.origin == msg.sender`면 EOA라고 믿고 무료 민팅을 허용한다. 하지만 EIP-7702로 EOA 주소에 실행 코드를 위임하면 조건은 여전히 참이면서 ERC-721 수신 콜백도 실행된다.

```solidity
function onERC721Received(...) external returns (bytes4) {
    if (target.tokenId() < 2) target.mintNFTEOA();
    return IERC721Receiver.onERC721Received.selector;
}
```

`_mintNFT()`는 tokenId를 증가시킨 뒤 `_mint()`보다 먼저 `checkOnERC721Received()`를 호출한다. 위임 EOA의 콜백에서 `mintNFTEOA()`를 재호출하면 아직 `balanceOf(player) == 0`이므로 두 개가 민팅된다. 별도 Foundry 테스트에서 최종 balance 2와 factory 검증 true를 확인했다.

### Level 39 — Forger

컨트랙트는 `keccak256(signature bytes)`만 사용 여부로 기록한다. 공개된 65바이트 `(r,s,v)` 서명을 한 번 쓴 뒤, 동일한 서명을 EIP-2098의 64바이트 `(r, yParityAndS)`로 압축한다. OpenZeppelin `ECDSA.recover`는 두 표현을 같은 signer로 복구하지만 raw bytes의 해시는 달라 두 번째 사용이 허용된다.

```solidity
bytes32 yParityAndS = bytes32(uint256(s) | (uint256(v - 27) << 255));
bytes memory compact = abi.encodePacked(r, yParityAndS);
```

별도 테스트에서 100 FT를 두 번 민팅해 totalSupply가 200 ether가 되는 것을 확인했다. 방어는 서명 바이트가 아니라 메시지 nonce 또는 digest의 사용 여부를 기록하는 것이다.

### Level 40 — NotOptimisticPortal

가장 복잡한 마지막 문제다. 취약점은 세 가지가 결합된다.

1. `executeMessage()`가 Merkle proof 검증보다 외부 메시지를 먼저 실행한다.
2. `_computeMessageSlot()` 루프가 `length - 1`까지만 돌아 마지막 receiver/data를 해시에 넣지 않는다.
3. `transferOwnership_____610165642(address)`의 selector가 허용 진입점 `onMessageReceived(bytes)`의 `0x3a69197e`와 충돌한다.

첫 메시지로 selector collision을 이용해 helper를 owner로 만들고, 해시에 포함되지 않는 마지막 메시지로 helper를 호출한다. helper는 새 state root를 담은 RLP block header를 제출하고 소유권·sequencer를 조정한다. 그 사이 단일 leaf storage trie와 account trie를 구성해 withdrawal slot 값 `0x01`에 대한 proof를 만든다. 마지막에 `executeMessage()` 검증이 공격 중 갱신된 root를 보게 하면 토큰이 민팅된다.

독립 PoC의 테스트에서 마지막 원소만 바꾼 두 메시지의 slot hash가 완전히 같고 takeover 경로가 실행되는 것을 확인했다.

```text
Hash 1: 0xbfa6...51f1c
Hash 2: 0xbfa6...51f1c
Bug verified: _computeMessageSlot skips the last element
```

방어하려면 proof를 먼저 검증하고 상태를 고정한 다음 외부 실행을 해야 한다. 배열 전체를 해시에 포함하고, selector만 비교하지 말고 정확한 ABI와 목적지를 검증해야 한다.

![전체 레벨 커버리지](/assets/img/ethernaut-all-clear/07-level-coverage.png)
_클래식 취약점에서 EIP-7702와 cross-chain proof 검증까지 41개 레벨을 분류했다._

## 9. 전체 취약점 지도

| 범주 | 대표 레벨 | 핵심 방어 |
|---|---|---|
| 접근 제어/호출 문맥 | Fallback, Telephone, Delegation | 명시적 role, `msg.sender`, 안전한 proxy |
| 산술/타입/ABI | Token, HigherOrder, Switch | checked math, canonical decoding |
| 저장소 | Vault, Privacy, Alien Codex | 비밀을 온체인에 두지 않기, layout 검증 |
| 외부 호출/DoS | King, Re-entrancy, Denial | CEI, pull payment, 실패 격리 |
| 가격·회계 | Dex, Dex Two, Stake, Bet House | 불변식, allowlist, 실제 수령량 검증 |
| 프록시/업그레이드 | Puzzle Wallet, Motorbike | EIP-1967 슬롯, 구현체 초기화 잠금 |
| 서명 | Impersonator, Elliptic Token, Forger | low-s, EIP-712, nonce/digest replay 방지 |
| 계정 추상화 | Cashback, UniqueNFT | EOA/컨트랙트 이분법 제거 |
| Cross-chain proof | NotOptimisticPortal | verify-before-execute, 전체 메시지 commitment |

## 10. 14일간 학습 흐름으로 정리

| 일차 | 학습 및 풀이 범위 |
|---|---|
| 1–2일 | Solidity 기본 문법, ABI, Remix/Foundry, Level 0–5 |
| 3–4일 | call/delegatecall, fallback, storage, Level 6–10 |
| 5–6일 | 인터페이스 신뢰, gas, 생성자, ERC-20, Level 11–15 |
| 7–8일 | storage collision, CREATE, bytecode, Level 16–21 |
| 9–10일 | AMM, proxy, UUPS, Forta, Level 22–27 |
| 11–12일 | calldata, 회계, ECDSA, Level 28–34 |
| 13일 | 곡선 서명, runtime bytecode, EIP-7702, Level 35–39 |
| 14일 | Merkle trie proof, Level 40, 전체 회귀 테스트와 라이트업 |

## 11. 마치며

초반에는 `private` 값을 읽고 fallback을 호출하는 정도였지만, 뒤로 갈수록 문제의 중심이 “문법 실수”에서 “시스템이 믿고 있는 불변식”으로 이동했다. 특히 다음 네 가지가 가장 크게 남았다.

- 외부 호출은 상대에게 제어권을 넘기는 일이다.
- 검증한 데이터와 실제 실행한 데이터가 정확히 같아야 한다.
- 서명은 raw bytes가 아니라 의도, 도메인, nonce를 묶어 검증해야 한다.
- EIP-7702 이후 `tx.origin == msg.sender`, `code.length == 0` 같은 EOA 판별은 보안 경계가 아니다.

Ethernaut는 오래된 취약점 모음에 머물지 않고 프록시, 서명, 계정 추상화, L2 proof까지 계속 확장되고 있었다. 한 번 올클리어하는 것으로 끝내기보다 새 레벨과 EVM 하드포크가 추가될 때 기존 가정이 어떻게 깨지는지 다시 확인하는 습관이 필요하다.

## 참고 자료

- [The Ethernaut](https://ethernaut.openzeppelin.com/)
- [OpenZeppelin Ethernaut 공식 저장소](https://github.com/OpenZeppelin/ethernaut)
- [Ethernaut Community Solutions](https://forum.openzeppelin.com/t/ethernaut-community-solutions/561)
- [EIP-2098: Compact Signature Representation](https://eips.ethereum.org/EIPS/eip-2098)
- [EIP-7702: Set Code for EOAs](https://eips.ethereum.org/EIPS/eip-7702)
- [EIP-6780: SELFDESTRUCT only in same transaction](https://eips.ethereum.org/EIPS/eip-6780)
- [참고 라이트업 1](https://katarinabluu-gosegulover.github.io/Hercent.github.io/posts/ethernaut-writeups/)
- [참고 라이트업 2](https://0xaxii.github.io/posts/ethernaut-writeups/)

