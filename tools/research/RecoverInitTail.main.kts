// Recover the reviewed initialization tail grammar from the pinned stock ELF.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 2) { "Usage: RecoverInitTail.main.kts STOCK_ELF NEW_OUTPUT_DIRECTORY" }
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
// A reviewed semantic graph, not a claim of automatic symbolic execution.
enum class Kind { STATIC_DETERMINED, RUNTIME_SELECTED, HARDWARE_RETURNED, ASYNCHRONOUS, UNKNOWN }
enum class Id { VERSION4, VERSION0, VERSION_PACK, VERSION_HW, VERSION_LOG, DAC_TIME, DDR_SELECT,
 TAP0, TAP1, TAP2, TAP3, TAP4, TAP_OUTPUT, MEM_RESET, SELF_READ, SELF_PREDICATE, CLOCK_READ, CLOCK_PREDICATE, POLL_SELECT,
 POLL_DELAY, POLL_TEST, FALLBACK_SELECT, BRAM, CALIBRATION, ADC_MODE, ALIGN, AFE_OFFSET,
 SAMPLE_MASK, ADC_RANGE, CHANNEL_SCALE, SINC, FAN, SCOPE_START, AFE_ENABLE, LA_DISABLE,
 PROC_LA_DISABLE, PROC_CH_ENABLE, RETURN, STACK_FAILURE, UPSTREAM }
enum class Direction { READ, WRITE }
data class Node(val id:Id, val kind:Kind, val operation:String, val semantics:String,
                val pcs:List<Long>, val inputs:List<String> = emptyList())
data class Edge(val from:Id, val to:Id, val condition:String)
data class Access(val id:String, val node:Id, val direction:Direction, val offset:Long,
                  val expression:String, val condition:String, val callPc:Long)
