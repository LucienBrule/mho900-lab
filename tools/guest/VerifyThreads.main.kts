// Independent local evidence checks for the private thread-observer controls.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size in 1..2) { "Usage: VerifyThreads.main.kts RUN_DIRECTORY [ARM]" }
val run=Path.of(args[0]).toAbsolutePath().normalize()
fun text(name:String)=Files.readString(run.resolve(name))
fun hash(bytes:ByteArray)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))
fun hash(file:Path)=hash(Files.readAllBytes(file))
val elf=Files.readAllBytes(run.resolve("thread-control.elf"))
require(hash(elf)==text("binary-sha256.txt").take(64))
fun u16(at:Int)=ByteBuffer.wrap(elf,at,2).order(ByteOrder.LITTLE_ENDIAN).short.toUShort().toInt()
fun u32(at:Int)=ByteBuffer.wrap(elf,at,4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong()
fun u64(at:Int)=ByteBuffer.wrap(elf,at,8).order(ByteOrder.LITTLE_ENDIAN).long.toULong()
require(elf.take(6)==listOf(127,69,76,70,2,1).map { it.toByte() } && u16(18)==183)
data class Segment(val offset:ULong,val address:ULong,val size:ULong,val flags:ULong)
val segments=(0 until u16(56)).map { u64(32).toInt()+it*u16(54) }.filter { u32(it)==1uL }.map { Segment(u64(it+8),u64(it+16),u64(it+32),u32(it+4)) }
fun word(address:ULong):ULong {
    val s=segments.single { it.flags and 1uL!=0uL && address>=it.address && address+4uL<=it.address+it.size }
    return u32((s.offset+address-s.address).toInt())
}
enum class Kind(val label:String) {
    SETUP("setup"),SEIZE("seize"),INITIAL("initial-stop"),THREAD("thread-status"),INVENTORY("thread-inventory"),
    RELEASE("release"),WAIT("wait"),CLONE("clone"),NEW("new-thread-stop"),FAULT("mapped-fault"),
    REGISTERS("fault-registers"),RESPONSE("response-registers"),TERMINAL("terminal"),REAPED("reaped"),CLEANUP("cleanup")
}
data class Event(val kind:Kind,val fields:Map<String,String>) {
    fun s(key:String)=fields.getValue(key)
    fun u(key:String)=s(key).removePrefix("0x").toULong(16)
}
fun events(name:String):List<Event> = text(name).split("[[events]]").drop(1).map {
    val pairs=it.lineSequence().filter { it.isNotBlank() }.map {
        val p=it.split(" = ",limit=2); require(p.size==2); p[0] to p[1].removeSurrounding("\"")
    }.toList()
    require(pairs.map { it.first }.distinct().size==pairs.size)
    val f=pairs.toMap(); Event(Kind.entries.single { it.label==f.getValue("kind") },f)
}
data class Registers(val tid:ULong,val pc:ULong,val sp:ULong,val pstate:ULong,val x:List<ULong>)
fun registers(e:Event)=Registers(e.u("tid"),e.u("pc"),e.u("sp"),e.u("pstate"),(0..30).map { e.u("x"+it.toString().padStart(2,'0')) })
val arms=if(args.size==2) listOf(args[1].toInt().also { require(it in 0..2) }) else listOf(0,1,2)
for(arm in arms) {
    require(text("thread-$arm-status.toml").trim()=="exit_code = 0")
    require(hash(run.resolve("thread-$arm.elf"))==hash(elf))
    val events=events("thread-$arm.toml"); var at=0; var waitIndex=0uL
    fun take(kind:Kind):Event = events[at++].also { require(it.kind==kind) { "arm $arm event ${at-1}: expected $kind, got ${it.kind}" } }
    val setup=take(Kind.SETUP); require(setup.u("arm")==arm.toULong())
    val pid=setup.u("pid"); val worker=setup.u("existing_tid"); val observer=setup.u("observer_pid"); val mapping=setup.u("mapping")
    require(setOf(pid,worker,observer).size==3 && listOf(pid,worker,observer).all { it>0uL })
    require(mapping>0uL && mapping and 4095uL==0uL && setup.u("mapping_length")==0x1000000uL && setup.u("clone_flags")==0x10f00uL)
    val firstPc=setup.u("first_pc"); val secondPc=setup.u("second_pc"); val writePc=setup.u("write_pc")
    require(word(firstPc)==0xb9400109uL && word(secondPc)==0xb9400109uL && word(writePc)==0xb9000109uL)
    for(tid in listOf(pid,worker)) {
        val s=take(Kind.SEIZE); require(s.u("tid")==tid && s.u("options")==0x100008uL && s.u("result")==0uL)
    }
    fun thread(phase:String,tid:ULong?=null):Event {
        val t=take(Kind.THREAD); require(t.s("phase")==phase && "read_error" !in t.fields)
        require(t.u("tgid")==pid && t.u("tracer_pid")==observer && t.u("state")>0uL)
        if(tid!=null) require(t.u("tid")==tid)
        return t
    }
    for(tid in listOf(pid,worker)) {
        val i=take(Kind.INITIAL); require(i.u("tid")==tid && i.u("status")==0x80057fuL)
        require(thread("initial",tid).u("state")==0x74uL)
    }
    fun inventory(phase:String,tids:Set<ULong>,stopping:ULong) {
        val ts=tids.indices.map { thread(phase) }
        require(ts.map { it.u("tid") }.toSet()==tids)
        require(ts.single { it.u("tid")==stopping }.u("state")==0x74uL)
        val i=take(Kind.INVENTORY)
        require(i.s("phase")==phase && i.u("pid")==pid && i.u("observer_pid")==observer && i.u("stopping_tid")==stopping)
        require(i.u("observed_count")==tids.size.toULong() && i.u("overflow")==0uL && i.u("error")==0uL)
        require(i.u("directory_flags")==0x4000uL && i.u("error_operation")==0uL && i.u("error_result")==0uL)
    }
    inventory("covered",setOf(pid,worker),pid)
    require(take(Kind.RELEASE).u("covered_threads")==2uL)
    fun wait(tid:ULong,status:ULong) {
        val w=take(Kind.WAIT); require(w.u("index")==waitIndex++ && w.u("tid")==tid && w.u("status")==status)
    }
    fun fault(tid:ULong,offset:ULong,pc:ULong,opcode:ULong,responses:ULong):Registers {
        wait(tid,0xb7fuL)
        val f=take(Kind.FAULT)
        require(f.u("tid")==tid && f.u("signal")==11uL && f.u("si_code")==2uL && f.u("offset")==offset)
        require(f.u("address")==mapping+offset && f.u("opcode")==opcode && f.u("responses")==responses)
        val r=registers(take(Kind.REGISTERS))
        require(r.tid==tid && r.pc==pc && word(r.pc)==opcode && r.x[8]==mapping+offset && r.sp>0uL && r.sp and 15uL==0uL)
        return r
    }
    val before=fault(worker,if(arm==1) 0x4040uL else 0x4048uL,firstPc,0xb9400109uL,0uL)
    var newTid:ULong?=null
    if(arm!=1) {
        val after=registers(take(Kind.RESPONSE))
        require(after.tid==worker && after.pc==before.pc+4uL && after.sp==before.sp && after.pstate==before.pstate)
        require(after.x[9]==0x11223344uL && (0..30).filter { it!=9 }.all { after.x[it]==before.x[it] })
        val nextEvents=events.drop(at).takeWhile { it.kind!=Kind.FAULT }
        val clone=nextEvents.single { it.kind==Kind.CLONE }; newTid=clone.u("new_tid")
        require(newTid>0uL && newTid !in setOf(pid,worker,observer))
        var sawClone=false; var sawStart=false
        repeat(2) {
            val w=events[at]; require(w.kind==Kind.WAIT)
            if(w.u("tid")==pid) {
                require(!sawClone); wait(pid,0x3057fuL); val c=take(Kind.CLONE)
                require(c.u("parent_tid")==pid && c.u("new_tid")==newTid && c.u("shared_result")==0x11223344uL && c.u("completed")==1uL)
                sawClone=true
            } else {
                require(!sawStart); wait(newTid,0x80057fuL); val n=take(Kind.NEW)
                require(n.u("tid")==newTid && n.u("status")==0x80057fuL)
                require(thread("new-thread",newTid).u("state")==0x74uL); sawStart=true
            }
        }
        require(sawClone && sawStart)
        val terminal=fault(newTid,0x4044uL,if(arm==2) writePc else secondPc,if(arm==2) 0xb9000109uL else 0xb9400109uL,1uL)
        if(arm==2) require(terminal.x[9]==0x55uL)
    }
    val terminal=take(Kind.TERMINAL); val stopping=newTid?:worker
    require(terminal.u("tid")==stopping && terminal.u("responses")==if(arm==1) 0uL else 1uL)
    require(terminal.u("new_started")==if(arm==1) 0uL else 1uL)
    require(terminal.u("completed")==if(arm==1) 0uL else 1uL)
    require(terminal.u("shared_result")==if(arm==1) ULong.MAX_VALUE else 0x11223344uL)
    val tids=if(newTid==null) setOf(pid,worker) else setOf(pid,worker,newTid)
    inventory("terminal",tids,stopping)
    val reaped=tids.indices.map { take(Kind.REAPED) }
    require(reaped.map { it.u("tid") }.toSet()==tids && reaped.all { it.u("status")==9uL })
    val cleanup=take(Kind.CLEANUP)
    require(cleanup.u("reaped_count")==tids.size.toULong() && cleanup.u("expected_count")==tids.size.toULong() && cleanup.u("wait_result").toLong()==-10L)
    require(at==events.size && waitIndex<=32uL)
    println("arm_$arm = \"verified\"")
    println("arm_${arm}_responses = ${if(arm==1) 0 else 1}")
    println("arm_${arm}_threads = ${tids.size}")
}
if(args.size==1) {
    for(line in Files.readAllLines(run.resolve("evidence-sha256.txt"))) {
        require(line.length>66); val artifact=Path.of(line.substring(66)).normalize()
        require(artifact.startsWith(run) && hash(artifact)==line.take(64))
    }
    require(text("result.toml").contains("mode = \"threads\"") && text("result.toml").contains("inspection = \"completed\""))
    require(text("thread-packages.txt").isBlank())
    require(text("thread-enforcing.txt").lineSequence().filter { it.isNotBlank() }.toList()==listOf("Enforcing","Enforcing"))
    val pids=text("thread-system-server.toml").lineSequence().filter { it.isNotBlank() }.map { it.substringAfter("= ").toInt() }.toList()
    require(pids.size==5 && pids.distinct().size==1)
    require(!text("thread-processes-after.txt").contains("/data/local/tmp/thread-control"))
    println("system_server_pid = ${pids.singleOrNull()?:pids.first()}")
    println("stock_application_run = false")
    println("evidence_index = \"verified\"")
}
