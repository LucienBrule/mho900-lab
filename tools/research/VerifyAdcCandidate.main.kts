// Independent snapshot-specific oracle: inverse-decode transport into logical ADC transactions.
// Does not import the generator or replay its shadow-update implementation.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size==1){"Usage: VerifyAdcCandidate.main.kts CANDIDATE_DIRECTORY"}
val dir=Path.of(args[0]);val manifest=Files.readString(dir.resolve("candidate.toml"))
fun hash(p:Path):String=Files.newInputStream(p).use{s->val m=MessageDigest.getInstance("SHA-256");val b=ByteArray(65536);while(true){val n=s.read(b);if(n<0)break;m.update(b,0,n)};HexFormat.of().formatHex(m.digest())}
fun field(block:String,key:String):String { val matches=Regex("(?m)^${Regex.escape(key)} = (.+)$").findAll(block).toList();require(matches.size==1){"field $key"};return matches.single().groupValues[1].removeSurrounding("\"") }
fun number(s:String)=if(s.startsWith("0x"))s.drop(2).toLong(16) else s.toLong()
fun blocks(name:String)=manifest.split("[[$name]]").drop(1).map{it.substringBefore("\n[")}
data class Pin(val path:Path,val hash:String)
val pins=blocks("inputs").map{Pin(Path.of(field(it,"path")),field(it,"sha256"))}
require(pins.map{it.path}.distinct().size==pins.size)
pins.forEach{require(hash(it.path)==it.hash){"stale input ${it.path.fileName}"}}
val review=pins.single{it.path.fileName.toString()=="review.toml"}
require(review.hash=="b34cf1a86a01dc54cbc14e28de60989352579423224e7ddfb8096d1990b0810b")
val reviewed=Files.readString(review.path).split("[[reviewed_artifacts]]").drop(1).map{Pin(Path.of(field(it,"path")),field(it,"sha256"))}
val stock=pins.single{it.path.fileName.toString()=="libscope-auklet.so"}
require(stock.hash=="4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e")
val raws=listOf("matrix","setting","drvparam","series","config","sample-entry","shadow-low","shadow-high","global-inputs").map{"adc-input-$it.bin"}+"native-loader-terminal-adc.bin"
for(name in raws){val p=pins.single{it.path.fileName.toString()==name};require(p.hash==reviewed.single{it.path.toString()==name}.hash)}
for(name in listOf("main-grammar","stary-grammar","stary-refinements","helper-grammar","helper-refinements","integer-refinements","getter-inputs","scope")){
    val p=pins.single{it.path.parent.fileName.toString()=="adc-parameter-static"&&it.path.fileName.toString()=="$name.toml"}
    require(p.hash==reviewed.single{it.path.toString()=="adc-parameter-static/$name.toml"}.hash)
}
val header=manifest.substringBefore("\n[selection]")
for((key,value) in listOf("classification" to "derived-software-prediction","guest_executed" to "false","hardware_read_values_supplied" to "false","writes" to "97","reads" to "2","requested_delay_us" to "25200","post_return_pc" to "0x333bac","post_return_opcode" to "0x5285070a")) require(field(header,key)==value)
val selection=manifest.substringAfter("[selection]").substringBefore("\n[[")
for((key,value) in listOf("selector0" to "8","selector1" to "900","row" to "2","table_bound" to "16","sample_rate_s64" to "0","sample_mode" to "1","raw_mask" to "0","normalized_mask" to "0","master_index" to "0","channel_delay_u32" to "[0, 0, 0, 0]","scale_index" to "3","bucket" to "0","branch" to "stary-bypass-only"))require(field(selection,key)==value)
// Each expected field location comes from the main grammar, independent of emitted field names/order.
data class Field(val offset:Int,val type:String,val value:Long)
val observedFields=blocks("calibration_fields").map{require(field(it,"source")=="native-loader-terminal-adc.bin");Field(number(field(it,"offset")).toInt(),field(it,"type"),number(field(it,"value")))}
val expectedOffsets=(0 until 16).map{2*it}+(0 until 16).map{0x20+2*it}+(0 until 8).map{0x40+2*it}+listOf(0x50,0x52,0x200,0x202,0x204,0x206)
val expectedFields=expectedOffsets.map{Field(it,"s16",0)}+(0 until 16).map{Field(0x4d0+4*it,"u32",0)}
require(observedFields.sortedBy{it.offset}==expectedFields.sortedBy{it.offset})
val maskWords=blocks("mask_words").map{number(field(it,"register")).toInt() to number(field(it,"value"))}
val maskRegisters=(listOf(1,4,5,9)+(0..7).flatMap{listOf(0x14+8*it,0x15+8*it)}).sorted()
require(maskWords==maskRegisters.map{it to when(it){4,5->0x8080L;9->0x2720L;else->0L}})
val runtimeFields=blocks("runtime_fields")
require(runtimeFields.size==54)
for(b in runtimeFields){val p=pins.single{it.path.fileName.toString()==field(b,"source")};val bytes=ByteBuffer.wrap(Files.readAllBytes(p.path)).order(ByteOrder.LITTLE_ENDIAN)
    val offset=number(field(b,"offset")).toInt();val value=when(field(b,"type")){
        "s64"->bytes.getLong(offset);"s32"->bytes.getInt(offset).toLong();"u32"->bytes.getInt(offset).toLong() and 0xffffffffL
        "u8-bit0"->bytes.get(offset).toLong() and 255;else->error("runtime field width")}
    require(number(field(b,"value"))==value)
}
data class Shadow(val name:String,val initial:List<Long>,val final:List<Long>)
fun numbers(text:String)=text.removeSurrounding("[","]").split(',').map{number(it.trim())}
val shadows=blocks("shadows").map{Shadow(field(it,"name"),numbers(field(it,"initial")),numbers(field(it,"final")))}
val expectedShadows=listOf(
    Shadow("reference09",listOf(0x5721,0x4721),listOf(0x5700,0x4700)),
    Shadow("gainAndDelay",List(8){2L},List(8){0L}),Shadow("offset",List(8){0L},List(8){0L}),
    Shadow("clock01",listOf(0,0),listOf(0,0)),Shadow("sample04",listOf(0x8000,0x8000),listOf(0,0)),
    Shadow("sample05",listOf(0,0),listOf(0,0)),Shadow("fineGain",listOf(0),listOf(0)),Shadow("syncControl",listOf(0),listOf(0)),
    Shadow("adjustGain",listOf(0),listOf(0)),Shadow("adjustGainLoad",listOf(0),listOf(0)),Shadow("adjustOffset1",listOf(0),listOf(0)),
    Shadow("adjustOffset1Load",listOf(0),listOf(0)),Shadow("adjustOffset2",listOf(0),listOf(0)),Shadow("adjustOffset2Load",listOf(0),listOf(0)),
    Shadow("adjustControl",listOf(0),listOf(1)))
