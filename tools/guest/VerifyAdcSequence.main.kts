// Independent verifier for the private whole-ADC-sequence controls.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 2) { "Usage: VerifyAdcSequence.main.kts RUN_DIRECTORY ARM" }
val run = Path.of(args[0]).toAbsolutePath().normalize()
val arm = args[1].toInt()
require(arm in 101..112) { "ARM must be in 101..112" }
val prefix = "adcseq-$arm"
fun raw(name: String): ByteArray = Files.readAllBytes(run.resolve(name))
fun text(name: String): String = Files.readString(run.resolve(name))
fun sha256(bytes: ByteArray): String = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))
fun fnv1a64(bytes: ByteArray): ULong { var hash = 14695981039346656037uL; for (byte in bytes) { hash = hash xor (byte.toInt() and 255).toULong(); hash *= 1099511628211uL }; return hash }

data class Event(val kind: String, val fields: Map<String, String>) {
    fun string(key: String): String = fields.getValue(key)
    fun unsigned(key: String): ULong = string(key).removePrefix("0x").toULong(16)
}
fun events(name: String): List<Event> = text(name).split("[[events]]").drop(1).map { block ->
    val pairs = block.lineSequence().filter { it.isNotBlank() }.map { line ->
        val parts = line.split(" = ", limit = 2)
        require(parts.size == 2) { "malformed event line" }
        parts[0] to parts[1].removeSurrounding("\"")
    }.toList()
    require(pairs.map { it.first }.distinct().size == pairs.size) { "duplicate event field" }
    val fields = pairs.toMap()
    Event(fields.getValue("kind"), fields)
}
data class Registers(val tid: ULong, val pc: ULong, val sp: ULong, val pstate: ULong, val x: List<ULong>)
fun registers(event: Event): Registers = Registers(event.unsigned("tid"), event.unsigned("pc"), event.unsigned("sp"), event.unsigned("pstate"), (0..30).map { event.unsigned("x" + it.toString().padStart(2, '0')) })
fun completed(before: Registers, after: Registers, read: ULong?): Boolean =
    before.tid == after.tid && after.pc == before.pc + 4uL && before.sp == after.sp && before.pstate == after.pstate &&
        (0..30).all { after.x[it] == if (it == 9 && read != null) read else before.x[it] }

data class Operation(val index: Int, val sequenceIndex: ULong, val read: Boolean, val offset: ULong, val value: ULong)
data class Guard(val index: Int, val source: String, val offset: ULong, val width: Int, val expected: ULong)
data class Profile(val operations: List<Operation>, val guards: List<Guard>, val finals: List<Guard>)
fun parseNumber(value: String): ULong = if (value.startsWith("0x")) value.removePrefix("0x").toULong(16) else value.toULong()
fun parseProfile(path: Path, headerPath: Path): Profile {
    require(sha256(Files.readAllBytes(path)) == "1fd5ffcf09094da41bd7aa08ed60974b6a6f4c3be9ba7f0f92eebdab087d8abb")
    require(sha256(Files.readAllBytes(headerPath)) == "e3a80852517fc033a065a599e729c028269d383250ec77e8c40c6a0ae1bce841")
    val source = Files.readString(path)
    fun blocks(marker: String, until: String?): List<Map<String, String>> {
        val region = source.substringAfter(marker).let { if (until == null) it else it.substringBefore(until) }
        return region.split(marker).filter { it.isNotBlank() }.map { block ->
            block.lineSequence().takeWhile { !it.startsWith("[[") }.filter { it.contains(" = ") }.associate { line ->
                val parts = line.split(" = ", limit = 2); parts[0] to parts[1].removeSurrounding("\"")
            }
        }
    }
    fun guard(rows: List<Map<String, String>>) = rows.map { row -> Guard(parseNumber(row.getValue("index")).toInt(), row.getValue("source"), parseNumber(row.getValue("offset")), parseNumber(row.getValue("width")).toInt(), parseNumber(row.getValue("expected_bits"))) }
    val operations = blocks("[[operations]]", null).map { row ->
        val read = row.getValue("kind") == "R32"
        Operation(parseNumber(row.getValue("index")).toInt(), parseNumber(row.getValue("sequence_index")), read, parseNumber(row.getValue("offset")), parseNumber(row.getValue(if (read) "synthetic_value" else "value")))
    }
    val header = Files.readString(headerPath).substringAfter("ap_final_shadows[AP_FINAL_SHADOWS]").substringAfter('{').substringBefore("};")
    val finalRows = Regex("\\{(\\d+)U,0x([0-9a-f]+)U(?:L)?,(\\d+)U,0x([0-9a-f]+)U(?:L)?}").findAll(header).mapIndexed { index, match ->
        val groups = match.groupValues
        Guard(index, groups[1], groups[2].toULong(16), groups[3].toInt(), groups[4].toULong(16))
    }.toList()
    return Profile(operations, guard(blocks("[[guards]]", "[[operations]]")), finalRows)
}

