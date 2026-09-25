// Independent evidence verification for the bounded integrated thread-aware observer.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
import java.util.zip.ZipFile
require(args.size in 1..2) { "Usage: VerifyGroupObserver.main.kts RUN_DIRECTORY [0|1|2|3|4|stock|next-stock]" }
val run=Path.of(args[0]).toAbsolutePath().normalize()
val stock=args.getOrNull(1) in setOf("stock","next-stock")
val stockNext=args.getOrNull(1)=="next-stock"
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
}
data class R(val tid:ULong,val pc:ULong,val relative:ULong,val sp:ULong,val pstate:ULong,val x:List<ULong>)
fun regs(e:E)=R(e.u("tid"),e.u("pc"),e.u("relative_pc"),e.u("sp"),e.u("pstate"),(0..30).map { e.u("x"+it.toString().padStart(2,'0')) })
data class T(var stopped:Boolean,var confirmed:Boolean,var live:Boolean=true)
val binary=Files.readAllBytes(run.resolve("group-control.elf")); val binaryHash=hash(binary)
require(binaryHash==text("binary-sha256.txt").take(64)); val control=Elf(binary)
val arms=if(stock) listOf(-1) else if(args.size==2) listOf(args[1].toInt().also { require(it in 0..4) }) else if(continuationSuite) listOf(0,1,2,3,4) else listOf(0,1,2)
for(arm in arms) {
    val continuation=stockNext || arm in 3..4
    val positive=stock || arm==0 || continuation; val prefix=if(stock) "native" else "group-$arm"
    require(text("$prefix-status.toml").trim()=="exit_code = ${if(positive && !continuation) 0 else 78}")
    require(hash(run.resolve(if(stock) "group-executed.elf" else "group-$arm.elf"))==binaryHash)
    val es=events(if(stock) "native-events.toml" else "$prefix.toml")
    val mode=es[0]; require(mode.kind=="model-mode" && mode.s("scope")==if(stock) "stock" else "private")
    if(!stock) require(mode.u("arm")==arm.toULong())
    require((mode.f["continuation"]?.removePrefix("0x")?.toULong(16) ?: 0uL)==if(continuation) 1uL else 0uL)
    val setup=es[1]; require(setup.kind=="group-setup" && setup.u("options")==0x100009uL)
    val pid=setup.u("pid"); val observer=setup.u("observer_pid"); require(pid==mode.u("pid") && pid>1uL && observer>1uL && pid!=observer)
    require(setup.u("thread_limit")==128uL && setup.u("pass_limit")==16uL && setup.u("event_limit")==256uL && setup.u("deadline_ms")==10000uL)
    val coveredAt=es.indexOfFirst { it.kind=="group-covered" }; require(coveredAt>1)
    val pre=es.subList(2,coveredAt)
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
    val elf=if(stock) {
        require(hash(run.resolve("installed.apk"))=="6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b")
        val bytes=ZipFile(run.resolve("installed.apk").toFile()).use { z->z.getInputStream(z.getEntry("lib/arm64-v8a/libscope-auklet.so")).readBytes() }
        require(hash(bytes)=="4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e")
        Elf(bytes)
    } else { require(base==0uL); control }
    require(elf.word(binding.u("first_pc")-base)==0xb9400109uL && elf.word(binding.u("second_pc")-base)==0xb9400109uL)
    require(binding.u("store_pc")+4uL==target && binding.u("store_opcode")==0xf9000128uL && elf.word(binding.u("store_pc")-base)==binding.u("store_opcode"))
    require(elf.word(target-base)==binding.u("target_opcode") && binding.u("target_opcode")==if(stock) 0x14000001uL else 0xd503201fuL)
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
    var unsupported:E?=null; var unsupportedRegs:R?=null
    var pendingUnknown:ULong?=null; val identities=mutableSetOf<ULong>(); val confirmed=initial.toMutableSet(); val clones=mutableSetOf<ULong>()
    val resumesBeforeWait=mutableSetOf<ULong>(); var rejected=false; var boundary:E?=null; var stopRegs:R?=null; var terminalTid=0uL
    while(at<es.size && es[at].kind!="thread-status") {
        val e=es[at++]
        when(e.kind) {
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
                    if(!stock) { require(e.u("offset")==0x4040uL && r.x[8]==e.u("address") && e.u("opcode")==0xb9400109uL)
                        require(r.tid==if(arm==4) mode.u("fixture_worker") else pid)
                        require(r.pc==if(arm==4) binding.u("worker_pc") else binding.u("second_pc")) }
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
            "unsupported-access"->{
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
    if(!stock) { require(terminal.u("worker_ack")==1uL && clones==setOf(terminal.u("fixture_new_tid")) && tracked.size==3) }
    val live=tracked.filterValues { it.live }.keys; val reaped=mutableSetOf<ULong>()
    while(es[at].kind=="group-reaped") { val e=take("group-reaped"); require(e.u("tid") in live && reaped.add(e.u("tid")) && e.u("status")==9uL) }
    val cleanup=take("group-cleanup"); require(reaped==live && cleanup.u("expected_count")==live.size.toULong() && cleanup.u("reaped_count")==live.size.toULong() && cleanup.u("wait_result").toLong()==-10L && at==es.size)
    val label=if(stock) "stock" else "arm_$arm"
    println("${label}_observer = \"verified\""); println("${label}_responses = $count"); println("${label}_initial_threads = ${initial.size}"); println("${label}_terminal_threads = ${live.size}"); println("${label}_clone_events = ${clones.size}")
    if(continuation) { val f=requireNotNull(unsupported); val r=requireNotNull(unsupportedRegs)
        println("${label}_unsupported_offset = \"${f.s("offset")}\""); println("${label}_unsupported_tid = \"${f.s("tid")}\""); println("${label}_unsupported_pc = \"0x${(r.pc-base).toString(16)}\""); println("${label}_unsupported_opcode = \"${f.s("opcode")}\"")
    }
    if(positive) println("${label}_global_value = \"0x0123456789abcdef\"")
}
if(args.size==1 || stock) {
    for(line in Files.readAllLines(run.resolve("evidence-sha256.txt"))) { require(line.length>66); val file=Path.of(line.substring(66)).normalize(); require(file.startsWith(run) && hash(file)==line.take(64)) }
    if(stock) {
        require(text("result.toml").contains("mode = \"${if(stockNext) "nextmodel" else "groupmodel"}\""))
        for(script in listOf("VerifySnapshot.main.kts","VerifyNative.main.kts")) {
            val command=mutableListOf("kotlin",run.resolve("source/$script").toString(),run.toString()); if(script=="VerifyNative.main.kts") command.add("admission-only")
            val p=ProcessBuilder(command).redirectErrorStream(true).start(); val output=p.inputStream.bufferedReader().readText(); require(p.waitFor()==0) { "$script failed: $output" }; print(output)
        }
        require(text("native-final-enforcing.txt").trim()=="Enforcing")
        val finalPid=text("native-final-system-server.txt").trim().toInt(); require(text("system-server-pid.toml").lineSequence().filter { it.isNotBlank() }.all { it.substringAfter("= ").toInt()==finalPid })
    } else {
        require(text("result.toml").contains("mode = \"${if(continuationSuite) "nextcontrol" else "groupcontrol"}\"") && text("result.toml").contains("inspection = \"completed\""))
        require(text("group-packages.txt").isBlank() && !text("group-processes-after.txt").contains("group-observer"))
        require(text("group-enforcing.txt").lineSequence().filter { it.isNotBlank() }.toList()==listOf("Enforcing","Enforcing"))
        val pids=text("group-system-server.toml").lineSequence().filter { it.isNotBlank() }.map { it.substringAfter("= ").toInt() }.toList(); require(pids.size==(if(continuationSuite) 7 else 5) && pids.distinct().size==1)
        println("system_server_pid = ${pids.first()}"); println("stock_application_run = false")
    }
    println("evidence_index = \"verified\"")
}
