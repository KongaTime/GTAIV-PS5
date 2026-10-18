/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "gtaiv_bootstrap.h"
#include "gtaiv_setup.h"
#include "pw_videoout_ps5.h"
#include "pw_pad_ps5.h"
#include "../src/pw_launcher_render.h"
#include <pthread.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>

typedef struct {
    pthread_mutex_t mutex;unsigned percent,phase;int done,result;
    char message[256],root[1024],app[1024],game[1024],last_message[256];unsigned last_percent;
} Bootstrap;
static Bootstrap setup={.mutex=PTHREAD_MUTEX_INITIALIZER};
static int file_exists(const char *path){struct stat st;return !stat(path,&st)&&S_ISREG(st.st_mode);}
static int dirs(const char *path){char b[1200];if(strlen(path)>=sizeof(b))return -1;strcpy(b,path);for(char *p=b+1;;p++)if(*p=='/'||!*p){char c=*p;*p=0;if(mkdir(b,0777)&&errno!=EEXIST)return -1;*p=c;if(!c)break;}return 0;}
static int save(const char *path,const char *text){char temp[1400];if(snprintf(temp,sizeof(temp),"%s.gtaiv-new",path)>=(int)sizeof(temp))return -1;FILE *f=fopen(temp,"wb");if(!f)return -1;size_t n=strlen(text);int ok=fwrite(text,1,n,f)==n;if(fclose(f))ok=0;return ok?rename(temp,path):-1;}
static void journal(Bootstrap *s,unsigned percent,const char *message){
    char path[1200],line[512];snprintf(path,sizeof(path),"%s/setup.log",s->root);
    FILE *f=fopen(path,"ab");if(!f)return;
    int n=snprintf(line,sizeof(line),"%u %s\n",percent,message);
    if(n>0&&(size_t)n<sizeof(line))(void)fwrite(line,1,(size_t)n,f);
    (void)fclose(f);
}
static void progress(void *context,unsigned percent,const char *message){Bootstrap *s=context;pthread_mutex_lock(&s->mutex);s->percent=s->phase?80+percent/5:percent*4/5;snprintf(s->message,sizeof(s->message),"%s",message);int log=strcmp(s->last_message,message)||percent>=s->last_percent+10;if(log){s->last_percent=percent;snprintf(s->last_message,sizeof(s->last_message),"%s",message);}pthread_mutex_unlock(&s->mutex);if(log)journal(s,percent,message);}
static int prepare(Bootstrap *s,char *error,size_t error_size){
    char path[1400],prefix[1200],template[1200],marker[1200];
    if(dirs(s->root)){snprintf(error,error_size,"Cannot open app storage");return -1;}
    journal(s,0,"Setup v3: dedicated 2 MiB worker stack, mapped transfer buffer");
    if(snprintf(s->game,sizeof(s->game),"%s/game",s->root)>=(int)sizeof(s->game))return -1;
    /* A user-supplied game always wins over the optional development alias. */
    snprintf(path,sizeof(path),"%s/GTAIV.exe",s->game);
    int local_game=file_exists(path);
    snprintf(path,sizeof(path),"%s/game.path",s->root);
    FILE *config=local_game?NULL:fopen(path,"rb");
    if(config){char configured[1024];if(fgets(configured,sizeof(configured),config)){configured[strcspn(configured,"\r\n")]=0;if(!strncmp(configured,"/data/",6)||!strncmp(configured,"/mnt/usb",8))snprintf(s->game,sizeof(s->game),"%s",configured);}fclose(config);}
    else if(dirs(s->game)){snprintf(error,error_size,"Cannot create the game folder");return -1;}
    journal(s,0,s->game);
    if(gtaiv_prepare_game(s->game,s->root,progress,s,error,error_size))return -1;
    journal(s,80,"Game validation and maps complete");
    snprintf(prefix,sizeof(prefix),"%s/prefixes/gtaiv",s->root);
    snprintf(template,sizeof(template),"%s/gtaiv/template",s->app);
    snprintf(marker,sizeof(marker),"%s/prefix-ready-v1.txt",s->root);
    if(!file_exists(marker)){
        pthread_mutex_lock(&s->mutex);s->phase=1;pthread_mutex_unlock(&s->mutex);
        if(gtaiv_copy_template(template,prefix,progress,s,error,error_size))return -1;
        if(save(marker,"GTAIV-PREFIX-1\n")){snprintf(error,error_size,"Cannot save app setup");return -1;}
    }
    snprintf(path,sizeof(path),"%s/drive_c/Games",prefix);if(dirs(path))return -1;
    snprintf(path,sizeof(path),"%s/drive_c/Games/.pw-symlinks",prefix);
    char link[1100];snprintf(link,sizeof(link),"GTAIV\t%s\n",s->game);if(save(path,link))return -1;
    snprintf(path,sizeof(path),"%s/profiles",s->root);if(dirs(path))return -1;
    snprintf(path,sizeof(path),"%s/profiles/gtaiv.profile",s->root);
    const char *profile=
        "[application]\nid = gtaiv\nname = Grand Theft Auto IV\n"
        "executable = C:\\Games\\GTAIV\\GTAIV.exe\nworking_directory = C:\\Games\\GTAIV\n"
        "arguments = -availablevidmem 1536 -nomemrestrict -norestrictions -width 1920 -height 1080 -refreshrate 60 -fullscreen -rglLanguage en-US\n"
        "dll_overrides = d3d8,d3d9,d3d10core,d3d11,dxgi=n;dinput8=n,b\n"
        "prefix = gtaiv\nruntime = wine-wow64\narchitecture = pe32\ngraphics = dxvk\n"
        "[display]\ndesktop = 1920x1080\n[input]\nmode = xinput\n[debug]\nwinedebug = -all,err+all\n";
    if(save(path,profile)){snprintf(error,error_size,"Cannot save game settings");return -1;}
    journal(s,100,"Prefix and game settings ready");
    return 0;
}
static void *worker(void *opaque){Bootstrap *s=opaque;char error[256]={0};int rc=prepare(s,error,sizeof(error));pthread_mutex_lock(&s->mutex);s->result=rc;s->done=1;s->percent=rc?s->percent:100;snprintf(s->message,sizeof(s->message),"%s",rc?(error[0]?error:"Setup could not finish. Check the game folder."):"Starting GTA IV");pthread_mutex_unlock(&s->mutex);return NULL;}

