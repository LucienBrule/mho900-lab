// A software prediction for one pinned, stopped stock snapshot. No device responses.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

fun digest(bytes: ByteArray) = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))
fun hash(path: Path): String = Files.newInputStream(path).use { stream ->
    val md = MessageDigest.getInstance("SHA-256"); val buffer = ByteArray(65536)
    while (true) { val n = stream.read(buffer); if (n < 0) break; md.update(buffer, 0, n) }
    HexFormat.of().formatHex(md.digest())
}
fun hex(v: Long) = "0x" + v.toString(16)
class Little(val bytes: ByteArray) {
    private val b = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
    fun s16(i: Int) = b.getShort(i).toInt()
    fun u16(i: Int) = s16(i) and 65535
    fun s32(i: Int) = b.getInt(i)
    fun u32(i: Int) = s32(i).toLong() and 0xffffffffL
    fun s64(i: Int) = b.getLong(i)
    fun u8(i: Int) = bytes[i].toInt() and 255
}
data class Segment(val offset: Long, val address: Long, val size: Long)
class Elf(bytes: ByteArray) {
    private val b = Little(bytes)
    private val segments = (0 until b.u16(56)).map { b.s64(32).toInt() + it*b.u16(54) }
        .filter { b.u32(it) == 1L }.map { Segment(b.s64(it+8),b.s64(it+16),b.s64(it+32)) }
    fun region(address: Long, length: Int): ByteArray {
        val s = segments.single { address >= it.address && address+length <= it.address+it.size }
        val offset = (s.offset+address-s.address).toInt(); return b.bytes.copyOfRange(offset,offset+length)
    }
    fun word(address: Long) = Little(region(address,4)).u32(0)
}
enum class Phase { REFERENCE, FINE_GAIN, CORE_GAIN, STARY, CORE_OFFSET, SAMPLE_DELAY, CLOCK_DELAY, SYNC }
sealed interface Operation { val phase: Phase }
data class Write(override val phase: Phase, val offset: Long, val value: Long): Operation
// Unknown is a type: a read cannot accidentally acquire a default numeric response.
data class Read(override val phase: Phase, val offset: Long, val chip: Int, val mask: Long): Operation
data class Delay(override val phase: Phase, val microseconds: Int): Operation
data class Shadow(val name: String, val address: Long, val width: Int, val initial: List<Long>, val values: MutableList<Long>)
data class Transition(val phase: Phase, val name: String, val index: Int, val before: Long, val after: Long)
data class Field(val name: String, val source: String, val offset: Int, val type: String, val value: Long)
data class Calibration(val reference: List<Int>, val fine: List<Long>, val gain: List<Int>, val offset: List<Int>,
                       val sampleDelay: List<Int>, val clockFine: List<Int>, val clockCoarse: List<Int>)