data class Range(val name:String, val address:Long, val size:Int)
val elf=Elf(Files.readAllBytes(input)); val stockHash=sha(input)
require(stockHash=="4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e")
val nodes=mutableListOf(
 Node(Id.VERSION4,Kind.HARDWARE_RETURNED,"R32","Read offset4 into initialized local. First unanswered stock access; returned value remains a model input.",listOf(0x2852f0,0x285300)),
 Node(Id.VERSION0,Kind.HARDWARE_RETURNED,"R32","Read offset0; its wrapper status overwrites first status, without a value-dependent branch.",listOf(0x28530c,0x285310)),
 Node(Id.VERSION_PACK,Kind.STATIC_DETERMINED,"PACK","Output=((R4&0xffffff)<<8)|(R0&0xff), written to Drv_Init stack[x29-0x48].",listOf(0x285318,0x285324,0x285334,0x28533c)),
 Node(Id.VERSION_HW,Kind.HARDWARE_RETURNED,"R32","Read offset0x401c into Drv_Init stack[x29-0x4c]. Distinct from GPIO version interface.",listOf(0x285380,0x285394)),
 Node(Id.VERSION_LOG,Kind.STATIC_DETERMINED,"CONSUME","Both versions are logged; immediate control flow does not depend on these values or read statuses.",listOf(0x2e5334,0x2e5358,0x2e5410,0x2e5434)),
 Node(Id.DAC_TIME,Kind.STATIC_DETERMINED,"W32","Unsigned division by50000000 gives100 and110; replace low16 with0x646e, preserve live upper16, write full u32 to0x1428. Parent ignores status.",listOf(0x27dd2c,0x27dd3c,0x27dd60,0x27dd7c,0x27dd88),listOf("live DAC shadow via GOT0xb8e118")),
 Node(Id.DDR_SELECT,Kind.RUNTIME_SELECTED,"BRANCH","Selected series record config pointer+0x18, field+0x68 controls skip-tap/reset block. Writable MHO900Conf image value1 is not a live observation.",listOf(0x272850,0x272854,0x2e547c),listOf("DevSystem_GetSeriesParam selection and writable config")),
 Node(Id.TAP0,Kind.HARDWARE_RETURNED,"R32","GetDdrSkipTap(true): read0x14a0; output1 = R&0x3f as u32. Caller logs this output.",listOf(0x27d4cc,0x27d4e0,0x27d4f0)),
 Node(Id.TAP1,Kind.HARDWARE_RETURNED,"R32","Read0x14a4; output3 = R&0xfff widened to u64.",listOf(0x27d5a0,0x27d5b4,0x27d5d0)),
 Node(Id.TAP2,Kind.HARDWARE_RETURNED,"R32","Read0x1498; output2 = R&0xfff widened to u64.",listOf(0x27d678,0x27d68c,0x27d6a8)),
 Node(Id.TAP3,Kind.HARDWARE_RETURNED,"R32","Read0x14ac; output4 = R&0xfff widened to u64.",listOf(0x27d750,0x27d764,0x27d780)),
 Node(Id.TAP4,Kind.HARDWARE_RETURNED,"R32","Read0x14b4; output5 = R&0x3ff widened to u64.",listOf(0x27d828,0x27d83c,0x27d858)),
 Node(Id.TAP_OUTPUT,Kind.STATIC_DETERMINED,"OUTPUT","Output6 is zero; return last read status, parent ignores it. No read-value branch in true skip-tap body; false helper branch performs no reads or output stores.",listOf(0x27d4b4,0x27d8e8,0x27d8ec,0x27d8f0)),
 Node(Id.MEM_RESET,Kind.STATIC_DETERMINED,"W32","SetMemReset(false,false) clears bits2 and3 of live SPU control shadow, preserves other bits, writes full u32 to0x1000. Parent ignores status.",listOf(0x2e5588,0x2e5590,0x277d5c,0x277d80,0x277d8c),listOf("live SPU control shadow via GOT0xb8d288")),
 Node(Id.SELF_READ,Kind.HARDWARE_RETURNED,"R32","Attempt read0x1008 into uncleared global status shadow. Extract from post-call object; if failed read leaves it unchanged the state may be stale. No physical completion inferred.",listOf(0x2735b0,0x2735c0),listOf("status shadow via GOT0xb8de08")),
 Node(Id.SELF_PREDICATE,Kind.STATIC_DETERMINED,"EXTRACT","Output bool=(R1008>>29)&1. SelfTest logs either outcome then checks ADC clock; eventually returns first read status. Parent branches on completion bool, not status.",listOf(0x2735d0,0x2735d8,0x2e5688,0x2e568c)),
 Node(Id.CLOCK_READ,Kind.HARDWARE_RETURNED,"R32","Every SelfTest also reads0x1210 through GetCheckAdcClk. Raw u32 is returned to SelfTest local; not the completion bool.",listOf(0x2734c0,0x2734c8,0x2734d8)),
 Node(Id.CLOCK_PREDICATE,Kind.STATIC_DETERMINED,"FLOAT_RANGE","Convert u32 to float; strict comparison62500f*(1f-0.0001f)<value<62500f*(1f+0.0001f). SelfTest logs predicate/raw word; ignores helper status and returns R1008 status. No readiness branch uses clock predicate here.",listOf(0x2734ec,0x273500,0x273508,0x273510,0x273518)),
 Node(Id.POLL_SELECT,Kind.RUNTIME_SELECTED,"BRANCH","If first completion bool false, initialize retry counter200; while !bool && counter>0, sleep then decrement and call SelfTest. Maximum201 invocations:201 reads at each of0x1008/0x1210,402 mapped read attempts.",listOf(0x2e5694,0x2e56ac,0x2e56bc,0x2e56cc),listOf("post-read-object completion bit")),
 Node(Id.POLL_DELAY,Kind.ASYNCHRONOUS,"DELAY","Request usleep50000 before each repeated read, ignore status. At most200 requests, nominal10 seconds; no actual FPGA latency inferred.",listOf(0x2e56d4,0x2e56d8,0x2e56e0)),
 Node(Id.POLL_TEST,Kind.HARDWARE_RETURNED,"REPEAT_SELFTEST","Call same SelfTest R1008 then R1210; log and return to retry condition. At most200 repeated pairs. Response sequence remains modeled.",listOf(0x2e56f4,0x2e57d8)),
 Node(Id.FALLBACK_SELECT,Kind.RUNTIME_SELECTED,"BRANCH","After retry loop, false bool invokes MemoryBram(true); true skips it. Both paths continue to calibration.",listOf(0x2e57dc,0x2e57e0,0x2e57e8,0x2e57ec)),
 Node(Id.BRAM,Kind.STATIC_DETERMINED,"W32","MemoryBram(true): set bit31 of live status shadow, write full u32 to0x1008, return write status ignored by parent. Physical memory behavior remains unknown.",listOf(0x2e57ec,0x2739a8),listOf("live status shadow via GOT0xb8de08")),
 Node(Id.CALIBRATION,Kind.UNKNOWN,"SUBSYSTEM_BOUNDARY","CDrvScope::GetCalibration then CCalibration::Init. This graph records parent continuation only; transitive calibration effects are not admitted.",listOf(0x2e57f8,0x2e57fc,0x2e5800)),
 Node(Id.ADC_MODE,Kind.UNKNOWN,"CALL_PAIR","If calibration returns, SetDataMode(0,4), SetDataMode(1,4); statuses ignored. Transitive operations require separate recovery.",listOf(0x2e581c,0x2e5834)),
 Node(Id.ALIGN,Kind.UNKNOWN,"BOUNDED_CALL","One iteration CalAdcCoreAlign(1,1,out), then usleep1000. Status and output are not branched on here; effects remain outside candidate.",listOf(0x2e5854,0x2e5870,0x2e5880,0x2e5894)),
 Node(Id.AFE_OFFSET,Kind.STATIC_DETERMINED,"LOOP","SetAfeOffset(channel,32768) for channel0..3 writes0x8000 to0x1418,0x141c,0x1420,0x1424; statuses ignored. Conditional on earlier unknown calls returning.",listOf(0x2e5898,0x2e58b4,0x2e58c4,0x2e58d8)),
 Node(Id.SAMPLE_MASK,Kind.RUNTIME_SELECTED,"SELECT","GetDrvSetting(2)->GetSampleChanMask supplies runtime channel mask.",listOf(0x2e5908,0x2e590c)),
 Node(Id.ADC_RANGE,Kind.RUNTIME_SELECTED,"W32","chn2log(mask,bytes[1,1,1,1]) supplies selector; W1014=((live_shadow|1)&0xff0fffff)|((selector&15)<<20). Status ignored, no constant selector presumed.",listOf(0x2e5914,0x27330c,0x273330,0x273340),listOf("chn2log output and shadow via GOT0xb8be90")),
 Node(Id.CHANNEL_SCALE,Kind.UNKNOWN,"CALL","DrvChannel_SetScale(0,100000000); status ignored; transitive effects not admitted.",listOf(0x2e5918,0x2e591c,0x2e5930)),
 Node(Id.SINC,Kind.UNKNOWN,"CALL_PAIR","SetSinc(1,1,2,200,1), then(1,1,3,200,1); statuses ignored; transitive effects not admitted.",listOf(0x2e595c,0x2e597c)),
 Node(Id.FAN,Kind.UNKNOWN,"CALL","DrvMonitor_SetFanSpeed(0,1.0); status ignored; transitive transport not admitted.",listOf(0x2e5980,0x2e5990)),
 Node(Id.SCOPE_START,Kind.UNKNOWN,"SUBSYSTEM_BOUNDARY","CDrvScope::Start(original bool) introduces larger application/thread lifecycle; effects not admitted.",listOf(0x2e599c,0x2e59a4),listOf("original Drv_Init bool")),
 Node(Id.AFE_ENABLE,Kind.UNKNOWN,"LOOP","DevInOutAFE_SetHzEnable(channel,true), channel0..3. Four calls, ignored statuses, transitive effects not admitted.",listOf(0x2e59bc,0x2e59cc,0x2e59e0)),
 Node(Id.LA_DISABLE,Kind.RUNTIME_SELECTED,"W32","W4008=S1=S0&0xfbffffff; clear bit26 of live shared shadow. Status ignored.",listOf(0x2e59ec,0x286828),listOf("shared shadow via GOT0xb8d3a8")),
 Node(Id.PROC_LA_DISABLE,Kind.RUNTIME_SELECTED,"W32","W4008=S2=S1&0xfeffffff; clear bit24 of same live shadow. Status ignored.",listOf(0x2e59fc,0x2865a0),listOf("shared shadow via GOT0xb8d3a8")),
 Node(Id.PROC_CH_ENABLE,Kind.RUNTIME_SELECTED,"W32","W4008=S3=S2|0x00800000; set bit23 of same live shadow. Status ignored. No intervening mutation presumed by formula chaining.",listOf(0x2e5a0c,0x28660c),listOf("shared shadow via GOT0xb8d3a8")),
 Node(Id.RETURN,Kind.STATIC_DETERMINED,"RETURN","Normal Drv_Init return is always0 after all calls return; it is not evidence of hardware success.",listOf(0x2e5a28,0x2e5a38)),
 Node(Id.STACK_FAILURE,Kind.UNKNOWN,"TERMINATE","Stack canary mismatch calls __stack_chk_fail. Function and helper stack checks are runtime exceptional edges, not modeled hardware outcomes.",listOf(0x2e5a20,0x2e5a3c)),
 Node(Id.UPSTREAM,Kind.STATIC_DETERMINED,"IGNORED_RETURN","Factory Api_Init calls Drv_Init(false) and forces own result0. Low-power restore calls Drv_Init(true) and continues without inspecting result. Direct callers do not establish successful hardware initialization.",listOf(0x2392dc,0x2392e0,0x41be5c,0x41be60))
)
val edges=mutableListOf<Edge>()
fun chain(vararg ids:Id) { ids.toList().zipWithNext().forEach{(a,b)->edges+=Edge(a,b,"operation returns normally") } }
chain(Id.VERSION4,Id.VERSION0,Id.VERSION_PACK,Id.VERSION_HW,Id.VERSION_LOG,Id.DAC_TIME,Id.DDR_SELECT)
edges+=Edge(Id.DDR_SELECT,Id.TAP0,"live config nonzero; helper mode=true")
edges+=Edge(Id.DDR_SELECT,Id.SELF_READ,"live config zero")
chain(Id.TAP0,Id.TAP1,Id.TAP2,Id.TAP3,Id.TAP4,Id.TAP_OUTPUT,Id.MEM_RESET,Id.SELF_READ,
 Id.SELF_PREDICATE,Id.CLOCK_READ,Id.CLOCK_PREDICATE,Id.POLL_SELECT)
