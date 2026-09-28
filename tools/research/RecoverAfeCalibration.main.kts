// Recover bounded AFE calibration call edges from the pinned stock ELF.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 2) { "Usage: RecoverAfeCalibration.main.kts STOCK_ELF NEW_OUTPUT_DIRECTORY" }
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
val names=listOf(
 "_ZN16CCalibration_Afe18LoadAfeZeroCalDataEv", "_ZN16CCalibration_Afe23LoadAfeBandWidthCalDataEv",
 "_Z35DrvCalibrationAfe_BandWidthSaveDatav", "_Z12Drv_GetScopev", "_ZN9CDrvScope14GetCalibrationEv",
 "_ZN14CCheckedStreamC1Ev", "_ZN14CCheckedStream4loadERK7RStringPvj", "_ZN14CCheckedStream4saveERK7RStringPvj",
 "_ZN14CCheckedStream10getNowTimeEv", "_Z5toBCDPhi", "_ZN6CCrc325crc32EPvi",
 "_ZN5RFileC2ERK7RString", "_ZN5RFile4openEi", "_ZN5RFile4readEPcj", "_ZN5RFile5writeEPKcj",
 "_ZN5RFile5closeEv", "_ZN5RFile5flushEv", "_ZN5RFile6handleEv", "_ZN5RFileD2Ev",
 "_ZN7RStringC2EPKc", "_ZN7RStringD2Ev", "_ZN10RByteArrayC2Ev", "_ZN10RByteArrayD2Ev",
 "_ZN10RByteArray6appendEPKci", "_ZN10RByteArray4dataEv", "_ZNK10RByteArray4sizeEv")
val selected=names.map{requireNotNull(elf.syms[it]){it}}+Sym("dispatcher_post_adc",0x333bac,0x4c,1)
val all=selected.flatMap(::calls)
require(all.none{it.form=="BLR"}){"Unexpected indirect call: review before continuation"}
val patches=(0 until 12).map{0x350f2cL+it*4}.map{pc->
 val word=elf.word(pc);require(word and 0xffc003ffL==0xb9000128L)
 pc to (((word ushr 10)and 0xfff)*4)
}
require(patches.map{it.second}==listOf(0x2738L,0x2750,0x2768,0x2788,0x27a0,0x27b8,0x27d8,0x27f0,0x2808,0x2828,0x2840,0x2858))
fun movz(pc:Long,register:Int):Long{val word=elf.word(pc);require(word and 0xffe0001fL==0x52800000L+register);return(word ushr 5)and 0xffff}
require(movz(0x350f24,8)==115L)
require(movz(0x35067c,3)==560L&&movz(0x350eac,3)==320L&&movz(0x351024,3)==320L)
require(movz(0x3dcd7c,1)==2L&&movz(0x25710c,9)==0x42L&&movz(0x257114,9)==0x1b6L)
fun cstr(va:Long):String{val bytes=mutableListOf<Byte>();var at=va;while(true){val b=elf.region(at++,1)[0];if(b==0.toByte())break;bytes.add(b);require(bytes.size<256)};return bytes.toByteArray().toString(Charsets.UTF_8)}
val paths=listOf(0x99d9b3L,0x99d9d0,0x99d9f5,0x99da17).map{it to cstr(it)}
require(paths.map{it.second}==listOf("/rigol/data/cal_afe_zero.hex","/rigol/data/default/cal_afe_zero.hex","/rigol/data/cal_afe_bandwidth.hex","/rigol/data/default/cal_afe_bandwidth.hex"))
Files.createDirectories(output)
Files.newBufferedWriter(output.resolve("inventory.toml")).use{w->
 w.appendLine("schema_version = \"mho900-lab.afe-static-inventory/1\"\nstock_library_sha256 = ${q(stockHash)}\ntransitive_complete = false\nindirect_calls_in_expanded_ranges = 0\nexception_and_standard_runtime_bodies_complete = false")
 for(s in selected.sortedBy{it.va})w.appendLine("\n[[ranges]]\nname = ${q(s.name)}\naddress = ${hx(s.va)}\nsize = ${s.size}\nsha256 = ${q(sha(elf.region(s.va,s.size.toInt())))}")
 for(c in all){w.appendLine("\n[[calls]]\nowner = ${q(c.owner)}\npc = ${hx(c.pc)}\nopcode = ${hx(c.word,8)}\nform = ${q(c.form)}")
 c.branch?.let{w.appendLine("branch_target = ${hx(it)}")};val t=c.target
 if(t==null)w.appendLine("resolution = \"INDIRECT-UNKNOWN\"")else{w.appendLine("symbol = ${q(t.name)}\nresolved_target = ${hx(t.va)}\ndefined = ${t.defined}\nexpanded = ${selected.any{it.name==t.name}}\nboundary = ${q(if(selected.any{it.name==t.name})"expanded" else if(!t.defined&&t.name!="UNRESOLVED")"external-runtime" else "unexpanded-review")}");t.slot?.let{w.appendLine("relocation_slot = ${hx(it)}")}}
 }
}
Files.newBufferedWriter(output.resolve("constants.toml")).use{w->
 w.appendLine("schema_version = \"mho900-lab.afe-static-constants/1\"\nzero_payload_bytes = ${movz(0x35067c,3)}\nbandwidth_payload_bytes = ${movz(0x350eac,3)}\npatch_value = ${movz(0x350f24,8)}\nsave_rfile_mode = ${movz(0x3dcd7c,1)}\nsave_open_flags = ${hx(movz(0x25710c,9))}\nsave_create_mode = ${hx(movz(0x257114,9))}")
 for((pc,offset)in patches)w.appendLine("\n[[patches]]\npc = ${hx(pc)}\noffset = ${hx(offset)}\nwidth = 4\nvalue = 115")
 for((va,path)in paths)w.appendLine("\n[[paths]]\naddress = ${hx(va)}\nvalue = ${q(path)}")
}
println("schema_version = \"mho900-lab.afe-static-derivation/1\"\nranges = ${selected.size}\ncalls = ${all.size}\ninventory_sha256 = ${q(sha(output.resolve("inventory.toml")))}\nconstants_sha256 = ${q(sha(output.resolve("constants.toml")))}")
