#define STAT_HOST_TEST
#include "stat-node.c"
#include <assert.h>
#include <string.h>
#include <stdio.h>
static int mode,calls,writes;static char result[256];static U destination;
static S syscall6(S n,U a,U b,U c,U d,U e,U f){
 (void)e;(void)f;
 if(n==79){assert(a==(U)-100&&!strcmp((char*)b,"/node")&&d==0);calls++;if(mode==1)return -2;struct stat64*s=(void*)c;s->mode=0020666;s->rdev=(1<<8)|3;s->ino=17;s->dev=9;return 0;}
 assert(n==64);writes++;destination=a;memcpy(result,(void*)b,c);result[c]=0;return mode==2?1:(S)c;
}
int main(void){char*args[]={"stat-node","/node"};
 for(mode=0;mode<3;mode++){calls=writes=0;int r=run(2,args);assert(calls==1&&writes==1&&r==(mode==0?0:mode==1?3:4));assert(destination==(U)(mode==1?2:1));if(mode==0)assert(!strcmp(result,"mode = 8630\nmajor = 1\nminor = 3\ninode = 17\ndevice = 9\n"));if(mode==1)assert(strstr(result,"errno = 2"));}
 args[1]="relative";calls=0;assert(run(2,args)==2&&calls==0&&destination==2);
 puts("host_controls_passed = 4");return 0;
}
