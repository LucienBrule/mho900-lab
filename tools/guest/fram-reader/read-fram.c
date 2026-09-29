/* Bounded ARM64 Linux I2C read wrapper. Controller must independently bind the
 * expected node to the live stock CFram fd/adapter. No inference of that binding. */
#include "../fram-contract/fram-read.h"
typedef unsigned long U; typedef long S;
struct stat64 { U dev,ino; unsigned mode,nlink,uid,gid; U rdev,pad1; S size; int blksize,pad2; S blocks,atime; U atime_ns; S mtime; U mtime_ns; S ctime; U ctime_ns; unsigned unused[2]; };
_Static_assert(sizeof(struct stat64)==128,"ARM64 stat");
#ifdef FRAM_HOST_TEST
static S syscall6(S,U,U,U,U,U,U);
#else
void *memset(void *p,int value,size_t n){volatile unsigned char *q=p;for(size_t i=0;i<n;i++)q[i]=(unsigned char)value;return p;}
static S syscall6(S n,U a,U b,U c,U d,U e,U f) {
 register U x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f;
 register S x8 __asm__("x8")=n;
 __asm__ volatile("svc 0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory");return (S)x0;
}
#endif
/* Fixed 64-byte little-endian journal record, including scratch on failure. */
struct transaction { U round,offset; S result; U error; unsigned char selector[2],scratch[16],reserved[14]; };
_Static_assert(sizeof(struct transaction)==64,"journal record");
struct state { S device,directory,journal; U round,calls; int evidence_error; };
static int number(const char*s,U*out){U n=0;if(!*s)return 0;while(*s){if(*s<'0'||*s>'9'||n>(~0UL-(U)(*s-'0'))/10)return 0;n=n*10+(U)(*s++-'0');}*out=n;return 1;}
static int save(struct state*s,const char*name,const void*data,U n){
 S f=syscall6(56,(U)s->directory,(U)name,0xa00c1,0600,0,0);if(f<0)return 0;
 S r=syscall6(64,(U)f,(U)data,n,0,0,0),sync=syscall6(82,(U)f,0,0,0,0,0),close=syscall6(57,(U)f,0,0,0,0,0);return r==(S)n&&sync==0&&close==0;
}
static int transfer(void*context,struct fram_rdwr*r){
 struct state*s=context; struct transaction t={0};
 t.round=s->round;t.offset=((U)r->msgs[0].buf[0]<<8)|r->msgs[0].buf[1];
 t.selector[0]=r->msgs[0].buf[0];t.selector[1]=r->msgs[0].buf[1];
 if(s->calls>=1024||r->nmsgs!=2||r->msgs[0].addr!=0x50||r->msgs[0].flags||r->msgs[0].len!=2||r->msgs[1].addr!=0x50||r->msgs[1].flags!=1||r->msgs[1].len!=16)return -1;
 t.result=syscall6(29,(U)s->device,0x707,(U)r,0,0,0);s->calls++;
 t.error=t.result<0?(U)-t.result:0;
 for(U i=0;i<16;i++)t.scratch[i]=r->msgs[1].buf[i];
 /* Never continue acquisition after evidence write failure. No syscall retry. */
 if(syscall6(64,(U)s->journal,(U)&t,sizeof t,0,0,0)!=(S)sizeof t||syscall6(82,(U)s->journal,0,0,0,0,0)!=0){s->evidence_error=1;return -1;}
 return (int)t.result;
}
static char manifest[2048];static U used;
static void append(const char*s){while(*s)manifest[used++]=*s++;}
static void num(U v){char b[24];U n=0;do{b[n++]=(char)('0'+v%10);v/=10;}while(v);while(n)manifest[used++]=b[--n];}
static int run(int argc,char**argv){
 struct state s={-1,-1,-1,0,0,0};struct stat64 st={0};U major=0,minor=0;const char*stage="arguments";int ok=0,equal=0;size_t completed[2]={0,0};unsigned char images[2][8192]={{0}};
 if(argc!=5||argv[1][0]!='/'||argv[4][0]!='/'||!number(argv[2],&major)||!number(argv[3],&minor)||major>0xffffffffUL||minor>0xffffffffUL)return 3;
 if(syscall6(34,(U)-100,(U)argv[4],0700,0,0,0)!=0)return 4;
 s.directory=syscall6(56,(U)-100,(U)argv[4],0xb0000,0,0,0);if(s.directory<0)return 4;
 stage="open-device";s.device=syscall6(56,(U)-100,(U)argv[1],0xa0002,0,0,0);if(s.device<0)goto finish;
 stage="device-identity";if(syscall6(80,(U)s.device,(U)&st,0,0,0,0)!=0)goto finish;
 U observed_major=((st.rdev>>8)&0xfff)|((st.rdev>>32)&0xfffff000),observed_minor=(st.rdev&0xff)|((st.rdev>>12)&0xffffff00);
 if((st.mode&0170000)!=0020000||major!=observed_major||minor!=observed_minor)goto finish;
 stage="journal";s.journal=syscall6(56,(U)s.directory,(U)"transactions.bin",0xa00c1,0600,0,0);if(s.journal<0)goto finish;
 for(s.round=0;s.round<2;s.round++){
  stage="transfer";int result=fram_image(transfer,&s,images[s.round],&completed[s.round]);
  if(!save(&s,s.round?"image-2.bin":"image-1.bin",images[s.round],completed[s.round])){s.evidence_error=1;goto finish;}
  if(result)goto finish;
 }
 stage="image-equality";equal=1;for(U i=0;i<8192;i++)if(images[0][i]!=images[1][i])equal=0;
 if(!equal)goto finish;stage="complete";ok=1;
finish:
 if(s.journal>=0&&syscall6(57,(U)s.journal,0,0,0,0,0)!=0)s.evidence_error=1;
 if(s.device>=0&&syscall6(57,(U)s.device,0,0,0,0,0)!=0)s.evidence_error=1;
 used=0;append("schema_version = \"mho900-lab.fram-reader/1\"\nresult = \"");append(ok&&!s.evidence_error?"accepted":"rejected");append("\"\nstage = \"");append(stage);append("\"\nexpected_major = ");num(major);append("\nexpected_minor = ");num(minor);append("\nobserved_rdev = ");num(st.rdev);append("\nobserved_mode = ");num(st.mode);append("\ntransactions = ");num(s.calls);append("\ncompleted_1 = ");num(completed[0]);append("\ncompleted_2 = ");num(completed[1]);append("\nimages_equal = ");append(equal?"true":"false");append("\nevidence_error = ");append(s.evidence_error?"true":"false");append("\nmaximum_transactions = 1024\nimage_bytes = 8192\npage_bytes = 16\nslave_address = 80\nretry_count = 0\nforce_slave = false\nfram_data_writes = false\natomic_snapshot_proven = false\n");
 if(!save(&s,"manifest.toml",manifest,used))s.evidence_error=1;
 if(syscall6(82,(U)s.directory,0,0,0,0,0)!=0)s.evidence_error=1;
 if(syscall6(57,(U)s.directory,0,0,0,0,0)!=0)s.evidence_error=1;
 return s.evidence_error?4:ok?0:3;
}
#ifndef FRAM_HOST_TEST
__attribute__((noreturn)) void reader_main(U*stack){int result=run((int)stack[0],(char**)(stack+1));syscall6(94,(U)result,0,0,0,0,0);for(;;){}}
__asm__(".global _start\n_start:\n mov x0, sp\n bl reader_main\n");
#endif
