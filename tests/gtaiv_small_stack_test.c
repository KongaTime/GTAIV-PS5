#include <pthread.h>
#include <stdint.h>
#include <assert.h>
#include <stdio.h>
extern int gtaiv_setup_cli_main(int,char **);
static int count;static char **words;
static void *run(void *unused){(void)unused;return (void *)(intptr_t)gtaiv_setup_cli_main(count,words);}
int main(int argc,char **argv){
    count=argc;words=argv;pthread_attr_t attr;pthread_t worker;void *result;
    assert(!pthread_attr_init(&attr));assert(!pthread_attr_setstacksize(&attr,128u*1024u));
    assert(!pthread_create(&worker,&attr,run,NULL));assert(!pthread_attr_destroy(&attr));
    assert(!pthread_join(worker,&result));fprintf(stderr,"SMALL_STACK_TEST bytes=131072 passed\n");return (int)(intptr_t)result;
}
