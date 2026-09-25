// Derive the fixed bounded SPU initialization candidate from the pinned stock ELF.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 2) { "Usage: DeriveSpuTranscript.main.kts STOCK_ELF NEW_OUTPUT_DIRECTORY" }
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
data class Binding(val kind:Int,val reloc:Long,val name:String,val slot:Long,val target:Long)
data class FunctionPin(val name:String,val va:Long,val size:Int,val hash:String)
data class Global(val name:String,val address:Long,val value:Long)
data class Sample(val index:Int,val address:Long,val words:List<Long>)
data class Shadow(val name:String,val slot:Long,val target:Long,val checkpoint:Long,val terminal:Long)
data class Write(val offset:Long,val value:Long,val source:String)
data class OpcodePin(val address:Long,val value:Long,val purpose:String)
val bytes=Files.readAllBytes(input); val elf=Elf(bytes); val stockHash=sha(bytes)
require(stockHash=="4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e")
fun sym(name:String,va:Long,size:Long){val s=requireNotNull(elf.syms[name]);require(s.va==va&&s.size==size&&s.shndx!=0){"symbol $name"}}
fun rel(slot:Long,type:Long,name:String?,target:Long){val r=requireNotNull(elf.rels[slot]);require(r.type==type);if(name==null){require(r.sym==null&&r.addend==target)}else require(r.sym?.name==name&&r.sym.va==target)}
fun op(va:Long,v:Long){require(elf.word(va)==v){"opcode ${hx(va)}"}}
val functions=listOf(
 FunctionPin("DevAcquireSPU_Init",0x272f40,216,"947f11b940914edcd82774be418801b22cc558c6bb1642ae674482fcb51fa302"),
 FunctionPin("DevAcquireSPU_Reset",0x272c8c,132,"d571bad3a20d8fc7ca2805e7c2c51746612e2beb19f5f9f008b5f6eb54eae313"),
 FunctionPin("DevAcquireSPU_TxReset",0x272da8,168,"cb6e74d81ea13d92687f6e97a7bb378fbb4a069368cab5359cc406d6ac95bcf6"),
 FunctionPin("DevAcquireSpuH12S4_SetAdcGain",0x273018,696,"b5d1a6d0874f417ffd9cb55ef2bd53abf0b4c5afe6ee509d5c00ac7e9d0b1f73"),
 FunctionPin("DevAcquireSpu_SetAdcBitRange",0x2732d0,172,"d255744c01a416653b2c7468d769bc8eb55ae898200d53674ce3a87404a80257"),
 FunctionPin("chn2log",0x274f04,1012,"5e27da3d64e573f8bf5bf0c479ed3a22cdf77b0afe95711912261e46f2e0956d"),
 FunctionPin("DevSystem_ChnMode",0x27254c,60,"4d76eba59afa2b8ad5c38af6463be59665948eaf59f4e63e550a776388357d7d"),
 FunctionPin("DevSystem_GetSampleMode",0x272490,112,"0da6225a8e5e369beb458fb76e78d00cb921315a599bac9a56bf3a53619a33e4"),
 FunctionPin("DevSystem_GetSeriesParam",0x272244,288,"f27934487bc0496d026e51f6e0fadd67e0d76bc99931d6fab68122edf90c511e"),
 FunctionPin("DevAcquireSpu_WriteRegister",0x272c2c,48,"cb653d202961cbffb4ace9a45ad4d9a3a6216fb0e63d998ab94a5659bcb71555"),
 FunctionPin("Dev_WriteRegister",0x2703c8,156,"3cbc8ab721e7c4fa684e44d6e3e55ac42e6d082a02f81450a4df79bcc133c877"))
