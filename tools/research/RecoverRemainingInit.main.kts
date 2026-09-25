// Recover the reviewed remaining initialization grammar from the pinned stock ELF.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 2) { "Usage: RecoverRemainingInit.main.kts STOCK_ELF NEW_OUTPUT_DIRECTORY" }
val input=Path.of(args[0]); val output=Path.of(args[1]); require(!Files.exists(output)) { "Output directory already exists" }
fun sha(bytes:ByteArray)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))
fun sha(path:Path):String=Files.newInputStream(path).use { s->val d=MessageDigest.getInstance("SHA-256"); val b=ByteArray(65536); while(true){val n=s.read(b);if(n<0)break;d.update(b,0,n)};HexFormat.of().formatHex(d.digest()) }
fun hx(v:Long,w:Int=0)="0x"+v.toString(16).padStart(w,'0')
fun q(s:String)="\""+s.replace("\\","\\\\").replace("\"","\\\"")+"\""
data class Seg(val off:Long,val va:Long,val size:Long,val memorySize:Long)
data class Sec(val type:Int,val off:Long,val size:Long,val link:Int,val entsize:Long)
data class Sym(val name:String,val va:Long,val size:Long,val shndx:Int)
data class Rel(val va:Long,val type:Long,val addend:Long,val sym:Sym?)
class Elf(val bytes:ByteArray) {
 private val d=ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
 private fun u16(i:Int)=d.getShort(i).toInt() and 0xffff
 private fun u32(i:Int)=d.getInt(i).toLong() and 0xffffffffL
 private fun u64(i:Int)=d.getLong(i)
 private val segs:List<Seg>; private val secs:List<Sec>; val syms:Map<String,Sym>; val rels:Map<Long,Rel>
 init {
  require(bytes.size>=64 && bytes.sliceArray(0 until 6).contentEquals(byteArrayOf(0x7f,0x45,0x4c,0x46,2,1)) && u16(18)==183)
  segs=(0 until u16(56)).map{u64(32).toInt()+it*u16(54)}.filter{u32(it)==1L}.map{Seg(u64(it+8),u64(it+16),u64(it+32),u64(it+40))}
  secs=(0 until u16(60)).map{u64(40).toInt()+it*u16(58)}.map{Sec(u32(it+4).toInt(),u64(it+24),u64(it+32),u32(it+40).toInt(),u64(it+56))}
  fun symbols(s:Sec):List<Sym>{require(s.entsize==24L);val st=secs[s.link];return (0 until (s.size/24).toInt()).map{n->val at=(s.off+n*24).toInt();val a=(st.off+u32(at)).toInt();var z=a;while(bytes[z]!=0.toByte())z++;Sym(String(bytes,a,z-a),u64(at+8),u64(at+16),u16(at+6))}}
  val dyn=secs.filter{it.type==11}.flatMap(::symbols)
  syms=dyn.filter{it.name.isNotEmpty()}.groupBy{it.name}.mapValues{(n,m)->val x=m.filter{it.shndx!=0};require(x.map{it.va to it.size}.distinct().size<=1){"conflicting $n"};x.singleOrNull()?:m.single()}
  rels=secs.filter{it.type==4}.flatMap{s->val linked=symbols(secs[s.link]);(0 until (s.size/s.entsize).toInt()).map{n->val at=(s.off+n*s.entsize).toInt();val info=u64(at+8);val si=(info ushr 32).toInt();Rel(u64(at),info and 0xffffffffL,u64(at+16),if(si==0)null else linked[si])}}.associateBy{it.va}
 }
 private fun off(va:Long,n:Int):Int { val m=segs.filter{va>=it.va&&va+n<=it.va+it.size};require(m.size==1){"not file backed ${hx(va)}"};return(m.single().off+va-m.single().va).toInt() }
 fun word(va:Long)=u32(off(va,4)); fun long(va:Long)=u64(off(va,8)); fun region(va:Long,n:Int)=bytes.copyOfRange(off(va,n),off(va,n)+n)
 fun zeroFilled(va:Long,n:Int):Boolean { val s=segs.single{va>=it.va&&va+n<=it.va+it.memorySize};return va>=s.va+s.size }
}
// Semantics are reviewed annotations; ELF checks bind them to specific code, not a general decompiler proof.
enum class Kind { STATIC_DETERMINED, RUNTIME_SELECTED, HARDWARE_RETURNED, ASYNCHRONOUS, UNKNOWN }
enum class Id { SCU, BOARD_OPEN, BOARD_FRAME, BOARD_WRITE, BOARD_CLOSE, EXIT, RESET_SELECT, GD32_FD, GPIO_OPEN, GPIO_READ, GPIO_CLOSE, GD32_PATH, GD32_OPEN, GD32_SETUP, GD32_WRITE, GD32_VERSION, GD32_DELAY, LA, VERSION4, VERSION0, VERSION_COMPOSE, VERSION_HW, VERSION_LOG, DAC_TIME, DDR_SELECT, DDR_BODY, TRUE_INIT }
data class Node(val id:Id,val kind:Kind,val operation:String,val semantics:String,val pcs:List<Long>,val inputs:List<String> = emptyList())
data class Edge(val from:Id,val to:Id,val condition:String)
data class Range(val name:String,val address:Long,val size:Int)
data class Candidate(val ordinal:Int,val node:Id,val offset:Long,val value:Long,val condition:String)
val elf=Elf(Files.readAllBytes(input));val stockHash=sha(input)
require(stockHash=="4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e")
val named=listOf("Dev_Init","_Z8Drv_Initb","DevSystemSCU_Init","DevSystemScu_WriteRegister","DevSystemScu_ReadRegister","DevBoardPower_SendAppUILoadStatus","UART_OPen","uartDataSeed","Uart_Close","crc7_mmc","Dev_SetGD32Reset","Dev_WriteCommand","Dev_GetHardwareVersion","uartXSetup","DevLaDisplaySpu_SetAccRst","DevLaDisplayWpu_WriteRegister","DevSystemSCU_GetVersion","DevSystemSCU_GetHardwareVersion","DevAcquireSpu_SetDacPolling","DevConfig_GetDdrCalSkip")
val ranges=named.map{n->val s=requireNotNull(elf.syms[n]);require(s.shndx!=0&&s.size>0);Range(n,s.va,s.size.toInt())}+listOf(Range("internal-gd32-reopen",0x2acfb8,0x100),Range("internal-version-path",0x2aef30,72))
// Internal helpers have reviewed instruction ranges without separate exported symbols.
val nodes=listOf(
 Node(Id.SCU,Kind.STATIC_DETERMINED,"W32_PAIR","S1=S|0x80000000; S2=S1&0x7ffffffb. Writes offset0x4004 twice. Returns second status; parent ignores it.",listOf(0x285250,0x285284),listOf("SCU shadow at0x3cb4620 via GOT0xb8cf08; observed operand matches S1=0x80000000")),
 Node(Id.BOARD_OPEN,Kind.RUNTIME_SELECTED,"OPEN","UART_OPen ignores its argument and opens literal /dev/ttyS0 with flags1. Negative descriptor makes board notification return-1; parent continues.",listOf(0x297e44,0x2955b8)),
 Node(Id.BOARD_FRAME,Kind.STATIC_DETERMINED,"FRAME","Construct fa050027af; stock crc7_mmc processes payload0500 using polynomial0x12 then shifts right once.",listOf(0x295698,0x29569c,0x2956d4,0x297f3c)),
 Node(Id.BOARD_WRITE,Kind.RUNTIME_SELECTED,"WRITE","uartDataSeed issues checked write of five bytes; result<=0 calls exit(0). Positive short write also continues.",listOf(0x295778,0x29578c,0x2957ac)),
 Node(Id.BOARD_CLOSE,Kind.RUNTIME_SELECTED,"CLOSE","Close returned UART descriptor; close status is ignored and board notification returns0.",listOf(0x297f44,0x295d7c)),
 Node(Id.EXIT,Kind.UNKNOWN,"PROCESS_EXIT","No continuation through LA if board-power write terminates the process. Runtime termination and cleanup remain evidence.",listOf(0x2957ac)),
 Node(Id.RESET_SELECT,Kind.RUNTIME_SELECTED,"BRANCH","Original Dev_Init bool selects GD32 reset when false and JESD/DAC-sync path when true.",listOf(0x2728e4,0x2728e8),listOf("Dev_Init original bool, saved in stack")),
 Node(Id.GD32_FD,Kind.RUNTIME_SELECTED,"CACHED_DESCRIPTOR","afg_uart_fd at0xbb127c starts-1; runtime negative value calls reopen helper. Nonnegative cached descriptor skips reopen.",listOf(0x2ad0b8),listOf("GOT0xb8e020 and cached descriptor")),
 Node(Id.GPIO_OPEN,Kind.RUNTIME_SELECTED,"OPEN","Dev_GetHardwareVersion opens /dev/hdcode_gpio flags0x802. Open failure returns-3 and reopen translates negative version to-7.",listOf(0x2ad564,0x2ad574)),
 Node(Id.GPIO_READ,Kind.HARDWARE_RETURNED,"READ1","Request ONE byte into zeroed four-byte int: __read_chk x2=count1 x3=capacity4. Negative read returns-5; zero bytes leaves0; ordinary one-byte result gives0..255. No returned value or side effect inferred.",listOf(0x2ad53c,0x2ad5a4,0x2ad5b0,0x2ad5e4,0x2ad5e8,0x2ad5ec)),
 Node(Id.GPIO_CLOSE,Kind.RUNTIME_SELECTED,"CLOSE","Close descriptor on completed read path, return read int or error. Distinct from mapped SCU hardware-version interface.",listOf(0x2ad60c,0x2ad624,0x2ad628)),
 Node(Id.GD32_PATH,Kind.RUNTIME_SELECTED,"PATH_SELECT","Version1 selects /dev/uart_simulate; every other nonnegative version selects /dev/ttyS4. Negative version stops reopen earlier.",listOf(0x2aef3c,0x2aef54,0x2aef64),listOf("GPIO returned integer")),
 Node(Id.GD32_OPEN,Kind.RUNTIME_SELECTED,"OPEN","Open selected GD32 UART with O_RDWR=2. Failed open returns-3. Version>=2 requires uartXSetup.",listOf(0x2ad034,0x2ad07c)),
 Node(Id.GD32_SETUP,Kind.RUNTIME_SELECTED,"TERMIOS","uartXSetup ignores tcgetattr and cfset speed statuses, calls tcsetattr twice with action0, either nonzero returns-1; tcflush(fd,0) ignored. Initial tcgetattr failure leaves partly undefined termios. Default config115200,8,N,1; inherited flags remain runtime inputs.",listOf(0x2ad07c,0x2aea40,0x2aebc0,0x2aebd4,0x2aecec,0x2aeeb4,0x2aeecc),listOf("stUartXInfo at0xbb1280 via GOT0xb8e068")),
 Node(Id.GD32_WRITE,Kind.RUNTIME_SELECTED,"WRITE","Write *RST newline through cached/reopened descriptor. Negative write returns-4; short nonnegative write is treated as success.",listOf(0x2ad198)),
 Node(Id.GD32_VERSION,Kind.HARDWARE_RETURNED,"VERSION_REQUERY","After nonnegative command write, call Dev_GetHardwareVersion again; includes another GPIO open/read/close. This new result selects delay, including negative errors.",listOf(0x2ad1c4)),
 Node(Id.GD32_DELAY,Kind.RUNTIME_SELECTED,"DELAY","Request usleep1000 for second version>=2, else220000; timing/completion is not established. Dev_SetGD32Reset reduces command result to0/-1; parent ignores it.",listOf(0x2ad1c4,0x2ad1ec)),
 Node(Id.LA,Kind.STATIC_DETERMINED,"W32_PAIR","Set then clear bit0 with exact mask0xfffffffe in writable LA shadow at0x106d4d8; wrapper adds0x7000 to selector0x34. Zero initial shadow predicts1,0. Parent ignores indeterminate child status loaded from uninitialized stack local.",listOf(0x294e0c,0x294e3c,0x294e60,0x2949e8),listOf("GOT0xb8d830 must bind0x294df8; live shadow")),
 Node(Id.VERSION4,Kind.HARDWARE_RETURNED,"R32","First post-Dev_Init mapped read is offset4 through SCU read wrapper (no0x4000 base addition).",listOf(0x285300)),
 Node(Id.VERSION0,Kind.HARDWARE_RETURNED,"R32","Read offset0. Second read status overwrites first status; neither selects a branch in Drv_Init.",listOf(0x285310)),
 Node(Id.VERSION_COMPOSE,Kind.STATIC_DETERMINED,"PACK","Write ((R4&0xffffff)<<8)|(R0&0xff) through output pointer. Drv_Init output is stack[x29-0x48].",listOf(0x285324,0x285334,0x28533c,0x2e526c)),
 Node(Id.VERSION_HW,Kind.HARDWARE_RETURNED,"R32","Read offset0x401c directly into Drv_Init stack[x29-0x4c]. Status stored but not branched upon in immediate consumer.",listOf(0x285394,0x2e527c)),
 Node(Id.VERSION_LOG,Kind.RUNTIME_SELECTED,"LOG","Both version integers are passed to __android_log_print. Immediate code continues independently of those values or returned read status.",listOf(0x2e5334,0x2e5358,0x2e5410,0x2e5434)),
 Node(Id.DAC_TIME,Kind.STATIC_DETERMINED,"W32","SetDacPolling(5000000000,5500000000) divides by50000000 and replaces low16 shadow bits with0x646e; upper16 preserved. Write0x1428 uses entire u32 shadow.",listOf(0x2e5468,0x27dd2c,0x27dd3c,0x27dd80,0x27dd88),listOf("GOT0xb8e118 to gInt32DevAcquireDacTime at0x3cb4550; live upper16")),
 Node(Id.DDR_SELECT,Kind.RUNTIME_SELECTED,"CONFIG_SELECT","GetDdrCalSkip obtains selected series configuration pointer+0x18, then int+0x68. MHO900Conf image default is1; writable inputs require live validation.",listOf(0x272850,0x272854,0x2e547c),listOf("series selector and configuration record")),
 Node(Id.DDR_BODY,Kind.UNKNOWN,"RECOVERY_BOUNDARY","Nonzero config calls GetDdrSkipTap and SetMemReset before SelfTest; zero skips first block. Full DDR polling/data grammar is not recovered here.",listOf(0x2e54a0,0x2e5590,0x2e55a4)),
 Node(Id.TRUE_INIT,Kind.UNKNOWN,"EXCLUDED_BRANCH","True Dev_Init path performs JESD/DAC-sync work. Excluded from false-branch candidate; reaching it is divergence.",listOf(0x2728f0))
)
val edges=listOf(
 Edge(Id.SCU,Id.BOARD_OPEN,"two writes return"),Edge(Id.BOARD_OPEN,Id.RESET_SELECT,"open<0"),Edge(Id.BOARD_OPEN,Id.BOARD_FRAME,"open>=0"),Edge(Id.BOARD_FRAME,Id.BOARD_WRITE,"frame constructed"),Edge(Id.BOARD_WRITE,Id.EXIT,"write<=0"),Edge(Id.BOARD_WRITE,Id.BOARD_CLOSE,"write>0 including short"),Edge(Id.BOARD_CLOSE,Id.RESET_SELECT,"any close result"),Edge(Id.RESET_SELECT,Id.GD32_FD,"false"),Edge(Id.RESET_SELECT,Id.TRUE_INIT,"true"),Edge(Id.GD32_FD,Id.GPIO_OPEN,"cached fd<0"),Edge(Id.GD32_FD,Id.GD32_WRITE,"cached fd>=0"),Edge(Id.GPIO_OPEN,Id.LA,"open<0 leads command failure ignored by parent"),Edge(Id.GPIO_OPEN,Id.GPIO_READ,"open>=0"),Edge(Id.GPIO_READ,Id.GPIO_CLOSE,"read returned"),Edge(Id.GPIO_CLOSE,Id.LA,"version<0 leads reopen failure"),Edge(Id.GPIO_CLOSE,Id.GD32_PATH,"version>=0"),Edge(Id.GD32_PATH,Id.GD32_OPEN,"selected path"),Edge(Id.GD32_OPEN,Id.LA,"open failed"),Edge(Id.GD32_OPEN,Id.GD32_SETUP,"fd>=0 and version>=2"),Edge(Id.GD32_OPEN,Id.GD32_WRITE,"fd>=0 and version<2"),Edge(Id.GD32_SETUP,Id.LA,"setup failed and descriptor closed"),Edge(Id.GD32_SETUP,Id.GD32_WRITE,"setup succeeded"),Edge(Id.GD32_WRITE,Id.LA,"write<0"),Edge(Id.GD32_WRITE,Id.GD32_VERSION,"write>=0"),Edge(Id.GD32_VERSION,Id.GD32_DELAY,"second version result including negative"),Edge(Id.GD32_DELAY,Id.LA,"sleep returns"),Edge(Id.LA,Id.VERSION4,"two LA writes and Dev_Init return"),Edge(Id.VERSION4,Id.VERSION0,"read returns"),Edge(Id.VERSION0,Id.VERSION_COMPOSE,"read returns"),Edge(Id.VERSION_COMPOSE,Id.VERSION_HW,"version returns"),Edge(Id.VERSION_HW,Id.VERSION_LOG,"read returns"),Edge(Id.VERSION_LOG,Id.DAC_TIME,"log calls return"),Edge(Id.DAC_TIME,Id.DDR_SELECT,"write returns"),Edge(Id.DDR_SELECT,Id.DDR_BODY,"config branch")
)
require(nodes.map{it.id}.toSet().size==nodes.size)
require(edges.all{e->nodes.any{it.id==e.from}&&nodes.any{it.id==e.to}&&e.condition.isNotBlank()})
val reachable=mutableSetOf(Id.SCU);while(true){val n=reachable.size;edges.filter{it.from in reachable}.forEach{reachable.add(it.to)};if(n==reachable.size)break};require(reachable==nodes.map{it.id}.toSet())
val scuCheckpoint=0x80000000L;val scuSecond=scuCheckpoint and 0x7ffffffbL
val laInitial=0L;val dacUpper=0L;val dacLow=((5000000000L/50000000L and 255) shl 8) or (5500000000L/50000000L and 255)
val candidates=listOf(Candidate(0,Id.SCU,0x4004,scuCheckpoint,"live SCU checkpoint=0x80000000"),Candidate(1,Id.SCU,0x4004,scuSecond,"no intervening shadow mutation"),Candidate(2,Id.LA,0x7034,laInitial or 1,"false branch transport returns; LA initial shadow0"),Candidate(3,Id.LA,0x7034,0,"LA second phase; no intervening shadow mutation"),Candidate(4,Id.DAC_TIME,0x1428,dacUpper or dacLow,"version reads returned; live DAC upper16=0"))
require(candidates.map{it.value}==listOf(0x80000000L,0L,1L,0L,0x646eL))
require(elf.zeroFilled(0x3cb4620,4)&&elf.zeroFilled(0x106d4d8,4)&&elf.zeroFilled(0x3cb4550,4))
require(elf.word(0xbb127c)==0xffffffffL&&elf.word(0xb8f478+0x68)==1L)
fun crc7(payload:List<Int>):Int { var c=0; for(b in payload){c=c xor b;repeat(8){c=((c shl 1) xor if(c and 128 != 0)0x12 else 0) and 255}};return c ushr 1 }
require(crc7(listOf(5,0))==0x27)
val literalPins=listOf(0x99814fL to "/dev/ttyS0",0x99364bL to "/dev/hdcode_gpio",0x999082L to "/dev/uart_simulate",0x999095L to "/dev/ttyS4",0x998f93L to "*RST\n")
literalPins.forEach{(va,text)->require(elf.region(va,text.length+1).contentEquals((text+"\u0000").toByteArray()))}
require((0 until 4).map{elf.word(0xbb1280+4L*it)}==listOf(115200L,8L,78L,1L))
val stateSlots=listOf(0xb8cf08L,0xb8d830L,0xb8e020L,0xb8e068L,0xb8e118L)
val rels=elf.rels.values.filter{it.sym?.name in named||it.va in stateSlots}.sortedBy{it.va}
require(stateSlots.all{slot->rels.any{it.va==slot}})
val fixedOpcodes=mapOf(0x2ad5b0L to 0x52800028L,0x2ad5e4L to 0xf9401fe2L,0x2ad5e8L to 0xf9401be3L,0x294e0cL to 0x12800029L,0x2728e4L to 0x37000069L,0x285324L to 0x12005d4aL,0x285334L to 0x2a0a216aL,0x27dd2cL to 0x9acc0929L,0x27dd3cL to 0x9acc0929L,0x272854L to 0xb9406900L,0x2e547cL to 0x340008eaL)
fixedOpcodes.forEach{(pc,word)->require(elf.word(pc)==word)}
Files.createDirectories(output)
Files.newBufferedWriter(output.resolve("grammar.toml")).use{w->
 w.appendLine("schema_version = \"mho900-lab.remaining-init-grammar/1\"")
 w.appendLine("stock_library_sha256 = ${q(stockHash)}")
 w.appendLine("method = \"Reviewed semantic graph bound to pinned ELF; not automatic symbolic execution or runtime evidence\"")
 w.appendLine("entry = \"SCU\"")
 w.appendLine("candidate_semantics = \"Conditional projection; intervening branches and reads remain in graph\"")
 ranges.filter{it.size>0}.forEach{r->w.appendLine("\n[[ranges]]\nname = ${q(r.name)}\naddress = ${hx(r.address)}\nsize = ${r.size}\nsha256 = ${q(sha(elf.region(r.address,r.size)))}")}
 rels.forEach{r->w.appendLine("\n[[bindings]]\nslot = ${hx(r.va)}\ntype = ${hx(r.type)}\nsymbol = ${q(requireNotNull(r.sym).name)}\ntarget = ${hx(r.sym.va)}")}
 nodes.forEach{n->w.appendLine("\n[[nodes]]\nid = ${q(n.id.name)}\nclassification = ${q(n.kind.name.replace('_','-'))}\noperation = ${q(n.operation)}\nsemantics = ${q(n.semantics)}\npcs = [${n.pcs.joinToString{hx(it)}}]\nopcodes = [${n.pcs.joinToString{hx(elf.word(it),8)}}]\ninputs = [${n.inputs.joinToString{q(it)}}]")}
 edges.forEach{e->w.appendLine("\n[[edges]]\nfrom = ${q(e.from.name)}\nto = ${q(e.to.name)}\ncondition = ${q(e.condition)}")}
 candidates.forEach{c->w.appendLine("\n[[candidate_writes]]\nordinal = ${c.ordinal}\nnode = ${q(c.node.name)}\noffset = ${hx(c.offset)}\nvalue = ${hx(c.value,8)}\ncondition = ${q(c.condition)}")}
}
println("schema_version = \"mho900-lab.remaining-init-derivation/1\"")
println("nodes = ${nodes.size}\nedges = ${edges.size}\nconditional_writes = ${candidates.size}\ngrammar_sha256 = ${q(sha(output.resolve("grammar.toml")))}")
