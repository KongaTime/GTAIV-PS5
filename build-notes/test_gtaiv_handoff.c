#define _DEFAULT_SOURCE
#include "gtaiv_bootstrap.h"
#include "gtaiv_setup.h"
#include "pw_videoout_ps5.h"
#include "pw_pad_ps5.h"
#include "pw_launcher_render.h"
#include <assert.h>
#include <stdio.h>
#include <unistd.h>
static unsigned opened,closed,presented;
int pw_videoout_ps5_open(PwVideoOutPs5 *p){(void)p;opened++;return PW_OK;}
int pw_videoout_ps5_close(PwVideoOutPs5 *p){(void)p;closed++;return PW_OK;}
int pw_videoout_ps5_present(PwVideoOutPs5 *p,const PwPresentView *v){(void)p;(void)v;presented++;return PW_OK;}
int pw_pad_ps5_platform_ops(PwPadPs5Ops *p){(void)p;return PW_ERR_UNSUPPORTED;}
int pw_pad_ps5_open(PwPadPs5 *p,const PwPadPs5Ops *o,const PwPadKeyMap *k,size_t n){(void)p;(void)o;(void)k;(void)n;return PW_ERR_UNSUPPORTED;}
int pw_pad_ps5_close(PwPadPs5 *p){(void)p;return PW_OK;}
int pw_pad_ps5_read(PwPadPs5 *p){(void)p;return PW_ERR_UNSUPPORTED;}
int gtaiv_status_render(const char *m,const char *h,unsigned p,int failed,const PwPresentTarget *t){(void)m;(void)h;(void)p;(void)failed;(void)t;return PW_OK;}
int gtaiv_prepare_game(const char *g,const char *s,GtaivProgress p,void *c,char *e,size_t n){(void)g;(void)s;(void)e;(void)n;if(p)p(c,1,"Checking game files");usleep(150000);return 0;}
int gtaiv_copy_template(const char *s,const char *d,GtaivProgress p,void *c,char *e,size_t n){(void)s;(void)d;(void)p;(void)c;(void)e;(void)n;return 0;}
int main(int argc,char **argv){
    assert(argc==3);
    assert(gtaiv_bootstrap(argv[1],argv[2])==1);
    assert(opened==1&&closed==1&&presented>0);
    unsigned frames=presented;
    assert(gtaiv_bootstrap(argv[1],argv[2])==0);
    assert(opened==1&&closed==1&&presented==frames);
    puts("PASS: first setup requests a fresh process; prepared launch makes zero graphics calls even when validation exceeds 50 ms");
    return 0;
}
