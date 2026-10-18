/* SPDX-License-Identifier: LGPL-2.1-or-later
 * IMG3 layout checked against GTAIVModdingToolkit (MIT). No game data or key
 * is embedded: the archive key is read from the user's supported executable.
 */
#define _DEFAULT_SOURCE
#define AES256 1
#define CBC 0
#define CTR 0
#define ECB 1
#include "gtaiv_setup.h"
#include "aes.h"
#include <sys/stat.h>
#include <sys/mman.h>
#include <dirent.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>

enum { PATH_CAP=1024, MAX_ARCHIVES=128, MAX_ENTRIES=30000, MAX_LIST=65536, BLOCK=2048 };
typedef struct {
    char name[256]; uint32_t flags,type,sector; uint16_t blocks,padding;
    unsigned source; uint64_t output;
} Entry;
typedef struct { char path[PATH_CAP]; uint64_t size; int64_t modified; } Source;
typedef struct {
    Entry *entries; uint8_t *io; unsigned count; Source sources[MAX_ARCHIVES]; unsigned sources_count;
    uint8_t key[32]; uint64_t fingerprint,payload_bytes;
    GtaivProgress progress; void *context; char *error; size_t error_size;
} Setup;
/* The title's libc startup heap is small. Large, temporary setup buffers use
 * native anonymous mappings, just like its working frame buffers. All are
 * released before Wine starts; the game does not lose a reserved heap. */
