// Recover byte-bound ADC parameter control flow and direct-call provenance.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 2) { "Usage: RecoverAdcParameter.main.kts STOCK_ELF NEW_OUTPUT_DIRECTORY" }
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
// Conditional pruning is limited to reviewed mode-zero selector tests. Every
// other conditional edge remains explicit, including loop exit and stack checks.
val forcedFallthrough = mapOf(0x33f074L to 0x3500042bL, 0x33f794L to 0x35000768L, 0x33ee24L to 0x540006ecL)
for ((pc, op) in forcedFallthrough) require(elf.word(pc) == op)
data class Jump(val branch:Long,val table:Long,val count:Int,val boundPc:Long)
val jumps=listOf(Jump(0x281a8c,0x9945cc,8,0x281a68),Jump(0x281f60,0x99460c,8,0x281f3c),Jump(0x284500,0x9946fc,8,0x2844dc),Jump(0x347ac0,0x99c558,4,0x347aa0))
val jumpTargets=jumps.associate{j->
 val pc=j.branch-20;val a=elf.word(pc);val add=elf.word(pc+4)
 require(a and 0x9f00001fL==0x90000008L&&add and 0xffc003ffL==0x91000108L)
 val base=(pc and -4096L)+(signed(((a ushr 29)and 3)or(((a ushr 5)and 0x7ffff)shl 2),21)shl 12)+((add ushr 10)and 0xfff)
 require(base==j.table&&((elf.word(j.boundPc) ushr 10)and 0xfff)==j.count-1L)
 j.branch to (0 until j.count).map{j.table+signed(elf.word(j.table+it*4L),32)}
}
data class Instruction(val pc:Long,val word:Long,val successors:List<Long>,val branchKind:String)
fun reachable(s:Sym):List<Instruction> {
 val seen=mutableMapOf<Long,Instruction>();val todo=ArrayDeque<Long>();todo.add(s.va)
 while(todo.isNotEmpty()) {
  val pc=todo.removeFirst();if(pc in seen)continue
  require(pc in s.va until s.va+s.size && pc%4==0L)
  val w=elf.word(pc);var kind="fallthrough"
  val next=when {
   w and 0xfffffc1fL==0xd65f0000L->{kind="return";emptyList()}
   w and 0xfffffc1fL==0xd61f0000L->{kind=if(pc in jumpTargets)"table-branch" else "indirect-branch-unknown";jumpTargets[pc]?:emptyList()}
   w and 0xfc000000L==0x14000000L->{kind="branch";listOf(pc+(signed(w and 0x3ffffff,26)shl 2))}
   w and 0xff000010L==0x54000000L->{kind="conditional";listOf(pc+4,pc+(signed((w ushr 5)and 0x7ffff,19)shl 2))}
   w and 0x7e000000L==0x34000000L->{kind="compare-branch";listOf(pc+4,pc+(signed((w ushr 5)and 0x7ffff,19)shl 2))}
   w and 0x7e000000L==0x36000000L->{kind="test-bit-branch";listOf(pc+4,pc+(signed((w ushr 5)and 0x3fff,14)shl 2))}
   else->listOf(pc+4)
  }.let{ if(pc in forcedFallthrough){kind="mode-zero-fallthrough";listOf(pc+4)}else it }
  val inside=next.filter{it in s.va until s.va+s.size}
  seen[pc]=Instruction(pc,w,next,kind);inside.forEach(todo::addLast)
 }
 return seen.values.sortedBy{it.pc}
}
val roots=listOf(0x33efe0L,0x33ec00L,0x33edacL,0x33fc80L,0x2801ecL,0x281a04L,0x281ed8L,0x2844b4L,0x284554L,0x275858L,0x2739c0L,0x27e8a8L,0x2717c8L,
 0x27e920L,0x2718b8L,0x270594L,0x2703c8L,0x272c2cL,0x284274L,0x284304L,0x284394L,0x284424L,
 0x27e490L,0x27e57cL,0x27e668L,0x27e754L,0x27e7dcL,0x27e844L,0x34b808L,0x347990L,
 0x2e5a40L,0x2f3db8L,0x2fce24L,0x2f006cL,0x2e83a4L)
