// ClaudePet 런처 — 코드서명 가능한 Mach-O 실행 파일.
// 핵심: python을 execv로 "대체"하지 않고 fork+wait로 "자식" 실행한다.
// 그래야 이 서명된 번들(ClaudePet)이 책임 프로세스로 남아, macOS가
// 키체인/파일 접근 권한을 python3.13이 아니라 "ClaudePet"에 기억한다.
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/wait.h>
#include <string.h>
#include <stdio.h>
#include <libgen.h>
#include <limits.h>
#include <mach-o/dyld.h>

static int has_appkit(const char *py) {
    pid_t pid = fork();
    if (pid == 0) {
        int dn = open("/dev/null", O_WRONLY);
        if (dn >= 0) { dup2(dn, 1); dup2(dn, 2); }
        execl(py, py, "-c", "import AppKit", (char *)NULL);
        _exit(127);
    }
    int st = 0;
    if (waitpid(pid, &st, 0) < 0) return 0;
    return WIFEXITED(st) && WEXITSTATUS(st) == 0;
}

int main(void) {
    // 실행 파일 경로 → .../Contents/MacOS/ClaudePet → Resources/claude_pet.py
    char exe[PATH_MAX];
    uint32_t sz = sizeof(exe);
    if (_NSGetExecutablePath(exe, &sz) != 0) return 1;
    char real[PATH_MAX];
    if (!realpath(exe, real)) strncpy(real, exe, sizeof(real));
    char *macos = dirname(real);              // .../Contents/MacOS
    char script[PATH_MAX];
    snprintf(script, sizeof(script), "%s/../Resources/claude_pet.py", macos);

    const char *home = getenv("HOME");
    const char *pyenv_root = getenv("PYENV_ROOT");
    char c_home[PATH_MAX] = "", c_root[PATH_MAX] = "";
    if (home) snprintf(c_home, sizeof(c_home), "%s/.pyenv/shims/python3", home);
    if (pyenv_root) snprintf(c_root, sizeof(c_root), "%s/shims/python3", pyenv_root);

    const char *cands[] = {
        c_home[0] ? c_home : NULL,
        c_root[0] ? c_root : NULL,
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        "/Library/Frameworks/Python.framework/Versions/Current/bin/python3",
        "/usr/bin/python3",
    };

    for (size_t i = 0; i < sizeof(cands) / sizeof(cands[0]); i++) {
        const char *py = cands[i];
        if (!py) continue;
        if (access(py, X_OK) != 0) continue;
        if (!has_appkit(py)) continue;
        pid_t pid = fork();
        if (pid == 0) {
            execl(py, py, script, (char *)NULL);
            _exit(127);
        }
        int st = 0;
        waitpid(pid, &st, 0);
        return WIFEXITED(st) ? WEXITSTATUS(st) : 1;
    }

    system("osascript -e 'display dialog \"AppKit 가능한 python을 못 찾았어요. "
           "framework 빌드 파이썬에 pyobjc-framework-Cocoa를 설치하세요.\" "
           "buttons {\"확인\"} default button 1 with title \"Claude Pet\"'");
    return 1;
}
