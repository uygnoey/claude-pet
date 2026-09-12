# ClaudePet for Windows (개발 중)

macOS 판과 실행 조건을 같게 맞추는 Windows 이식입니다. 설계와 단계는
`docs-design/windows-port-plan-20260911.md` 를 따릅니다. 이 폴더의 코드는 `claude_pet.py` 를 **그대로 import** 해
추정기·자율 이동·업데이트 판단·설정·다국어를 재사용하고, 창·그리기·메뉴·트레이·시딩 게시·업데이트 교체만 Windows 용으로 구현합니다.
`claude_pet.py` 와 macOS 빌드·릴리즈 스크립트는 이 폴더의 코드로 바뀌지 않습니다.

## 소스로 실행 (개발)

```powershell
# python.org Python 3.13 (Microsoft Store 판은 사용하지 않음)
winget install --id Python.Python.3.13 -e --scope user
cd C:\Users\<you>\claude-pet
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r windows\requirements.txt
pythonw windows\claude_pet_win.py           # 펫 실행 (pythonw: 콘솔 창 없이)
python claude_pet.py --report               # GUI 없이 사용량 보고 (macOS 와 같은 명령)
```

처음 실행하면 Windows 11 은 새 트레이 아이콘을 `^`(숨겨진 아이콘) 안에 넣습니다. 작업표시줄 버튼이 없는 앱이라 트레이가
보이기/숨기기·종료의 진입로이니, `^` 를 열어 고양이 아이콘을 작업표시줄로 끌어내 고정해 두세요(설정 → 개인 설정 → 작업 표시줄 →
기타 시스템 트레이 아이콘에서도 켤 수 있습니다). 우클릭 메뉴는 펫 위에서 바로 열립니다.

## 알아 둘 것

- 첫 배포판은 **코드 서명이 없습니다.** 처음 실행할 때 SmartScreen 이 "Windows 의 PC 보호" 창을 띄우면 "추가 정보 → 실행" 을 누르세요.
  서명은 사용자 결정 뒤 별도 단계로 추가됩니다.
- 로그 위치는 `%USERPROFILE%\.claude\projects`, 정확 모드는 `%USERPROFILE%\.claude\.credentials.json` 을 읽습니다(내용을 저장하거나 전송하지 않습니다).
- 설정 파일은 macOS 와 같은 `%USERPROFILE%\.claude_pet.json`, 펫 폴더는 `%USERPROFILE%\.claude_pet\` 입니다.


## 배포 zip 만들기 (3단계)

Windows 에서, 저장소 루트, venv 활성화 후:

```
pip install -r windows\requirements.txt
python windows\build_win.py
```

`dist-win\ClaudePet\ClaudePet.exe` 가 만들어지고 `release\claude-pet-win.zip` 으로 묶이며, 이어서 Inno Setup 으로
`release\claude-pet-win-setup.exe`(설치 파일: 사용자별 설치, 시작 메뉴, 로그인 시 자동 실행 옵션, 프로그램 추가/제거)를
만든다. Inno Setup 6 이 필요하다: `winget install --id JRSoftware.InnoSetup -e`. 사용자는 zip 을 풀어
`ClaudePet\ClaudePet.exe` 를 실행한다(서명이 없어 첫 실행 때 SmartScreen 의 "추가 정보 → 실행"). 번들 안에는 코어와
같은 자리에 `frames\`, `fonts\`(Pretendard), `.claude_pet\`, `claudepet.ico`, 그리고 `fcntl` shim 이 들어간다.