edges+=Edge(Id.POLL_SELECT,Id.CALIBRATION,"completion bool true")
edges+=Edge(Id.POLL_SELECT,Id.POLL_DELAY,"completion false; remaining retries>0 (initially200)")
chain(Id.POLL_DELAY,Id.POLL_TEST)
edges+=Edge(Id.POLL_TEST,Id.POLL_SELECT,"same SelfTest read pair completed; counter already decremented")
edges+=Edge(Id.POLL_SELECT,Id.FALLBACK_SELECT,"completion false; remaining retries=0")
edges+=Edge(Id.FALLBACK_SELECT,Id.BRAM,"completion remains false")
edges+=Edge(Id.FALLBACK_SELECT,Id.CALIBRATION,"completion bool true on final branch recheck")
chain(Id.BRAM,Id.CALIBRATION,Id.ADC_MODE,Id.ALIGN,Id.AFE_OFFSET,Id.SAMPLE_MASK,Id.ADC_RANGE,
 Id.CHANNEL_SCALE,Id.SINC,Id.FAN,Id.SCOPE_START,Id.AFE_ENABLE,Id.LA_DISABLE,Id.PROC_LA_DISABLE,Id.PROC_CH_ENABLE)
edges+=Edge(Id.PROC_CH_ENABLE,Id.RETURN,"callee returns; stack canary matches")
edges+=Edge(Id.PROC_CH_ENABLE,Id.STACK_FAILURE,"stack canary differs")
chain(Id.RETURN,Id.UPSTREAM)
val accesses=listOf(
 Access("version4",Id.VERSION4,Direction.READ,4,"R4","always at entry",0x285300),
 Access("version0",Id.VERSION0,Direction.READ,0,"R0","version4 returned",0x285310),
 Access("hardware_version",Id.VERSION_HW,Direction.READ,0x401c,"R401c","packed version stored",0x285394),
 Access("dac_time",Id.DAC_TIME,Direction.WRITE,0x1428,"(live_dac&0xffff0000)|0x646e","version calls/logging returned",0x27dd88),
 Access("tap0",Id.TAP0,Direction.READ,0x14a0,"R14a0&0x3f -> out1:u32","config!=0; mode=true",0x27d4cc),
 Access("tap1",Id.TAP1,Direction.READ,0x14a4,"R14a4&0xfff -> out3:u64","config!=0; mode=true",0x27d5a0),
 Access("tap2",Id.TAP2,Direction.READ,0x1498,"R1498&0xfff -> out2:u64","config!=0; mode=true",0x27d678),
 Access("tap3",Id.TAP3,Direction.READ,0x14ac,"R14ac&0xfff -> out4:u64","config!=0; mode=true",0x27d750),
 Access("tap4",Id.TAP4,Direction.READ,0x14b4,"R14b4&0x3ff -> out5:u64","config!=0; mode=true",0x27d828),
 Access("mem_reset",Id.MEM_RESET,Direction.WRITE,0x1000,"live_ctrl&0xfffffff3","config!=0; tap helper returned",0x277d8c),
 Access("self_status",Id.SELF_READ,Direction.READ,0x1008,"(R1008>>29)&1 -> completion","initial and each repeated SelfTest",0x2735c0),
 Access("self_clock",Id.CLOCK_READ,Direction.READ,0x1210,"u32_to_float(R1210) -> clock predicate; logged only","every SelfTest after self_status",0x2734c8),
 Access("bram",Id.BRAM,Direction.WRITE,0x1008,"(post_last_selftest_object&0x7fffffff)|0x80000000","201st SelfTest still incomplete",0x2739a8),
 Access("afe0",Id.AFE_OFFSET,Direction.WRITE,0x1418,"0x8000","earlier UNKNOWN calls return; channel0",0x27ddfc),
 Access("afe1",Id.AFE_OFFSET,Direction.WRITE,0x141c,"0x8000","earlier UNKNOWN calls return; channel1",0x27de10),
 Access("afe2",Id.AFE_OFFSET,Direction.WRITE,0x1420,"0x8000","earlier UNKNOWN calls return; channel2",0x27de24),
 Access("afe3",Id.AFE_OFFSET,Direction.WRITE,0x1424,"0x8000","earlier UNKNOWN calls return; channel3",0x27de38),
 Access("adc_range",Id.ADC_RANGE,Direction.WRITE,0x1014,"((live_shadow|1)&0xff0fffff)|((selector&15)<<20)","earlier UNKNOWN calls and chn2log return",0x273340),
 Access("la_disable",Id.LA_DISABLE,Direction.WRITE,0x4008,"live_scu&0xfbffffff","earlier UNKNOWN calls return",0x286828),
 Access("proc_la_disable",Id.PROC_LA_DISABLE,Direction.WRITE,0x4008,"live_scu&0xfeffffff","LA disable returned",0x2865a0),
 Access("proc_ch_enable",Id.PROC_CH_ENABLE,Direction.WRITE,0x4008,"live_scu|0x00800000","processor LA disable returned",0x28660c)
)
val named=listOf("_Z8Drv_Initb","DevSystemSCU_GetVersion","DevSystemSCU_GetHardwareVersion",
 "DevSystemScu_ReadRegister","DevAcquireSpu_ReadRegister","DevAcquireSpu_WriteRegister",
 "DevAcquireSpu_SetDacPolling","DevConfig_GetDdrCalSkip","DevSystem_GetSeriesParam",
 "DevAcquireSPU_GetDdrSkipTap","DevAcquireSPU_SetMemReset","DevAcquireSpu_SelfTest",
 "DevAcquireSpu_GetCheckAdcClk","DevAcquireSpu_MemoryBram","_ZN12CCalibration4InitEv",
 "_ZN11CApiFactory8Api_InitEv","_ZN11CApiUtility28ApiUtility_SetLowPowerStatusEi",
 "DevAcquireSpu_SetAfeOffset","DevAcquireSpu_SetAdcBitRange","DevSystemSCU_SetLaEanble",
 "DevSystemSCU_SetProcLaEn","DevSystemSCU_SetProcChEn")
