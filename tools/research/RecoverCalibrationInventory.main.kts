// Recover direct calibration call edges from the pinned stock ELF.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 2) { "Usage: RecoverCalibrationInventory.main.kts STOCK_ELF NEW_OUTPUT_DIRECTORY" }
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
val elf=Elf(Files.readAllBytes(input));val stockHash=sha(input)
require(stockHash=="4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e")
fun signed(v:Long,bits:Int)=(v shl (64-bits)) shr (64-bits)
data class Target(val name:String,val va:Long,val slot:Long?,val defined:Boolean)
fun target(pc:Long):Target {
 val direct=elf.syms.values.filter{it.va==pc&&it.shndx!=0}.sortedBy{it.name}.firstOrNull()
 if(direct!=null)return Target(direct.name,pc,null,true)
 val a=elf.word(pc);val l=elf.word(pc+4)
 if(a and 0x9f00001fL==0x90000010L&&l and 0xffc003ffL==0xf9400211L){
  val page=(pc and -4096L)+(signed(((a ushr 29)and 3)or(((a ushr 5)and 0x7ffff)shl 2),21)shl 12)
  val slot=page+((l ushr 10)and 0xfff)*8
  val r=requireNotNull(elf.rels[slot]);val s=requireNotNull(r.sym)
  return Target(s.name,s.va,slot,s.shndx!=0)
 }
 return Target("UNRESOLVED",pc,null,false)
}
data class Call(val owner:String,val pc:Long,val word:Long,val form:String,val branch:Long?,val target:Target?)
fun calls(s:Sym):List<Call> {
 require(s.size>0&&s.size%4==0L)
 return (0 until(s.size/4).toInt()).mapNotNull{i->val pc=s.va+4*i;val w=elf.word(pc)
  when {
   w and 0xfc000000L==0x94000000L->{val b=pc+(signed(w and 0x3ffffff,26)shl 2);Call(s.name,pc,w,"BL",b,target(b))}
   w and 0xfffffc1fL==0xd63f0000L->Call(s.name,pc,w,"BLR",null,null)
   w and 0xfc000000L==0x14000000L->{val b=pc+(signed(w and 0x3ffffff,26)shl 2);if(b !in s.va until s.va+s.size)Call(s.name,pc,w,"B-tail",b,target(b))else null}
   else->null
  }
 }
}
val init=requireNotNull(elf.syms["_ZN12CCalibration4InitEv"])
require(init.va==0x333afcL&&init.size==0x2c8L)
val roots=listOf("_Z12Drv_GetScopev","_ZN9CDrvScope14GetCalibrationEv",init.name)
val first=calls(init).mapNotNull{it.target}.filter{it.defined}.map{it.name}
val selected=(roots+first).distinct().map{requireNotNull(elf.syms[it])}.sortedBy{it.va}
val all=selected.flatMap(::calls)
Files.createDirectories(output)
Files.newBufferedWriter(output.resolve("inventory.toml")).use{w->
 w.appendLine("schema_version = \"mho900-lab.calibration-call-inventory/1\"\nstock_library_sha256 = ${q(stockHash)}")
 w.appendLine("scope = \"Entry getters and Init plus defined direct callees; instruction-level direct-call inventory only\"\ntransitive_complete = false")
 for(s in selected)w.appendLine("\n[[ranges]]\nname = ${q(s.name)}\naddress = ${hx(s.va)}\nsize = ${s.size}\nsha256 = ${q(sha(elf.region(s.va,s.size.toInt())))}")
 for(c in all){w.appendLine("\n[[calls]]\nowner = ${q(c.owner)}\npc = ${hx(c.pc)}\nopcode = ${hx(c.word,8)}\nform = ${q(c.form)}")
  c.branch?.let{w.appendLine("branch_target = ${hx(it)}")}
  val t=c.target
  if(t==null)w.appendLine("resolution = \"INDIRECT-UNKNOWN\"")else{
   w.appendLine("symbol = ${q(t.name)}\nresolved_target = ${hx(t.va)}\ndefined = ${t.defined}\nexpanded = ${selected.any{it.name==t.name}}")
   t.slot?.let{w.appendLine("relocation_slot = ${hx(it)}")}
  }
 }
}
println("schema_version = \"mho900-lab.calibration-inventory-derivation/1\"\nranges = ${selected.size}\ncalls = ${all.size}\ninventory_sha256 = ${q(sha(output.resolve("inventory.toml")))}")
// Reviewed dispatcher semantics; direct-call coverage is independently enumerable above.
enum class Class { STATIC_DETERMINED, RUNTIME_SELECTED, HARDWARE_RETURNED, ASYNCHRONOUS, UNKNOWN }
data class Node(val id:String,val kind:Class,val pc:Long,val semantics:String)
data class Edge(val from:String,val to:String,val condition:String)
val nodes=listOf(
 Node("get_scope",Class.STATIC_DETERMINED,0x2e57f8,"Drv_GetScope returns library base+0x10bee40 via ADRP/ADD; fixed image-relative global object."),
 Node("get_calibration",Class.STATIC_DETERMINED,0x2e57fc,"GetCalibration returns scope+0x60d8."),
 Node("initialize_buffers",Class.STATIC_DETERMINED,0x333b40,"Zero1120 bytes at sp+0xa8 and40 bytes at sp+0x80."),
 Node("load_lsb",Class.RUNTIME_SELECTED,0x333b74,"Load vertical LSB into this+0x8fc0; status stored then overwritten."),
 Node("load_vertical",Class.RUNTIME_SELECTED,0x333b80,"Load vertical calibration on this+0x8fc0; status ignored by dispatcher."),
 Node("load_adc",Class.RUNTIME_SELECTED,0x333b98,"Load ADC calibration on this+0x18; status ignored by dispatcher."),
 Node("apply_adc_zero",Class.RUNTIME_SELECTED,0x333ba8,"SetADCParameter(this+0x18,0), consuming mutable calibration fields; returned status ignored."),
 Node("load_afe_zero",Class.RUNTIME_SELECTED,0x333bcc,"Load AFE zero on this+0x242838; status ignored."),
 Node("load_afe_bandwidth",Class.RUNTIME_SELECTED,0x333bd8,"Load AFE bandwidth on same object; status ignored."),
 Node("load_clock",Class.RUNTIME_SELECTED,0x333bf4,"Load clock on this+0x245450; status ignored."),
 Node("load_ext",Class.RUNTIME_SELECTED,0x333c10,"Load external calibration on this+0x245458; status ignored."),
 Node("load_ddr",Class.RUNTIME_SELECTED,0x333c2c,"Load DDR calibration on this+0x245510; signed result selects next edge."),
 Node("configure_ddr",Class.UNKNOWN,0x333c58,"Configure loaded DDR data only when signed load result>=1; physical behavior unresolved."),
 Node("load_afg",Class.RUNTIME_SELECTED,0x333ca8,"For selectors1..2, call LoadAfgCalibration(this+0x245568+(selector-1)*0x290,selector); results ignored."),
 Node("load_stray",Class.RUNTIME_SELECTED,0x333ce8,"For selectors0..3, call LoadAdcStary(this+0x18,selector); results ignored."),
 Node("load_la",Class.RUNTIME_SELECTED,0x333d14,"Load LA calibration on this+0x245558; status ignored."),
 Node("sync_delay",Class.HARDWARE_RETURNED,0x333d1c,"CalAdcSyncDelay has device-feedback-dependent internal selection; parent ignores returned status."),
 Node("data_line",Class.UNKNOWN,0x333d40,"CalAdcDataLine(this+0x18,sp+0xa8); buffer may change; parent ignores status."),
 Node("input_delay",Class.UNKNOWN,0x333d5c,"LoadAdcIDelay(this+0x18,false,sp+0xa8); runtime output from prior call is input; status ignored."),
 Node("core_align",Class.HARDWARE_RETURNED,0x333d74,"CalAdcCoreAlign(1,1,sp+0x80); hardware-dependent algorithm not collapsed to constant; parent ignores status/output."),
 Node("qadc",Class.UNKNOWN,0x333d84,"CalQADC(this+0x18); unexpanded hardware/runtime boundary; parent ignores status."),
 Node("thread_start",Class.ASYNCHRONOUS,0x333d94,"RQThread::start(this) creates a thread then detaches it; worker execution need not wait for caller return."),
 Node("return",Class.STATIC_DETERMINED,0x333dbc,"Normal return preserves x0 left by RQThread::start; no forced-success result."),
 Node("canary_failure",Class.UNKNOWN,0x333dc0,"Stack-canary mismatch calls __stack_chk_fail; exceptional terminal boundary.")
)
val edges=mutableListOf<Edge>()
fun chain(vararg ids:String){ids.toList().zipWithNext().forEach{(a,b)->edges+=Edge(a,b,"callee returns normally")}}
chain("get_scope","get_calibration","initialize_buffers","load_lsb","load_vertical","load_adc","apply_adc_zero","load_afe_zero","load_afe_bandwidth","load_clock","load_ext","load_ddr")
edges+=Edge("load_ddr","configure_ddr","signed load result>=1")
edges+=Edge("load_ddr","load_afg","signed load result<1")
chain("configure_ddr","load_afg","load_stray","load_la","sync_delay","data_line","input_delay","core_align","qadc","thread_start")
edges+=Edge("thread_start","return","callee returns and stack canary unchanged")
edges+=Edge("thread_start","canary_failure","callee returns and stack canary differs")
val ids=nodes.map{it.id}.toSet();require(ids.size==nodes.size&&edges.all{it.from in ids&&it.to in ids})
val dispatcherCalls=all.filter{it.owner==init.name}.map{it.pc}.toSet()
require(dispatcherCalls==nodes.filter{it.pc in init.va until init.va+init.size&&it.id!="return"}.map{it.pc}.toSet())
Files.newBufferedWriter(output.resolve("dispatcher.toml")).use{w->
 w.appendLine("schema_version = \"mho900-lab.calibration-dispatcher/1\"\nstock_library_sha256 = ${q(stockHash)}\nentry = \"get_scope\"\nparent_calls_complete = true\ntransitive_recovery_complete = false")
 for(n in nodes)w.appendLine("\n[[nodes]]\nid = ${q(n.id)}\nclassification = ${q(n.kind.name.replace('_','-'))}\npc = ${hx(n.pc)}\nopcode = ${hx(elf.word(n.pc),8)}\nsemantics = ${q(n.semantics)}")
 for(e in edges)w.appendLine("\n[[edges]]\nfrom = ${q(e.from)}\nto = ${q(e.to)}\ncondition = ${q(e.condition)}")
 w.appendLine("\n[loops]\nafg_selectors = [1,2]\nafg_stride = 0x290\nadc_stray_selectors = [0,1,2,3]\npcs = [0x333c60,0x333c70,0x333cb4,0x333cc0,0x333cd0,0x333cf4]\nopcodes = [${listOf(0x333c60L,0x333c70L,0x333cb4L,0x333cc0L,0x333cd0L,0x333cf4L).joinToString{hx(elf.word(it),8)}}]")
 val scope=0x10bee40L;val record=scope+0x60d8+0x18+0x8804
 w.appendLine("\n[storage]\nscope_relative_address = ${hx(scope)}\nadc_record_relative_address = ${hx(record)}\nadc_record_bytes = 1936\nrecord_in_zero_fill = ${elf.zeroFilled(record,1936)}\nrelocations_in_record = ${elf.rels.keys.count{it in record until record+1936}}\nget_scope_pcs = [0x2e5a40,0x2e5a44,0x2e5a48]\nget_scope_opcodes = [${listOf(0x2e5a40L,0x2e5a44L,0x2e5a48L).joinToString{hx(elf.word(it),8)}}]\nlive_state_proven = false")
}
println("dispatcher_nodes = ${nodes.size}\ndispatcher_edges = ${edges.size}\ndispatcher_sha256 = ${q(sha(output.resolve("dispatcher.toml")))}")
