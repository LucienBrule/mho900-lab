#define FRAM_HOST_TEST
#include "read-fram.c"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static int mode,ioctls,journal_count;static U sizes[2];static struct transaction records[1024];static char report[2048];
static S syscall6(S n,U a,U b,U c,U d,U e,U f){
 (void)d;(void)e;(void)f;
 if(n==34)return 0;
 if(n==56){const char*p=(const char*)b;
  if(!strcmp(p,"/output")){assert(c==0x8c000);return 10;}
  if(!strcmp(p,"/device")){assert(c==0x88002);return mode==9?-13:11;}
  assert(c==0x880c1);
  if(!strcmp(p,"transactions.bin"))return 12;
  if(!strcmp(p,"image-1.bin"))return 13;
  if(!strcmp(p,"image-2.bin"))return 14;
  if(!strcmp(p,"manifest.toml"))return 15;
  assert(0);
 }
 if(n==80){if(mode==10)return -5;struct stat64*s=(void*)b;s->mode=mode==5?0100600:0020600;s->rdev=(89UL<<8)| (mode==1?2:1);return 0;}
 if(n==29){assert(a==11&&b==0x707);struct fram_rdwr*r=(void*)c;assert(r->nmsgs==2);assert(r->msgs[0].addr==80&&r->msgs[0].flags==0&&r->msgs[0].len==2);assert(r->msgs[1].addr==80&&r->msgs[1].flags==1&&r->msgs[1].len==16);
  U off=(U)r->msgs[0].buf[0]*256+r->msgs[0].buf[1];assert(off==(U)(ioctls%512)*16);
  for(int i=0;i<16;i++)r->msgs[1].buf[i]=(unsigned char)(off+(U)i+(mode==4&&ioctls>=512));
  ioctls++;if(ioctls==3&&mode==2)return 1;if(ioctls==3&&mode==3)return -5;return 2;
 }
 if(n==64){assert(a!=11);if(a==12){assert(c==64);records[journal_count++]=*(struct transaction*)b;if(mode==6)return 32;}if(a==13||a==14){sizes[a-13]=c;if(mode==8)return -28;}if(a==15){assert(c<sizeof report);memcpy(report,(void*)b,c);report[c]=0;}return (S)c;}
 if(n==82&&a==12&&mode==7)return -5;
 if(n==82||n==57)return 0;
 assert(0);return -1;
}
int main(void){char*args[]={"read-fram","/device","89","1","/output"};
 for(mode=0;mode<11;mode++){
  ioctls=journal_count=0;sizes[0]=sizes[1]=0;memset(records,0,sizeof records);
  int result=run(5,args);assert(result==((mode>=6&&mode<=8)?4:mode?3:0));
  if(mode==9||mode==10){assert(!ioctls&&!journal_count);assert(strstr(report,mode==9?"open-device":"device-identity"));}
  else if(mode==6||mode==7){assert(ioctls==1&&journal_count==1&&sizes[0]==0&&sizes[1]==0);assert(strstr(report,"evidence_error = true"));}
  else if(mode==8){assert(ioctls==512&&journal_count==512&&sizes[0]==8192&&sizes[1]==0);assert(strstr(report,"evidence_error = true"));}
  else if(mode==1||mode==5){assert(!ioctls&&!journal_count);assert(strstr(report,"device-identity"));}
  else if(mode==2||mode==3){assert(ioctls==3&&journal_count==3&&sizes[0]==32&&sizes[1]==0);assert(records[2].scratch[0]==32);assert(records[2].result==(mode==2?1:-5));assert(records[2].error==(U)(mode==2?0:5));}
  else{assert(ioctls==1024&&journal_count==1024&&sizes[0]==8192&&sizes[1]==8192);assert(strstr(report,mode==4?"image-equality":"complete"));}
 }
 puts("actual_wrapper_syscall_controls = 11\npassed = true");return 0;
}