static size_t mapping_size(size_t bytes) {
    return bytes && bytes <= SIZE_MAX-16383 ? (bytes+16383)&~(size_t)16383 : 0;
}
static void *setup_alloc(size_t bytes) {
    size_t rounded=mapping_size(bytes);
    if(!rounded)return NULL;
    void *p=mmap(NULL,rounded,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);
    return p==MAP_FAILED?NULL:p;
}
static void setup_release(void *p,size_t bytes) {
    if(p)(void)munmap(p,mapping_size(bytes));
}
static uint32_t u32(const uint8_t *b) { return (uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24; }
static uint16_t u16(const uint8_t *b) { return (uint16_t)(b[0]|b[1]<<8); }
static void p32(uint8_t *b,uint32_t x) { for(unsigned i=0;i<4;i++)b[i]=(uint8_t)(x>>(8*i)); }
static void p16(uint8_t *b,uint16_t x) { b[0]=(uint8_t)x;b[1]=(uint8_t)(x>>8); }
static int fail(Setup *s,const char *message) { snprintf(s->error,s->error_size,"%s",message);return -1; }
static void report(Setup *s,unsigned n,const char *message) { if(s->progress)s->progress(s->context,n,message); }
static int join(char *out,size_t size,const char *a,const char *b) { int n=snprintf(out,size,"%s/%s",a,b);return n<0||(size_t)n>=size?-1:0; }
static char lower(char c) { return c>='A'&&c<='Z'?(char)(c+32):c; }
static int equal(const char *a,const char *b) { while(*a&&*b&&lower(*a)==lower(*b)){a++;b++;}return !*a&&!*b; }
static int starts(const char *a,const char *b) { while(*b){if(lower(*a++)!=lower(*b++))return 0;}return 1; }
static int mkdirs(const char *path) {
    char b[PATH_CAP];struct stat st;
    if(strlen(path)>=sizeof(b))return -1;
    strcpy(b,path);
    for(char *p=b+1;;p++)if(*p=='/'||!*p){char end=*p;*p=0;
        if(stat(b,&st)){if(mkdir(b,0777)&&errno!=EEXIST)return -1;}
        else if(!S_ISDIR(st.st_mode))return -1;
        *p=end;if(!end)break;
    }
    return 0;
}
/* Resolve only relative components under the supplied game directory. */
static int resolve(char *out,const char *root,const char *relative) {
    char part[256]; const char *p=relative;
    if(*p=='/'||strchr(p,':')||strlen(root)>=PATH_CAP)return -1;
    strcpy(out,root);
    while(*p){size_t n=0;while(*p&&*p!='/'){if(n+1>=sizeof(part))return -1;part[n++]=*p++;}part[n]=0;
        if(!n||!strcmp(part,".")||!strcmp(part,".."))return -1;
        DIR *d=opendir(out);struct dirent *e;char actual[256]={0};if(!d)return -1;
        while((e=readdir(d)))if(equal(e->d_name,part)){snprintf(actual,sizeof(actual),"%s",e->d_name);break;}
        closedir(d);if(!actual[0])return -1;
        size_t used=strlen(out);if(used+strlen(actual)+2>=PATH_CAP)return -1;
        out[used++]='/';strcpy(out+used,actual);if(*p)p++;
    }return 0;
}
static int exists(const char *path) { struct stat st;return !stat(path,&st)&&S_ISREG(st.st_mode); }
static void hash_bytes(Setup *s,const void *data,size_t size) { const uint8_t *p=data;while(size--)s->fingerprint=(s->fingerprint^*p++)*UINT64_C(1099511628211); }
static uint32_t crc_table[256];
static void crc_init(void) { for(unsigned i=0;i<256;i++){uint32_t n=i;for(unsigned j=0;j<8;j++)n=(n>>1)^((n&1)?0xedb88320u:0);crc_table[i]=n;} }
static uint32_t crc_add(uint32_t n,const uint8_t *data,size_t size) { while(size--)n=crc_table[(n^*data++)&255]^(n>>8);return n; }
static void archive_crypt(uint8_t *data,size_t size,const uint8_t *key,int encrypt) {
    struct AES_ctx aes;AES_init_ctx(&aes,key);size&=~(size_t)15;
    for(unsigned pass=0;pass<16;pass++)for(size_t i=0;i<size;i+=16){if(encrypt)AES_ECB_encrypt(&aes,data+i);else AES_ECB_decrypt(&aes,data+i);}
}
static int executable_key(Setup *s,const char *game) {
    char path[PATH_CAP];struct stat st;
    if(resolve(path,game,"GTAIV.exe"))return fail(s,"Copy your GTA IV folder to /data/gtaiv/game/");
    if(stat(path,&st)||st.st_size<0xc95ff8||st.st_size>64*1024*1024)return fail(s,"This build needs GTA IV 1.0.8.0 game files");
    FILE *f=fopen(path,"rb");if(!f)return fail(s,"Cannot read GTAIV.exe");
    uint8_t *data=setup_alloc(65536);if(!data){fclose(f);return fail(s,"Cannot map memory to check game files");}
    int version=0,ok=1;size_t carry=0,n;
    while((n=fread(data+carry,1,65536-carry,f))){
        size_t used=carry+n;
        for(size_t i=0;i+24<=used;i++)if(u32(data+i)==0xfeef04bdu&&u32(data+i+4)==0x10000u&&u32(data+i+8)==0x10000u&&u32(data+i+12)==0x80000u){version=1;break;}
        carry=used<23?used:23;memmove(data,data+used-carry,carry);
    }
    if(ferror(f)||fseek(f,0xc95fd8,SEEK_SET)||fread(s->key,1,32,f)!=32)ok=0;
    fclose(f);setup_release(data,65536);
    if(!ok)return fail(s,"Cannot read GTAIV.exe completely");
    if(!version)return fail(s,"This build supports the tested GTA IV 1.0.8.0 version");
    hash_bytes(s,&st.st_size,sizeof(st.st_size));hash_bytes(s,&st.st_mtime,sizeof(st.st_mtime));
    if(resolve(path,game,"xlive.dll"))return fail(s,"Include the compatibility files from your working GTA IV folder");
    return 0;
}
static int add_archive(Setup *s,const char *path) {
    struct stat st;uint8_t head[20];FILE *f=fopen(path,"rb");
    if(!f||stat(path,&st)||fread(head,1,20,f)!=20){if(f)fclose(f);return fail(s,"A map archive is missing or incomplete");}
    int encrypted=u32(head)!=0xa94e2a52u;if(encrypted)archive_crypt(head,20,s->key,0);
    uint32_t count=u32(head+8),size=u32(head+12);
    if(u32(head)!=0xa94e2a52u||u32(head+4)!=3||u16(head+16)!=16||u16(head+18)!=233||count>MAX_ENTRIES-s->count||size<count*16u||size>16*1024*1024||20u+(uint64_t)size>(uint64_t)st.st_size){fclose(f);return fail(s,"Unsupported or damaged map archive");}
    uint8_t *toc=setup_alloc(size);if(!toc){fclose(f);return fail(s,"Cannot map memory to prepare map files");}
    int read_ok=fread(toc,1,size,f)==size;fclose(f);
    if(!read_ok){setup_release(toc,size);return fail(s,"A map archive is incomplete");}
    if(encrypted)archive_crypt(toc,size,s->key,0);
    if(s->sources_count>=MAX_ARCHIVES){setup_release(toc,size);return fail(s,"Too many map archives");}
    Source *source=&s->sources[s->sources_count];snprintf(source->path,sizeof(source->path),"%s",path);source->size=(uint64_t)st.st_size;source->modified=(int64_t)st.st_mtime;
    hash_bytes(s,path,strlen(path));hash_bytes(s,&source->size,sizeof(source->size));hash_bytes(s,&source->modified,sizeof(source->modified));
    size_t cursor=(size_t)count*16;
    for(uint32_t i=0;i<count;i++){
        Entry *e=&s->entries[s->count];uint8_t *r=toc+i*16;size_t n=0;
        while(cursor+n<size&&toc[cursor+n])n++;
        if(!n||n>=sizeof(e->name)||cursor+n>=size){setup_release(toc,size);return fail(s,"Invalid map asset name");}
        memcpy(e->name,toc+cursor,n);e->name[n]=0;cursor+=n+1;
        e->flags=u32(r);e->type=u32(r+4);e->sector=u32(r+8);e->blocks=u16(r+12);e->padding=u16(r+14);e->source=s->sources_count;
        uint64_t bytes=(uint64_t)e->blocks*BLOCK;
        if(!bytes||(uint64_t)e->sector*BLOCK+bytes>source->size||(e->padding&2047)>bytes){setup_release(toc,size);return fail(s,"Invalid map asset bounds");}
        for(unsigned j=0;j<s->count;j++)if(equal(s->entries[j].name,e->name)){setup_release(toc,size);return fail(s,"Conflicting map assets: use the tested game folder");}
        s->payload_bytes+=bytes;s->count++;
    }
    setup_release(toc,size);s->sources_count++;return 0;
}
static int read_text(const char *path,char *out,size_t capacity) { FILE *f=fopen(path,"rb");if(!f)return -1;size_t n=fread(out,1,capacity-1,f);int extra=fgetc(f);fclose(f);out[n]=0;return extra==EOF?0:-1; }
static int write_file(const char *path,const void *data,size_t size) { FILE *f=fopen(path,"wb");if(!f)return -1;int ok=fwrite(data,1,size,f)==size;int rc=fclose(f);return ok&&!rc?0:-1; }
/* Bound each stdio write, including the index, rather than passing a whole
 * archive index to the console's stdio implementation in one call. */
static int write_chunks(FILE *file,const void *data,size_t size) {
    const uint8_t *p=data;
    while(size){size_t n=size>16384?16384:size;if(fwrite(p,1,n,file)!=n)return -1;p+=n;size-=n;}
    return 0;
}
static int validate_payload(const char *path,uint64_t start,uint64_t length,uint32_t wanted,uint8_t *b) {
    FILE *f=fopen(path,"rb");if(!f||fseek(f,(long)start,SEEK_SET)){if(f)fclose(f);return -1;}
    uint32_t crc=0xffffffffu;
    while(length){size_t n=length>65536?65536:(size_t)length;if(fread(b,1,n,f)!=n){fclose(f);return -1;}crc=crc_add(crc,b,n);length-=n;}
    fclose(f);return (crc^0xffffffffu)==wanted?0:-1;
}
static int same_prefix(const char *a,const char *b,uint64_t bytes) {
    FILE *x=fopen(a,"rb"),*y=fopen(b,"rb");uint8_t bx[4096],by[4096];int same=x&&y;
    while(same&&bytes){size_t n=bytes>sizeof(bx)?sizeof(bx):(size_t)bytes;
        if(fread(bx,1,n,x)!=n||fread(by,1,n,y)!=n||memcmp(bx,by,n))same=0;
        bytes-=n;
    }if(x)fclose(x);if(y)fclose(y);return same;
}
static int prepare_maps(Setup *s,const char *game,const char *state) {
    char episode[PATH_CAP],list[PATH_CAP],backup[PATH_CAP],bundle[PATH_CAP],temp[PATH_CAP],marker[PATH_CAP];
    char *original=setup_alloc(MAX_LIST),*current=setup_alloc(MAX_LIST),*updated=setup_alloc(MAX_LIST);
    int result=-1;FILE *output=NULL;
    if(!original||!current||!updated){fail(s,"Not enough memory to prepare game files");goto done;}
    if(resolve(episode,game,"TBoGT")){result=0;goto done;}
    char plugin[PATH_CAP];if(resolve(plugin,game,"plugins/ZolikaPatch.asi")){fail(s,"Include the episode compatibility files from your working folder");goto done;}
    if(resolve(list,episode,"common/data/images.txt")||read_text(list,current,MAX_LIST)){fail(s,"The Tony episode image list is missing");goto done;}
    if(join(backup,sizeof(backup),episode,"common/data/images-before-pw-map-bundle.txt")||join(bundle,sizeof(bundle),episode,"pc/data/maps/pw_tbogt_maps.img")||join(marker,sizeof(marker),state,"maps-ready-v1.txt")){fail(s,"Game folder path is too long");goto done;}
    int already=strstr(current,"pc/data/maps/pw_tbogt_maps")!=NULL;
    if(already){if(read_text(backup,original,MAX_LIST)){fail(s,"The original Tony image list is needed to verify this bundle");goto done;}}
    else strcpy(original,current);
    size_t used=0;int inserted=0;char *line=original;
    while(*line){char *end=strchr(line,'\n');size_t length=end?(size_t)(end-line):strlen(line);while(length&&(line[length-1]=='\r'||line[length-1]==' '||line[length-1]=='\t'))length--;
        char token[PATH_CAP];if(length>=sizeof(token)){fail(s,"Invalid episode image list");goto done;}memcpy(token,line,length);token[length]=0;
        char *p=token;while(*p==' '||*p=='\t')p++;
        if(starts(p,"pc/data/maps/")){
            char relative[PATH_CAP],resolved[PATH_CAP];if(snprintf(relative,sizeof(relative),"%s.img",p)>=(int)sizeof(relative)||resolve(resolved,episode,relative)){fail(s,"An episode map archive is missing");goto done;}if(add_archive(s,resolved))goto done;
            report(s,5+s->sources_count/3,"Checking episode map files");
            if(!inserted){const char *replacement="pc/data/maps/pw_tbogt_maps\r\n";size_t n=strlen(replacement);if(used+n>=MAX_LIST){fail(s,"Episode image list is too large");goto done;}memcpy(updated+used,replacement,n);used+=n;inserted=1;}
            int n=snprintf(updated+used,MAX_LIST-used,"# PW bundled: %s\r\n",p);if(n<0||(size_t)n>=MAX_LIST-used){fail(s,"Episode image list is too large");goto done;}used+=(size_t)n;
        }else{if(used+length+3>=MAX_LIST){fail(s,"Episode image list is too large");goto done;}memcpy(updated+used,line,length);used+=length;memcpy(updated+used,"\r\n",2);used+=2;updated[used]=0;}
        line=end?end+1:line+strlen(line);
    }
    if(s->sources_count!=56||!s->count){fail(s,"This Tony map layout differs from the tested game files");goto done;}
    struct stat bundle_stat;char marker_text[160];unsigned long long saved_hash=0,saved_size=0;long long saved_time=0;
    if(already&&!stat(bundle,&bundle_stat)&&!read_text(marker,marker_text,sizeof(marker_text))&&sscanf(marker_text,"GTAIV-MAPS-1 %llx %llu %lld",&saved_hash,&saved_size,&saved_time)==3&&saved_hash==s->fingerprint&&saved_size==(unsigned long long)bundle_stat.st_size&&saved_time==(long long)bundle_stat.st_mtime){result=0;goto done;}
    size_t names_size=0;for(unsigned i=0;i<s->count;i++)names_size+=strlen(s->entries[i].name)+1;
    size_t toc_size=(size_t)s->count*16+names_size;uint8_t *toc=setup_alloc(toc_size);if(!toc){fail(s,"Cannot map memory for map index");goto done;}
    uint64_t start=((uint64_t)20+toc_size+2047)&~UINT64_C(2047),position=start;size_t name_offset=(size_t)s->count*16;
    for(unsigned i=0;i<s->count;i++){Entry *e=&s->entries[i];uint8_t *r=toc+i*16;e->output=position;p32(r,e->flags);p32(r+4,e->type);p32(r+8,(uint32_t)(position/BLOCK));p16(r+12,e->blocks);p16(r+14,e->padding);size_t n=strlen(e->name)+1;memcpy(toc+name_offset,e->name,n);name_offset+=n;position+=(uint64_t)e->blocks*BLOCK;}
    uint8_t head[20]={0};p32(head,0xa94e2a52u);p32(head+4,3);p32(head+8,s->count);p32(head+12,(uint32_t)toc_size);p16(head+16,16);p16(head+18,233);archive_crypt(head,20,s->key,1);archive_crypt(toc,toc_size,s->key,1);
    if(snprintf(temp,sizeof(temp),"%s.gtaiv-new",bundle)>=(int)sizeof(temp)){setup_release(toc,toc_size);fail(s,"Game folder path is too long");goto done;}
    output=fopen(temp,"wb");if(!output){setup_release(toc,toc_size);fail(s,"Cannot create map bundle - check free storage");goto done;}
    report(s,25,"Writing prepared map index");
    int header_ok=!write_chunks(output,head,20)&&!write_chunks(output,toc,toc_size);setup_release(toc,toc_size);
    if(!header_ok){fail(s,"Cannot write map index");goto done;}
    uint8_t *bytes=s->io;memset(bytes,0,65536);uint64_t pad=start-20-toc_size;if(pad&&write_chunks(output,bytes,(size_t)pad)){fail(s,"Cannot write map bundle");goto done;}
    uint32_t crc=0xffffffffu;uint64_t copied=0;
    for(unsigned i=0;i<s->count;i++){Entry *e=&s->entries[i];FILE *input=fopen(s->sources[e->source].path,"rb");uint64_t left=(uint64_t)e->blocks*BLOCK;
        if(!input||fseek(input,(long)((uint64_t)e->sector*BLOCK),SEEK_SET)){if(input)fclose(input);fail(s,"Cannot read a source map asset");goto done;}
        while(left){size_t n=left>65536?65536:(size_t)left;if(fread(bytes,1,n,input)!=n||write_chunks(output,bytes,n)){fclose(input);fail(s,"Map preparation stopped - check files and free storage");goto done;}crc=crc_add(crc,bytes,n);left-=n;copied+=n;}
        fclose(input);if(!(i%32))report(s,25+(unsigned)(copied*60/s->payload_bytes),"Preparing episode map bundle");
    }
    if(fclose(output)){output=NULL;fail(s,"Cannot finish map bundle");goto done;}output=NULL;
    report(s,90,"Verifying prepared map files");
    if(validate_payload(temp,start,s->payload_bytes,crc^0xffffffffu,s->io)){fail(s,"Map bundle verification failed");goto done;}
    /* An already working bundle is retained byte-for-byte when its payload
     * matches the same sources. This is used when testing an existing folder. */
    if(already&&!stat(bundle,&bundle_stat)&&(uint64_t)bundle_stat.st_size==position&&same_prefix(bundle,temp,start)&&!validate_payload(bundle,start,s->payload_bytes,crc^0xffffffffu,s->io))unlink(temp);
    else {
        if(!already&&exists(backup)){fail(s,"An original image-list backup already exists - check the game folder");goto done;}
        if(!already&&write_file(backup,current,strlen(current))){fail(s,"Cannot preserve the original image list");goto done;}
        if(rename(temp,bundle)){fail(s,"Cannot activate the prepared map bundle");goto done;}
        char list_temp[PATH_CAP];if(snprintf(list_temp,sizeof(list_temp),"%s.gtaiv-new",list)>=(int)sizeof(list_temp)||write_file(list_temp,updated,used)||rename(list_temp,list)){fail(s,"Cannot activate episode image list; original backup preserved");goto done;}
    }
    if(stat(bundle,&bundle_stat)){fail(s,"Prepared map bundle is missing");goto done;}
    snprintf(marker_text,sizeof(marker_text),"GTAIV-MAPS-1 %llx %llu %lld\n",(unsigned long long)s->fingerprint,(unsigned long long)bundle_stat.st_size,(long long)bundle_stat.st_mtime);
    if(write_file(marker,marker_text,strlen(marker_text))){fail(s,"Cannot save setup state");goto done;}
    result=0;
done:if(output)fclose(output);setup_release(original,MAX_LIST);setup_release(current,MAX_LIST);setup_release(updated,MAX_LIST);return result;
}
int gtaiv_prepare_game(const char *game,const char *state,GtaivProgress progress,void *context,char *error,size_t error_size) {
    Setup *s=setup_alloc(sizeof(*s));if(!s){snprintf(error,error_size,"Cannot map memory for game setup");return -1;}s->error=error;s->error_size=error_size;s->progress=progress;s->context=context;s->fingerprint=UINT64_C(14695981039346656037);
    s->entries=setup_alloc(MAX_ENTRIES*sizeof(*s->entries));int rc=-1;
    if(!s->entries){fail(s,"Cannot map memory for game preparation");goto done;}
    s->io=setup_alloc(65536);if(!s->io){fail(s,"Cannot map setup transfer buffer");goto done;}
    if(mkdirs(state)){fail(s,"Cannot create app data folder");goto done;}
    report(s,1,"Checking game files");crc_init();
    if(executable_key(s,game))goto done;
    char path[PATH_CAP];if(resolve(path,game,"common")||resolve(path,game,"pc")){fail(s,"Copy the complete GTA IV game folder");goto done;}
    rc=prepare_maps(s,game,state);if(!rc)report(s,100,"Game files ready");
done:setup_release(s->io,65536);setup_release(s->entries,MAX_ENTRIES*sizeof(*s->entries));memset(s->key,0,sizeof(s->key));setup_release(s,sizeof(*s));return rc;
}
static int copy_tree(const char *source,const char *dest,unsigned depth) {
    if(depth>24||mkdirs(dest))return -1;
    DIR *d=opendir(source);if(!d)return -1;
    struct dirent *entry;int result=0;uint8_t *buffer=setup_alloc(65536);if(!buffer){closedir(d);return -1;}
    while((entry=readdir(d))){if(!strcmp(entry->d_name,".")||!strcmp(entry->d_name,".."))continue;char a[PATH_CAP],b[PATH_CAP];struct stat st;
        if(join(a,sizeof(a),source,entry->d_name)||join(b,sizeof(b),dest,entry->d_name)||stat(a,&st)){result=-1;break;}
        if(S_ISDIR(st.st_mode)){if(copy_tree(a,b,depth+1)){result=-1;break;}}
        else if(S_ISREG(st.st_mode)&&!exists(b)){char staging[PATH_CAP];if(snprintf(staging,sizeof(staging),"%s.gtaiv-copy",b)>=(int)sizeof(staging)){result=-1;break;}
            FILE *in=fopen(a,"rb"),*out=in?fopen(staging,"wb"):NULL;size_t n;int ok=in&&out;
            while(ok&&(n=fread(buffer,1,65536,in)))if(fwrite(buffer,1,n,out)!=n)ok=0;
            if(in&&ferror(in))ok=0;
            if(in)fclose(in);
            if(out&&fclose(out))ok=0;
            if(!ok||rename(staging,b)){unlink(staging);result=-1;break;}
        }
    }setup_release(buffer,65536);closedir(d);return result;
}
int gtaiv_copy_template(const char *source,const char *destination,GtaivProgress progress,void *context,char *error,size_t error_size) {
    if(progress)progress(context,0,"Preparing app storage");
    if(copy_tree(source,destination,0)){snprintf(error,error_size,"Cannot prepare app storage - check available space");return -1;}return 0;
}
#ifdef GTAIV_SETUP_HOST_TEST
static void print_progress(void *unused,unsigned n,const char *message){(void)unused;fprintf(stderr,"%u %s\n",n,message);}
int main(int argc,char **argv){char error[256]={0};if(argc!=3)return 2;int rc=gtaiv_prepare_game(argv[1],argv[2],print_progress,NULL,error,sizeof(error));if(rc)fprintf(stderr,"ERROR: %s\n",error);return rc?1:0;}
#endif