fun symbolAt(address:Long)=elf.syms.values.filter{it.va==address&&it.shndx!=0&&it.size>0}.sortedBy{it.name}.firstOrNull()?:error("Missing symbol ${hx(address)}")
val selected=roots.map(::symbolAt)
Files.createDirectories(output)
val instructions=selected.associateWith(::reachable)
Files.newBufferedWriter(output.resolve("inventory.toml")).use{w->
 w.appendLine("schema_version = \"mho900-lab.adc-parameter-inventory/1\"\nstock_elf_sha256 = ${q(stockHash)}")
 w.appendLine("scope = \"Selected high-level functions and transport helpers; mode-zero pruning only at three byte-bound selector tests\"")
 w.appendLine("transitive_complete = false\nsemantic_formulas_machine_proven = false")
 for(s in selected){
  val cfg=instructions.getValue(s);val pcs=cfg.map{it.pc}.toSet()
  w.appendLine("\n[[ranges]]\nname = ${q(s.name)}\naddress = ${hx(s.va)}\nsize = ${s.size}\nsha256 = ${q(sha(elf.region(s.va,s.size.toInt())))}\nreachable_instruction_count = ${cfg.size}")
  for(c in calls(s).filter{it.pc in pcs}){
   w.appendLine("\n[[calls]]\nowner = ${q(s.name)}\npc = ${hx(c.pc)}\nopcode = ${hx(c.word,8)}\nform = ${q(c.form)}")
   c.branch?.let{w.appendLine("branch_target = ${hx(it)}")}
   val t=c.target
   if(t==null)w.appendLine("resolution = \"INDIRECT-UNKNOWN\"")else{
    w.appendLine("symbol = ${q(t.name)}\nresolved_target = ${hx(t.va)}\ndefined = ${t.defined}\nexpanded = ${selected.any{it.name==t.name}}")
    t.slot?.let{w.appendLine("relocation_slot = ${hx(it)}")}
   }
  }
  for(i in cfg.filter{it.branchKind!="fallthrough"})w.appendLine("\n[[branches]]\nowner = ${q(s.name)}\npc = ${hx(i.pc)}\nopcode = ${hx(i.word,8)}\nkind = ${q(i.branchKind)}\nsuccessors = [${i.successors.joinToString(", "){hx(it)}}]")
 }
 val tables=listOf(Triple("sample-clock-order",0x99c500L,16),Triple("gain-index-pairs",0x99d210L,80),Triple("adc-mask",0x9948bcL,416),Triple("delay-map",0x99d420L,32),Triple("lane-permutation",0x99d518L,64))+jumps.map{Triple("jump-${hx(it.branch)}",it.table,it.count*4)}
 for((id,a,n) in tables){
  val bytes=elf.region(a,n);val d=ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
  val values=(0 until n/4).map{d.getInt(it*4)}
  w.appendLine("\n[[tables]]\nid = ${q(id)}\naddress = ${hx(a)}\nbytes = $n\nelement_width = 4\nsigned = true\nsha256 = ${q(sha(bytes))}\nvalues = [${values.joinToString(", ")}]")
 }
}
Files.newBufferedWriter(output.resolve("reachable-instructions.tsv")).use{w->
 w.appendLine("function\tpc\topcode\tsuccessors")
 for((s,cfg) in instructions)for(i in cfg)w.appendLine("${s.name}\t${hx(i.pc)}\t${hx(i.word,8)}\t${i.successors.joinToString(","){hx(it)}}")
}
println("schema_version = \"mho900-lab.adc-parameter-extraction/1\"")
println("ranges = ${selected.size}\nreachable_instructions = ${instructions.values.sumOf{it.size}}")
println("inventory_sha256 = ${q(sha(output.resolve("inventory.toml")))}")
println("instructions_sha256 = ${q(sha(output.resolve("reachable-instructions.tsv")))}")