functions.forEach{sym(it.name,it.va,it.size.toLong());require(sha(elf.region(it.va,it.size))==it.hash)}
val opcodes=listOf(OpcodePin(0x2724a0,0x97fe30f0,"series-call"),OpcodePin(0x2724c0,0xb940112a,"sample-count"),OpcodePin(0x2724dc,0xf9400508,"sample-pointer"),OpcodePin(0x2724e4,0xd280020a,"sample-stride"),OpcodePin(0x2724f0,0xb9400500,"sample-mode"),OpcodePin(0x27304c,0xb85ec3a0,"gain-selector"),OpcodePin(0x273054,0x97fea63f,"gain-chnmode-call"),OpcodePin(0x272fc0,0x528001e0,"range-selector15"),OpcodePin(0x272fc8,0x97fe1376,"range-helper-call"),OpcodePin(0x274f34,0xb94037e0,"range-selector-reload"),OpcodePin(0x274f40,0x97fe9e84,"range-chnmode-call"),OpcodePin(0x27043c,0xb9000109,"mapped-w32"))
opcodes.forEach{op(it.address,it.value)}
val bindings=listOf(
 Binding(1,0x401,"DevAcquireSPU_Init",0xb8cb50,0x272f40),Binding(1,0x402,"DevAcquireSPU_Reset",0xb7ca38,0x272c8c),Binding(1,0x402,"DevAcquireSPU_TxReset",0xb78630,0x272da8),Binding(1,0x402,"DevAcquireSpuH12S4_SetAdcGain",0xb85af0,0x273018),Binding(1,0x402,"DevAcquireSpu_SetAdcBitRange",0xb785a8,0x2732d0),Binding(1,0x402,"chn2log",0xb820f8,0x274f04),Binding(1,0x402,"DevSystem_ChnMode",0xb8ab80,0x27254c),Binding(1,0x402,"DevSystem_GetSampleMode",0xb7a568,0x272490),Binding(1,0x402,"DevSystem_GetSeriesParam",0xb7bb08,0x272244),Binding(1,0x402,"DevAcquireSpu_WriteRegister",0xb86690,0x272c2c),Binding(1,0x402,"Dev_WriteRegister",0xb79db8,0x2703c8),
 Binding(2,0x401,"gInt32DevAcquireSpuH12S4Ctrl",0xb8d288,0x3cb44fc),Binding(2,0x401,"gInt32DevAcquireSpuH12S4AdcGain",0xb8bb48,0x3cb44a0),Binding(2,0x401,"gInt32DevAcquireSpuTx",0xb8d060,0x3cb44f0),Binding(2,0x401,"gInt32DevAcquireSpuCtrlAdc",0xb8be90,0x3cb44b0))