val ranges=named.map { n->val s=requireNotNull(elf.syms[n]);require(s.shndx!=0&&s.size>0);Range(n,s.va,s.size.toInt()) }
val slots=listOf(0xb8e118L,0xb8d288L,0xb8de08L,0xb8d850L,0xb8d640L,0xb8e050L,0xb8c9f0L,0xb8ba20L,0xb8be90L,0xb8d3a8L)
val bindings=elf.rels.values.filter { it.sym?.name in named || it.va in slots }.sortedBy{it.va}
require(slots.all { slot->bindings.any { it.va==slot } })
require(nodes.map{it.id}.toSet()==Id.entries.toSet())
require(edges.all{it.condition.isNotBlank()})
val reached=mutableSetOf(Id.VERSION4)
while(true){val before=reached.size;edges.filter{it.from in reached}.forEach{reached+=it.to};if(before==reached.size)break}
require(reached==Id.entries.toSet())
require(accesses.map{it.id}.distinct().size==accesses.size)
// Bind specific semantic pivots independently of the emitted opcode arrays.
val pivots=mapOf(0x285324L to 0x12005d4aL,0x285334L to 0x2a0a216aL,0x2735d0L to 0x531d754aL,
 0x2734ecL to 0x7e21d800L,0x273508L to 0x1a9fd7e9L,0x273518L to 0x1a9f57eaL,
 0x2e5694L to 0x52801908L,0x2e56d4L to 0x52986a00L,0x2e5a28L to 0x2a1f03e0L)