fun bypass(rate: Long) = rate.toDouble() <= 500000000.0
fun quantize(value: Long, pointTime: Long): Long {
    val quantum = (pointTime shl 2) and 0xffffffffL
    val quotient = if (quantum == 0L) 0L else value / quantum
    return (quotient * quantum) and 0xffffffffL
}
if (args.toList() == listOf("--self-test")) {
    val b=Little(byteArrayOf(-1,-1,0,0,0,0,0,0))
    check(b.s16(0)==-1 && b.u16(0)==65535)
    check(bypass(-1) && bypass(Long.MIN_VALUE) && bypass(500000000) && !bypass(500000001))
    check(quantize(-1500000,250000)==0xfff0bdc0L && quantize(-999999,250000)==0L)
    check(quantize(123,0x40000000)==0L)
    println("signed-width, signed-rate, truncation and low32 quantum controls passed"); kotlin.system.exitProcess(0)
}
require(args.size==3) { "Usage: InstantiateAdcCandidate.main.kts STOCK_RUN STOCK_ELF NEW_OUTPUT_DIRECTORY | --self-test" }
val run=Path.of(args[0]);val stock=Path.of(args[1]);val output=Path.of(args[2])
require(!Files.exists(output)) { "output exists" }
val reviewPath=Path.of("out/adc-input-evidence-review/review01/review.toml")
require(hash(reviewPath)=="b34cf1a86a01dc54cbc14e28de60989352579423224e7ddfb8096d1990b0810b")
data class Pin(val path: Path, val sha256: String)
val pins=Files.readString(reviewPath).split("[[reviewed_artifacts]]").drop(1).map { block ->
    fun field(key:String)=Regex("(?m)^$key = \"([^\"]+)\"$").find(block)!!.groupValues[1]
    Pin(run.resolve(field("path")),field("sha256"))
}
require(pins.size==333 && pins.map{it.path}.distinct().size==333)
pins.forEach { require(hash(it.path)==it.sha256) { "stale reviewed input ${it.path.fileName}" } }
require(hash(stock)=="4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e")
val elf=Elf(Files.readAllBytes(stock));val maskBytes=elf.region(0x9948bc,416)
require(digest(maskBytes)=="d9b88ca5b40ae86cc40dfa2a20cc3a6f49841c5d97cb0c309617c0dba6034b2d")
val masks=Little(maskBytes)
require(elf.word(0x333ba8)==0x97fb9b9eL && elf.word(0x333bac)==0x5285070aL && elf.word(0x33fc78)==0xd65f03c0L)
require(Little(elf.region(0x99d210,8)).let{it.u32(0)==0L && it.u32(4)==0L})
val clockOrder=Little(elf.region(0x99c500,16)).let{b->List(4){b.u32(4*it).toInt()}}
require(clockOrder==listOf(0,2,1,3))
fun capture(name:String)=Little(Files.readAllBytes(run.resolve(name)))
val record=capture("native-loader-terminal-adc.bin")
val setting=capture("adc-input-setting.bin");val drv=capture("adc-input-drvparam.bin")
val series=capture("adc-input-series.bin");val config=capture("adc-input-config.bin")
val sample=capture("adc-input-sample-entry.bin");val global=capture("adc-input-global-inputs.bin")
val low=capture("adc-input-shadow-low.bin");val high=capture("adc-input-shadow-high.bin")
val fields=mutableListOf<Field>()
fun signedRecord(name:String,offset:Int):Int = record.s16(offset-0x8804).also {
    fields+=Field(name,"native-loader-terminal-adc.bin",offset-0x8804,"s16",it.toLong())
}
val cal=Calibration(List(2){signedRecord("reference[$it]",0x8854+2*it)},
    List(16){i->record.u32(0x8cd4-0x8804+4*i).also{fields+=Field("fine[$i]","native-loader-terminal-adc.bin",0x8cd4-0x8804+4*i,"u32",it)}},
    List(16){signedRecord("gain[$it]",0x8824+2*it)},List(16){signedRecord("offset[$it]",0x8804+2*it)},
    List(8){signedRecord("sampleDelay[$it]",0x8844+2*it)},
    List(2){signedRecord("clockFine[$it]",0x8a04+4*it)},List(2){signedRecord("clockCoarse[$it]",0x8a06+4*it)})
