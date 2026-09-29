/* Disposable mapping control: never execute stock code or access instrument devices. */
typedef unsigned long U;
typedef long S;
static S syscall6(S n, U a, U b, U c, U d, U e, U f) {
  register U x0 __asm__("x0")=a, x1 __asm__("x1")=b, x2 __asm__("x2")=c,
    x3 __asm__("x3")=d, x4 __asm__("x4")=e, x5 __asm__("x5")=f;
  register S x8 __asm__("x8")=n;
  __asm__ volatile("svc 0" : "+r"(x0) : "r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8) : "memory");
  return (S)x0;
}
static void fail(void) {
  syscall6(64,2,(U)"fixture rejected\n",17,0,0,0);
  syscall6(94,3,0,0,0,0,0);
  for (;;) {}
}
static void check(int v) { if (!v) fail(); }
__attribute__((noreturn)) void fixture_main(U *stack) {
  check(stack[0]==2);
  S fd=syscall6(56,(U)-100,stack[2],0x80000,0,0,0);
  check(fd>=0);
  S raw=syscall6(222,0,0x3cb5000,0,0x22,(U)-1,0);
  check(raw>0); U base=(U)raw;
  check(syscall6(222,base,0xb69000,5,0x12,(U)fd,0xf05000)==(S)base);
  check(syscall6(222,base+0xb69000,0x78000,3,0x12,(U)fd,0x1a6d000)==(S)(base+0xb69000));
  check(syscall6(226,base+0xb69000,0x26000,1,0,0,0)==0);
  /* A distinct executable entry with the same APK inode must not become Auklet. */
  check(syscall6(222,0,0xf2000,5,2,(U)fd,0x73f000)>0);
  for (U i=0;i<8;i++) *(volatile unsigned char *)(base+0xbbccf0+i)=(unsigned char)(0x10+i);
  for (U i=0;i<16;i++) *(volatile unsigned char *)(base+0xbbcd1c+i)=(unsigned char)(0x20+i);
  check(syscall6(57,(U)fd,0,0,0,0,0)==0);
  check(syscall6(64,1,(U)"ready\n",6,0,0,0)==6);
  for (;;) { S delay[2]={1,0}; syscall6(101,(U)delay,0,0,0,0,0); }
}
__asm__(".global _start\n_start:\n mov x0, sp\n bl fixture_main\n");
