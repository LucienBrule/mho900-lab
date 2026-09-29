/* Linux ARM64 metadata-only probe: follows links with newfstatat flags0. */
#include <stddef.h>
typedef unsigned long U; typedef long S;
struct stat64 { U dev,ino; unsigned mode,nlink,uid,gid; U rdev,pad1; S size; int blksize,pad2; S blocks,atime; U atime_ns; S mtime; U mtime_ns; S ctime; U ctime_ns; unsigned unused[2]; };
_Static_assert(sizeof(struct stat64)==128,"ARM64 stat");
#ifdef STAT_HOST_TEST
static S syscall6(S,U,U,U,U,U,U);
#else
void *memset(void *p,int value,size_t n){volatile unsigned char *q=p;for(size_t i=0;i<n;i++)q[i]=(unsigned char)value;return p;}
static S syscall6(S n,U a,U b,U c,U d,U e,U f) {
 register U x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f;
 register S x8 __asm__("x8")=n;
 __asm__ volatile("svc 0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory");return (S)x0;
}
#endif

static char output[256];static U used;
static void text(const char*s){while(*s)output[used++]=*s++;}
static void number(U v){char b[24];U n=0;do{b[n++]=(char)('0'+v%10);v/=10;}while(v);while(n)output[used++]=b[--n];}
static int run(int argc,char**argv){
 used=0;if(argc!=2||argv[1][0]!='/'){text("stat-node: expected one absolute path\n");syscall6(64,2,(U)output,used,0,0,0);return 2;}
 struct stat64 st={0};S r=syscall6(79,(U)-100,(U)argv[1],(U)&st,0,0,0);
 if(r){text("stat-node: newfstatat errno = ");number(r<0?(U)-r:(U)r);text("\n");syscall6(64,2,(U)output,used,0,0,0);return 3;}
 text("mode = ");number(st.mode);text("\nmajor = ");number(((st.rdev>>8)&0xfff)|((st.rdev>>32)&0xfffff000));text("\nminor = ");number((st.rdev&0xff)|((st.rdev>>12)&0xffffff00));text("\ninode = ");number(st.ino);text("\ndevice = ");number(st.dev);text("\n");
 return syscall6(64,1,(U)output,used,0,0,0)==(S)used?0:4;
}
#ifndef STAT_HOST_TEST
__attribute__((noreturn)) void reader_main(U*stack){int result=run((int)stack[0],(char**)(stack+1));syscall6(94,(U)result,0,0,0,0,0);for(;;){}}
__asm__(".global _start\n_start:\n mov x0, sp\n bl reader_main\n");
#endif