require(shadows==expectedShadows){"snapshot shadow oracle"}
// Transitions must form complete chains between observed and predicted states.
data class Transition(val name:String,val index:Int,val before:Long,val after:Long)
val transitions=blocks("transitions").map{Transition(field(it,"shadow"),number(field(it,"index")).toInt(),number(field(it,"before")),number(field(it,"after")))}
require(transitions.size==49)
for(s in shadows)for(i in s.initial.indices){var state=s.initial[i];for(t in transitions.filter{it.name==s.name&&it.index==i}){require(t.before==state);state=t.after};require(state==s.final[i])}
enum class Kind{W32,R32,SLEEP}
data class Op(val index:Int,val phase:String,val kind:Kind,val offset:Long?,val operand:Long?)
val ops=blocks("operations").map{b->val kind=Kind.valueOf(field(b,"kind"));Op(number(field(b,"index")).toInt(),field(b,"phase"),kind,if(kind==Kind.SLEEP)null else number(field(b,"offset")),when(kind){Kind.W32->number(field(b,"value"));Kind.SLEEP->number(field(b,"microseconds"));Kind.R32->{require(field(b,"value_class")=="HARDWARE-RETURNED-UNOBSERVED"&&field(b,"mask")=="0x0");require(!Regex("(?m)^value =").containsMatchIn(b));null}})}
require(ops.size==150 && ops.map{it.index}==(0..149).toList())
val rows=Files.readAllLines(dir.resolve("sequence.tsv"));require(rows.first()=="index\tphase\tkind\toffset\toperand")
val fromTsv=rows.drop(1).map{r->val c=r.split('\t');require(c.size==5);Op(c[0].toInt(),c[1],Kind.valueOf(c[2]),if(c[3]=="-")null else number(c[3]),if(c[4]=="UNKNOWN")null else number(c[4]))}
require(fromTsv==ops){"manifest/TSV disagree"}
fun take(at:Int,count:Int,phase:String):List<Op> = ops.subList(at,at+count).also{require(it.all{it.phase==phase})}
fun expect(o:Op,k:Kind,offset:Long?,value:Long?) {require(o.kind==k&&o.offset==offset&&o.operand==value){"operation ${o.index}"}}
// Decode pairs back into chip/register/payload, rather than reproducing generator command assembly.
data class Adc(val chip:Int,val register:Int,val encoded:Int)
fun transaction(at:Int,expected:Adc,phase:String){val q=take(at,3,phase);val command=requireNotNull(q[0].operand)
    expect(q[0],Kind.W32,0x3000,command);expect(q[1],Kind.SLEEP,null,100);expect(q[2],Kind.W32,0x3000,command-0x04000000)
    require(command and 0x04000000L!=0L && command ushr 27==0L)
    val decoded=Adc(((command ushr 24) and 3).toInt()-1,((command ushr 16) and 0xff).toInt(),(command and 65535).toInt())
    require(decoded==expected){"logical ADC transaction at $at: $decoded != $expected"}
}
transaction(0,Adc(0,9,0x7020),"REFERENCE");transaction(3,Adc(1,9,0x6020),"REFERENCE")
expect(take(6,1,"FINE_GAIN").single(),Kind.W32,0x1058,0)
val gains=listOf(0 to 0x15,0 to 0x35,1 to 0x15,1 to 0x35,0 to 0x1d,0 to 0x3d,1 to 0x1d,1 to 0x3d,
    0 to 0x25,0 to 0x45,1 to 0x25,1 to 0x45,0 to 0x2d,0 to 0x4d,1 to 0x2d,1 to 0x4d)