require(fields.size==62)
val rate=drv.s64(8);require(rate==0L && bypass(rate)) { "Only captured bypass branch admitted" }
val selector0=series.u32(0);val selector1=series.u32(4)
val effective1=if(selector1==4000L && global.u32(12)==1L)2000L else selector1
val matching=(0..8).filter { i->series.u32(12+32*i)==selector0 && series.u32(16+32*i)==effective1 }
require(matching==listOf(2))
val row=matching.single();val bound=series.u32(12+32*row+16)
val rawMask=(0..3).fold(0){a,i->a or (if((0..7).any{setting.u8(0xc0*i+0xb4+it) and 1 != 0})1 shl i else 0)}
val bode=setting.u8(0x1c70) and 1
val normalized=(if(bode!=0)15 else rawMask).let{if(it.toLong()>=bound)0 else it}
require(bound==16L && rawMask==0 && normalized==0 && sample.u32(4)==1L)
val master=(setting.s32(0x1b30)-1)%4;require(master in 0..3)
val d=config.u32(0x20);val pointTime=config.u32(0x38)
val initial=listOf(0L,-2*d,-d,-3*d)
// This observed mode is not the two-channel branch.
require(sample.u32(4)!=2L)
val delays=List(4){i->quantize(initial[i]-initial[master]+setting.s64(0xc0*i+0x28)+setting.s32(0x300+0x40*i+0x38),pointTime)}
val scale=setting.s64(0);val impedance=setting.s32(0x1c)
val thresholds=listOf(5000000L,10000000L,20000000L,50000000L,100000000L,200000000L,500000000L,1000000000L,2000000000L,5000000000L,10000000000L)
val maximum=if(impedance==1)7 else 10
val scaleIndex=(0..maximum).firstOrNull{scale<=thresholds[it]}?:maximum
val bucket=((((delays[0]*0x10624dd3L) ushr 38)+120000L).and(0xffffffffL)*0x10624dd3L ushr 36) and 15
val runtimeFields=mutableListOf<Field>()
for(i in 0..3) {
    runtimeFields+=Field("channel[$i].scale","adc-input-setting.bin",0xc0*i,"s64",setting.s64(0xc0*i))
    runtimeFields+=Field("channel[$i].impedance","adc-input-setting.bin",0xc0*i+0x1c,"s32",setting.s32(0xc0*i+0x1c).toLong())
    runtimeFields+=Field("channel[$i].delay","adc-input-setting.bin",0xc0*i+0x28,"s64",setting.s64(0xc0*i+0x28))
    runtimeFields+=Field("probe[$i].delay","adc-input-setting.bin",0x300+0x40*i+0x38,"s32",setting.s32(0x300+0x40*i+0x38).toLong())
    for(j in 0..7) runtimeFields+=Field("channel[$i].on[$j]","adc-input-setting.bin",0xc0*i+0xb4+j,"u8-bit0",setting.u8(0xc0*i+0xb4+j).toLong())
}
runtimeFields+=listOf(Field("sampleRate","adc-input-drvparam.bin",8,"s64",rate),
    Field("masterSource","adc-input-setting.bin",0x1b30,"s32",setting.s32(0x1b30).toLong()),
    Field("bode","adc-input-setting.bin",0x1c70,"u8-bit0",setting.u8(0x1c70).toLong()),
    Field("sampleMode","adc-input-sample-entry.bin",4,"u32",sample.u32(4)),
    Field("delay","adc-input-config.bin",0x20,"u32",d),Field("pointTime","adc-input-config.bin",0x38,"u32",pointTime))
val shadows=mutableListOf<Shadow>()
fun shadow(name:String,address:Long,width:Int,count:Int):Shadow {
    val (b,base)=when(address){in 0x3cb44fcL..0x3cb4534L->low to 0x3cb44fcL
        in 0x3cb457cL..0x3cb45ecL->high to 0x3cb457cL
        else->global to 0xbe1128L}
    val values=List(count){val at=(address-base).toInt()+width*it;if(width==2)b.u16(at).toLong() else b.u32(at)}
    return Shadow(name,address,width,values,values.toMutableList()).also{shadows+=it}
}
val ref=shadow("reference09",0x3cb45bc,2,2)
val gain=shadow("gainAndDelay",0x3cb45a6,2,8);val offset=shadow("offset",0x3cb457c,2,8)
val clk=shadow("clock01",0x3cb45b8,2,2);val smp4=shadow("sample04",0x3cb45ec,2,2);val smp5=shadow("sample05",0x3cb45d8,2,2)
val fine=shadow("fineGain",0x3cb4534,4,1);val sync=shadow("syncControl",0x3cb44fc,4,1)
listOf("adjustGain","adjustGainLoad","adjustOffset1","adjustOffset1Load","adjustOffset2","adjustOffset2Load").zip(
    listOf(0xbe1138L,0xbe1144L,0xbe113cL,0xbe1148L,0xbe1140L,0xbe114cL)).forEach{(n,a)->shadow(n,a,4,1)}
