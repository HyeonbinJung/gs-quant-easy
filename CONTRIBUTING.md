# gs-quant 기여 가이드

이 문서는 이슈 보고와 코드 기여 방법을 설명합니다. 참여하기 전에 [기여자 서약 행동 강령](CODE_OF_CONDUCT.md)을 꼭 읽어 주세요.


# 개발 및 빌드 환경

gs-quant 개발 환경에는 다음이 필요합니다.

### 1) Python 3.10 이상
[Python.org](https://www.python.org/downloads/) 또는 운영체제의 패키지 관리자에서 설치할 수 있습니다.


### 2) IDE
주요 개발자들은 [PyCharm](https://www.jetbrains.com/pycharm/)을 사용하지만, 다른 IDE나 편집기를 써도 됩니다.

IDE 설정 파일은 커밋하지 마세요.


# 이슈
이슈 트래커에서 관련 이슈를 먼저 검색하고, 없으면 새로 만드세요.


# 변경 사항 만들기
GitHub에서 저장소를 포크한 뒤 포크한 저장소에서 작업하세요.

첫 풀 리퀘스트를 보내기 전에, 이 문서 마지막 섹션의 안내에 따라 DCO(개발자 원산지 증명서)를 먼저 제출해야 합니다.

그다음 풀 리퀘스트를 보냅니다. 풀 리퀘스트는 다음을 지켜야 합니다.
* 풀 리퀘스트가 fast-forward 병합될 수 있도록 [포크를 리베이스](https://github.com/edx/edx-platform/wiki/How-to-Rebase-a-Pull-Request)하세요.
* 여러 커밋이 내용을 더 명확하게 하거나 저작권자가 섞인 커밋이라 꼭 필요한 경우가 아니면, 커밋을 하나로 합치는(squash) 것을 선호합니다.
* 코드 커밋 메시지에는 `covered by: <dco>` 줄이 반드시 들어가야 합니다. 위 내용을 참고하세요.
* 수정하는 모든 파일에는 Apache 헤더 다음에 저작권 정보를 담은 한 줄을 넣어야 합니다.
```
//Portions copyright <copyright holder>. Licensed under Apache 2.0 license
```
* 새 파일에는 알맞은 저작권자를 적은 표준 Apache 2.0 헤더가 있어야 합니다.
* 다른 오픈소스 프로젝트의 코드를 가져오는 경우, 먼저 그 코드를 `covered by: <license>`로 커밋하세요.
여기서 `<license>`는 커밋하는 코드의 라이선스입니다. 파일의 원래 저작권 표시는 그대로 두고, 같은 커밋에서 NOTICE.txt에 알맞은 줄을 추가하세요. 이후 커밋에서는 본인의 DCO와 저작권을 명시해 그 코드를 수정할 수 있습니다.

# 라이선스

새로 추가하는 의존성의 라이선스는 다음 사전 승인 목록에 있어야 합니다.

```
MIT
ASL (all versions)
BSD
BSD-like
``` 


# 코딩 스타일
[PEP 8 - 파이썬 코드 스타일 가이드](https://www.python.org/dev/peps/pep-0008/)를 따르세요.


# 부록: 기여 전 필수 사항 - DCO 제출

gs-quant에 처음 기여하거나 저작권 소유 관계가 바뀌었다면, 먼저 DCO(developer certificate of origin)가 담긴 풀 리퀘스트를 만들어야 합니다. 방법은 다음과 같습니다.

먼저 본인이 작성하는 코드의 저작권자가 누구인지 확인하세요. 미국에서 고용되어 있다면, 근무 시간 외에 회사 장비를 쓰지 않고 작성한 코드라도 고용주가 저작권을 주장할 수 있습니다. 저작권법은 관할 지역마다 크게 다릅니다. 확실하지 않으면 고용주나 변호사와 상의하세요.

저작권자가 본인이라면 아래 양식을 채워(`<>` 부분을 모두 바꿔서) `dco/<your name>.dco` 파일로 저장하세요.
DCO 파일은 법적 증명서이므로 **아래 영문 원문 그대로** 작성해야 합니다.

```
1) I, <your name>, certify that all work committed with the commit message 
"covered by: <your name>.dco" is my original work and I own the copyright 
to this work. I agree to contribute this code under the Apache 2.0 license.

2) I understand and agree all contribution including all personal 
information I submit with it is maintained indefinitely and may be 
redistributed consistent with the open source license(s) involved. 

This certification is effective for all code contributed from <date submitted> to 9999-01-01.
```

> 참고 번역: (1) 나 `<이름>`은 커밋 메시지에 "covered by: `<이름>`.dco"가 붙은 모든 작업이 나의 독창적 저작물이며 내가 그 저작권을 가지고 있음을 증명한다. 이 코드를 Apache 2.0 라이선스로 기여하는 데 동의한다. (2) 제출한 개인 정보를 포함한 모든 기여물이 무기한 보관되며 관련 오픈소스 라이선스에 따라 재배포될 수 있음을 이해하고 동의한다. 이 증명은 `<제출일>`부터 9999-01-01까지 기여한 모든 코드에 효력이 있다.

저작권자가 본인이 아닌 다른 주체(예: 고용주)라면, 저작권자로부터 gs-quant 기여 목적으로 이 코드를 Apache 2.0 라이선스로 제공할 권한을 받았는지 확인해야 합니다. 이러한 권한을 협의하고 관리하는 것은 전적으로 본인과 저작권자 사이의 일입니다. 아래 양식을 채워(`<>` 부분을 모두 바꿔서) `dco/<copyright holder name>-<your name>.dco` 파일로 저장하세요.

```
1) I, <your name>, certify that all work committed with the commit message 
"covered by: <copyright holder name>-<your name>.dco" is copyright 
<copyright holder name> and that I am authorized by <copyright holder name> 
to contribute this code under the Apache 2.0 license.

2) I understand and agree all contribution including all personal 
information I submit with it is maintained indefinitely and may be 
redistributed consistent with the open source license(s) involved. 

This certification is effective for all code contributed from <date submitted> to 9999-01-01.
```

> 참고 번역: (1) 나 `<이름>`은 커밋 메시지에 "covered by: `<저작권자>`-`<이름>`.dco"가 붙은 모든 작업의 저작권이 `<저작권자>`에게 있으며, 내가 `<저작권자>`로부터 이 코드를 Apache 2.0 라이선스로 기여할 권한을 받았음을 증명한다. (2)와 효력 기간은 위와 같다.

`<your name>`에는 반드시 실명을 써야 하며, 별칭, 가명, 익명 기여는 받지 않습니다.
알맞은 DCO 파일과 함께 NOTICE.txt에
`This product contains code copyright <copyright holder name>, licensed under Apache 2.0 license` 한 줄을 추가하는 풀 리퀘스트를 보내세요.
