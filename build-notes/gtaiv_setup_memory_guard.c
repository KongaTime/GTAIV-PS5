#define _DEFAULT_SOURCE
#include <sys/mman.h>
#include <sys/types.h>
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#include <stdint.h>
static struct {void *p;size_t n;} maps[128];
static size_t live,peak;static unsigned allocations;
void *__real_mmap(void *,size_t,int,int,int,off_t);
int __real_munmap(void *,size_t);
void *__wrap_malloc(size_t n){(void)n;assert(!"setup must not use the small title heap");return NULL;}
void *__wrap_calloc(size_t n,size_t width){(void)n;(void)width;assert(!"setup must not use the small title heap");return NULL;}
void *__wrap_mmap(void *at,size_t n,int prot,int flags,int fd,off_t offset){
    void *p=__real_mmap(at,n,prot,flags,fd,offset);
    if(p!=MAP_FAILED){unsigned i;for(i=0;i<128&&maps[i].p;i++);assert(i<128);maps[i].p=p;maps[i].n=n;live+=n;if(live>peak)peak=live;allocations++;}
    return p;
}
int __wrap_munmap(void *p,size_t n){
    unsigned i;for(i=0;i<128&&maps[i].p!=p;i++);assert(i<128&&maps[i].n==n);
    int rc=__real_munmap(p,n);assert(!rc);live-=n;maps[i].p=NULL;return rc;
}
static void verify(void){assert(!live);fprintf(stderr,"SETUP_MEMORY maps=%u peak=%zu live=%zu heap_calls=0\n",allocations,peak,live);}
__attribute__((constructor)) static void initialize(void){assert(!atexit(verify));}
