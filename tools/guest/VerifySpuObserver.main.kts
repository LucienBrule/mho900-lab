// Independent evidence verification for ADC plus the complete SPU candidate.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
import java.util.zip.ZipFile
require(args.size in 1..3) { "Usage: VerifySpuObserver.main.kts RUN_DIRECTORY [25..39|spu-stock] [ADMISSION_VERIFIER_OVERRIDE]" }
val run=Path.of(args[0]).toAbsolutePath().normalize()
val stock=args.getOrNull(1)=="spu-stock"
val stockPair=false
val stockWrite=stock
val stockNext=stock
require(args.size<3 || stock) { "Verifier override is only for stock evidence" }
val pairSuite=Files.exists(run.resolve("pair-write-fixture.toml"))
val writeSuite=Files.exists(run.resolve("write-fixture.toml"))
val continuationSuite=Files.exists(run.resolve("continuation-fixture.toml"))
fun text(name:String)=Files.readString(run.resolve(name))
fun hash(bytes:ByteArray)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))
fun hash(file:Path)=hash(Files.readAllBytes(file))
data class E(val kind:String,val f:Map<String,String>) {
    fun s(k:String)=f.getValue(k)
    fun u(k:String)=s(k).removePrefix("0x").toULong(16)
}
fun events(name:String)=text(name).split("[[events]]").drop(1).map {
    val ps=it.lineSequence().filter { it.isNotBlank() }.map { val p=it.split(" = ",limit=2); require(p.size==2); p[0] to p[1].removeSurrounding("\"") }.toList()
    require(ps.map { it.first }.distinct().size==ps.size); val f=ps.toMap(); E(f.getValue("kind"),f)
}
class Elf(val bytes:ByteArray) {
    data class Seg(val offset:ULong,val address:ULong,val size:ULong,val flags:ULong)
    fun u16(at:Int)=ByteBuffer.wrap(bytes,at,2).order(ByteOrder.LITTLE_ENDIAN).short.toUShort().toInt()
    fun u32(at:Int)=ByteBuffer.wrap(bytes,at,4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong()
    fun u64(at:Int)=ByteBuffer.wrap(bytes,at,8).order(ByteOrder.LITTLE_ENDIAN).long.toULong()
    val segments:List<Seg>
    init { require(bytes.take(6)==listOf(127,69,76,70,2,1).map { it.toByte() } && u16(18)==183)
        segments=(0 until u16(56)).map { u64(32).toInt()+it*u16(54) }.filter { u32(it)==1uL }.map { Seg(u64(it+8),u64(it+16),u64(it+32),u32(it+4)) }
    }
    fun word(address:ULong):ULong { val s=segments.single { it.flags and 1uL!=0uL && address>=it.address && address+4uL<=it.address+it.size }; return u32((s.offset+address-s.address).toInt()) }
    fun symbol(name:String):ULong {
        val headers=(0 until u16(60)).map { u64(40).toInt()+it*u16(58) }
        val table=headers.single { u32(it+4)==2uL }
        val strings=headers[u32(table+40).toInt()]
        val symbols=(0 until (u64(table+32)/u64(table+56)).toInt()).map { i ->
            val at=u64(table+24).toInt()+i*u64(table+56).toInt()
            val start=u64(strings+24).toInt()+u32(at).toInt(); var end=start
            while(bytes[end]!=0.toByte()) end++
            String(bytes,start,end-start,Charsets.UTF_8) to u64(at+8)
        }
        return symbols.single { it.first==name }.second
    }
}
data class R(val tid:ULong,val pc:ULong,val relative:ULong,val sp:ULong,val pstate:ULong,val x:List<ULong>)
fun regs(e:E)=R(e.u("tid"),e.u("pc"),e.u("relative_pc"),e.u("sp"),e.u("pstate"),(0..30).map { e.u("x"+it.toString().padStart(2,'0')) })
data class T(var stopped:Boolean,var confirmed:Boolean,var live:Boolean=true)
val binary=Files.readAllBytes(run.resolve("group-control.elf")); val binaryHash=hash(binary)
require(binaryHash==text("binary-sha256.txt").take(64)); val control=Elf(binary)
val oracle=Files.readAllLines(run.resolve("reference.tsv")).drop(1).mapIndexed { i,line ->
    val fields=line.split('\t'); require(fields.size==7 && fields[0].toInt()==i); fields[6].removePrefix("0x").toULong(16)
}
require(hash(run.resolve("reference.tsv"))=="6b9f7b8cdfba8d99fa720b2771cd741f285a05d5f9a77f0aa7173fbf5a2e39c9" && oracle.size==452)
val spuBytes=Files.readAllBytes(run.resolve(if(stock) "spu-stock.bin" else "spu-private.bin"))
require(hash(spuBytes)==if(stock) "34ee0cb515117c91adc89ed065a66628e8f52283d0863a4b7f87b6cfb23be9a6" else "d55b7d70b4bcd1e3e95cd48fc7a7e791c2a16fc52cea32398b3799b94fb7aac6")
val spuInput=ByteBuffer.wrap(spuBytes).order(ByteOrder.LITTLE_ENDIAN)
fun su32(at:Int)=spuInput.getInt(at).toUInt().toULong()
fun su64(at:Int)=spuInput.getLong(at).toULong()
val offsets=List(452) { 0x3000uL }+(0..7).map { su32(1000+8*it) }
val operands=oracle+(0..7).map { su32(1004+8*it) }
val arms=if(stock) listOf(-1) else if(args.size==2) listOf(args[1].toInt().also { require(it in 25..39) }) else (25..39).toList()
for(arm in arms) {
    val pairWrite=false
    val oneWrite=true
    val continuation=true
    val expectedWrites=if(stock || arm in listOf(25,26,39)) 460 else if(arm in 27..28) 453 else 452
    val fixtureName=if(stock) "adc-stock.bin" else "adc-private.bin"
    val fixtureBytes=Files.readAllBytes(run.resolve(fixtureName))
    val fixture=ByteBuffer.wrap(fixtureBytes).order(ByteOrder.LITTLE_ENDIAN)
    fun input32(at:Int)=fixture.getInt(at).toUInt().toULong()
    fun input64(at:Int)=fixture.getLong(at).toULong()
    val fixtureHash=if(stock) "42138210921f16b38a4627de3601cd9330bd413638bd96414e69a1a3d47592e7" else if(arm==18) "ff7b60aee0f2cc79c69d8f28b92dd50b12ee8de3f3a6b3df25027e7997376e93" else "28471720179d4bf0e41911c0a4d29e108c89bbb4279d264793efb5f8ff9e866d"
    require(hash(fixtureBytes)==fixtureHash)
    val writeLimit=460
    require(input32(24)==452uL)
    val positive=stock || arm==0 || continuation; val prefix=if(stock) "native" else "spu-$arm"
    require(text("$prefix-status.toml").trim()=="exit_code = ${if(positive && !continuation) 0 else 78}")
    require(hash(run.resolve(if(stock) "group-executed.elf" else "spu-$arm.elf"))==binaryHash)
    val es=events(if(stock) "native-events.toml" else "$prefix.toml")
    val inputEvent=es[0]; require(inputEvent.kind=="transcript-input")
    require(inputEvent.u("profile")==if(stock) 1uL else 2uL)
    require(inputEvent.u("write_count")==452uL && inputEvent.u("total_size")==fixtureBytes.size.toULong())
    require(inputEvent.u("table_count")==111uL && inputEvent.u("binding_count")==11uL && inputEvent.u("shadow_count")==2uL && inputEvent.u("write_offset")==0x3000uL && inputEvent.u("write_width")==4uL)
    val accepted=es[1]; require(accepted.kind=="transcript-input-accepted" && accepted.u("profile")==inputEvent.u("profile") && accepted.u("write_count")==inputEvent.u("write_count"))
    val si=es[2]; require(si.kind=="spu-input" && si.u("profile")==if(stock) 1uL else 2uL)
    require(si.u("total_size")==1064uL && si.u("write_count")==8uL && si.u("binding_count")==15uL && si.u("series_count")==9uL && si.u("sample_count")==3uL && si.u("shadow_count")==4uL && si.u("repeat_count")==2uL)
    val sa=es[3]; require(sa.kind=="spu-input-accepted" && sa.u("profile")==si.u("profile") && sa.u("write_count")==8uL)
    val mode=es[4]; require(mode.kind=="model-mode" && mode.s("scope")==if(stock) "stock" else "private")
    require(mode.u("transcript")==1uL && mode.u("profile")==inputEvent.u("profile") && mode.u("write_count")==452uL && mode.u("spu")==1uL && mode.u("spu_write_count")==8uL)
    if(!stock) require(mode.u("arm")==arm.toULong())
    require((mode.f["continuation"]?.removePrefix("0x")?.toULong(16) ?: 0uL)==if(continuation) 1uL else 0uL)
    require((mode.f["one_write"]?.removePrefix("0x")?.toULong(16) ?: 0uL)==0uL)
    require((mode.f["pair_write"]?.removePrefix("0x")?.toULong(16) ?: 0uL)==if(pairWrite) 1uL else 0uL)
    val setup=es[5]; require(setup.kind=="group-setup" && setup.u("options")==0x100009uL)
    val pid=setup.u("pid"); val observer=setup.u("observer_pid"); require(pid==mode.u("pid") && pid>1uL && observer>1uL && pid!=observer)
    require(setup.u("thread_limit")==128uL && setup.u("pass_limit")==16uL && setup.u("event_limit")==256uL && setup.u("deadline_ms")==10000uL)
    val coveredAt=es.indexOfFirst { it.kind=="group-covered" }; require(coveredAt>1)
    val pre=es.subList(6,coveredAt)
    val allowed=setOf("enumeration-start","enumerated","enumeration-end","group-identity","group-track","group-seize","group-interrupt","group-wait")
    require(pre.all { it.kind in allowed }) { "Setup churn requires separate adjudication" }
    val starts=pre.filter { it.kind=="enumeration-start" }; val ends=pre.filter { it.kind=="enumeration-end" }
    require(starts.map { it.u("pass") }==listOf(0uL,1uL) && ends.map { it.u("pass") }==listOf(0uL,1uL))
    val sets=(0uL..1uL).map { p->pre.filter { it.kind=="enumerated" && it.u("pass")==p }.map { it.u("tid") } }
    require(sets.all { it.size in 1..128 && it.distinct().size==it.size } && sets[0].toSet()==sets[1].toSet())
    val initial=sets[0].toSet(); require(pid in initial && observer !in initial)
    if(!stock) require(initial==setOf(pid,mode.u("fixture_worker")))
    for(p in 0..1) {
        require(ends[p].u("count")==sets[p].size.toULong())
        val a=pre.indexOf(starts[p]); val b=pre.indexOf(ends[p]); require(b>a)
        require(pre.subList(a+1,b).all { it.kind=="enumerated" && it.u("pass")==p.toULong() })
    }
    val waits=pre.filter { it.kind=="group-wait" }; require(waits.map { it.u("index") }==initial.indices.map { it.toULong() })
    for(tid in initial) {
        fun one(kind:String)=pre.single { it.kind==kind && it.u("tid")==tid }
        val ids=pre.filter { it.kind=="group-identity" && it.u("tid")==tid }
        require(ids.size==2 && ids[0].s("phase")=="before-seize" && ids[1].s("phase")=="converged")
        require(ids.all { it.u("tgid")==pid } && ids[0].u("tracer_pid")==0uL && ids[1].u("tracer_pid")==observer && ids[1].u("state")==0x74uL)
        val seize=one("group-seize"); require(seize.u("result")==0uL && seize.u("options")==0x100009uL)
        require(one("group-interrupt").u("result")==0uL && one("group-wait").u("status")==0x80057fuL)
        val ordered=listOf(ends[0],ids[0],one("group-track"),seize,one("group-interrupt"),one("group-wait"),starts[1],ids[1])
        require(ordered.map { pre.indexOf(it) }.zipWithNext().all { (a,b)->a<b })
    }
    require(pre.filter { it.kind in setOf("group-track","group-seize","group-interrupt","group-wait") }.size==initial.size*4)
    require(pre.count { it.kind=="group-identity" }==initial.size*2)
    val covered=es[coveredAt]; require(covered.u("pid")==pid && covered.u("observer_pid")==observer && covered.u("count")==initial.size.toULong() && covered.u("passes")==2uL)
    var at=coveredAt+1
    fun take(kind:String):E=es[at++].also { require(it.kind==kind) { "arm $arm event ${at-1}: expected $kind, got ${it.kind}" } }
    val binding=take("model-binding"); require(binding.u("pid")==pid && binding.u("initial_value")==ULong.MAX_VALUE)
    val base=binding.u("base"); val target=binding.u("target"); val obj=binding.u("object")
    // AArch64 layout of the reviewed GmShared fixture: output at48, pointer array at64,
    // address/value arrays at152/596, sources at1040, shadows at1056/1060, SPU at1064.
    val privateShared=if(stock) 0uL else (obj-48uL).also { require(it>0uL && it and 4095uL==0uL) }
    val privateTargets=if(stock) emptyList() else listOf(
        control.symbol("gm_private_leader"),control.symbol("gm_at_private_init"),control.symbol("gm_write"),
        control.symbol("gm_store"),control.symbol("gm_write"),privateShared+152uL,privateShared+596uL,
        privateShared+1040uL,privateShared+1048uL,privateShared+1056uL,privateShared+1060uL)
    val spuPrivateTargets=if(stock) emptyList() else listOf(
        "gm_private_leader","gm_first","gm_second","gm_write","gm_write64","gm_store",
        "gm_worker_read","gm_at_private_init","gm_st_private_init","gm_write","gm_write"
    ).map { control.symbol(it) }+(0..3).map { privateShared+1548uL+4uL*it.toULong() }
    fun spuTarget(i:Int)=if(stock) base+su64(80+24*i) else spuPrivateTargets[i]
    fun globalAddress(i:Int)=if(stock) base+su64(424+16*i) else privateShared+1200uL+4uL*i.toULong()
    fun seriesAddress(i:Int)=if(stock) base+0xb8f4f0uL+32uL*i.toULong() else privateShared+1212uL+32uL*i.toULong()
    fun samplePointer(i:Int)=if(stock) base+su64(496+32*i) else privateShared+1564uL+256uL*listOf(0,0,0,1,2,3,4,4,4)[i].toULong()
    fun configPointer(i:Int):ULong {
        val relative=su64(512+32*i)
        return if(relative==0uL) 0uL else if(stock) base+relative else privateShared+2844uL+4uL*listOf(0,0,1,2,3,0,0,0,0)[i].toULong()
    }
    fun sampleAddress(i:Int)=if(stock) base+su64(784+32*i) else samplePointer(2)+16uL*listOf(0,1,15)[i].toULong()
    data class Capture(val kind:String,val values:Map<String,ULong>)
    val captureExpected=buildList {
        for(i in 0..14) {
            val mismatch=!stock && arm==32 && i==9
            add(Capture("spu-binding",mapOf("index" to i.toULong(),"binding_kind" to su32(64+24*i),"slot" to su64(72+24*i),
                "expected_target" to spuTarget(i),"actual_target" to spuTarget(i)+(if(mismatch) 1uL else 0uL),"match" to if(mismatch) 0uL else 1uL)))
            if(mismatch) return@buildList
        }
        for(pass in 0..1) {
            if(pass==1 && !stock && arm==38) add(Capture("spu-private-mutation",emptyMap()))
            for(i in 0..2) {
                val mismatch=!stock && ((arm==33 && i==0) || (arm==38 && pass==1 && i==0))
                val expected=su32(432+16*i)
                add(Capture("spu-global",mapOf("pass" to pass.toULong(),"index" to i.toULong(),"address" to globalAddress(i),
                    "expected" to expected,"actual" to expected+(if(mismatch) 1uL else 0uL),"match" to if(mismatch) 0uL else 1uL)))
                if(mismatch) return@buildList
            }
            for(i in 0..8) {
                val badPointer=!stock && arm==34 && i==2
                val badCount=!stock && arm==35 && i==2
                add(Capture("spu-series",mapOf("pass" to pass.toULong(),"index" to i.toULong(),"address" to seriesAddress(i),
                    "key0" to su32(488+32*i),"key1" to su32(492+32*i),"pointer" to samplePointer(i)+(if(badPointer) 1uL else 0uL),
                    "expected_pointer" to samplePointer(i),"count" to su32(504+32*i)+(if(badCount) 1uL else 0uL),
                    "word20" to su32(508+32*i),"expected_word20" to su32(508+32*i),"config_pointer" to configPointer(i),
                    "expected_config_pointer" to configPointer(i),"match" to if(badPointer || badCount) 0uL else 1uL)))
                if(badPointer || badCount) return@buildList
            }
            for(i in 0..2) {
                val mismatch=!stock && arm==36 && i==1
                val expected=su32(796+32*i)
                add(Capture("spu-sample",mapOf("pass" to pass.toULong(),"ordinal" to i.toULong(),"requested_index" to su32(776+32*i),
                    "address" to sampleAddress(i),"w0" to su32(792+32*i),"mode" to expected+(if(mismatch) 1uL else 0uL),
                    "w2" to su32(800+32*i),"w3" to su32(804+32*i),"match" to if(mismatch) 0uL else 1uL)))
                if(mismatch) return@buildList
            }
            for(i in 0..3) {
                val mismatch=!stock && arm==37 && i==0
                val expected=su32(892+32*i)
                add(Capture("spu-shadow",mapOf("pass" to pass.toULong(),"index" to i.toULong(),"slot" to su64(872+32*i),
                    "object" to spuTarget(11+i),"expected_object" to spuTarget(11+i),"expected" to expected,
                    "actual" to expected+(if(mismatch) 1uL else 0uL),"match" to if(mismatch) 0uL else 1uL)))
                if(mismatch) return@buildList
            }
            add(Capture("spu-capture",mapOf("pass" to pass.toULong(),"valid" to 1uL)))
        }
    }
    val elf=if(stock) {
        require(hash(run.resolve("installed.apk"))=="6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b")
        val bytes=ZipFile(run.resolve("installed.apk").toFile()).use { z->z.getInputStream(z.getEntry("lib/arm64-v8a/libscope-auklet.so")).readBytes() }
        require(hash(bytes)=="4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e")
        Elf(bytes)
    } else { require(base==0uL); control }
    require(elf.word(binding.u("first_pc")-base)==0xb9400109uL && elf.word(binding.u("second_pc")-base)==0xb9400109uL)
    require(binding.u("store_pc")+4uL==target && binding.u("store_opcode")==0xf9000128uL && elf.word(binding.u("store_pc")-base)==binding.u("store_opcode"))
    require(elf.word(target-base)==binding.u("target_opcode") && binding.u("target_opcode")==if(stock) 0x14000001uL else 0xd503201fuL)
    if(oneWrite) { require(binding.u("write_opcode")==0xb9000109uL && elf.word(binding.u("write_pc")-base)==0xb9000109uL)
        if(stock) require(binding.u("write_pc")==base+0x27043cuL) }
    if(stock) {
        require(target==base+0x42a8f0uL && obj==base+0xbbccf0uL && binding.u("got_slot")==base+0xb8d758uL)
        require(binding.u("first_pc")==base+0x270604uL && binding.u("second_pc")==base+0x270604uL)
        val map=text("native-snapshot-maps.txt").lineSequence().map { it.trim().split(Regex("\\s+")) }.single { it.size>=6 && it[1]=="r-xp" && it[2].toULong(16)==0xf05000uL && it.last().endsWith("/base.apk") }
        val seg=elf.segments.single { it.offset==0uL && it.flags and 1uL!=0uL }; require(base==map[0].substringBefore('-').toULong(16)-seg.address)
        require(pid==text("native-app-pid.toml").substringAfter("= ").trim().toULong())
    }
    val tracked=initial.associateWith { T(true,true) }.toMutableMap()
    fun inventory(phase:String,stopping:ULong) {
        val ts=mutableListOf<E>(); while(es[at].kind=="thread-status") ts.add(take("thread-status"))
        val live=tracked.filterValues { it.live }.keys
        require(ts.map { it.u("tid") }.toSet()==live && ts.size==live.size)
        require(ts.all { it.s("phase")==phase && "read_error" !in it.f && it.u("tgid")==pid && it.u("tracer_pid")==observer && it.u("state")==0x74uL })
        val inv=take("thread-inventory"); require(inv.s("phase")==phase && inv.u("pid")==pid && inv.u("observer_pid")==observer && inv.u("stopping_tid")==stopping)
        require(inv.u("observed_count")==live.size.toULong() && inv.u("overflow")==0uL && inv.u("error")==0uL && inv.u("directory_flags")==0x4000uL && inv.u("error_operation")==0uL && inv.u("error_result")==0uL)
        require(tracked.filterValues { it.live }.values.all { it.stopped })
    }
    inventory("before-ready",pid)
    val ready=take("ready"); require(ready.u("pid")==pid && ready.u("observer_pid")==observer && ready.u("stopping_tid")==pid)
    var armed=false; var quiescing=false; var count=0; var waitIndex=0uL; var mapBase=0uL; var fd:ULong?=null
    var lastWait:E?=null; var lastCall:E?=null; var firstFault:R?=null; var finalFault:R?=null; var currentFault:E?=null
    var writes=0; var ledgerOffset=0uL; var ledgerValue=0uL
    var liveState:Boolean?=null
    val liveBindings=mutableListOf<E>(); val liveTables=mutableListOf<E>(); val liveSources=mutableListOf<E>(); val liveShadows=mutableListOf<E>()
    var liveRejection:E?=null; var writeRejection:E?=null; var transcriptComplete=false
    var spuCaptureIndex=0; var spuLive=false; var spuComplete=false; var spuRejected:E?=null
    var unsupported:E?=null; var unsupportedRegs:R?=null
    var pendingUnknown:ULong?=null; val identities=mutableSetOf<ULong>(); val confirmed=initial.toMutableSet(); val clones=mutableSetOf<ULong>()
    val resumesBeforeWait=mutableSetOf<ULong>(); var rejected=false; var boundary:E?=null; var stopRegs:R?=null; var terminalTid=0uL
    while(at<es.size && es[at].kind!="thread-status") {
        val e=es[at++]
        when(e.kind) {
            "spu-binding","spu-global","spu-series","spu-sample","spu-shadow","spu-capture","spu-private-mutation"->{
                require(writes==452 && count==2 && !quiescing && !spuLive && spuRejected==null)
                require(spuCaptureIndex<captureExpected.size)
                val expected=captureExpected[spuCaptureIndex++]
                require(e.kind==expected.kind) { "SPU capture order expected ${expected.kind}, got ${e.kind}" }
                for((key,value) in expected.values) require(e.u(key)==value) { "SPU arm $arm ${e.kind} field $key expected $value, got ${e.f[key]}" }
                if(e.kind=="spu-private-mutation") require(!stock && arm==38 && e.s("category")=="global" && e.u("index")==0uL && e.u("before")==8uL && e.u("after")==9uL)
            }
            "spu-live-state"->{
                require(writes==452 && !spuLive && spuRejected==null && spuCaptureIndex==captureExpected.size && (stock || arm !in 32..38))
                require(e.u("valid")==1uL && e.u("captures")==2uL); spuLive=true
            }
            "spu-live-rejected"->{
                require(!stock && arm in 32..38 && writes==452 && !spuLive && spuRejected==null && spuCaptureIndex==captureExpected.size)
                val category=when(arm) { 32->"binding";33,38->"global";34,35->"series";36->"sample";else->"shadow" }
                require(e.s("category")==category)
                val last=captureExpected.last(); require(last.values.getValue("match")==0uL)
                val actual=when(arm) { 32->last.values.getValue("actual_target");34->last.values.getValue("pointer");35->last.values.getValue("count");36->last.values.getValue("mode");else->last.values.getValue("actual") }
                require(e.u("actual")==actual && e.u("expected")==actual-1uL)
                spuRejected=e
            }
            "spu-complete"->{ require(writes==460 && spuLive && !spuComplete && e.u("writes")==8uL && e.u("total_writes")==460uL);spuComplete=true }
            "spu-write-rejected","spu-boundary"->{
                require(writes>=452 && writeRejection==null && count==2 && !quiescing)
                val f=requireNotNull(unsupported); val r=requireNotNull(unsupportedRegs)
                require(e.u("tid")==r.tid && e.u("index")== (writes-452).toULong() && e.u("global_index")==writes.toULong())
                require(e.u("offset")==f.u("offset") && e.u("pc")==r.pc && e.u("actual_value")==r.x[9] and 0xffffffffuL)
                require((e.kind=="spu-boundary")== (writes==460))
                if(spuRejected!=null) require(e.s("reason")=="live-state")
                else {
                    require(e.u("expected_offset")==if(writes<460) offsets[writes] else 0uL)
                    require(e.u("expected_value")==if(writes<460) operands[writes] else 0uL)
                    require(e.u("signal")==f.u("signal") && e.u("si_code")==f.u("si_code") && e.u("address")==f.u("address") && e.u("opcode")==f.u("opcode"))
                }
                writeRejection=e
            }
            "transcript-binding"->{
                require(count==2 && writes==0 && !quiescing && liveState==null && liveRejection==null)
                val i=liveBindings.size; require(i<11 && e.u("index")==i.toULong())
                require(e.u("binding_kind")==input32(64+24*i) && e.u("slot")==input64(72+24*i))
                val expected=e.u("expected_target"); require(expected>0uL)
                if(stock) require(expected==base+input64(80+24*i))
                else require(expected==privateTargets[i])
                val mismatch=!stock && arm==21 && i==4
                require(e.u("actual_target")==expected+(if(mismatch) 1uL else 0uL) && e.u("match")==if(mismatch) 0uL else 1uL)
                liveBindings.add(e)
            }
            "transcript-table-word"->{
                require(liveBindings.size==11 && liveState==null && liveRejection==null)
                val ordinal=liveTables.size; val table=ordinal/111; val i=ordinal%111; require(ordinal<222)
                require(e.u("table")==table.toULong() && e.u("index")==i.toULong() && e.u("expected")==input32((if(table==0) 328 else 772)+4*i))
                require(e.u("object")==liveBindings[5+table].u("actual_target"))
                val mismatch=!stock && arm==23 && ordinal==112
                require(e.u("actual")==e.u("expected")+(if(mismatch) 1uL else 0uL) && e.u("match")==if(mismatch) 0uL else 1uL)
                liveTables.add(e)
            }
            "transcript-source-word"->{
                require(liveTables.size==222 && liveState==null && liveRejection==null)
                val i=liveSources.size; require(i<4 && e.u("index")==i.toULong() && e.u("expected")==input32(1216+4*i))
                val objectAddress=if(stock) base+listOf(0x994740uL,0x99473cuL,0x9948e0uL,0x9948dcuL)[i] else liveBindings[7].u("actual_target")+i.toULong()*4uL
                require(e.u("object")==objectAddress)
                if(!stock && i>=2) require(e.u("object")==liveBindings[8].u("actual_target")+(i-2).toULong()*4uL)
                val mismatch=!stock && arm==24 && i==1
                require(e.u("actual")==e.u("expected")+(if(mismatch) 1uL else 0uL) && e.u("match")==if(mismatch) 0uL else 1uL)
                liveSources.add(e)
            }
            "transcript-shadow"->{
                require(liveSources.size==4 && liveState==null && liveRejection==null && e.s("phase")=="initial")
                val i=liveShadows.size; require(i<2 && e.u("index")==i.toULong())
                require(e.u("slot")==input64(1232+32*i) && e.u("width")==input32(1248+32*i) && e.u("expected")==input32(1252+32*i))
                require(e.u("object")==liveBindings[9+i].u("actual_target"))
                val mismatch=!stock && arm==22 && i==0
                require(e.u("actual")==e.u("expected")+(if(mismatch) 1uL else 0uL) && e.u("match")==if(mismatch) 0uL else 1uL)
                liveShadows.add(e)
            }
            "transcript-live-rejected"->{
                require(!stock && arm in 21..24 && liveRejection==null && liveState==null && writes==0)
                val category=when(arm) { 21->"binding"; 22->"shadow"; 23->"table"; else->"source" }
                val previous=when(arm) { 21->liveBindings.last(); 22->liveShadows.last(); 23->liveTables.last(); else->liveSources.last() }
                require(e.s("category")==category && e.u("index")==when(arm) { 21->4uL; 22->0uL; 23->112uL; else->1uL })
                require(e.u("actual")==previous.u(if(arm==21) "actual_target" else "actual") && e.u("expected")==previous.u(if(arm==21) "expected_target" else "expected"))
                liveRejection=e; liveState=false
            }
            "transcript-live-state"->{
                require(liveState==null && liveRejection==null && liveBindings.size==11 && liveTables.size==222 && liveSources.size==4 && liveShadows.size==2)
                require(e.u("valid")==1uL && e.u("checked_bindings")==11uL && e.u("checked_table_words")==222uL && e.u("checked_sources")==4uL && e.u("checked_shadows")==2uL)
                liveState=true
            }
            "transcript-complete"->{ require(writes==452 && !transcriptComplete && e.u("writes")==452uL); transcriptComplete=true }
            "transcript-write-rejected","transcript-boundary"->{
                require(writeRejection==null && count==2 && !quiescing)
                val f=requireNotNull(unsupported); val r=requireNotNull(unsupportedRegs)
                require(e.u("tid")==r.tid && e.u("index")==writes.toULong() && e.u("offset")==f.u("offset") && e.u("pc")==r.pc && e.u("actual_value")==r.x[9] and 0xffffffffuL)
                if(liveRejection!=null) require(e.kind=="transcript-write-rejected" && e.s("reason")=="live-state" && writes==0)
                else {
                    require(e.u("writes")==writes.toULong() && e.u("signal")==f.u("signal") && e.u("si_code")==f.u("si_code") && e.u("address")==f.u("address") && e.u("opcode")==f.u("opcode"))
                    require(e.u("expected_offset")==if(writes<writeLimit) 0x3000uL else 0uL)
                    require(e.u("expected_value")==if(writes<writeLimit) oracle[writes] else 0uL)
                    require((e.kind=="transcript-boundary")== (writes==writeLimit))
                }
                writeRejection=e
            }
            "runtime-resume"->{
                require(!quiescing); val tid=e.u("tid"); val t=tracked.getValue(tid)
                require(t.live && t.stopped && tid in confirmed)
                require(e.u("operation")==if(tid==pid && !armed) 24uL else 7uL); t.stopped=false
                if(lastWait==null) require(resumesBeforeWait.add(tid))
            }
            "runtime-wait"->{
                require(resumesBeforeWait==initial && e.u("index")==waitIndex++ && waitIndex<=200000uL)
                val tid=e.u("tid"); val status=e.u("status"); val t=tracked[tid]; lastWait=e
                if(status and 255uL==127uL) {
                    if(t==null) { require(status==0x80057fuL && pendingUnknown==null); pendingUnknown=tid }
                    else { require(t.live && !t.stopped); t.stopped=true }
                } else require(t!=null && t.live)
            }
            "group-identity"->{
                require(e.s("phase") in setOf("runtime-auto","runtime-clone-child") && e.u("tgid")==pid && e.u("tracer_pid")==observer)
                identities.add(e.u("tid"))
            }
            "group-track"->{
                val tid=e.u("tid"); require(tid in identities && tid !in tracked && tracked.size<128)
                tracked[tid]=T(pendingUnknown==tid,tid in confirmed); if(pendingUnknown==tid) pendingUnknown=null
            }
            "runtime-clone"->{
                val w=requireNotNull(lastWait); val parent=e.u("parent_tid"); val child=e.u("new_tid")
                require(w.u("tid")==parent && w.u("status")==0x3057fuL && tracked.getValue(parent).stopped)
                require(child!=parent && child!=observer && clones.add(child)); confirmed.add(child); tracked[child]?.confirmed=true
            }
            "runtime-new-stop","terminal-interrupt-stop"->{
                val w=requireNotNull(lastWait); require(w.u("tid")==e.u("tid") && w.u("status")==0x80057fuL && e.u("status")==w.u("status"))
                require(tracked.getValue(e.u("tid")).stopped && (e.kind=="terminal-interrupt-stop")==quiescing)
            }
            "runtime-exit"->{
                val w=requireNotNull(lastWait); val tid=e.u("tid"); require(w.u("tid")==tid && w.u("status")==e.u("status") && w.u("status") and 255uL!=127uL && tid!=pid)
                tracked.getValue(tid).live=false
            }
            "runtime-syscall"->{
                val w=requireNotNull(lastWait); require(!quiescing && !armed && w.u("tid")==pid && w.u("status")==0x857fuL && e.u("tid")==pid && e.u("phase") in 0uL..1uL); lastCall=e
            }
            "open-result"->{
                val call=requireNotNull(lastCall); require(fd==null && call.u("phase")==1uL && call.u("number")==56uL && e.u("fd")==call.u("a0") && e.u("fd")<0x7fffffffuL); fd=e.u("fd")
            }
            "mmap-request"->{
                val call=requireNotNull(lastCall); require(call.u("phase")==0uL && call.u("number")==222uL && mapBase==0uL)
                require((0..5).map { e.u("a$it") }==listOf(0uL,0x1000000uL,3uL,1uL,requireNotNull(fd),0uL))
                require((0..5).all { e.u("a$it")==call.u("a$it") } && e.u("pc")==call.u("pc") && e.u("lr")==call.u("lr"))
                if(stock) require(e.u("lr")==base+0x270284uL)
            }
            "mapping-result"->{
                val call=requireNotNull(lastCall); require(call.u("phase")==1uL && call.u("number")==222uL && mapBase==0uL)
                mapBase=e.u("base"); require(mapBase==call.u("a0") && mapBase>0uL && mapBase<0x8000000000000000uL && mapBase and 4095uL==0uL && e.u("protection")==0uL)
            }
            "mapped-fault"->{
                val w=requireNotNull(lastWait); require(!quiescing && w.u("tid")==e.u("tid") && w.u("status")==0xb7fuL)
                require(e.u("signal")==11uL && e.u("si_code")==2uL && e.u("mapping")==mapBase && mapBase>0uL && e.u("address")==mapBase+e.u("offset") && e.u("responses")==count.toULong())
                val r=regs(take("fault-registers")); require(r.tid==e.u("tid") && r.sp>0uL && r.sp and 15uL==0uL)
                require(elf.word(r.pc-base)==e.u("opcode"))
                if(count<2) require(r.x[8]==e.u("address") && e.u("opcode")==0xb9400109uL)
                if(count==0) { require(r.tid==pid && r.pc==binding.u("first_pc") && e.u("offset")==0x4048uL); firstFault=r }
                else if(count==2) {
                    require(continuation && armed && unsupported==null && e.u("offset")<0x1000000uL)
                    if(!stock) {
                        val worker=(arm==30 && writes==452) || (arm==26 && writes==460)
                        val readTerminal=arm==26 && writes==460
                        val wide=arm==31 && writes==452
                        val badOffset=arm==28 && writes==453
                        val offset=if(readTerminal) 0x4040uL else if(writes==460) (if(arm==39) 0x1000uL else 0x4004uL) else if(badOffset) 0x1004uL else offsets[writes]
                        require(r.x[8]==e.u("address") && e.u("offset")==offset)
                        require(r.tid==if(worker) mode.u("fixture_worker") else pid)
                        require(r.pc==if(readTerminal) binding.u("worker_pc") else if(wide) binding.u("write64_pc") else binding.u("write_pc"))
                        require(e.u("opcode")==if(readTerminal) 0xb9400109uL else if(wide) 0xf9000109uL else 0xb9000109uL)
                        if(!readTerminal) {
                            val value=if(writes==460) 1uL else if(arm==27 && writes==453) operands[writes] xor 1uL else if(arm==29 && writes==452) operands[453] else operands[writes]
                            require(r.x[9] and 0xffffffffuL==value)
                        }
                    }
                    unsupported=e; unsupportedRegs=r
                }
                else { require(count==1); finalFault=r; val wanted=if(positive) 0x4044uL else 0x4040uL; require(e.u("offset")==wanted)
                    require(r.pc==if(arm==2 && !stock) binding.u("worker_pc") else binding.u("second_pc"))
                    require(r.tid==if(arm==2 && !stock) mode.u("fixture_worker") else pid)
                }
                currentFault=e
            }
            "modeled-read"->{
                val f=requireNotNull(currentFault); val before=if(count==0) requireNotNull(firstFault) else requireNotNull(finalFault)
                require(!quiescing && !rejected && count<2 && (count==0 || positive) && e.u("tid")==pid && e.u("index")==count.toULong())
                val value=if(count==0) 0xe1234567uL else 0x89abcdefuL; require(e.u("value")==value && f.u("tid")==pid)
                val after=regs(take("response-registers")); require(after.tid==pid && after.pc==before.pc+4uL && after.sp==before.sp && after.pstate==before.pstate)
                require(after.x[9]==value && (0..30).filter { it!=9 }.all { after.x[it]==before.x[it] }); count++
            }
            "continuation-mode"->{
                require(continuation && count==2 && !armed && e.u("responses")==2uL && e.u("hardware_breakpoint")==0uL && e.u("resume_operation")==7uL); armed=true
            }
            "modeled-write"->{
                val f=requireNotNull(unsupported); val before=requireNotNull(unsupportedRegs)
                require(liveState==true && count==2 && writes<writeLimit && !quiescing && !rejected && armed)
                val expectedWord=operands[writes]; val expectedOffset=offsets[writes]
                require(f.u("tid")==pid && before.tid==pid && f.u("offset")==expectedOffset && before.x[8]==f.u("address") && before.x[9] and 0xffffffffuL==expectedWord)
                require(before.pc==binding.u("write_pc") && f.u("opcode")==0xb9000109uL)
                require(e.u("tid")==pid && e.u("index")==writes.toULong() && e.u("offset")==expectedOffset && e.u("value")==expectedWord && e.u("width")==4uL)
                val claim=take(if(writes<452) "transcript-write" else "spu-write")
                require(claim.u("index")== (if(writes<452) writes else writes-452).toULong() && claim.u("tid")==pid && claim.u("pc")==before.pc && claim.u("opcode")==0xb9000109uL && claim.u("offset")==expectedOffset && claim.u("value")==expectedWord && claim.u("width")==4uL)
                if(writes>=452) { require(spuLive && claim.u("global_index")==writes.toULong()) }
                val after=regs(take("write-registers")); require(after.tid==pid && after.pc==before.pc+4uL && after.sp==before.sp && after.pstate==before.pstate && after.x==before.x)
                writes++; ledgerOffset=e.u("offset"); ledgerValue=e.u("value"); unsupported=null; unsupportedRegs=null
            }
            "unsupported-access"->{
                if(oneWrite) require(e.u("writes")==writes.toULong())
                val f=requireNotNull(unsupported); require(continuation && count==2 && !rejected && e.u("tid")==f.u("tid") && e.u("responses")==2uL && e.s("classification")=="mapped"); rejected=true
            }
            "debug-before"->{
                require(!continuation && count==2 && !armed && positive && e.u("result")==0uL && e.u("size")==264uL && e.u("info") and 255uL!=0uL)
                fun emptySlots(d:E,start:Int) { for(i in start..15) { val n=i.toString().padStart(2,'0'); require(d.u("a$n")==0uL && d.u("c$n")==0uL) } }
                emptySlots(e,0); val p=take("debug-profile"); require(p.s("guest_profile")=="cached-enable" && p.u("requested_control")==0x1e5uL && p.u("expected_readback_control")==0x1e4uL)
                val q=take("debug-request"); require(q.u("result")==0uL && q.u("size")==24uL && q.u("info")==e.u("info") && q.u("a00")==target && q.u("c00")==0x1e5uL); emptySlots(q,1)
                require(take("debug-set").u("result")==0uL)
                val a=take("debug-after"); require(a.u("result")==0uL && a.u("size")==264uL && a.u("info")==e.u("info") && a.u("a00")==target && a.u("c00")==0x1e4uL); emptySlots(a,1); armed=true
            }
            "post-store-stop"->{
                val w=requireNotNull(lastWait); require(!continuation && positive && armed && count==2 && w.u("tid")==pid && w.u("status")==0x57fuL)
                require(e.u("tid")==pid && e.u("status")==0x57fuL && e.u("signal")==5uL && e.u("si_code")==4uL && e.u("address")==target && e.u("opcode")==binding.u("target_opcode"))
                stopRegs=regs(take("post-store-registers")); require(stopRegs!!.tid==pid && stopRegs!!.pc==target && stopRegs!!.x[8]==0x0123456789abcdefuL && stopRegs!!.x[9]==obj)
            }
            "post-store-boundary"->{
                require(!continuation && positive && stopRegs!=null && boundary==null && e.u("target")==target && e.u("object")==obj && e.u("value")==0x0123456789abcdefuL && e.u("x8")==stopRegs!!.x[8] && e.u("x9")==stopRegs!!.x[9]); boundary=e
            }
            "response-guard-rejected"->{ require(!positive && !rejected && count==1 && e.u("responses")==1uL && e.u("tid")==requireNotNull(finalFault).tid); rejected=true }
            "terminal-quiesce"->{
                require(!quiescing && pendingUnknown==null && if(positive && !continuation) boundary!=null else rejected)
                quiescing=true; terminalTid=e.u("stopping_tid"); require(terminalTid==(if(continuation) requireNotNull(unsupportedRegs).tid else if(positive) pid else requireNotNull(finalFault).tid) && tracked.getValue(terminalTid).stopped)
            }
            "terminal-interrupt"->{ require(quiescing && tracked.getValue(e.u("tid")).let { it.live && !it.stopped } && e.u("result").toLong() in listOf(0L,-5L)) }
            "terminal-pending-signal"->{
                require(quiescing && !positive && arm==2 && e.u("tid")==pid && e.u("status")==0x857fuL)
                val w=requireNotNull(lastWait); require(w.u("tid")==pid && w.u("status")==e.u("status"))
            }
            else->error("Unsupported runtime evidence: ${e.kind}")
        }
    }
    require(quiescing && pendingUnknown==null && fd!=null && mapBase>0uL && count==if(positive) 2 else 1)
    inventory("terminal",terminalTid)
    val terminal=take("terminal-state"); require(terminal.u("object")==obj && terminal.u("value")==if(positive) 0x0123456789abcdefuL else ULong.MAX_VALUE)
    require(terminal.u("responses")==count.toULong())
    if(oneWrite) { require(writes==expectedWrites)
        require(terminal.u("modeled_writes")==writes.toULong() && terminal.u("write_offset")==ledgerOffset && terminal.u("write_value")==ledgerValue) }
    require(liveState==true && liveRejection==null)
    require(writeRejection!=null || liveRejection!=null)
    require(transcriptComplete)
    require(spuComplete==(writes==460))
    if(!stock && arm in 32..38) require(spuRejected!=null && !spuLive)
    else if(stock || arm !in 30..31) require(spuLive)
    else require(!spuLive && spuCaptureIndex==0)
    for(i in 0..1) {
        val shadow=take("transcript-shadow")
        val expected=input32(1256+32*i)
        require(shadow.s("phase")=="terminal" && shadow.u("index")==i.toULong() && shadow.u("slot")==input64(1232+32*i) && shadow.u("width")==input32(1248+32*i))
        require(shadow.u("expected")==expected)
        if(stock) require(shadow.u("object")==base+input64(1240+32*i))
        else require(shadow.u("object")==privateTargets[9+i])
        val actual=expected+(if(!stock && arm==22 && i==0) 1uL else 0uL)
        require(shadow.u("actual")==actual && shadow.u("match")==if(actual==expected) 1uL else 0uL)
    }
    for(i in 0..3) {
        val shadow=take("transcript-spu-shadow")
        require(shadow.u("index")==i.toULong() && shadow.u("slot")==listOf(0xb8d288uL,0xb8bb48uL,0xb8d060uL,0xb8be90uL)[i])
        require(shadow.u("object_match")==1uL && shadow.u("object")==shadow.u("expected_object"))
        if(stock) require(shadow.u("object")==base+listOf(0x3cb44fcuL,0x3cb44a0uL,0x3cb44f0uL,0x3cb44b0uL)[i])
        else require(shadow.u("value")==0uL && shadow.u("object")==privateShared+1064uL+i.toULong()*4uL)
    }
    for(i in 0..3) {
        val shadow=take("spu-terminal-shadow")
        require(shadow.u("index")==i.toULong() && shadow.u("slot")==su64(872+32*i))
        require(shadow.u("object")==spuTarget(11+i) && shadow.u("expected_object")==spuTarget(11+i))
        val expected=if(writes==460) su32(896+32*i) else if(i==0 && writes==453) 0uL else su32(892+32*i)
        require(shadow.u("expected")==expected && shadow.u("object_match")==1uL)
        val actual=expected+(if(arm==37 && i==0) 1uL else 0uL)
        require(shadow.u("actual")==actual && shadow.u("match")==if(actual==shadow.u("expected")) 1uL else 0uL)
    }
    if(!stock) { require(terminal.u("worker_ack")==1uL && clones==setOf(terminal.u("fixture_new_tid")) && tracked.size==3) }
    val live=tracked.filterValues { it.live }.keys; val reaped=mutableSetOf<ULong>()
    while(es[at].kind=="group-reaped") { val e=take("group-reaped"); require(e.u("tid") in live && reaped.add(e.u("tid")) && e.u("status")==9uL) }
    val cleanup=take("group-cleanup"); require(reaped==live && cleanup.u("expected_count")==live.size.toULong() && cleanup.u("reaped_count")==live.size.toULong() && cleanup.u("wait_result").toLong()==-10L && at==es.size)
    val label=if(stock) "stock" else "arm_$arm"
    println("${label}_observer = \"verified\""); println("${label}_responses = $count"); println("${label}_initial_threads = ${initial.size}"); println("${label}_terminal_threads = ${live.size}"); println("${label}_clone_events = ${clones.size}")
    if(oneWrite) println("${label}_modeled_writes = $writes")
    if(continuation) { val f=requireNotNull(unsupported); val r=requireNotNull(unsupportedRegs)
        println("${label}_unsupported_offset = \"${f.s("offset")}\""); println("${label}_unsupported_tid = \"${f.s("tid")}\""); println("${label}_unsupported_pc = \"0x${(r.pc-base).toString(16)}\""); println("${label}_unsupported_opcode = \"${f.s("opcode")}\""); println("${label}_unsupported_x09 = \"0x${r.x[9].toString(16)}\"")
    }
    if(positive) println("${label}_global_value = \"0x0123456789abcdef\"")
}
if(args.size==1 || stock) {
    for(line in Files.readAllLines(run.resolve("evidence-sha256.txt"))) { require(line.length>66); val file=Path.of(line.substring(66)).normalize(); require(file.startsWith(run) && hash(file)==line.take(64)) }
    if(stock) {
        require(text("result.toml").contains("mode = \"spumodel\""))
        for(script in listOf("VerifySnapshot.main.kts","VerifyNative.main.kts")) {
            val verifier=if(script=="VerifyNative.main.kts" && args.size==3) Path.of(args[2]).toAbsolutePath().normalize() else run.resolve("source/$script")
            if(script=="VerifyNative.main.kts") println("admission_verifier_sha256 = \"${hash(verifier)}\"")
            val command=mutableListOf("kotlin",verifier.toString(),run.toString()); if(script=="VerifyNative.main.kts") command.add(if(stockNext) "admission-next-access" else "admission-only")
            val p=ProcessBuilder(command).redirectErrorStream(true).start(); val output=p.inputStream.bufferedReader().readText(); require(p.waitFor()==0) { "$script failed: $output" }; print(output)
        }
        require(text("native-final-enforcing.txt").trim()=="Enforcing")
        val finalPid=text("native-final-system-server.txt").trim().toInt(); require(text("system-server-pid.toml").lineSequence().filter { it.isNotBlank() }.all { it.substringAfter("= ").toInt()==finalPid })
    } else {
        require(text("result.toml").contains("mode = \"spucontrol\"") && text("result.toml").contains("inspection = \"completed\""))
        require(text("group-packages.txt").isBlank() && !text("group-processes-after.txt").contains("group-observer"))
        require(text("group-enforcing.txt").lineSequence().filter { it.isNotBlank() }.toList()==listOf("Enforcing","Enforcing"))
        val pids=text("group-system-server.toml").lineSequence().filter { it.isNotBlank() }.map { it.substringAfter("= ").toInt() }.toList(); require(pids.size==28 && pids.distinct().size==1)
        require(hash(run.resolve("group-invalid.elf"))==binaryHash)
        for(name in listOf("magic","version","profile","count","reference-count","reserved","truncated","trailing","oversized","binding","table-count","width","offset")) {
            require(text("adc-invalid-$name-status.toml").trim()=="exit_code = 2")
            val rejection=events("adc-invalid-$name.toml")
            require(rejection.size==1 && rejection.single().kind=="transcript-input-rejected")
        }
        for(arm in 0..12) {
            val p=ProcessBuilder("kotlin",run.resolve("source/VerifyGroupObserver.main.kts").toString(),run.toString(),arm.toString()).redirectErrorStream(true).start()
            val output=p.inputStream.bufferedReader().readText(); require(p.waitFor()==0) { "Legacy arm $arm failed: $output" }
        }
        for(arm in 13..24) {
            val p=ProcessBuilder("kotlin",run.resolve("source/VerifyAdcObserver.main.kts").toString(),run.toString(),arm.toString()).redirectErrorStream(true).start()
            val output=p.inputStream.bufferedReader().readText(); require(p.waitFor()==0) { "ADC regression $arm failed: $output" }
        }
        require(text("spu-packages.txt").isBlank() && !text("spu-processes-after.txt").contains("group-observer"))
        require(text("spu-enforcing.txt").lineSequence().filter { it.isNotBlank() }.toList()==listOf("Enforcing","Enforcing"))
        val spuPids=text("spu-system-server.toml").lineSequence().filter { it.isNotBlank() }.map { it.substringAfter("= ").toInt() }.toList()
        require(spuPids.size==17 && spuPids.all { it==pids.first() })
        require(hash(run.resolve("spu-invalid.elf"))==binaryHash)
        for(name in listOf("magic","version","profile","count","reserved","binding","global","derived","series-pointer","series-config-pointer","sample","shadow","terminal-shadow","offset","operand","truncated","trailing")) {
            require(text("spu-invalid-$name-status.toml").trim()=="exit_code = 2")
            val rejection=events("spu-invalid-$name.toml")
            require(rejection.size==3 && rejection.map { it.kind }==listOf("transcript-input","transcript-input-accepted","spu-input-rejected"))
        }
        println("system_server_pid = ${pids.first()}"); println("stock_application_run = false")
    }
    println("evidence_index = \"verified\"")
}