int gtaiv_bootstrap(const char *data_root,const char *app_root){
    snprintf(setup.root,sizeof(setup.root),"%s",data_root);snprintf(setup.app,sizeof(setup.app),"%s",app_root);
    const size_t bytes=(size_t)1920*1080*4;
    uint8_t *frame=NULL;PwVideoOutPs5 video;PwPadPs5 pad;PwPadPs5Ops ops;int video_open=0,pad_open=0;
    char prepared_marker[1200];snprintf(prepared_marker,sizeof(prepared_marker),"%s/prefix-ready-v1.txt",data_root);
    int progress_screen=!file_exists(prepared_marker);
    for(;;){
        setup.done=setup.result=0;setup.phase=setup.percent=0;setup.last_message[0]=0;setup.last_percent=0;snprintf(setup.message,sizeof(setup.message),"Checking game files");
        pthread_attr_t attr;pthread_t thread;
        if(pthread_attr_init(&attr))return -1;
        int thread_error=pthread_attr_setstacksize(&attr,2u*1024u*1024u);
        if(!thread_error)thread_error=pthread_create(&thread,&attr,worker,&setup);
        pthread_attr_destroy(&attr);
        if(thread_error)return -1;
        /* A prepared launch usually finishes without opening a setup screen. */
        usleep(50000);pthread_mutex_lock(&setup.mutex);int done=setup.done,result=setup.result;pthread_mutex_unlock(&setup.mutex);
        if(!(done&&!result)&&!video_open&&(progress_screen||done)){
            frame=mmap(NULL,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);
            if(frame==MAP_FAILED)frame=NULL;
            video_open=pw_videoout_ps5_open(&video)==PW_OK;
            if(pw_pad_ps5_platform_ops(&ops)==PW_OK){static const PwPadKeyMap buttons[]={{0x4000u,0x20,0,0,"cross"}};pad_open=pw_pad_ps5_open(&pad,&ops,buttons,1)==PW_OK;}
        }
        unsigned ticks=0;
        while(!done){
            char message[256];unsigned percent;
            pthread_mutex_lock(&setup.mutex);done=setup.done;result=setup.result;percent=setup.percent;snprintf(message,sizeof(message),"%s",setup.message);pthread_mutex_unlock(&setup.mutex);
            if(video_open&&frame&&!(ticks++%5)){PwPresentTarget target={frame,1920,1080,1920*4,bytes};PwPresentView view={frame,1920,1080,1920*4,(uint32_t)bytes};gtaiv_status_render(message,"First launch may take a moment",percent,0,&target);(void)pw_videoout_ps5_present(&video,&view);}
            usleep(16000);
        }
        pthread_join(thread,NULL);
        if(!result)break;
        /* A cached launch stays off the GPU unless it actually needs user
         * input. Errors must still show an actionable setup screen. */
        if(!video_open){
            frame=mmap(NULL,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);
            if(frame==MAP_FAILED)frame=NULL;
            video_open=pw_videoout_ps5_open(&video)==PW_OK;
            if(pw_pad_ps5_platform_ops(&ops)==PW_OK){static const PwPadKeyMap buttons[]={{0x4000u,0x20,0,0,"cross"}};pad_open=pw_pad_ps5_open(&pad,&ops,buttons,1)==PW_OK;}
        }
        if(!video_open||!frame){if(pad_open)pw_pad_ps5_close(&pad);if(video_open)pw_videoout_ps5_close(&video);if(frame)munmap(frame,bytes);return -1;}
        int retry=0;
        while(!retry){
            PwPresentTarget target={frame,1920,1080,1920*4,bytes};PwPresentView view={frame,1920,1080,1920*4,(uint32_t)bytes};
            gtaiv_status_render(setup.message,"Copy files to /data/gtaiv/game/ then press X",setup.percent,1,&target);(void)pw_videoout_ps5_present(&video,&view);
            if(pad_open&&pw_pad_ps5_read(&pad)==PW_OK&&(pad.core.pressed_edges&0x4000))retry=1;
            usleep(50000);
        }
    }
    journal(&setup,100,"Closing setup display");
    if(pad_open)(void)pw_pad_ps5_close(&pad);
    if(video_open)(void)pw_videoout_ps5_close(&video);
    if(frame)munmap(frame,bytes);
    journal(&setup,100,video_open?"Setup display used: requesting clean process for graphics":"Starting game runtime without opening setup display");
    return video_open?1:0;
}