pivots.forEach{(pc,word)->require(elf.word(pc)==word)}
val nominal=Float.fromBits(0x47742400); val tolerance=Float.fromBits(0x38d1b717)
val low=nominal*(1f-tolerance); val high=nominal*(1f+tolerance)
fun clockAccept(value:Long)=value.toFloat()>low && value.toFloat()<high
require(nominal==62500f && (62480L..62520L).filter(::clockAccept)==(62494L..62506L).toList())
data class PollProjection(val name:String,val readyAt:Int?,val pairs:Int,val sleeps:Int,val fallback:Boolean)
fun project(name:String,readyAt:Int?):PollProjection {
 require(readyAt==null || readyAt in 1..201)
 var pairs=1;var sleeps=0
 while(readyAt!=pairs && sleeps<200) { sleeps++;pairs++ }
 return PollProjection(name,readyAt,pairs,sleeps,readyAt!=pairs)
}
val projections=listOf(project("first_ready",1),project("second_ready",2),project("last_ready",201),project("never_ready",null))
require(projections.map{it.pairs}==listOf(1,2,201,201) && projections.map{it.sleeps}==listOf(0,1,200,200))
Files.createDirectories(output)
Files.newBufferedWriter(output.resolve("grammar.toml")).use { w->
 w.appendLine("schema_version = \"mho900-lab.init-tail-grammar/1\"")
 w.appendLine("stock_library_sha256 = ${q(stockHash)}")
 w.appendLine("method = \"Reviewed semantic graph bound to ELF; independent byte/shape checks are not a semantic proof\"")
 w.appendLine("entry = \"VERSION4\"\nparent_flow_complete = true\ntransitive_recovery_complete = false")
 w.appendLine("candidate_boundary = \"CALIBRATION\"\nexception_scope = \"Parent canary edge explicit; helper canary/process exceptions are terminal outside ordinary operation graph\"")
 ranges.forEach { r->w.appendLine("\n[[ranges]]\nname = ${q(r.name)}\naddress = ${hx(r.address)}\nsize = ${r.size}\nsha256 = ${q(sha(elf.region(r.address,r.size)))}") }
 bindings.forEach { r->w.appendLine("\n[[bindings]]\nslot = ${hx(r.va)}\ntype = ${hx(r.type)}\nsymbol = ${q(requireNotNull(r.sym).name)}\ntarget = ${hx(r.sym.va)}") }
 nodes.forEach { n->w.appendLine("\n[[nodes]]\nid = ${q(n.id.name)}\nclassification = ${q(n.kind.name.replace('_','-'))}\noperation = ${q(n.operation)}\nsemantics = ${q(n.semantics)}\npcs = [${n.pcs.joinToString{hx(it)}}]\nopcodes = [${n.pcs.joinToString{hx(elf.word(it),8)}}]\ninputs = [${n.inputs.joinToString{q(it)}}]") }
 edges.forEach { e->w.appendLine("\n[[edges]]\nfrom = ${q(e.from.name)}\nto = ${q(e.to.name)}\ncondition = ${q(e.condition)}") }
 accesses.forEach { a->w.appendLine("\n[[accesses]]\nid = ${q(a.id)}\nnode = ${q(a.node.name)}\ndirection = ${q(a.direction.name)}\noffset = ${hx(a.offset)}\nwidth = 4\nexpression = ${q(a.expression)}\ncondition = ${q(a.condition)}\ncall_pc = ${hx(a.callPc)}\ncall_opcode = ${hx(elf.word(a.callPc),8)}") }
 w.appendLine("\n[clock_predicate]\nnominal_bits = 0x47742400\ntolerance_bits = 0x38d1b717\nstrict = true\nfirst_accepted_u32 = 62494\nlast_accepted_u32 = 62506\ncontrols_parent_retry = false")
 projections.forEach{p->w.appendLine("\n[[poll_projections]]\nname = ${q(p.name)}\nready_at = ${p.readyAt?:0}\nread_pairs = ${p.pairs}\nsleep_requests = ${p.sleeps}\nfallback_write = ${p.fallback}\nobserved = false")}
}
println("schema_version = \"mho900-lab.init-tail-derivation/1\"")
println("ranges = ${ranges.size}\nbindings = ${bindings.size}\nnodes = ${nodes.size}\nedges = ${edges.size}\naccesses = ${accesses.size}")
println("grammar_sha256 = ${q(sha(output.resolve("grammar.toml")))}")