val ctrl=shadow("adjustControl",0xbe1150,4,1)
val operations=mutableListOf<Operation>();val transitions=mutableListOf<Transition>()
fun change(phase:Phase,s:Shadow,i:Int,v:Long):Long {
    val after=v and (if(s.width==2)65535L else 0xffffffffL)
    transitions+=Transition(phase,s.name,i,s.values[i],after);s.values[i]=after;return after
}
fun write(p:Phase,o:Long,v:Long){operations+=Write(p,o,v and 0xffffffffL)}
fun delay(p:Phase,u:Int){operations+=Delay(p,u)}
fun adc(p:Phase,chip:Int,reg:Int,value:Long) {
    require(chip in 0..1 && reg in 0..77)
    val encoded=(value xor masks.u32(reg*4)) and 65535L
    val command=((chip+1).toLong() shl 24) or 0x04000000L or (reg.toLong() shl 16) or encoded
    write(p,0x3000,command);delay(p,100);write(p,0x3000,command and 0x03ffffff)
}
for(chip in 0..1) adc(Phase.REFERENCE,chip,9,change(Phase.REFERENCE,ref,chip,(ref.values[chip] and 0xffc0) or (cal.reference[chip].toLong() and 63)))
val packed=cal.fine.withIndex().fold(0L){a,(i,v)->a or ((v and 3) shl (2*i))}
write(Phase.FINE_GAIN,0x1058,change(Phase.FINE_GAIN,fine,0,packed))
for(ch in 0..3) for(k in 0..3) {
    val chip=k/2;val core=ch+4*(k%2);val value=cal.gain[ch+4*k];require(value in -64..63)
    adc(Phase.CORE_GAIN,chip,0x15+8*core,change(Phase.CORE_GAIN,gain,core,(gain.values[core] and 0xff80) or (value.toLong() and 127)))
}
write(Phase.STARY,0x1574,change(Phase.STARY,ctrl,0,ctrl.values[0] or 1));delay(Phase.STARY,20000)
for(i in 0..15) {
    val core=i%8;val value=cal.offset[i];require(value in -1024..1023)
    adc(Phase.CORE_OFFSET,i/8,0x14+8*core,change(Phase.CORE_OFFSET,offset,core,(offset.values[core] and 0xf800) or (value.toLong() and 2047)))
}
for(chip in 0..1) for(j in 0..3) {
    val selector=clockOrder[j];val s=if(selector<2)smp4 else smp5;val shift=8*(selector%2)
    val value=(s.values[chip] and (if(shift==0)0xff00L else 0x00ffL)) or ((cal.sampleDelay[chip*4+j].toLong() and 255) shl shift)
    adc(Phase.SAMPLE_DELAY,chip,if(selector<2)4 else 5,change(Phase.SAMPLE_DELAY,s,chip,value))
}
for(chip in 0..1) {
    val p=Phase.CLOCK_DELAY
    adc(p,chip,1,change(p,clk,chip,(clk.values[chip] and 0xfc00) or (cal.clockFine[chip].toLong() and 1023) or ((cal.clockCoarse[chip].toLong() and 7) shl 10)))
    val command=((chip+1).toLong() shl 24) or 0x04810000L
    write(p,0x3000,command);delay(p,100);write(p,0x3000,command and 0x03ffffff);delay(p,100)
    operations+=Read(p,0x3004,chip,masks.u32(4))
}
for(i in 0..2) {
    val value=(sync.values[0] and 0xfffffffdL) or (if(i==1)2L else 0L)
    write(Phase.SYNC,0x1000,change(Phase.SYNC,sync,0,value));if(i<2)delay(Phase.SYNC,200)
}
require(operations.filterIsInstance<Write>().size==97 && operations.filterIsInstance<Read>().size==2)
require(operations.filterIsInstance<Delay>().sumOf{it.microseconds}==25200)
Files.createDirectories(output)
val manifest=buildString {
    append("schema_version = \"mho900-lab.adc-candidate/1\"\nclassification = \"derived-software-prediction\"\n")
    append("guest_executed = false\nhardware_read_values_supplied = false\nmode = 0\nwrites = 97\nreads = 2\nrequested_delay_us = 25200\n")
    append("entry_call_pc = 0x333ba8\nreturn_instruction_pc = 0x33fc78\npost_return_pc = 0x333bac\npost_return_opcode = 0x5285070a\n")
    append("normal_return = 0\nnormal_return_requires_stack_check = true\nhelper_statuses_control_main_branch = false\n")
    append("read_use = \"bit16 selects low16 or initialized zero, then XOR mask[1]; caller logs only\"\n")
    append("transport_assumption = \"mapped base present; normal mutex and logging completion\"\n")
    append("thread_scope = \"one stopped thread-group snapshot; future observation must cover all mapping users\"\n")
    append("original_experiment_result = \"frozen-full-verifier-rejected; separate offline completeness review\"\n")
    append("\n[selection]\nselector0 = $selector0\nselector1 = $selector1\nrow = $row\ntable_bound = $bound\nraw_mask = $rawMask\nnormalized_mask = $normalized\nsample_mode = ${sample.u32(4)}\nsample_rate_s64 = $rate\nbranch = \"stary-bypass-only\"\n")
    append("master_index = $master\nconfig_delay_u32 = $d\nconfig_point_time_u32 = $pointTime\nchannel_delay_u32 = $delays\nscale_s64 = $scale\nimpedance_s32 = $impedance\nscale_index = $scaleIndex\nbucket = $bucket\nmatrix_values_used_for_mmio = false\n")
    for(f in fields) append("\n[[calibration_fields]]\nname = \"${f.name}\"\nsource = \"${f.source}\"\noffset = ${hex(f.offset.toLong())}\ntype = \"${f.type}\"\nvalue = ${f.value}\n")
    for(f in runtimeFields) append("\n[[runtime_fields]]\nname = \"${f.name}\"\nsource = \"${f.source}\"\noffset = ${hex(f.offset.toLong())}\ntype = \"${f.type}\"\nvalue = ${f.value}\n")
    for(reg in (listOf(1,4,5,9)+(0..7).flatMap{listOf(0x14+8*it,0x15+8*it)}).sorted())
        append("\n[[mask_words]]\nregister = $reg\nvalue = ${hex(masks.u32(reg*4))}\n")
    for(s in shadows) append("\n[[shadows]]\nname = \"${s.name}\"\naddress = ${hex(s.address)}\nwidth = ${s.width}\ninitial = ${s.initial}\nfinal = ${s.values}\n")
    for(t in transitions) append("\n[[transitions]]\nphase = \"${t.phase}\"\nshadow = \"${t.name}\"\nindex = ${t.index}\nbefore = ${t.before}\nafter = ${t.after}\n")
    for((i,op) in operations.withIndex()) {
        append("\n[[operations]]\nindex = $i\nphase = \"${op.phase}\"\n")
        when(op) {
            is Write->append("kind = \"W32\"\noffset = ${hex(op.offset)}\nvalue = ${hex(op.value)}\n")
            is Read->append("kind = \"R32\"\noffset = ${hex(op.offset)}\nchip = ${op.chip}\nvalue_class = \"HARDWARE-RETURNED-UNOBSERVED\"\nmask = ${hex(op.mask)}\n")
            is Delay->append("kind = \"SLEEP\"\nmicroseconds = ${op.microseconds}\n")
        }
    }
    val consumed=listOf(reviewPath,stock,Path.of("tools/research/InstantiateAdcCandidate.main.kts"))+pins.filter{
        it.path.fileName.toString().startsWith("adc-input-") || it.path.fileName.toString()=="native-loader-terminal-adc.bin" || it.path.parent.fileName.toString()=="adc-parameter-static"
    }.map{it.path}
    for(p in consumed) append("\n[[inputs]]\npath = \"$p\"\nsha256 = \"${hash(p)}\"\n")
}
Files.writeString(output.resolve("candidate.toml"),manifest)
val tsv="index\tphase\tkind\toffset\toperand\n"+operations.withIndex().joinToString(""){(i,op)->
    val row=when(op){is Write->"W32\t${hex(op.offset)}\t${hex(op.value)}";is Read->"R32\t${hex(op.offset)}\tUNKNOWN";is Delay->"SLEEP\t-\t${op.microseconds}"}
    "$i\t${op.phase}\t$row\n"
}
Files.writeString(output.resolve("sequence.tsv"),tsv)
pins.forEach{require(hash(it.path)==it.sha256)}
println("Derived ${operations.size} ordered operations: 97 writes, 2 unknown reads, 25200 us; originals unchanged")
