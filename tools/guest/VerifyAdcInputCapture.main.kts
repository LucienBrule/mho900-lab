// Independent verifier for the bounded ADC software-input capture phase.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size in 1..2) { "Usage: VerifyAdcInputCapture.main.kts RUN_DIRECTORY [90..100]" }
val run = Path.of(args[0]).toAbsolutePath().normalize()
val arm = if (args.size == 2) args[1].toInt() else null
require(arm == null || arm in 90..100)
val eventName = if (arm == null) "native-events.toml" else "adcinput-$arm.toml"
fun artifact(name: String): String = if (arm == null) name else "adcinput-$arm-$name"
fun raw(name: String): ByteArray = Files.readAllBytes(run.resolve(name))
fun text(name: String): String = Files.readString(run.resolve(name))
fun digest(bytes: ByteArray): String = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))
val captureNativeSha256 = "c30ebe79fcc31512231c2c0a5d3a4b5795fba7179af70a22acb412db49bf0dbf"
require(captureNativeSha256.length == 64) { "capture native pin unresolved" }
data class Event(val kind: String, val fields: Map<String, String>) {
    fun string(key: String): String = fields.getValue(key)
    fun unsigned(key: String): ULong = string(key).removePrefix("0x").toULong(16)
}
fun events(name: String): List<Event> = text(name).split("[[events]]").drop(1).map { block ->
    val pairs = block.lineSequence().filter { it.isNotBlank() }.map { line ->
        val p = line.split(" = ", limit = 2)
        require(p.size == 2) { "malformed event line" }
        p[0] to p[1].removeSurrounding("\"")
    }.toList()
    require(pairs.map { it.first }.distinct().size == pairs.size) { "duplicate event field" }
    val fields = pairs.toMap()
    Event(fields.getValue("kind"), fields)
}
class Little(private val bytes: ByteArray) {
    fun u8(offset: Int): Int { require(offset in bytes.indices); return bytes[offset].toInt() and 0xff }
    fun u32(offset: Int): ULong { require(offset >= 0 && offset + 4 <= bytes.size); return ByteBuffer.wrap(bytes, offset, 4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong() }
    fun u64(offset: Int): ULong { require(offset >= 0 && offset + 8 <= bytes.size); return ByteBuffer.wrap(bytes, offset, 8).order(ByteOrder.LITTLE_ENDIAN).long.toULong() }
}
data class Mapping(val start: ULong, val end: ULong, val readable: Boolean)
fun parseMaps(name: String): List<Mapping> {
    val bytes = raw(name)
    require(bytes.size <= 262144) { "maps byte cap" }
    val lines = bytes.toString(Charsets.UTF_8).lineSequence().filter { it.isNotBlank() }.toList()
    require(lines.size in 1..2048) { "maps record cap" }
    return lines.map { line ->
        val columns = line.trim().split(Regex("\\s+"), limit = 6)
        require(columns.size >= 5) { "malformed maps record" }
        val bounds = columns[0].split('-', limit = 2)
        require(bounds.size == 2 && columns[1].length == 4)
        val start = bounds[0].toULong(16); val end = bounds[1].toULong(16)
        require(start < end)
        Mapping(start, end, columns[1][0] == 'r')
    }
}
fun add(a: ULong, b: ULong): ULong { val result = a + b; require(result >= a) { "address overflow" }; return result }
fun mul(a: ULong, b: ULong): ULong { if (a == 0uL || b == 0uL) return 0uL; val result = a * b; require(result / a == b) { "address overflow" }; return result }
fun contained(maps: List<Mapping>, address: ULong, length: ULong): Boolean {
    val end = add(address, length)
    return maps.any { it.readable && address >= it.start && end <= it.end }
}

data class Registers(val tid:ULong,val pc:ULong,val sp:ULong,val pstate:ULong,val x:List<ULong>)
fun registers(e:Event)=Registers(e.unsigned("tid"),e.unsigned("pc"),e.unsigned("sp"),e.unsigned("pstate"),(0..30).map{e.unsigned("x"+it.toString().padStart(2,'0'))})
fun completed(before:Registers,after:Registers,read:ULong?):Boolean = before.tid==after.tid&&after.pc==before.pc+4uL&&before.sp==after.sp&&before.pstate==after.pstate&&(0..30).all{after.x[it]==if(it==9&&read!=null)read else before.x[it]}
data class Segment(val offset:ULong,val address:ULong,val fileSize:ULong)
class Elf(private val bytes:ByteArray){
    fun u16(i:Int)=ByteBuffer.wrap(bytes,i,2).order(ByteOrder.LITTLE_ENDIAN).short.toUShort().toInt()
    fun u32(i:Int)=ByteBuffer.wrap(bytes,i,4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong()
    fun u64(i:Int)=ByteBuffer.wrap(bytes,i,8).order(ByteOrder.LITTLE_ENDIAN).long.toULong()
    private val sections=(0 until u16(60)).map{u64(40).toInt()+it*u16(58)}
    init{require(bytes.take(6)==listOf(127,69,76,70,2,1).map{it.toByte()}&&u16(18)==183)}
    fun symbol(name:String):ULong{val table=sections.single{u32(it+4)==2uL};val strings=sections[u32(table+40).toInt()];val entries=(u64(table+32)/u64(table+56)).toInt();val found=(0 until entries).map{i->val p=u64(table+24).toInt()+i*u64(table+56).toInt();val n=u64(strings+24).toInt()+u32(p).toInt();var z=n;while(bytes[z]!=0.toByte())z++;String(bytes,n,z-n) to u64(p+8)}.filter{it.first==name};return found.single().second}
}
fun debugDump(e:Event,address:ULong,control:ULong,request:Boolean){require(e.unsigned("result")==0uL&&e.unsigned("size")== (if(request)24uL else 264uL) &&e.unsigned("info")==0x606uL&&e.unsigned("a00")==address&&e.unsigned("c00")==control);for(i in 1..15){val n=i.toString().padStart(2,'0');require(e.unsigned("a$n")==0uL&&e.unsigned("c$n")==0uL)}}
fun verifyPrivateInherited(es:List<Event>,controlArm:Int) {
    val prefix="adcinput-$controlArm"
    require(text("$prefix-status.toml").trim()=="exit_code = 78")
    val binary=raw("$prefix.elf");require(digest(binary)==captureNativeSha256&&binary.contentEquals(raw("group-control.elf")));val elf=Elf(binary)
    val model=es.single{it.kind=="model-mode"};require(model.string("scope")=="private"&&model.unsigned("arm")==controlArm.toULong()&&model.unsigned("profile")==2uL&&model.unsigned("remaining")==1uL&&model.unsigned("tail")==1uL&&model.unsigned("loaders")==1uL&&model.unsigned("adc_inputs")==1uL)
    val pid=model.unsigned("pid");val mapping=es.single{it.kind=="mapping-result"}.unsigned("base")
    val reads=es.filter{it.kind=="modeled-read"};require(reads.map{it.unsigned("index") to it.unsigned("value")}==listOf(0uL to 0xe1234567uL,1uL to 0x89abcdefuL))
    val writes=es.filter{it.kind=="modeled-write"};require(writes.size==466&&writes.map{it.unsigned("index")}==(0..465).map{it.toULong()}&&writes.all{it.unsigned("tid")==pid&&it.unsigned("width")==4uL})
    val oracle=Files.readAllLines(run.resolve("reference.tsv")).drop(1).mapIndexed{i,line->val f=line.split('\t');require(f.size==7&&f[0].toInt()==i);f[6].removePrefix("0x").toULong(16)}
    val spu=ByteBuffer.wrap(raw("spu-private.bin")).order(ByteOrder.LITTLE_ENDIAN);fun su32(i:Int)=spu.getInt(i).toUInt().toULong()
    val offsets=List(452){0x3000uL}+(0..7).map{su32(1000+8*it)}+listOf(0x4004uL,0x4004uL,0x7034uL,0x7034uL)
    val values=oracle+(0..7).map{su32(1004+8*it)}+listOf(0x80000000uL,0uL,1uL,0uL)
    writes.take(464).forEachIndexed{i,e->require(e.unsigned("offset")==offsets[i]&&e.unsigned("value")==values[i])}
    val oldCp=es.filter{it.kind=="remaining-checkpoint"};val oldGuard=es.filter{it.kind=="remaining-checkpoint-guard"};require(oldCp.map{it.unsigned("index")}==(0..9).map{it.toULong()}&&oldGuard.size==10&&oldGuard.all{it.unsigned("match")==1uL})
    val tailCp=es.filter{it.kind=="tail-checkpoint"};val tailGuard=es.filter{it.kind=="tail-checkpoint-guard"};require(tailCp.map{it.unsigned("index")}==(0..2).map{it.toULong()}&&tailGuard.size==3&&tailGuard.all{it.unsigned("match")==1uL})
    val tailSummary=es.single{it.kind=="tail-summary"};require(tailSummary.unsigned("reads")==10uL&&tailSummary.unsigned("writes")==2uL&&tailSummary.unsigned("checkpoints")==3uL&&tailSummary.unsigned("total_writes")==466uL)
    val readOffsets=listOf(4uL,0uL,0x401cuL,0x14a0uL,0x14a4uL,0x1498uL,0x14acuL,0x14b4uL,0x1008uL,0x1210uL)
    val readValues=listOf(0xa1123456uL,0xbbaa0078uL,0x10203040uL,0xa5a50021uL,0xb6b61234uL,0xc7c72345uL,0xd8d83456uL,0xe9e94567uL,0x20000000uL,62500uL)
    val tailReads=es.filter{it.kind=="tail-read"};require(tailReads.size==10)
    tailReads.forEachIndexed{i,e->val p=es.indexOf(e);val fault=es.subList(0,p).last{it.kind=="mapped-fault"};val before=registers(es.subList(0,p).last{it.kind=="fault-registers"});val after=registers(es[p+1]);require(e.unsigned("index")==i.toULong()&&e.unsigned("offset")==readOffsets[i]&&e.unsigned("value")==readValues[i]&&e.unsigned("width")==4uL&&fault.unsigned("signal")==11uL&&fault.unsigned("si_code")==2uL&&fault.unsigned("address")==mapping+readOffsets[i]&&before.x[8]==fault.unsigned("address")&&completed(before,after,readValues[i]))}
    val tailWrites=es.filter{it.kind=="tail-write"};val wo=listOf(0x1428uL,0x1000uL);val wv=listOf(0x646euL,0uL);require(tailWrites.size==2)
    tailWrites.forEachIndexed{i,e->val p=es.indexOf(e);val fault=es.subList(0,p).last{it.kind=="mapped-fault"};val before=registers(es.subList(0,p).last{it.kind=="fault-registers"});require(e.unsigned("global_index")==464uL+i.toULong()&&e.unsigned("offset")==wo[i]&&e.unsigned("value")==wv[i]&&before.x[8]==fault.unsigned("address")&&before.x[9].toUInt().toULong()==wv[i]&&completed(before,registers(es[p+1]),null))}
    val tokens=es.filter{it.kind in setOf("tail-read","tail-write","tail-checkpoint")}.map{when(it.kind){"tail-read"->"R${it.unsigned("index")}";"tail-write"->"W${it.unsigned("index")}";else->"CP${it.unsigned("index")}"}}
    require(tokens==listOf("R0","R1","R2","W0","CP0","R3","R4","R5","R6","R7","W1","R8","R9","CP1","CP2"))
    val lm=es.single{it.kind=="loader-mode"};require(lm.string("scope")=="private"&&lm.unsigned("profile")==2uL&&lm.unsigned("checkpoint_count")==4uL&&lm.unsigned("capture_count")==5uL&&lm.unsigned("binding_count")==6uL)
    val mb=es.single{it.kind=="model-binding"};val shared=mb.unsigned("object")-48uL;require(shared and 4095uL==0uL)
    val loaderSymbols=listOf("gm_tail_private","gm_loader_private","gm_private_leader","gm_cl_cp0","gm_cl_cp1","gm_cl_cp2").map{elf.symbol(it)}
    val loaderBindings=es.filter{it.kind=="loader-binding"};require(loaderBindings.size==6);loaderBindings.forEachIndexed{i,e->require(e.unsigned("index")==i.toULong()&&e.unsigned("slot")==shared+3224uL+8uL*i.toULong()&&e.unsigned("actual_target")==loaderSymbols[i]&&e.unsigned("expected_target")==loaderSymbols[i]&&e.unsigned("match")==1uL)}
    val layouts=es.filter{it.kind=="loader-layout"};require(layouts.size==7);val objects=listOf(shared,shared+3200uL,shared+3216uL,shared+3208uL);layouts.take(4).forEachIndexed{i,e->require(e.string("category")=="object"&&e.unsigned("index")==i.toULong()&&e.unsigned("address")==objects[i]&&e.unsigned("expected_address")==objects[i])};val lsb=layouts[4].unsigned("address");val destinations=listOf(lsb,lsb+0x1000uL,lsb+0x3000uL);val lengths=listOf(192uL,1936uL,0x1b60c0uL);layouts.drop(4).forEachIndexed{i,e->require(e.string("category")=="destination"&&e.unsigned("index")==i.toULong()&&e.unsigned("address")==destinations[i]&&e.unsigned("expected_address")==destinations[i]&&e.unsigned("length")==lengths[i]&&e.unsigned("expected_length")==lengths[i]&&e.unsigned("match")==1uL)}
    val loaderCp=es.filter{it.kind=="loader-checkpoint"}
    if(controlArm!=100){require(loaderCp.size==4&&loaderCp.map{it.unsigned("index")}==(0..3).map{it.toULong()});val statuses=listOf(192uL,0x1b60c0uL,1936uL);val status=es.filter{it.kind=="loader-status"};require(status.size==3);status.forEachIndexed{i,e->require(e.unsigned("index")==i.toULong()&&e.unsigned("actual")==statuses[i]&&e.unsigned("expected")==statuses[i]&&e.unsigned("match")==1uL)}}
    val loaderCaptures=es.filter{it.kind=="loader-capture"};val expectedLoaderFiles=listOf("entry-lsb" to Pair(192,Pair(0,0xa5)),"entry-adc" to Pair(1936,Pair(0,0x5a)),"terminal-lsb" to Pair(192,Pair(3,1)),"terminal-adc" to Pair(1936,Pair(0,0x5a)),"terminal-vertical" to Pair(0x1b60c0,Pair(5,7)))
    if(controlArm!=100){require(loaderCaptures.size==5);expectedLoaderFiles.forEachIndexed{i,d->val name="adcinput-$controlArm-loader-${d.first}.bin";val actual=raw(name);require(actual.size==d.second.first&&actual.indices.all{j->actual[j]==(j*d.second.second.first+d.second.second.second).toByte()});val e=loaderCaptures[i];require(e.unsigned("index")==i.toULong()&&e.unsigned("completed")==d.second.first.toULong()&&e.unsigned("match")==1uL)}}
    if(controlArm!=100){
        val before=es.filter{it.kind=="loader-debug-before"};val clearReq=es.filter{it.kind=="loader-debug-clear-request"};val clearSet=es.filter{it.kind=="loader-debug-clear-set"};val clearAfter=es.filter{it.kind=="loader-debug-clear-after"};val armReq=es.filter{it.kind=="loader-debug-arm-request"};val armSet=es.filter{it.kind=="loader-debug-arm-set"};val armAfter=es.filter{it.kind=="loader-debug-arm-after"};val ready=es.filter{it.kind=="loader-debug-ready"};require(before.size==5&&clearReq.size==4&&clearSet.size==4&&clearAfter.size==4&&armReq.size==4&&armSet.size==4&&armAfter.size==4&&ready.size==4);val pcs=listOf("gm_cl_cp0","gm_cl_cp1","gm_cl_cp2","gm_cl_cp3").map{elf.symbol(it)};debugDump(before[0],0uL,0x1e5uL,false);for(i in 0..3){debugDump(armReq[i],pcs[i],0x1e5uL,true);require(armSet[i].unsigned("result")==0uL);debugDump(armAfter[i],pcs[i],0x1e4uL,false);require(ready[i].unsigned("checkpoint")==i.toULong()&&ready[i].unsigned("tid")==pid&&ready[i].unsigned("target")==pcs[i]);debugDump(before[i+1],pcs[i],0x1e4uL,false);debugDump(clearReq[i],0uL,0uL,true);require(clearSet[i].unsigned("result")==0uL);debugDump(clearAfter[i],0uL,0x1e5uL,false)}
        val converge=es.single{it.kind=="loader-terminal-converge"};require(es.indexOf(converge)<es.indexOf(loaderCaptures[2])&&es.subList(es.indexOf(loaderCp.last()),es.size).none{it.kind=="runtime-resume"})
    } else {
        require(loaderCp.size==3&&es.filter{it.kind=="loader-capture"}.size==2);val reject=es.single{it.kind=="loader-rejected"};require(reject.string("reason")=="clone"&&reject.string("stage")=="runtime"&&reject.unsigned("checkpoint")==3uL)
    }
    val observer=es.single{it.kind=="ready"}.unsigned("observer_pid")
    fun inventory(phase:String):Set<ULong>{val rows=es.filter{it.kind=="thread-status"&&it.string("phase")==phase};val inv=es.single{it.kind=="thread-inventory"&&it.string("phase")==phase};val ids=rows.map{it.unsigned("tid")};require(ids.distinct().size==ids.size&&rows.all{it.unsigned("tgid")==pid&&it.unsigned("tracer_pid")==observer&&it.unsigned("state")==0x74uL}&&inv.unsigned("observed_count")==ids.size.toULong()&&inv.unsigned("overflow")==0uL&&inv.unsigned("error")==0uL);return ids.toSet()}
    val beforeTids=inventory("before-ready");val terminalTids=inventory("terminal");val clones=es.filter{it.kind=="runtime-clone"}.map{it.unsigned("new_tid")}.toSet();val tracked=es.filter{it.kind=="group-track"}.map{it.unsigned("tid")};require(tracked.distinct().size==tracked.size&&tracked.toSet()==beforeTids+clones&&terminalTids==tracked.toSet());val reaped=es.filter{it.kind=="group-reaped"};require(reaped.size==tracked.size&&reaped.map{it.unsigned("tid")}.toSet()==tracked.toSet()&&reaped.all{it.unsigned("status")==9uL});val cleanup=es.single{it.kind=="group-cleanup"};require(cleanup.unsigned("expected_count")==tracked.size.toULong()&&cleanup.unsigned("reaped_count")==tracked.size.toULong()&&cleanup.unsigned("wait_result").toLong()==-10L&&es.last()==cleanup)
}

val captureNames = listOf("matrix", "setting", "drvparam", "series", "config", "sample-entry", "shadow-low", "shadow-high", "global-inputs")
val captureFiles = captureNames.map { "adc-input-$it.bin" }
val captureLengths = listOf(0xe60, 0x1c71, 0x10, 0x12c, 0x3c, 8, 0x3c, 0x74, 0x2c)
require(captureLengths.sum() <= 16384)
val allEvents = events(eventName)
if (arm != null) verifyPrivateInherited(allEvents, arm)
val expectedCaptureEvents = when (arm) { null,90,91,98,99 -> 9; 97 -> 1; else -> 0 }
for (index in 0 until expectedCaptureEvents) { val expectedSize=if(arm==97&&index==0)captureLengths[0]/2 else captureLengths[index];require(raw(artifact(captureFiles[index])).size==expectedSize){"${captureFiles[index]} length"} }
if(arm!=100)require(raw(if (arm == null) "native-loader-terminal-adc.bin" else "adcinput-$arm-loader-terminal-adc.bin").size == 1936) { "terminal ADC record length" }
val rejectEvents=allEvents.filter{it.kind=="adc-input-rejected"}
if(arm==100){val lr=allEvents.single{it.kind=="loader-rejected"};require(lr.string("reason")=="clone"&&lr.string("stage")=="runtime"&&lr.unsigned("checkpoint")==3uL&&allEvents.none{it.kind.startsWith("adc-input-")});println("schema_version = \"mho900-lab.adc-input-capture-verification/1\"\nresult = \"accepted\"\narm = 100\ncontrol_outcome = \"expected-late-clone-rejection\"");kotlin.system.exitProcess(0)}
val adcMode=allEvents.single{it.kind=="adc-input-mode"};require(adcMode.string("scope")== (if(arm==null)"stock" else "private")&&adcMode.unsigned("arm")== (arm?:0).toULong()&&adcMode.unsigned("profile")== (if(arm==null)1uL else 2uL)&&adcMode.unsigned("file_count")==9uL&&adcMode.unsigned("binding_count")==16uL&&adcMode.unsigned("map_limit")==2048uL&&adcMode.unsigned("map_byte_limit")==262144uL&&adcMode.unsigned("raw_max")==16384uL&&adcMode.unsigned("no_resume")==1uL)
val mapEvent=allEvents.single{it.kind=="adc-input-maps"};val mapBytes=raw(artifact("adc-input-maps.txt"));val mapRecords=mapBytes.toString(Charsets.UTF_8).lineSequence().count{it.isNotBlank()};require(mapEvent.unsigned("bytes")==mapBytes.size.toULong()&&mapEvent.unsigned("records")==mapRecords.toULong()&&mapEvent.unsigned("maximum_bytes")==262144uL&&mapEvent.unsigned("maximum_records")==2048uL&&mapEvent.unsigned("overflow")==0uL&&mapEvent.unsigned("read_error")==0uL)
val adcBindings=allEvents.filter{it.kind=="adc-input-binding"};val expectedBindingCount=if(arm==92)4 else 16;require(adcBindings.size==expectedBindingCount&&adcBindings.map{it.unsigned("index")}==(0 until expectedBindingCount).map{it.toULong()})
val privateTargetOffsets=listOf(0xc000uL,0xa040uL,0xa02auL,0xa000uL,0xa03cuL,0xa070uL,0xa05cuL,0x9038uL,0x9000uL,0xb010uL,0xb01cuL,0xb014uL,0xb020uL,0xb018uL,0xb024uL,0xb028uL)
val stockSlots=listOf(0xb8eea8uL,0xb8cb08uL,0xb8c9d0uL,0xb8b940uL,0xb8cae0uL,0xb8ec98uL,0xb8e680uL,0xb8da70uL,0xb8d288uL,0xb8de88uL,0xb8ed38uL,0xb8dd30uL,0xb8db70uL,0xb8d5b8uL,0xb8ddc0uL,0xb8ccd8uL);val stockTargets=listOf(0x9948bcuL,0x3cb45bcuL,0x3cb45a6uL,0x3cb457cuL,0x3cb45b8uL,0x3cb45ecuL,0x3cb45d8uL,0x3cb4534uL,0x3cb44fcuL,0xbe1138uL,0xbe1144uL,0xbe113cuL,0xbe1148uL,0xbe1140uL,0xbe114cuL,0xbe1150uL);val widths=listOf(312uL,4uL,16uL,16uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL)
val earlyBase=allEvents.single{it.kind=="model-binding"}.unsigned("base");val earlyArena=if(arm==null)0uL else adcBindings[0].unsigned("expected_target")-0xc000uL
adcBindings.forEachIndexed{i,e->val expected=if(arm==null)add(earlyBase,stockTargets[i])else add(earlyArena,privateTargetOffsets[i]);val actual=expected+if(arm==92&&i==3)1uL else 0uL;require(e.unsigned("expected_target")==expected&&e.unsigned("actual_target")==actual&&e.unsigned("target_width")==widths[i]&&e.unsigned("relocation_type")==0x401uL&&e.unsigned("match")==if(actual==expected)1uL else 0uL);if(arm==null)require(e.unsigned("slot")==add(earlyBase,stockSlots[i]))}
val maps = parseMaps(artifact("adc-input-maps.txt"))
val mapChecks=allEvents.filter{it.kind=="adc-input-map"}
mapChecks.forEach { e ->
    val address=e.unsigned("address");val length=e.unsigned("length")
    val enclosing=maps.firstOrNull{address>=it.start&&add(address,length)<=it.end}
    require(e.unsigned("map_start")== (enclosing?.start?:0uL)&&e.unsigned("map_end")== (enclosing?.end?:0uL))
    require(e.unsigned("readable")== (if(enclosing?.readable==true)1uL else 0uL))
    require(e.unsigned("match")== (if(contained(maps,address,length))1uL else 0uL))
}
val loaderCheckpoints=allEvents.filter{it.kind=="loader-checkpoint"};require(loaderCheckpoints.size==4)
val terminalCheckpoint=loaderCheckpoints.single{it.unsigned("index")==3uL}
val terminalRegisters=allEvents[allEvents.indexOf(terminalCheckpoint)+1];require(terminalRegisters.kind=="loader-checkpoint-registers")
if(arm==null)require(terminalCheckpoint.unsigned("relative_pc")==0x333ba8uL&&terminalCheckpoint.unsigned("opcode")==0x97fb9b9euL)
else require(terminalCheckpoint.unsigned("relative_pc")==0uL&&terminalCheckpoint.unsigned("opcode")==0xd503201fuL)
val existingCaptures=allEvents.filter{it.kind=="loader-capture"};require(existingCaptures.size==5)
val loaderSummary=allEvents.single{it.kind=="loader-summary"}
require(allEvents.indexOf(existingCaptures.last())<allEvents.indexOf(adcMode)&&allEvents.indexOf(adcMode)<allEvents.indexOf(loaderSummary))
require(allEvents.drop(allEvents.indexOf(terminalCheckpoint)).none{it.kind=="runtime-resume"})
val adcSummary=allEvents.single{it.kind=="adc-input-summary"}
require(adcSummary.unsigned("modeled_reads")==0uL&&adcSummary.unsigned("modeled_writes")==0uL&&adcSummary.unsigned("resumes")==0uL&&adcSummary.unsigned("bindings")==16uL)
require(allEvents.indexOf(adcSummary)<allEvents.indexOf(loaderSummary))
val captureEvents=allEvents.filter{it.kind=="adc-input-capture"}
require(captureEvents.size==expectedCaptureEvents)
val base=earlyBase;val arena=earlyArena
if(arm!=null)require(arena and 4095uL==0uL)
val fixedAddresses=if(arm==null)listOf(add(base,0x10c4f30uL+0x4e94uL),add(base,0x10bee58uL),add(base,0x10c4840uL),add(base,0xb8f4e4uL),0uL,0uL,add(base,0x3cb44fcuL),add(base,0x3cb457cuL),add(base,0xbe1128uL))
else listOf(if(arm==96)1uL else add(arena,0x800uL),add(arena,0x3000uL),add(arena,0x5000uL),add(arena,0x6000uL),0uL,0uL,add(arena,0x9000uL),add(arena,0xa000uL),add(arena,0xb000uL))
if(arm==null)require(terminalRegisters.unsigned("x00")==add(base,0x10c4f30uL))
mapChecks.forEach{e->val i=e.unsigned("index").toInt();when(e.string("category")){
    "binding-slot"->require(arm==null&&e.unsigned("address")==add(base,stockSlots[i])&&e.unsigned("length")==8uL)
    "binding-target"->require(e.unsigned("address")==adcBindings[i].unsigned("actual_target")&&e.unsigned("length")==widths[i])
    "fixed"->require(i in listOf(0,1,2,3,6,7,8)&&e.unsigned("address")==fixedAddresses[i]&&e.unsigned("length")==captureLengths[i].toULong())
    "config","sample-entry"->Unit
    else->error("unexpected map category")
}}
fun fnv1a64(b:ByteArray):ULong { var h=14695981039346656037uL;for(v in b){h=h xor (v.toInt() and 255).toULong();h*=1099511628211uL};return h }
fun accepted(outcome:String) { println("schema_version = \"mho900-lab.adc-input-capture-verification/1\"\nresult = \"accepted\"\ncontrol_outcome = \"$outcome\"") }
if(arm in 92..97){
    val expected=when(arm){92->Triple("binding","binding",3);93->Triple("pointer","table",2);94->Triple("pointer","config",2);95->Triple("bound","sample-count",2);96->Triple("map","fixed",0);97->Triple("short-read","raw",0);else->error("arm")}
    val r=rejectEvents.single();require(r.string("reason")==expected.first&&r.string("stage")==expected.second&&r.unsigned("index")==expected.third.toULong()&&r.unsigned("captures")==0uL)
    val values=when(arm){92->add(arena,0xa001uL) to add(arena,0xa000uL);93->add(arena,0x8001uL) to add(arena,0x8000uL);94->add(arena,0x7001uL) to add(arena,0x7000uL);95->17uL to 16uL;96->1uL to 0xe60uL;else->0x730uL to 0xe60uL}
    require(r.unsigned("actual")==values.first&&r.unsigned("expected")==values.second)
    require(adcSummary.unsigned("captures")==0uL&&adcSummary.unsigned("requested_bytes")== (if(arm==97)0xe60uL else 0uL)&&adcSummary.unsigned("completed_bytes")== (if(arm==97)0x730uL else 0uL))
    if(arm==97){val e=captureEvents.single();val bytes=raw(artifact(captureFiles[0]));require(bytes.contentEquals(ByteArray(0x730){(it*7+3).toByte()}));require(e.string("name")==captureFiles[0]&&e.unsigned("index")==0uL&&e.unsigned("address")==fixedAddresses[0]&&e.unsigned("length")==0xe60uL&&e.unsigned("completed")==0x730uL&&e.unsigned("hash_fnv1a64")==fnv1a64(bytes)&&e.unsigned("match")==0uL)}
    require(allEvents.indexOf(r)<allEvents.indexOf(adcSummary))
    accepted("expected-${expected.first}-rejection");kotlin.system.exitProcess(0)
}
require(rejectEvents.isEmpty())
val setting=Little(raw(artifact(captureFiles[1])));val series=Little(raw(artifact(captureFiles[3])));val globals=Little(raw(artifact(captureFiles[8])))
var mask=0
for(c in 0..3)if((0..7).any{setting.u8(c*0xc0+0xb4+it) and 1!=0})mask=mask or (1 shl c)
if(setting.u8(0x1c70) and 1!=0)mask=15
val selector0=series.u32(0);val selector1=series.u32(4);val special=globals.u32(12)
val effective=if(selector1==4000uL&&special==1uL)2000uL else selector1
val matchedRow=(0..8).firstOrNull{series.u32(12+32*it)==selector0&&series.u32(16+32*it)==effective}
val selectedRow=matchedRow?:0;val rowOffset=12+32*selectedRow;val fallback=if(matchedRow==null)1uL else 0uL
val tablePointer=series.u64(rowOffset+8);val configPointer=series.u64(rowOffset+24);val bound=series.u32(rowOffset+16)
require(bound in 1uL..16uL);val normalizedMask=if(mask.toULong()>bound-1uL)0uL else mask.toULong()
val tableOffsets=listOf(0xb8f808uL,0xb8f808uL,0xb8f808uL,0xb8f908uL,0xb8fa08uL,0xb8fb08uL,0xb8fc08uL,0xb8fc08uL,0xb8fc08uL)
val configOffsets=listOf(0xb8f40cuL,0xb8f40cuL,0xb8f478uL,0xb8f2c8uL,0xb8f3a0uL,0xb8f40cuL,0uL,0uL,0uL)
require(tablePointer==if(arm==null)add(base,tableOffsets[selectedRow])else add(arena,0x8000uL))
require(configPointer!=0uL&&configPointer==if(arm==null){require(configOffsets[selectedRow]!=0uL);add(base,configOffsets[selectedRow])}else add(arena,0x7000uL))
val record=add(fixedAddresses[3],rowOffset.toULong())
val selectorEvent=allEvents.single{it.kind=="adc-input-selector"}
mapOf("selector0" to selector0,"selector1" to selector1,"effective_selector1" to effective,"special_flag" to special,"selected_index" to selectedRow.toULong(),"fallback" to fallback,"record" to record).forEach{(k,v)->require(selectorEvent.unsigned(k)==v){"selector $k"}}
val pointers=allEvents.filter{it.kind=="adc-input-pointer"};require(pointers.size==2)
pointers.forEachIndexed{i,e->val pointer=if(i==0)tablePointer else configPointer;require(e.string("category")==if(i==0)"table" else "config");require(e.unsigned("index")==selectedRow.toULong()&&e.unsigned("site")==add(record,if(i==0)8uL else 24uL)&&e.unsigned("actual")==pointer&&e.unsigned("expected")==pointer&&e.unsigned("relocation_type")==0x101uL&&e.unsigned("match")==1uL)}
val samplePointer=add(tablePointer,mul(16uL,normalizedMask))
val expectedAddresses=fixedAddresses.toMutableList();expectedAddresses[4]=configPointer;expectedAddresses[5]=samplePointer
expectedAddresses.forEachIndexed{i,address->require(contained(maps,address,captureLengths[i].toULong()))}
val expectedMapKeys=buildList{for(i in 0..15){if(arm==null)add("binding-slot" to i);add("binding-target" to i)};for(i in listOf(0,1,2,3,6,7,8))add("fixed" to i);add("config" to 4);add("sample-entry" to 5)}
require(mapChecks.map{it.string("category") to it.unsigned("index").toInt()}==expectedMapKeys)
mapChecks.takeLast(2).forEachIndexed{i,e->require(e.unsigned("address")==expectedAddresses[4+i]&&e.unsigned("length")==captureLengths[4+i].toULong())}
val state=allEvents.single{it.kind=="adc-input-state"};val config=Little(raw(artifact(captureFiles[4])));val sample=Little(raw(artifact(captureFiles[5])));val drv=Little(raw(artifact(captureFiles[2])))
mapOf("sample_count" to bound,"raw_mask" to mask.toULong(),"normalized_mask" to normalizedMask,"mode" to sample.u32(4),"config_adcs_delay" to config.u32(0x20),"config_point_time" to config.u32(0x38),"sample_rate" to drv.u64(8),"mapped_base_value" to globals.u64(0)).forEach{(k,v)->require(state.unsigned(k)==v){"state $k"}}
if(arm==null)require(globals.u64(0)==allEvents.single{it.kind=="mapping-result"}.unsigned("base"))
if(arm!=null){
    val patterns=listOf(7 to 3,9 to 5,11 to 7,13 to 9,15 to 11,17 to 13,19 to 15,21 to 17,23 to 19)
    captureFiles.forEachIndexed{i,name->
        val expected=ByteArray(captureLengths[i]){j->((j+if(i==5)16 else 0)*patterns[i].first+patterns[i].second).toByte()}
        fun p32(o:Int,v:Int){for(j in 0..3)expected[o+j]=(v ushr (8*j)).toByte()}
        fun p64(o:Int,v:ULong){for(j in 0..7)expected[o+j]=(v shr (8*j)).toByte()}
        when(i){
            0->if(arm==98)expected[7]=(expected[7].toInt() xor 1).toByte()
            1->{for(c in 0..3)for(j in 0..7)expected[c*0xc0+0xb4+j]=0;expected[0xb4]=1;expected[0x1c70]=0}
            2->p64(8,2000000000uL)
            3->{p32(0,if(arm==91)0xdead else 8);p32(4,if(arm==91)0xbeef else 900);for(row in 0..8){val o=12+32*row;p32(o,if(row==2)8 else 100+row);p32(o+4,if(row==2)900 else 200+row);p64(o+8,add(arena,0x8000uL));p32(o+16,16);p64(o+24,add(arena,0x7000uL))}}
            4->{p32(0x20,if(arm==99)32 else 31);p32(0x38,7)}
            5->p32(4,if(arm==99)5 else 4)
            8->p32(12,0)
        }
        require(raw(artifact(name)).contentEquals(expected)){"private raw pattern $i"}
    }
}
captureEvents.forEachIndexed{i,e->val bytes=raw(artifact(captureFiles[i]));require(e.unsigned("index")==i.toULong()&&e.string("name")==captureFiles[i]&&e.unsigned("address")==expectedAddresses[i]&&e.unsigned("length")==captureLengths[i].toULong()&&e.unsigned("completed")==bytes.size.toULong()&&e.unsigned("chunks")==1uL&&e.unsigned("result")==bytes.size.toULong()&&e.unsigned("match")==1uL);require(e.unsigned("hash_fnv1a64")==fnv1a64(bytes)){"capture hash $i"}}
mapOf("captures" to 9uL,"requested_bytes" to 11565uL,"completed_bytes" to 11565uL,"maps_observed" to maps.size.toULong(),"selected_index" to selectedRow.toULong(),"fallback" to fallback).forEach{(k,v)->require(adcSummary.unsigned(k)==v){"summary $k"}}
require(allEvents.indexOf(state)<allEvents.indexOf(captureEvents.first())&&allEvents.indexOf(captureEvents.last())<allEvents.indexOf(adcSummary))
accepted(if(arm==98)"exact-canonical-one-bit-divergence-observed" else "complete-snapshot")
println("selected_row = $selectedRow\nsample_mask = $mask\nnormalized_mask = $normalizedMask\nsample_bound = $bound")
