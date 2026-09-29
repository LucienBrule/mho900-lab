/* Disposable deterministic process-memory ownership/cache fixture.
 * Maps pinned APK bytes but never calls them or accesses instrument devices. */
typedef unsigned long U;
typedef long S;
static S syscall6(S n,U a,U b,U c,U d,U e,U f) {
  register U x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,
    x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f;
  register S x8 __asm__("x8")=n;
  __asm__ volatile("svc 0" : "+r"(x0) : "r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8) : "memory");
  return (S)x0;
}
static int same(const char*a,const char*b) { while(*a&&*a==*b){a++;b++;}return *a==*b; }
static void fail(void) { syscall6(64,2,(U)"fixture rejected\n",17,0,0,0);syscall6(94,3,0,0,0,0,0);for(;;){} }
static void check(int v) { if(!v)fail(); }
static void word(U a,U v) { *(volatile U*)a=v; }
static void integer(U a,unsigned int v) { *(volatile unsigned int*)a=v; }
__attribute__((noreturn)) void fixture_main(U *stack) {
  check(stack[0]==2||stack[0]==3);
  const char *mode=stack[0]==3?(const char*)stack[3]:"positive";
  check(same(mode,"positive")||same(mode,"bad-backlink")||same(mode,"bad-vtable")||same(mode,"wrong-id")||same(mode,"oversize-vector"));
  S fd=syscall6(56,(U)-100,stack[2],0x80000,0,0,0);check(fd>=0);
  S raw=syscall6(222,0,0x3cb5000,0,0x22,(U)-1,0);check(raw>0);U base=(U)raw;
  check(syscall6(222,base,0xb69000,5,0x12,(U)fd,0xf05000)==(S)base);
  check(syscall6(222,base+0xb69000,0x78000,3,0x12,(U)fd,0x1a6d000)==(S)(base+0xb69000));
  /* Populate only private COW metadata: this is not dynamic execution/loading. */
  U vp=base+0xb6c3a0,ti=base+0xb6c440;
  word(vp,0);word(vp+8,ti);word(vp+64,(U)-8);word(vp+72,ti);word(vp+104,(U)-72);word(vp+112,ti);
  check(syscall6(226,base+0xb69000,0x26000,1,0,0,0)==0);
  check(syscall6(222,0,0xf2000,5,2,(U)fd,0x73f000)>0);
  S allocation=syscall6(222,0,0x6000,3,0x22,(U)-1,0);check(allocation>0);U heap=(U)allocation;
  U item=heap+0x100,setup=heap+0x200,work=heap+0x1000,reference=heap+0x3000;
  word(base+0xbe0f18,heap);word(base+0xbe0f20,heap+8);word(base+0xbe0f28,heap+8);
  word(heap,item);integer(item,38);word(item+32,setup+8);
  word(setup,vp+16);word(setup+8,vp+80);word(setup+16,item);word(setup+72,vp+120);
  integer(setup+88,3);integer(setup+92,0x50);integer(setup+96,8192);
  word(setup+104,work);word(setup+112,reference);
  /* Empty valid stock-format MemFile: length8 and its int32 negation. */
  integer(work+256,8);integer(work+260,0xfffffff8U);
  integer(reference+256,8);integer(reference+260,0xfffffff8U);
  if(same(mode,"bad-backlink"))word(setup+16,item+8);
  if(same(mode,"bad-vtable"))word(setup+8,vp+16);
  if(same(mode,"wrong-id"))integer(item,37);
  if(same(mode,"oversize-vector")){word(base+0xbe0f20,heap+65*8);word(base+0xbe0f28,heap+65*8);}
  check(syscall6(57,(U)fd,0,0,0,0,0)==0);
  check(syscall6(64,1,(U)"ready\n",6,0,0,0)==6);
  for(;;){S delay[2]={1,0};syscall6(101,(U)delay,0,0,0,0,0);}
}
__asm__(".global _start\n_start:\n mov x0, sp\n bl fixture_main\n");