fun debugDump(event: Event, address: ULong, control: ULong, request: Boolean) {
    require(event.unsigned("result") == 0uL && event.unsigned("size") == if (request) 24uL else 264uL)
    require(event.unsigned("info") == 0x606uL && event.unsigned("a00") == address && event.unsigned("c00") == control)
    for (i in 1..15) { val n = i.toString().padStart(2, '0'); require(event.unsigned("a$n") == 0uL && event.unsigned("c$n") == 0uL) }
}
class Elf(private val bytes:ByteArray){
    fun u16(i:Int)=ByteBuffer.wrap(bytes,i,2).order(ByteOrder.LITTLE_ENDIAN).short.toUShort().toInt()
    fun u32(i:Int)=ByteBuffer.wrap(bytes,i,4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong()
    fun u64(i:Int)=ByteBuffer.wrap(bytes,i,8).order(ByteOrder.LITTLE_ENDIAN).long.toULong()
    private val sections=(0 until u16(60)).map{u64(40).toInt()+it*u16(58)}
    init{require(bytes.take(6)==listOf(127,69,76,70,2,1).map{it.toByte()}&&u16(18)==183)}
    fun symbol(name:String):ULong{val table=sections.single{u32(it+4)==2uL};val strings=sections[u32(table+40).toInt()];val entries=(u64(table+32)/u64(table+56)).toInt();val found=(0 until entries).map{i->val p=u64(table+24).toInt()+i*u64(table+56).toInt();val n=u64(strings+24).toInt()+u32(p).toInt();var z=n;while(bytes[z]!=0.toByte())z++;String(bytes,n,z-n) to u64(p+8)}.filter{it.first==name};return found.single().second}
}

fun verifyPrivateInherited(es:List<Event>,controlArm:Int) {
    val prefix="adcseq-$controlArm"
    require(text("$prefix-status.toml").trim()=="exit_code = 78")
    val binary=raw("$prefix.elf");require(sha256(binary)=="960b91e1b3cd7de8f49d47833c6e13ec43afcc597bb0d205c379f471a2bcda37"&&binary.contentEquals(raw("group-control.elf")));val elf=Elf(binary)
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
    val tailSummary=es.single{it.kind=="tail-summary"};require(tailSummary.unsigned("reads")==10uL&&tailSummary.unsigned("writes")==2uL&&tailSummary.unsigned("checkpoints")==3uL&&tailSummary.unsigned("total_writes")==466uL+es.single{it.kind=="adc-sequence-summary"}.unsigned("writes"))
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
    val loaderCaptures=es.filter{it.kind=="loader-capture"};val expectedLoaderFiles=listOf("entry-lsb" to Pair(192,Pair(0,0xa5)),"entry-adc" to Pair(1936,Pair(0,0)),"terminal-lsb" to Pair(192,Pair(3,1)),"terminal-adc" to Pair(1936,Pair(0,0)),"terminal-vertical" to Pair(0x1b60c0,Pair(5,7)))
    if(controlArm!=100){require(loaderCaptures.size==5);expectedLoaderFiles.forEachIndexed{i,d->val name="adcseq-$controlArm-loader-${d.first}.bin";val actual=raw(name);require(actual.size==d.second.first&&actual.indices.all{j->actual[j]==(j*d.second.second.first+d.second.second.second).toByte()});val e=loaderCaptures[i];require(e.unsigned("index")==i.toULong()&&e.unsigned("completed")==d.second.first.toULong()&&e.unsigned("match")==1uL)}}
    if(controlArm!=100){
        val before=es.filter{it.kind=="loader-debug-before"};val clearReq=es.filter{it.kind=="loader-debug-clear-request"};val clearSet=es.filter{it.kind=="loader-debug-clear-set"};val clearAfter=es.filter{it.kind=="loader-debug-clear-after"};val armReq=es.filter{it.kind=="loader-debug-arm-request"};val armSet=es.filter{it.kind=="loader-debug-arm-set"};val armAfter=es.filter{it.kind=="loader-debug-arm-after"};val ready=es.filter{it.kind=="loader-debug-ready"};require(before.size==5&&clearReq.size==4&&clearSet.size==4&&clearAfter.size==4&&armReq.size==4&&armSet.size==4&&armAfter.size==4&&ready.size==4);val pcs=listOf("gm_cl_cp0","gm_cl_cp1","gm_cl_cp2","gm_cl_cp3").map{elf.symbol(it)};debugDump(before[0],0uL,0x1e5uL,false);for(i in 0..3){debugDump(armReq[i],pcs[i],0x1e5uL,true);require(armSet[i].unsigned("result")==0uL);debugDump(armAfter[i],pcs[i],0x1e4uL,false);require(ready[i].unsigned("checkpoint")==i.toULong()&&ready[i].unsigned("tid")==pid&&ready[i].unsigned("target")==pcs[i]);debugDump(before[i+1],pcs[i],0x1e4uL,false);debugDump(clearReq[i],0uL,0uL,true);require(clearSet[i].unsigned("result")==0uL);debugDump(clearAfter[i],0uL,0x1e5uL,false)}
        val converge=es.first{it.kind=="loader-terminal-converge"};require(es.indexOf(converge)<es.indexOf(loaderCaptures[2])&&es.subList(es.indexOf(loaderCp.last()),es.indexOf(es.single{it.kind=="adc-sequence-mode"})).none{it.kind=="runtime-resume"})
    } else {
        require(loaderCp.size==3&&es.filter{it.kind=="loader-capture"}.size==2);val reject=es.single{it.kind=="loader-rejected"};require(reject.string("reason")=="clone"&&reject.string("stage")=="runtime"&&reject.unsigned("checkpoint")==3uL)
    }
    val observer=es.single{it.kind=="ready"}.unsigned("observer_pid")
    fun inventory(phase:String):Set<ULong>{val rows=es.filter{it.kind=="thread-status"&&it.string("phase")==phase};val inv=es.single{it.kind=="thread-inventory"&&it.string("phase")==phase};val ids=rows.map{it.unsigned("tid")};require(ids.distinct().size==ids.size&&rows.all{it.unsigned("tgid")==pid&&it.unsigned("tracer_pid")==observer&&it.unsigned("state")==0x74uL}&&inv.unsigned("observed_count")==ids.size.toULong()&&inv.unsigned("overflow")==0uL&&inv.unsigned("error")==0uL);return ids.toSet()}
    val beforeTids=inventory("before-ready");val terminalTids=inventory("terminal");val clones=es.filter{it.kind=="runtime-clone"}.map{it.unsigned("new_tid")}.toSet();val tracked=es.filter{it.kind=="group-track"}.map{it.unsigned("tid")};require(tracked.distinct().size==tracked.size&&tracked.toSet()==beforeTids+clones&&terminalTids==tracked.toSet());val reaped=es.filter{it.kind=="group-reaped"};require(reaped.size==tracked.size&&reaped.map{it.unsigned("tid")}.toSet()==tracked.toSet()&&reaped.all{it.unsigned("status")==9uL});val cleanup=es.single{it.kind=="group-cleanup"};require(cleanup.unsigned("expected_count")==tracked.size.toULong()&&cleanup.unsigned("reaped_count")==tracked.size.toULong()&&cleanup.unsigned("wait_result").toLong()==-10L&&es.last()==cleanup)
}

fun verifyCleanup(es: List<Event>) {
    val tracked = es.filter { it.kind == "group-track" }.map { it.unsigned("tid") }
    require(tracked.isNotEmpty() && tracked.distinct().size == tracked.size)
    val terminalRows = es.filter { it.kind == "thread-status" && it.string("phase") == "terminal" }
    val live = terminalRows.map { it.unsigned("tid") }.toSet()
    require(live == tracked.toSet())
    val inventory = es.single { it.kind == "thread-inventory" && it.string("phase") == "terminal" }
    require(inventory.unsigned("observed_count") == live.size.toULong() && inventory.unsigned("overflow") == 0uL && inventory.unsigned("error") == 0uL)
    val reaped = es.filter { it.kind == "group-reaped" }
    require(reaped.map { it.unsigned("tid") }.toSet() == live && reaped.size == live.size && reaped.all { it.unsigned("status") == 9uL })
    val cleanup = es.single { it.kind == "group-cleanup" }
    require(cleanup.unsigned("expected_count") == live.size.toULong() && cleanup.unsigned("reaped_count") == live.size.toULong() && cleanup.unsigned("wait_result").toLong() == -10L && es.last() == cleanup)
}

fun verifyInheritedPrefix(es: List<Event>, binary: ByteArray, profile: Profile): Pair<ULong, ULong> {
    require(sha256(binary) == "960b91e1b3cd7de8f49d47833c6e13ec43afcc597bb0d205c379f471a2bcda37")
    require(binary.contentEquals(raw("group-control.elf")))
    require(text("$prefix-status.toml").trim() == "exit_code = 78")
    val mode = es.single { it.kind == "model-mode" }
    require(mode.string("scope") == "private" && mode.unsigned("arm") == arm.toULong() && mode.unsigned("profile") == 2uL)
    for (key in listOf("continuation", "transcript", "spu", "remaining", "tail", "loaders", "adc_inputs")) require(mode.unsigned(key) == 1uL)
    val pid = mode.unsigned("pid")
    val mapping = es.single { it.kind == "mapping-result" }.unsigned("base")
    require(mapping != 0uL)
    val writes = es.filter { it.kind == "modeled-write" }
    require(writes.size >= 466 && writes.take(466).map { it.unsigned("index") } == (0..465).map { it.toULong() } && writes.take(466).all { it.unsigned("tid") == pid && it.unsigned("width") == 4uL })
    val initialReads = es.filter { it.kind == "modeled-read" }
    require(initialReads.map { it.unsigned("index") to it.unsigned("value") } == listOf(0uL to 0xe1234567uL, 1uL to 0x89abcdefuL))
    val oracle = Files.readAllLines(run.resolve("reference.tsv")).drop(1).mapIndexed { index, line ->
        val fields = line.split('\t'); require(fields.size == 7 && fields[0].toInt() == index); fields[6].removePrefix("0x").toULong(16)
    }
    require(oracle.size == 452)
    val spu = ByteBuffer.wrap(raw("spu-private.bin")).order(ByteOrder.LITTLE_ENDIAN)
    fun spu32(offset: Int): ULong = spu.getInt(offset).toUInt().toULong()
    val expectedOffsets = List(452) { 0x3000uL } + (0..7).map { spu32(1000 + 8 * it) } + listOf(0x4004uL, 0x4004uL, 0x7034uL, 0x7034uL, 0x1428uL, 0x1000uL)
    val expectedValues = oracle + (0..7).map { spu32(1004 + 8 * it) } + listOf(0x80000000uL, 0uL, 1uL, 0uL, 0x646euL, 0uL)
    writes.take(466).forEachIndexed { index, event -> require(event.unsigned("offset") == expectedOffsets[index] && event.unsigned("value") == expectedValues[index]) }
    val remainingCheckpoints = es.filter { it.kind == "remaining-checkpoint" }
    require(remainingCheckpoints.map { it.unsigned("index") } == (0..9).map { it.toULong() })
    require(es.filter { it.kind == "remaining-checkpoint-guard" }.let { it.size == 10 && it.all { event -> event.unsigned("match") == 1uL } })
    val tailCheckpoints = es.filter { it.kind == "tail-checkpoint" }
    require(tailCheckpoints.map { it.unsigned("index") } == (0..2).map { it.toULong() })
    require(es.filter { it.kind == "tail-checkpoint-guard" }.let { it.size == 3 && it.all { event -> event.unsigned("match") == 1uL } })
    val tail = es.single { it.kind == "tail-summary" }
    require(tail.unsigned("reads") == 10uL && tail.unsigned("writes") == 2uL && tail.unsigned("checkpoints") == 3uL && tail.unsigned("total_writes") == 466uL + es.single { it.kind == "adc-sequence-summary" }.unsigned("writes"))
    val loader = es.single { it.kind == "loader-summary" }
    require(loader.unsigned("checkpoints") == 4uL && loader.unsigned("captures") == 5uL && loader.unsigned("modeled_reads") == 0uL && loader.unsigned("modeled_writes") == 0uL && loader.unsigned("atomic") == 4uL && loader.unsigned("old_executed") == 0uL)
    val elf = Elf(binary)
    es.filter { it.kind == "loader-checkpoint" }.forEachIndexed { i, e ->
        require(e.unsigned("tid") == pid && e.unsigned("pc") == elf.symbol("gm_cl_cp$i") && e.unsigned("opcode") == 0xd503201fuL)
        require(e.unsigned("signal") == 5uL && e.unsigned("si_code") == 4uL && e.unsigned("address") == e.unsigned("pc") && e.unsigned("expected_pc") == e.unsigned("pc"))
        val r = registers(es[es.indexOf(e) + 1])
        require(r.tid == pid && r.pc == e.unsigned("pc"))
        require(r == registers(es.filter { it.kind == "loader-debug-registers" }[i + 1]))
    }
    val captures = es.filter { it.kind == "loader-capture" }
    val loaderFiles = listOf("entry-lsb" to 192, "entry-adc" to 1936, "terminal-lsb" to 192, "terminal-adc" to 1936, "terminal-vertical" to 0x1b60c0)
    require(captures.size == loaderFiles.size)
    loaderFiles.forEachIndexed { index, (name, length) ->
        val bytes = raw("$prefix-loader-$name.bin")
        require(bytes.size == length && captures[index].unsigned("index") == index.toULong() && captures[index].unsigned("completed") == length.toULong() && captures[index].unsigned("match") == 1uL)
    }
    val bindings = es.filter { it.kind == "adc-input-binding" }
    require(bindings.size == 16 && bindings.map { it.unsigned("index") } == (0..15).map { it.toULong() } && bindings.all { it.unsigned("match") == 1uL && it.unsigned("relocation_type") == 0x401uL })
    val mapChecks = es.filter { it.kind == "adc-input-map" }
    require(mapChecks.size == 25 && mapChecks.all { it.unsigned("readable") == 1uL && it.unsigned("match") == 1uL })
    val inputCaptures = es.filter { it.kind == "adc-input-capture" }
    val names = listOf("matrix", "setting", "drvparam", "series", "config", "sample-entry", "shadow-low", "shadow-high", "global-inputs")
    val lengths = listOf(0xe60, 0x1c71, 0x10, 0x12c, 0x3c, 8, 0x3c, 0x74, 0x2c)
    require(inputCaptures.size == 9)
    names.forEachIndexed { index, name ->
        val bytes = raw("$prefix-adc-input-$name.bin")
        val event = inputCaptures[index]
        require(bytes.size == lengths[index] && event.unsigned("index") == index.toULong() && event.string("name") == "adc-input-$name.bin" && event.unsigned("length") == lengths[index].toULong() && event.unsigned("completed") == lengths[index].toULong() && event.unsigned("chunks") == 1uL && event.unsigned("result") == lengths[index].toULong() && event.unsigned("hash_fnv1a64") == fnv1a64(bytes) && event.unsigned("match") == 1uL)
    }
    val matrix = raw("$prefix-adc-input-matrix.bin")
    require(matrix.contentEquals(ByteArray(matrix.size) { (it * 7 + 3).toByte() }))
    val adcRecord = raw("$prefix-loader-terminal-adc.bin")
    val expectedAdcRecord = ByteArray(adcRecord.size)
    profile.guards.filter { it.source == "ADC_RECORD" }.forEach { guard ->
        require(guard.offset + guard.width.toULong() <= expectedAdcRecord.size.toULong())
        for (i in 0 until guard.width) expectedAdcRecord[guard.offset.toInt() + i] = (guard.expected shr (8 * i)).toByte()
    }
    require(adcRecord.contentEquals(expectedAdcRecord)) { "ADC guard capture differs from zero-based fixture" }
    require(raw("$prefix-loader-entry-adc.bin").contentEquals(expectedAdcRecord))
    require(raw("$prefix-loader-entry-lsb.bin").all { it == 0xa5.toByte() })
    require(raw("$prefix-loader-terminal-lsb.bin").let { bytes -> bytes.indices.all { bytes[it] == (it * 3 + 1).toByte() } })
    require(raw("$prefix-loader-terminal-vertical.bin").let { bytes -> bytes.indices.all { bytes[it] == (it * 5 + 7).toByte() } })
    val loaderTerminalAdc = captures[3]
    val sourceBase = mapOf(
        "ADC_RECORD" to loaderTerminalAdc.unsigned("address"), "SETTING" to inputCaptures[1].unsigned("address"),
        "DRV" to inputCaptures[2].unsigned("address"), "SERIES" to inputCaptures[3].unsigned("address"),
        "CONFIG" to inputCaptures[4].unsigned("address"), "SAMPLE" to inputCaptures[5].unsigned("address"),
        "LOW" to inputCaptures[6].unsigned("address"), "HIGH" to inputCaptures[7].unsigned("address"),
        "GLOBAL" to inputCaptures[8].unsigned("address"), "MASK" to bindings[0].unsigned("expected_target")
    )
    val guards = es.filter { it.kind == "adc-sequence-entry-guard" }
    val expectedGuardCount = if (arm == 107) profile.guards.indexOfFirst { it.source == "CONFIG" && it.offset == 0x38uL } + 1 else 175
    require(expectedGuardCount > 0 && guards.size == expectedGuardCount && profile.guards.size == 175)
    guards.forEachIndexed { index, event ->
        val expected = profile.guards[index]
        val altered = arm == 107 && index == expectedGuardCount - 1
        require(expected.index == index && event.unsigned("index") == index.toULong() && event.unsigned("source") == listOf("ADC_RECORD","SETTING","DRV","CONFIG","SAMPLE","LOW","HIGH","GLOBAL","SERIES","MASK").indexOf(expected.source).toULong() && event.unsigned("offset") == expected.offset && event.unsigned("address") == sourceBase.getValue(expected.source) + expected.offset && event.unsigned("width") == expected.width.toULong() && event.unsigned("expected") == expected.expected && event.unsigned("read_ok") == 1uL)
        require(if (altered) event.unsigned("actual") == 250001uL && event.unsigned("match") == 0uL else event.unsigned("actual") == expected.expected && event.unsigned("match") == 1uL)
    }
    if (arm == 107) return pid to mapping
    val binding = es.single { it.kind == "adc-sequence-entry-binding" }
    require(binding.unsigned("selected_row") == 2uL && binding.unsigned("expected_row") == 2uL && binding.unsigned("mapped_base") == mapping && binding.unsigned("expected_mapping") == mapping)
    val converge = es.first { it.kind == "loader-terminal-converge" }
    require(es.subList(es.indexOf(converge), es.indexOf(es.single { it.kind == "adc-sequence-mode" })).none { it.kind == "runtime-resume" })
    return pid to mapping
}

fun verifyCaptureEvidence(es: List<Event>, profile: Profile) {
    fun check(e:Event, fields:Map<String,ULong>) { fields.forEach{(k,v)->require(e.unsigned(k)==v){"${e.kind}.$k"}} }
    val caps=es.filter{it.kind=="adc-input-capture"};require(caps.size==9)
    val names=listOf("matrix","setting","drvparam","series","config","sample-entry","shadow-low","shadow-high","global-inputs")
    val data=names.map{raw("$prefix-adc-input-$it.bin")}
    fun value(b:ByteArray,offset:Int,width:Int):ULong {require(offset>=0&&offset+width<=b.size);var v=0uL;repeat(width){v=v or ((b[offset+it].toInt()and 255).toULong()shl(8*it))};return v}
    val arena=caps[0].unsigned("address")-0x800uL;require(arena and 4095uL==0uL)
    val addresses=listOf(0x800uL,0x3000uL,0x5000uL,0x6000uL,0x7000uL,0x8000uL,0x9000uL,0xa000uL,0xb000uL).map{arena+it}
    caps.forEachIndexed{i,e->require(e.unsigned("address")==addresses[i])}
    val bindings=es.filter{it.kind=="adc-input-binding"}
    val offsets=listOf(0xc000uL,0xa040uL,0xa02auL,0xa000uL,0xa03cuL,0xa070uL,0xa05cuL,0x9038uL,0x9000uL,0xb010uL,0xb01cuL,0xb014uL,0xb020uL,0xb018uL,0xb024uL,0xb028uL)
    val widths=listOf(312uL,4uL,16uL,16uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL)
    val shared=es.single{it.kind=="model-binding"}.unsigned("object")-48uL
    require(bindings.size==16)
    bindings.forEachIndexed{i,e->check(e,mapOf("index" to i.toULong(),"slot" to shared+3384uL+i.toULong()*8uL,"actual_target" to arena+offsets[i],"expected_target" to arena+offsets[i],"target_width" to widths[i],"relocation_type" to 0x401uL,"match" to 1uL))}
    val mapsBytes=raw("$prefix-adc-input-maps.txt");require(mapsBytes.size<=262144)
    val maps=mapsBytes.toString(Charsets.UTF_8).lineSequence().filter{it.isNotBlank()}.map{line->
        val c=line.trim().split(Regex("\\s+"),limit=6);require(c.size>=5&&c[1].length==4)
        val r=c[0].split('-');require(r.size==2);Triple(r[0].toULong(16),r[1].toULong(16),c[1][0]=='r')
    }.toList();require(maps.size in 1..2048&&maps.all{it.first<it.second})
    check(es.single{it.kind=="adc-input-maps"},mapOf("bytes" to mapsBytes.size.toULong(),"records" to maps.size.toULong(),"maximum_bytes" to 262144uL,"maximum_records" to 2048uL,"overflow" to 0uL,"read_error" to 0uL))
    fun enclosing(address:ULong,length:ULong):Triple<ULong,ULong,Boolean>{require(length>0uL&&address+length>address);return maps.first{address>=it.first&&address+length<=it.second}.also{require(it.third)}}
    enclosing(es.filter{it.kind=="loader-capture"}[3].unsigned("address"),1936uL)
    val mapKeys=(0..15).map{"binding-target" to it}+listOf(0,1,2,3,6,7,8).map{"fixed" to it}+listOf("config" to 4,"sample-entry" to 5)
    val mapEvents=es.filter{it.kind=="adc-input-map"};require(mapEvents.map{it.string("category") to it.unsigned("index").toInt()}==mapKeys)
    mapEvents.forEachIndexed{i,e->val key=mapKeys[i];val address=if(key.first=="binding-target")arena+offsets[key.second]else addresses[key.second];val length=if(key.first=="binding-target")widths[key.second]else data[key.second].size.toULong();val m=enclosing(address,length)
        check(e,mapOf("address" to address,"length" to length,"map_start" to m.first,"map_end" to m.second,"readable" to 1uL,"match" to 1uL))}
    val series=data[3];val selected=(0..8).first{value(series,12+32*it,4)==8uL&&value(series,16+32*it,4)==900uL};require(selected==2)
    require(value(series,0,4)==8uL&&value(series,4,4)==900uL&&value(series,0x5c,4)==16uL)
    val record=addresses[3]+0x4cuL
    check(es.single{it.kind=="adc-input-selector"},mapOf("selector0" to 8uL,"selector1" to 900uL,"effective_selector1" to 900uL,"special_flag" to 0uL,"selected_index" to 2uL,"fallback" to 0uL,"record" to record))
    val pointers=es.filter{it.kind=="adc-input-pointer"};require(pointers.size==2)
    pointers.forEachIndexed{i,e->val off=if(i==0)8 else 24;val target=if(i==0)addresses[5]else addresses[4];require(value(series,0x4c+off,8)==target&&e.string("category")==if(i==0)"table" else "config")
        check(e,mapOf("index" to 2uL,"site" to record+off.toULong(),"actual" to target,"expected" to target,"relocation_type" to 0x101uL,"match" to 1uL))}
    var mask=0uL;for(c in 0..3)if((0..7).any{value(data[1],c*0xc0+0xb4+it,1)and 1uL!=0uL})mask=mask or(1uL shl c)
    if(value(data[1],0x1c70,1)and 1uL!=0uL)mask=15uL;require(mask==0uL)
    val mapping=es.single{it.kind=="mapping-result"}.unsigned("base");require(value(data[8],0,8)==mapping&&value(data[8],12,4)==0uL)
    check(es.single{it.kind=="adc-input-state"},mapOf("sample_count" to 16uL,"raw_mask" to 0uL,"normalized_mask" to 0uL,"mode" to value(data[5],4,4),"config_adcs_delay" to value(data[4],0x20,4),"config_point_time" to value(data[4],0x38,4),"sample_rate" to value(data[2],8,8),"mapped_base_value" to mapping))
    val sourceData=mapOf("ADC_RECORD" to raw("$prefix-loader-terminal-adc.bin"),"SETTING" to data[1],"DRV" to data[2],"CONFIG" to data[4],"SAMPLE" to data[5],"LOW" to data[6],"HIGH" to data[7],"GLOBAL" to data[8],"SERIES" to data[3])
    profile.guards.filter{it.source!="MASK"}.forEach{g->val expected=if(arm==107&&g.source=="CONFIG"&&g.offset==0x38uL)250001uL else g.expected;require(value(sourceData.getValue(g.source),g.offset.toInt(),g.width)==expected){"raw entry ${g.source}+${g.offset}"}}
    check(es.single{it.kind=="adc-input-summary"},mapOf("captures" to 9uL,"requested_bytes" to 11565uL,"completed_bytes" to 11565uL,"bindings" to 16uL,"maps_observed" to maps.size.toULong(),"selected_index" to 2uL,"fallback" to 0uL,"modeled_reads" to 0uL,"modeled_writes" to 0uL,"resumes" to 0uL))
    val mode=es.single{it.kind=="adc-input-mode"};require(mode.string("scope")=="private")
    check(mode,mapOf("arm" to arm.toULong(),"profile" to 2uL,"file_count" to 9uL,"binding_count" to 16uL,"map_limit" to 2048uL,"map_byte_limit" to 262144uL,"raw_max" to 16384uL,"no_resume" to 1uL))
    require(es.none{it.kind in setOf("adc-input-rejected","error","group-failure","unexpected-runtime-signal","terminal-cleanup-deadline","loader-rejected")})
}

fun verifySequencePhase(es: List<Event>, binary: ByteArray, profile: Profile, pid: ULong, mapping: ULong): String {
    val elf = Elf(binary)
    val mode = es.single { it.kind == "adc-sequence-mode" }
    val begin = es.indexOf(mode)
    val full = arm in setOf(101,106,111,112)
    val badAccess = arm in setOf(102,103,104,105,108)
    val transfers = if (full) 99 else 0
    val returnPc = elf.symbol("gm_ap_cp")
    val wrongPc = elf.symbol("gm_ap_wrong_cp")
    require(wrongPc + 4uL == returnPc)
    require(mode.string("scope") == "private")
    fun fields(e: Event, expected: Map<String, ULong>) { expected.forEach { (k,v) -> require(e.unsigned(k) == v) { "${e.kind}.$k" } } }
    fields(mode, mapOf("arm" to arm.toULong(), "operations" to 99uL, "guards" to 175uL, "final_shadows" to 33uL,
        "synthetic0" to 0x11234uL, "synthetic1" to 0uL, "return_pc" to returnPc, "stock_return_relative" to 0x333bacuL, "sleep_observation" to 0uL))
    val scope = es.drop(begin)
    val expectedKinds = mutableListOf("adc-sequence-mode")
    repeat(if(arm==107) profile.guards.indexOfFirst { it.source=="CONFIG" && it.offset==0x38uL }+1 else 175) { expectedKinds.add("adc-sequence-entry-guard") }
    val rejectSpec = when(arm) {
        101 -> null
        102,103,104 -> "value" to "access"
        105 -> "offset" to "access"
        106 -> "pc" to "return"
        107 -> "value" to "entry"
        108 -> "thread" to "access"
        109 -> "clone" to "runtime"
        110 -> "deadline" to "runtime"
        111 -> "private-state" to "return"
        112 -> "value" to "final-shadow"
        else -> error("arm")
    }
    val tracked = es.take(begin).filter { it.kind=="group-track" }.map { it.unsigned("tid") }
    require(tracked.size>=2 && tracked.toSet().size==tracked.size && pid in tracked)
    val returnRows = scope.filter { it.kind=="adc-sequence-return" }
    if(arm!=107) {
        expectedKinds += listOf("adc-sequence-entry-binding", "adc-sequence-debug-before", "adc-sequence-debug-request", "adc-sequence-debug-set", "adc-sequence-debug-after", "adc-sequence-entry-registers", "adc-sequence-resume-group")
        val armed = if(arm==106)wrongPc else returnPc
        debugDump(scope.first { it.kind=="adc-sequence-debug-before" },0uL,0x1e5uL,false)
        debugDump(scope.first { it.kind=="adc-sequence-debug-request" },armed,0x1e5uL,true)
        fields(scope.first { it.kind=="adc-sequence-debug-set" },mapOf("result" to 0uL))
        debugDump(scope.first { it.kind=="adc-sequence-debug-after" },armed,0x1e4uL,false)
        val entry = registers(scope.single { it.kind=="adc-sequence-entry-registers" })
        require(entry==registers(es.last { it.kind=="loader-debug-registers" }))
        fields(scope.single { it.kind=="adc-sequence-resume-group" },mapOf("threads" to tracked.size.toULong(),"leader" to pid))
        val resumes=scope.filter { it.kind=="runtime-resume" }
        require(resumes.size==tracked.size+transfers && resumes.all { it.unsigned("operation")==7uL }) { "ordinary group continuation count" }
        require(resumes.take(tracked.size).map { it.unsigned("tid") }==tracked)
        require(resumes.drop(tracked.size).all { it.unsigned("tid")==pid })
    } else require(scope.none { it.kind=="runtime-resume" })
    val accesses=scope.filter { it.kind=="adc-sequence-access" }
    require(accesses.size==transfers+(if(badAccess)1 else 0))
    for(i in 0 until transfers) {
        val op=profile.operations[i];require(op.index==i)
        val a=accesses[i];val pos=es.indexOf(a)
        val before=registers(es[pos+1]);val transfer=es[pos+2];val after=registers(es[pos+3])
        val pc=elf.symbol(if(op.read)"gm_first_pc" else "gm_write_pc")
        fields(a,mapOf("index" to i.toULong(),"tid" to pid,"signal" to 11uL,"si_code" to 2uL,"address" to mapping+op.offset,"offset" to op.offset,"pc" to pc,"opcode" to if(op.read)0xb9400109uL else 0xb9000109uL))
        require(before.tid==pid && before.pc==pc && before.x[8]==mapping+op.offset && before.x[9].toUInt().toULong()==a.unsigned("operand"))
        if(!op.read)require(a.unsigned("operand")==op.value)
        fields(transfer,mapOf("index" to i.toULong(),"sequence_index" to op.sequenceIndex,"tid" to pid,"offset" to op.offset,"value" to op.value,"width" to 4uL,"synthetic_response" to if(op.read)1uL else 0uL))
        require(completed(before,after,if(op.read)op.value else null))
        require(es[pos+4].kind=="runtime-resume" && es[pos+4].unsigned("tid")==pid)
        expectedKinds += listOf("adc-sequence-access","adc-sequence-before-registers",if(op.read)"adc-sequence-read" else "adc-sequence-write","adc-sequence-after-registers")
    }
    if(badAccess) {
        expectedKinds.add("adc-sequence-access")
        val a=accesses.single();val op=profile.operations[if(arm==103||arm==104)1 else 0]
        val offset=when(arm){105->0x3010uL;108->0x3004uL;else->op.offset}
        val tid=if(arm==108)es.single{it.kind=="model-mode"}.unsigned("fixture_worker") else pid
        val pc=elf.symbol(when(arm){105->"gm_first_pc";108->"gm_worker_pc";else->"gm_write_pc"})
        fields(a,mapOf("index" to 0uL,"tid" to tid,"signal" to 11uL,"si_code" to 2uL,"address" to mapping+offset,"offset" to offset,"pc" to pc,"opcode" to when(arm){105->0xb9400109uL;108->0xf9400109uL;else->0xb9000109uL}))
        if(arm!=105&&arm!=108)require(a.unsigned("operand")==op.value+if(arm==102)1uL else 0uL)
        if(arm==108)require(tid!=pid && tid in tracked)
    }
    if(full) {
        expectedKinds += listOf("adc-sequence-return","adc-sequence-return-registers")
        val r=returnRows.single();val pc=if(arm==106)wrongPc else returnPc
        fields(r,mapOf("tid" to pid,"pc" to pc,"expected_pc" to returnPc,"si_code" to 4uL,"address" to pc,"opcode" to 0xd503201fuL,"status" to 0uL,"operations" to 99uL))
        val rr=registers(es[es.indexOf(r)+1]);require(rr.tid==pid && rr.pc==pc && rr.x[0].toUInt()==0u)
        require(es.drop(es.indexOf(r)+1).none { it.kind=="runtime-resume" })
    } else require(returnRows.isEmpty())
    val finals=scope.filter { it.kind=="adc-sequence-final-shadow" }
    val finalCount=when(arm){101,111->33;112->1;else->0}
    require(finals.size==finalCount && profile.finals.size==33)
    val cap=es.filter { it.kind=="adc-input-capture" }
    val bases=listOf(es.filter{it.kind=="loader-capture"}[3].unsigned("address"),cap[1].unsigned("address"),cap[2].unsigned("address"),cap[4].unsigned("address"),cap[5].unsigned("address"),cap[6].unsigned("address"),cap[7].unsigned("address"),cap[8].unsigned("address"),cap[3].unsigned("address"),es.first{it.kind=="adc-input-binding"}.unsigned("expected_target"))
    finals.forEachIndexed { i,e ->
        val g=profile.finals[i];val source=g.source.toInt();val bad=arm==112
        fields(e,mapOf("index" to i.toULong(),"source" to source.toULong(),"offset" to g.offset,"address" to bases[source]+g.offset,"width" to g.width.toULong(),"actual" to g.expected+if(bad)1uL else 0uL,"expected" to g.expected,"read_ok" to 1uL,"match" to if(bad)0uL else 1uL))
        expectedKinds.add("adc-sequence-final-shadow")
    }
    if(arm==101) {
        expectedKinds += listOf("adc-sequence-debug-before","adc-sequence-debug-request","adc-sequence-debug-set","adc-sequence-debug-after","adc-sequence-final-registers","adc-sequence-complete")
        debugDump(scope.last{it.kind=="adc-sequence-debug-before"},returnPc,0x1e4uL,false)
        debugDump(scope.last{it.kind=="adc-sequence-debug-request"},0uL,0uL,true)
        fields(scope.last{it.kind=="adc-sequence-debug-set"},mapOf("result" to 0uL))
        debugDump(scope.last{it.kind=="adc-sequence-debug-after"},0uL,0x1e5uL,false)
        require(registers(scope.single{it.kind=="adc-sequence-return-registers"})==registers(scope.single{it.kind=="adc-sequence-final-registers"}))
        fields(scope.single{it.kind=="adc-sequence-complete"},mapOf("return_instruction_executed" to 0uL))
    } else {
        expectedKinds.add("adc-sequence-rejected")
        val r=scope.single{it.kind=="adc-sequence-rejected"};require(r.string("reason")==rejectSpec!!.first && r.string("stage")==rejectSpec.second)
        val expectedTid=when(arm){108->es.single{it.kind=="model-mode"}.unsigned("fixture_worker");110->0uL;else->pid}
        fields(r,mapOf("tid" to expectedTid,"index" to transfers.toULong()))
        val actualExpected=when(arm){
            102->profile.operations[0].value+1uL to profile.operations[0].value
            103,104->profile.operations[1].value to profile.operations[0].value
            105->0x3010uL to 0x3000uL
            106->wrongPc to returnPc
            107->250001uL to 250000uL
            108->expectedTid to pid
            109->scope.single{it.kind=="runtime-clone"}.unsigned("new_tid") to 0uL
            110->0uL to 99uL
            111->0uL to 1uL
            112->profile.finals[0].expected+1uL to profile.finals[0].expected
            else->error("arm")
        }
        fields(r,mapOf("actual" to actualExpected.first,"expected" to actualExpected.second))
        require(es.drop(es.indexOf(r)+1).none{it.kind=="runtime-resume"})
    }
    expectedKinds.add("adc-sequence-summary")
    require(scope.filter{it.kind.startsWith("adc-sequence-")}.map{it.kind}==expectedKinds) { "ADC event order/cardinality" }
    val summary=scope.single{it.kind=="adc-sequence-summary"}
    fields(summary,mapOf("operations" to transfers.toULong(),"writes" to if(full)97uL else 0uL,"reads" to if(full)2uL else 0uL,
        "private_metrics" to 1uL,"worker_ack" to if(arm==107)0uL else 1uL,"atomic" to if(full&&arm!=111)1uL else 0uL,
        "raw0" to if(full)0x11234uL else 0uL,"raw1" to 0uL,"protocol0" to if(full)0x1234uL else 0uL,"protocol1" to 0uL,"private_reads" to if(full)2uL else 0uL,"old_executed" to 0uL))
    val clones=scope.filter{it.kind=="runtime-clone"};require(clones.size==if(arm==109)1 else 0)
    if(arm==109)require(clones.single().unsigned("parent_tid")==pid && clones.single().unsigned("new_tid") !in tracked)
    val convergence=es.filter{it.kind=="loader-terminal-converge"}
    require(convergence.size==if(arm in setOf(101,111,112))2 else 1)
    return if(arm==101)"complete-sequence" else "expected-${rejectSpec!!.first}-rejection"
}

val binary = raw("$prefix.elf")
val profile = parseProfile(run.resolve("adc-sequence/profile.toml"), run.resolve("source/adc-sequence-profile.h"))
require(profile.operations.size == 99 && profile.operations.count { it.read } == 2 && profile.operations.count { !it.read } == 97)
val allEvents = events("$prefix.toml")
verifyPrivateInherited(allEvents, arm)
val (pid, mapping) = verifyInheritedPrefix(allEvents, binary, profile)
verifyCaptureEvidence(allEvents, profile)
val outcome = verifySequencePhase(allEvents, binary, profile, pid, mapping)
val apSummary = allEvents.single { it.kind == "adc-sequence-summary" }
val terminalState = allEvents.single { it.kind == "terminal-state" }
require(terminalState.unsigned("modeled_writes") == 466uL + apSummary.unsigned("writes"))
verifyCleanup(allEvents)
println("schema_version = \"mho900-lab.adc-sequence-verification/1\"")
println("result = \"accepted\"")
println("arm = $arm")
println("control_outcome = \"$outcome\"")
