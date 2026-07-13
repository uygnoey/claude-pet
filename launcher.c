// ClaudePet 런처 — 코드서명 가능한 Mach-O.
// 번들 안에 넣은 python 복사본(Contents/MacOS/ClaudePet_py)을 실행한다.
// 그러면 실행 바이너리가 앱 번들 내부에 있어 [NSBundle mainBundle]이
// ClaudePet.app(LSUIElement 에이전트)로 잡히고, macOS가 이 앱을 문서편집
// 앱(org.python.python)으로 오인하지 않아 보호폴더 접근 프롬프트가 안 뜬다.
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <libgen.h>
#include <limits.h>
#include <mach-o/dyld.h>

int main(void) {
    char exe[PATH_MAX];
    uint32_t sz = sizeof(exe);
    if (_NSGetExecutablePath(exe, &sz) != 0) return 1;
    char real[PATH_MAX];
    if (!realpath(exe, real)) strncpy(real, exe, sizeof(real));
    char *macos = dirname(real);                 // .../Contents/MacOS
    char script[PATH_MAX], bundled[PATH_MAX];
    snprintf(script, sizeof(script), "%s/../Resources/claude_pet.py", macos);
    snprintf(bundled, sizeof(bundled), "%s/ClaudePet_py", macos);

    // 1순위: 번들 내장 python (mainBundle=ClaudePet → 프롬프트 없음)
    if (access(bundled, X_OK) == 0)
        execl(bundled, bundled, script, (char *)NULL);

    // 폴백(개발용): 시스템/pyenv framework python 탐색 후 실행
    const char *home = getenv("HOME");
    char c_home[PATH_MAX] = "";
    if (home) snprintf(c_home, sizeof(c_home), "%s/.pyenv/shims/python3", home);
    const char *cands[] = {
        c_home[0] ? c_home : NULL,
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        "/Library/Frameworks/Python.framework/Versions/Current/bin/python3",
        "/usr/bin/python3",
    };
    for (size_t i = 0; i < sizeof(cands) / sizeof(cands[0]); i++) {
        if (cands[i] && access(cands[i], X_OK) == 0)
            execl(cands[i], cands[i], script, (char *)NULL);
    }
    system("osascript -e 'display dialog \"실행할 python을 못 찾았어요.\" "
           "buttons {\"확인\"} default button 1 with title \"Claude Pet\"'");
    return 1;
}
