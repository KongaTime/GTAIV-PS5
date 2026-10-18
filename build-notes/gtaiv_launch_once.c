/* SPDX-License-Identifier: GPL-3.0-or-later
 * Launch API layouts from the existing PS5 Vulkan control helper, Mihawk-99.
 * One-shot test: only launch PPSA99774 when no big app is running. No service,
 * process termination, credential changes, or arbitrary title argument. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
typedef struct {uint32_t size;int user_id;uint32_t app_opt;uint64_t crash_report,check_flag;} Launch;
typedef struct {int user_id[4];} Users;
extern uint32_t sceLncUtilGetAppIdOfRunningBigApp(void);
extern int sceLncUtilGetAppTitleId(uint32_t,char *);
extern int sceLncUtilLaunchApp(const char *,const char **,Launch *);
extern int sceUserServiceInitialize(void *);
extern int sceUserServiceGetForegroundUser(int *);
extern int sceUserServiceGetLoginUserIdList(Users *);
int main(void){
    FILE *log=fopen("/data/gtaiv/launch-test.log","a");if(!log)return 1;
    uint32_t app=sceLncUtilGetAppIdOfRunningBigApp();char title[32]={0};
    if(app&&app!=UINT32_MAX)(void)sceLncUtilGetAppTitleId(app,title);
    fprintf(log,"before app=0x%08x title=%s\n",app,title);fflush(log);
    if(app&&app!=UINT32_MAX){fprintf(log,"Skipped: an app is already running\n");fclose(log);return 0;}
    int init=sceUserServiceInitialize(NULL),user=-1,rc=sceUserServiceGetForegroundUser(&user);
    if(rc||user<0){Users users={{-1,-1,-1,-1}};if(!sceUserServiceGetLoginUserIdList(&users))for(int i=0;i<4;i++)if(users.user_id[i]>=0){user=users.user_id[i];break;}}
    fprintf(log,"user_service=0x%08x foreground_rc=0x%08x user=%d\n",(unsigned)init,(unsigned)rc,user);fflush(log);
    if(user<0){fclose(log);return 2;}
    Launch options={0};options.size=sizeof(options);options.user_id=user;
    rc=sceLncUtilLaunchApp("PPSA99774",NULL,&options);fprintf(log,"launch PPSA99774 result=0x%08x\n",(unsigned)rc);fflush(log);
    for(int i=0;i<8;i++){
        usleep(250000);app=sceLncUtilGetAppIdOfRunningBigApp();memset(title,0,sizeof(title));
        if(app&&app!=UINT32_MAX)(void)sceLncUtilGetAppTitleId(app,title);
        if(!strcmp(title,"PPSA99774"))break;
    }
    fprintf(log,"after app=0x%08x title=%s\n",app,title);fclose(log);return 0;
}
