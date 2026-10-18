#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>
#include "fd_limits.h"

static int scenario(int which)
{
    struct rlimit limits;
    if (getrlimit(RLIMIT_NOFILE, &limits)) return 10;
    if (limits.rlim_max < 8192) return 11;
    limits.rlim_cur = which == 1 ? 8192 : 64;
    if (which == 2) limits.rlim_max = 64;
    if (setrlimit(RLIMIT_NOFILE, &limits)) return 12;
    /* Drop root privileges so the fallback case cannot raise its hard limit. */
    if (which == 2 && geteuid() == 0 && setuid(65534)) return 13;
    ps5_init_file_limits();
    if (getrlimit(RLIMIT_NOFILE, &limits)) return 14;
    if (which == 0 && limits.rlim_cur != 4096) return 15;
    if (which == 1 && limits.rlim_cur != 8192) return 16;
    if (which == 2 && (limits.rlim_cur != 64 || limits.rlim_max != 64)) return 17;
    if (which == 0)
    {
        FILE *files[128];
        for (int i = 0; i < 128; ++i)
            if (!(files[i] = fopen("/dev/null", "r"))) return 18;
        for (int i = 0; i < 128; ++i) fclose(files[i]);
    }
    return 0;
}

int main(void)
{
    for (int i = 0; i < 3; ++i)
    {
        pid_t child = fork();
        int status;
        if (child < 0) return 20;
        if (!child) _exit(scenario(i));
        if (waitpid(child, &status, 0) != child || !WIFEXITED(status) || WEXITSTATUS(status))
        {
            fprintf(stderr, "FAIL scenario=%d status=%d\n", i, status);
            return 1;
        }
    }
    puts("PASS: raises low soft limit, preserves higher limits, survives denied hard-limit increase; opens 128 files after a 64-file limit.");
    return 0;
}