gains.forEachIndexed{i,(chip,reg)->transaction(7+3*i,Adc(chip,reg,0),"CORE_GAIN")}
expect(take(55,2,"STARY")[0],Kind.W32,0x1574,1);expect(ops[56],Kind.SLEEP,null,20000)
val offsetRegs=listOf(0x14,0x1c,0x24,0x2c,0x34,0x3c,0x44,0x4c)
for(i in 0..15)transaction(57+3*i,Adc(i/8,offsetRegs[i%8],0),"CORE_OFFSET")
val delayRegisters=listOf(4,5,4,5);val encodedDelays=listOf(0x0080,0x8080,0x8080,0x8080)
for(i in 0..7)transaction(105+3*i,Adc(i/4,delayRegisters[i%4],encodedDelays[i%4]),"SAMPLE_DELAY")
for(chip in 0..1){val at=129+8*chip;transaction(at,Adc(chip,1,0),"CLOCK_DELAY")
    val q=take(at+3,5,"CLOCK_DELAY");val command=if(chip==0)0x05810000L else 0x06810000L
    expect(q[0],Kind.W32,0x3000,command);expect(q[1],Kind.SLEEP,null,100);expect(q[2],Kind.W32,0x3000,command-0x04000000)
    expect(q[3],Kind.SLEEP,null,100);expect(q[4],Kind.R32,0x3004,null)
}
take(145,5,"SYNC");expect(ops[145],Kind.W32,0x1000,0);expect(ops[146],Kind.SLEEP,null,200)
expect(ops[147],Kind.W32,0x1000,2);expect(ops[148],Kind.SLEEP,null,200);expect(ops[149],Kind.W32,0x1000,0)
require(ops.count{it.kind==Kind.W32}==97&&ops.count{it.kind==Kind.R32}==2&&ops.filter{it.kind==Kind.SLEEP}.sumOf{it.operand!!}==25200L)
println("schema_version = \"mho900-lab.adc-candidate-verification/1\"\naccepted = true\noperations = 150\nwrites = 97\nunknown_reads = 2\nrequested_delay_us = 25200\nshadow_transitions = 49\nguest_executed = false")
