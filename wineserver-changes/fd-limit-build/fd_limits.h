/* Per-process descriptor budget for the in-process PS5 server.
 * The ordinary Wine main() calls init_limits(), but this entry bypasses it.
 * Never lower a limit, and keep the requested budget within the cwd table.
 */
static void ps5_init_file_limits(void)
{
    struct rlimit before, wanted, after;
    int result = 0, saved_errno = 0;

    if (getrlimit(RLIMIT_NOFILE, &before))
    {
        fprintf(stderr, "wine-ps5: fd-limit get failed errno=%d\n", errno);
        return;
    }
    wanted = before;
    if (wanted.rlim_cur < 4096) wanted.rlim_cur = 4096;
    if (wanted.rlim_max < wanted.rlim_cur) wanted.rlim_max = wanted.rlim_cur;
    if (wanted.rlim_cur != before.rlim_cur || wanted.rlim_max != before.rlim_max)
    {
        result = setrlimit(RLIMIT_NOFILE, &wanted);
        if (result)
        {
            saved_errno = errno;
            /* Raising the hard limit may be denied; use existing headroom. */
            wanted = before;
            if (wanted.rlim_cur < wanted.rlim_max)
            {
                wanted.rlim_cur = wanted.rlim_max < 4096 ? wanted.rlim_max : 4096;
                result = setrlimit(RLIMIT_NOFILE, &wanted);
                if (result) saved_errno = errno;
            }
        }
    }
    after = before;
    if (getrlimit(RLIMIT_NOFILE, &after)) after = before;
    fprintf(stderr, "wine-ps5: fd-limit before=%llu/%llu after=%llu/%llu status=%d errno=%d\n",
            (unsigned long long)before.rlim_cur, (unsigned long long)before.rlim_max,
            (unsigned long long)after.rlim_cur, (unsigned long long)after.rlim_max,
            result, saved_errno);
}