bindings.forEach{sym(it.name,it.target,if(it.kind==1)functions.single{f->f.name==it.name}.size.toLong() else 4);rel(it.slot,it.reloc,it.name,it.target)}
val globals=listOf(Global("domain",0xb8f4e4,8),Global("selector",0xb8f4e8,900),Global("power_mode",0xbe1134,0))
require(elf.word(globals[0].address)==8L&&elf.word(globals[1].address)==900L) // power mode is BSS and checked live.
require(elf.zeroFilled(globals[2].address,4))
val series=MutableList(9){i->elf.region(0xb8f4f0+i*32L,32)}
val ptrs=listOf(0xb8f808L,0xb8f808L,0xb8f808L,0xb8f908L,0xb8fa08L,0xb8fb08L,0xb8fc08L,0xb8fc08L,0xb8fc08L)
val configs=listOf(0xb8f40cL,0xb8f40cL,0xb8f478L,0xb8f2c8L,0xb8f3a0L,0xb8f40cL,0L,0L,0L)
for(i in 0 until 9){rel(0xb8f4f8+i*32L,0x403,null,ptrs[i]);if(configs[i]!=0L)rel(0xb8f508+i*32L,0x101,when(configs[i]){0xb8f40cL->"HDO4000Conf";0xb8f478L->"MHO900Conf";0xb8f2c8L->"HDO900Conf";else->"HDO2000Conf"},configs[i]) else require(elf.long(0xb8f508+i*32L)==0L)}
fun sw(a:ByteArray,o:Int)=ByteBuffer.wrap(a,o,8).order(ByteOrder.LITTLE_ENDIAN).getLong()
for(i in 0 until 9){require(sw(series[i],8)==ptrs[i]);if(configs[i]!=0L){require(sw(series[i],24)==0L);ByteBuffer.wrap(series[i]).order(ByteOrder.LITTLE_ENDIAN).putLong(24,configs[i])}else require(sw(series[i],24)==0L)}
val keys=series.map{ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).let{b->b.int.toLong()and 0xffffffffL to (b.int.toLong()and 0xffffffffL)}}
require(keys==listOf(2L to 800L,2L to 900L,8L to 900L,2L to 1000L,2L to 2000L,2L to 4000L,1L to 7000L,0L to 7000L,1L to 8000L))
val selected=keys.indexOfFirst{it==8L to 900L};require(selected==2)
val sampleBase=ptrs[selected];require(elf.word(0xb8f4f0+selected*32L+16)==16L)
val samples=listOf(0,1,15).map{i->Sample(i,sampleBase+i*16L,(0 until 4).map{elf.word(sampleBase+i*16L+it*4L)})}
require(samples.map{it.words[1]}==listOf(1L,1L,4L));val mg=samples[1].words[1];val mr=samples[2].words[1]
val checkpointControl=1L;val checkpointGain=0L;val checkpointTx=0L;val checkpointAdc=0L
val resetClear=checkpointControl and 1L.inv() and 0xffffffffL
val txResetClear=resetClear and 0x11L.inv() and 0xffffffffL;val txResetSet=txResetClear or 0x10L
val gainArgument=1L;val gainByte=(gainArgument%4L)*85L
val finalGain=when(mg){1L->gainByte*0x01010101L;2L->(checkpointGain and 0xffff0000L) or (gainByte*0x101L);else->(checkpointGain and 0xffffff00L) or gainByte}
val rangeInput=0x01010101L;val logicalMask=if(mr==1L||mr==2L)0L else (0 until 4).fold(0L){a,i->a or (((rangeInput ushr (i*8))and 1L) shl i)}
val finalTx=checkpointTx or (1L shl 29);val finalAdc=((checkpointAdc or 1L) and 0xff0fffffL) or ((logicalMask and 0xfL) shl 20)
require(listOf(resetClear,txResetClear,txResetSet,finalGain,finalTx,finalAdc)==listOf(0L,0L,0x10L,0x55555555L,0x20000000L,0x00f00001L))
val shadows=listOf(Shadow("control",0xb8d288,0x3cb44fc,checkpointControl,txResetClear),Shadow("gain",0xb8bb48,0x3cb44a0,checkpointGain,finalGain),Shadow("tx",0xb8d060,0x3cb44f0,checkpointTx,finalTx),Shadow("adc_control",0xb8be90,0x3cb44b0,checkpointAdc,finalAdc))
val writes=listOf(Write(0x1000,checkpointControl,"control-post-first-bitset"),Write(0x1000,resetClear,"control-clear-bit0"),Write(0x1000,txResetClear,"tx-reset-clear"),Write(0x1000,txResetSet,"tx-reset-set-bit4"),Write(0x1000,txResetClear,"tx-reset-clear"),Write(0x105c,finalGain,"gain-Mg1"),Write(0x1010,finalTx,"tx-bit29"),Write(0x1014,finalAdc,"adc-range-Mr4"))
require(mg==1L&&mr==4L&&writes.size==8)
val header=64;val bindOff=64;val globalsOff=424;val derivedOff=472;val seriesOff=488;val samplesOff=776;val shadowsOff=872;val writesOff=1000;val total=1064
fun fixture(profile:Int):ByteArray{val b=ByteBuffer.allocate(total).order(ByteOrder.LITTLE_ENDIAN);b.put("MHOSPUT1".toByteArray());b.putInt(1).putInt(header).putInt(total).putInt(profile).putInt(8).putInt(15).putInt(9).putInt(3).putInt(4).putInt(4).putInt(2);repeat(3){b.putInt(0)};bindings.forEach{b.putInt(it.kind).putInt(0).putLong(it.slot).putLong(it.target)};globals.forEach{b.putLong(it.address).putInt(it.value.toInt()).putInt(0)};b.putInt(900).putInt(2).putInt(1).putInt(4);series.forEach{b.put(it)};samples.forEach{s->b.putInt(s.index).putInt(0).putLong(s.address);s.words.forEach{b.putInt(it.toInt())}};shadows.forEach{s->b.putLong(s.slot).putLong(s.target).putInt(4).putInt(s.checkpoint.toInt()).putInt(s.terminal.toInt()).putInt(0)};writes.forEach{b.putInt(it.offset.toInt()).putInt(it.value.toInt())};require(b.position()==total);return b.array()}
Files.createDirectories(output)
val tsv=output.resolve("spu-transcript.tsv");Files.newBufferedWriter(tsv).use{w->w.appendLine("ordinal\toffset\tvalue\tsource");writes.forEachIndexed{i,x->w.appendLine("$i\t${hx(x.offset,4)}\t${hx(x.value,8)}\t${x.source}")}}
val stock=output.resolve("spu-stock.bin");val private=output.resolve("spu-private.bin");Files.write(stock,fixture(1));Files.write(private,fixture(2))
val manifest=output.resolve("manifest.toml");Files.newBufferedWriter(manifest).use{w->
 w.appendLine("schema_version = \"mho900-lab.spu-transcript-derivation/1\"");w.appendLine("stock_library_sha256 = ${q(stockHash)}");w.appendLine("candidate = \"fixed-domain8-series900-record2-count16-Mg1-Mr4\"");w.appendLine("write_count = 8");w.appendLine("control_checkpoint = \"post-first-bitset\"");w.appendLine("pre_spu_control_unique = false")
 w.appendLine("\n[protocol]");w.appendLine("magic = \"MHOSPUT1\"\nversion = 1\nbyte_order = \"little-endian\"\ntotal_size = $total\nheader_offset = 0\nheader_size = $header\nbindings_offset = $bindOff\nbinding_count = 15\nbinding_size = 24\nglobals_offset = $globalsOff\nglobal_count = 3\nglobal_size = 16\nderived_offset = $derivedOff\nseries_offset = $seriesOff\nseries_count = 9\nseries_size = 32\nsamples_offset = $samplesOff\nsample_count = 3\nsample_size = 32\nshadows_offset = $shadowsOff\nshadow_count = 4\nshadow_size = 32\nwrites_offset = $writesOff\nwrite_count = 8\nwrite_size = 8\nrepeat_count = 2")
 bindings.forEach{x->w.appendLine("\n[[bindings]]\nname = ${q(x.name)}\nkind = ${x.kind}\nrelocation_type = ${q(hx(x.reloc))}\nslot_relative = ${q(hx(x.slot))}\nexpected_relative = ${q(hx(x.target))}")}
 functions.forEach{x->w.appendLine("\n[[function_pins]]\nname = ${q(x.name)}\naddress = ${q(hx(x.va))}\nsize = ${x.size}\nsha256 = ${q(x.hash)}")}
 opcodes.forEach{x->w.appendLine("\n[[instruction_pins]]\naddress = ${q(hx(x.address))}\nword = ${q(hx(x.value,8))}\npurpose = ${q(x.purpose)}")}
 for(p in listOf(tsv,stock,private))w.appendLine("\n[[files]]\npath = ${q(p.fileName.toString())}\nsize = ${Files.size(p)}\nsha256 = ${q(sha(p))}")
 w.appendLine("\n[limits]\nclassification = \"fixed-conditional-software-transcript\"\nlive_deviation_is_rejection = true\nthreshold_object_included = false\nruntime_bindings_verified = false\nconcurrent_mutation_excluded = false\nhardware_effects_inferred = false")
}
println("output = ${output.toAbsolutePath()}");println("stock_fixture_sha256 = ${sha(stock)}");println("private_fixture_sha256 = ${sha(private)}")
