// Offline verification of stock mapped-read responses and a precise post-store stop.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
import java.util.zip.ZipFile

require(args.size in 1..2) { "Usage: VerifyPostStore.main.kts RUN_DIRECTORY [controls|inventory-failure]" }
val run = Path.of(args[0]).toAbsolutePath().normalize()
val inventoryFailure = args.getOrNull(1) == "inventory-failure"
val controlsOnly = args.size == 2
require(args.size == 1 || args[1] == "controls" || inventoryFailure)
fun text(name: String) = Files.readString(run.resolve(name))
fun hash(bytes: ByteArray) = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))
fun hash(path: Path) = hash(Files.readAllBytes(path))
fun n(value: String) = value.removePrefix("0x").toULong(16)
fun status(name: String, expected: Int) = require(text(name).trim() == "exit_code = $expected")
fun fields(section: String): Map<String,String> {
    val pairs = section.lineSequence().filter { it.isNotBlank() }.map {
        val p = it.split(" = ", limit=2); require(p.size == 2); p[0] to p[1].removeSurrounding("\"")
    }.toList()
    require(pairs.map { it.first }.distinct().size == pairs.size)
    return pairs.toMap()
}
class Elf(val bytes: ByteArray) {
    data class Segment(val offset: ULong, val address: ULong, val size: ULong, val flags: ULong)
    fun u16(at: Int) = ByteBuffer.wrap(bytes,at,2).order(ByteOrder.LITTLE_ENDIAN).short.toUShort().toInt()
    fun u32(at: Int) = ByteBuffer.wrap(bytes,at,4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong()
    fun u64(at: Int) = ByteBuffer.wrap(bytes,at,8).order(ByteOrder.LITTLE_ENDIAN).long.toULong()
    val segments: List<Segment>
    init {
        require(bytes.take(6) == listOf(127,69,76,70,2,1).map { it.toByte() })
        require(u16(18)==183 && u16(16) in listOf(2,3))
        val start=u64(32).toInt(); val stride=u16(54)
        segments=(0 until u16(56)).map { start+it*stride }.filter { u32(it)==1uL }.map {
            Segment(u64(it+8),u64(it+16),u64(it+32),u32(it+4))
        }
    }
    fun word(address: ULong): ULong {
        val s=segments.single { it.flags and 1uL != 0uL && address>=it.address && address+4uL<=it.address+it.size }
        return u32((s.offset+address-s.address).toInt())
    }
}
sealed interface Event
data class Ready(val pid: ULong,val observer: ULong,val stopping: ULong): Event
data class Binding(val base: ULong,val mmapGot: ULong): Event
data class StoreBinding(val target: ULong,val opcode: ULong,val store: ULong,val storeOpcode: ULong,
    val got: ULong,val obj: ULong,val initial: ULong): Event
data class Open(val fd: ULong): Event
data class Request(val args: List<ULong>,val pc: ULong,val lr: ULong): Event
data class Mapping(val base: ULong,val protection: ULong): Event
data class Fault(val signal: ULong,val code: ULong,val address: ULong,val mapping: ULong,val offset: ULong,
    val pc: ULong,val relative: ULong,val opcode: ULong,val regs: List<ULong>): Event
data class Response(val value: ULong,val pcBefore: ULong,val pcAfter: ULong,val before: ULong,val after: ULong,
    val unchanged: ULong,val output: ULong): Event
data class Debug(val kind: String,val result: ULong,val size: ULong,val info: ULong,
    val addresses: List<ULong>,val controls: List<ULong>): Event
data class Profile(val id: String,val request: ULong,val readback: ULong): Event
data class DebugSet(val result: ULong): Event
data class Stop(val status: ULong,val signal: ULong,val code: ULong,val address: ULong,val observer: ULong,
    val tid: ULong,val pc: ULong,val relative: ULong,val opcode: ULong,val regs: List<ULong>): Event
data class Boundary(val expected: ULong,val target: ULong,val obj: ULong,val value: ULong,val observer: ULong,
    val tid: ULong,val x8: ULong,val x9: ULong,val expectedValue: ULong): Event
data class Thread(val phase: String,val tid: ULong,val tgid: ULong,val tracer: ULong,val state: ULong): Event
data class Inventory(val phase: String,val pid: ULong,val observer: ULong,val tid: ULong,val count: ULong,
    val overflow: ULong,val error: ULong): Event
data class Terminated(val status: ULong): Event
class Rejected: Event
fun events(name: String): List<Event> = text(name).split("[[events]]").drop(1).map {
    val f=fields(it); val kind=f.getValue("kind"); fun v(k:String)=n(f.getValue(k))
    fun regs()=(0..30).map { i->v("x"+i.toString().padStart(2,'0')) }
    when(kind) {
        "ready"->Ready(v("pid"),v("observer_pid"),v("stopping_tid"))
        "stock-binding"->Binding(v("base"),v("mmap_got"))
        "post-store-binding"->StoreBinding(v("target"),v("target_opcode"),v("store"),v("store_opcode"),v("got_slot"),v("object"),v("initial_value"))
        "open-result"->Open(v("fd"))
        "mmap-request"->Request((0..5).map { i->v("a$i") },v("pc"),v("lr"))
        "mapping-result"->Mapping(v("base"),v("protection"))
        "fault"->Fault(v("signal"),v("si_code"),v("address"),v("mapping"),v("offset"),v("pc"),v("relative_pc"),v("opcode"),regs())
        "synthetic-response"->Response(v("value"),v("pc_before"),v("pc_after"),v("destination_before"),v("destination_after"),v("other_registers_unchanged"),v("output_address"))
        "debug-before","debug-request","debug-after"->Debug(kind,v("result"),v("size"),v("info"),(0..15).map { i->v("a"+i.toString().padStart(2,'0')) },(0..15).map { i->v("c"+i.toString().padStart(2,'0')) })
        "debug-profile"->Profile(f.getValue("guest_profile"),v("requested_control"),v("expected_readback_control"))
        "debug-set"->DebugSet(v("result"))
        "post-store-stop"->Stop(v("status"),v("signal"),v("si_code"),v("address"),v("observer_pid"),v("stopping_tid"),v("pc"),v("relative_pc"),v("opcode"),regs())
        "post-store-boundary"->Boundary(v("expected_stop"),v("target"),v("object"),v("value"),v("observer_pid"),v("stopping_tid"),v("x8"),v("x9"),v("expected_value"))
        "thread-status"->{ require("read_error" !in f) { "Thread status read failed" }; Thread(f.getValue("phase"),v("tid"),v("tgid"),v("tracer_pid"),v("state")) }
        "thread-inventory"->Inventory(f.getValue("phase"),v("pid"),v("observer_pid"),v("stopping_tid"),v("observed_count"),v("overflow"),v("error"))
        "terminated"->Terminated(v("status"))
        "response-guard-rejected"->Rejected()
        else->error("Unexpected event: $kind")
    }
}
val controlBytes=Files.readAllBytes(run.resolve("native-probe.elf"))
require(hash(controlBytes)==text("binary-sha256.txt").take(64))
val control=Elf(controlBytes)
fun common(r: List<Event>) {
    val ready=r.filterIsInstance<Ready>().single(); require(ready.pid>0uL && ready.observer>0uL && ready.stopping==ready.pid)
    val open=r.filterIsInstance<Open>().single(); val q=r.filterIsInstance<Request>().single()
    require(open.fd<0x7fffffffUL && q.args==listOf(0uL,0x1000000uL,3uL,1uL,open.fd,0uL))
    val m=r.filterIsInstance<Mapping>().single(); require(m.base>0uL && m.protection==0uL)
    for(f in r.filterIsInstance<Fault>()) {
        require(f.signal==11uL && f.code==2uL && f.mapping==m.base && f.address==m.base+f.offset)
        require(f.opcode and 0x3f800000uL==0x39000000uL)
        val width=1uL shl (f.opcode shr 30).toInt(); val register=((f.opcode shr 5) and 31uL).toInt()
        require(register<31 && width in listOf(4uL,8uL) && f.offset+width<=0x1000000uL)
        require(f.address==f.regs[register]+((f.opcode shr 10) and 4095uL)*width)
    }
}
fun inventories(r: List<Event>,private: Boolean) {
    val ready=r.filterIsInstance<Ready>().single(); val all=r.filterIsInstance<Inventory>()
    require(all.map { it.phase }==listOf("before-ready","terminal"))
    for(g in all) {
        require(g.pid==ready.pid && g.tid==ready.pid && g.observer==ready.observer && g.overflow==0uL)
        val ts=r.filterIsInstance<Thread>().filter { it.phase==g.phase }
        require(ts.size.toULong()==g.count && ts.map { it.tid }.distinct().size==ts.size)
        if(inventoryFailure) require(g.error==1uL && g.count==0uL && ts.isEmpty())
        else require(g.error==0uL && g.count in 1uL..128uL)
        if(private && !inventoryFailure) require(ts.size==1)
        require(ts.all { it.tgid==ready.pid && it.state>0uL && it.tracer==if(it.tid==ready.pid) ready.observer else 0uL })
        if(!inventoryFailure) require(ts.single { it.tid==ready.pid }.state in listOf(0x54uL,0x74uL))
        val at=r.indexOf(g); require(at>=ts.size && r.subList(at-ts.size,at)==ts)
    }
    require(r.filterIsInstance<Thread>().all { it.phase in listOf("before-ready","terminal") })
    require(r.indexOf(all[0])+1==r.indexOf(ready))
    require(r.indexOf(all[1])+1==r.lastIndex && r.last() is Terminated)
    require((r.last() as Terminated).status==9uL)
}
fun response(f: Fault,s: Response,value: ULong) {
    require(f.opcode and 0xffc0001fuL==0xb9400009uL)
    require(s.value==value && s.before==f.regs[9] && s.after==value && s.pcBefore==f.pc && s.pcAfter==f.pc+4uL && s.unchanged==1uL)
}
fun core(r: List<Event>)=r.filterNot { it is Thread || it is Inventory }
fun positive(r: List<Event>,elf: Elf,base: ULong,private: Boolean) {
    common(r); inventories(r,private)
    val fs=r.filterIsInstance<Fault>(); val rs=r.filterIsInstance<Response>(); require(fs.size==2 && rs.size==2)
    require(fs.map { it.offset }==listOf(0x4048uL,0x4044uL))
    response(fs[0],rs[0],0xe1234567uL); response(fs[1],rs[1],0x89abcdefuL)
    for(f in fs) require(elf.word(f.pc-base)==f.opcode)
    val ds=r.filterIsInstance<Debug>(); require(ds.map { it.kind }==listOf("debug-before","debug-request","debug-after"))
    require(ds.all { it.result==0uL && it.info==ds[0].info } && ds[0].info and 255uL != 0uL)
    require(ds.map { it.size }==listOf(264uL,24uL,264uL))
    require(ds[0].addresses.all { it==0uL } && ds[0].controls.all { it==0uL })
    require(ds.drop(1).all { d->d.addresses.drop(1).all { it==0uL } && d.controls.drop(1).all { it==0uL } })
    val profile=r.filterIsInstance<Profile>().single(); require(profile==Profile("cached-enable",0x1e5uL,0x1e4uL))
    val set=r.filterIsInstance<DebugSet>().single(); require(set.result==0uL)
    val stop=r.filterIsInstance<Stop>().single(); val b=r.filterIsInstance<Boundary>().single()
    val ready=r.filterIsInstance<Ready>().single()
    require(ds[1].addresses[0]==b.target && ds[2].addresses[0]==b.target && ds[1].controls[0]==0x1e5uL && ds[2].controls[0]==0x1e4uL)
    require(stop.status==0x57fuL && stop.signal==5uL && stop.code==4uL && stop.pc==b.target && stop.address==stop.pc)
    require(stop.observer==ready.observer && stop.tid==ready.pid && b.observer==ready.observer && b.tid==ready.pid)
    require(stop.opcode==elf.word(stop.pc-base) && b.x8==stop.regs[8] && b.x9==stop.regs[9])
    require(b.expected==1uL && b.value==0x0123456789abcdefuL && b.expectedValue==b.value)
    if(private) {
        require(stop.opcode==0xd503201fuL && stop.relative==0uL && b.x9==b.value && rs.all { it.output==b.obj })
        require(elf.word(stop.pc-12uL)==0xb3607d69uL && elf.word(stop.pc-8uL)==0x9240e129uL)
        require(elf.word(stop.pc-4uL) and 0xffc0001fuL==0xf9000009uL)
    } else {
        require(stop.relative==0x42a8f0uL && stop.pc==base+stop.relative && stop.opcode==0x14000001uL)
        require(fs.all { it.pc==base+0x270604uL && it.relative==0x270604uL && it.opcode==0xb9400109uL })
        val sb=r.filterIsInstance<StoreBinding>().single()
        require(sb.target==stop.pc && sb.opcode==stop.opcode && sb.store==base+0x42a8ecuL && sb.storeOpcode==elf.word(0x42a8ecuL))
        require(sb.storeOpcode==0xf9000128uL && sb.got==base+0xb8d758uL && sb.obj==base+0xbbccf0uL)
        require(b.obj==sb.obj && b.x8==b.value && b.x9==b.obj)
        require(r.filterIsInstance<Request>().single().lr==base+0x270284uL)
    }
    val prefix: List<Event> = if(private) emptyList() else listOf(r.filterIsInstance<Binding>().single(),r.filterIsInstance<StoreBinding>().single())
    val expected=prefix+listOf(ready,r.filterIsInstance<Open>().single(),r.filterIsInstance<Request>().single(),r.filterIsInstance<Mapping>().single(),
        fs[0],rs[0],fs[1],rs[1],ds[0],profile,ds[1],set,ds[2],stop,b,r.filterIsInstance<Terminated>().single())
    require(core(r)==expected) { "Unexpected event order" }
}
for(which in 0..3) {
    status("native-control-$which-status.toml",0); val r=events("native-control-$which.toml"); common(r)
    val f=r.filterIsInstance<Fault>().single(); require(r==listOf(r.filterIsInstance<Ready>().single(),r.filterIsInstance<Open>().single(),r.filterIsInstance<Request>().single(),r.filterIsInstance<Mapping>().single(),f))
    require(control.word(f.pc)==f.opcode && f.offset==0x4048uL)
    require(1uL shl (f.opcode shr 30).toInt()==if(which<2) 4uL else 8uL)
    require((f.opcode and 0x00400000uL!=0uL)==(which%2==0))
    if(which%2==1) require(f.regs[(f.opcode and 31uL).toInt()]==0x1122334455667788uL)
}
status("native-post-store-control-status.toml",0)
positive(events("native-post-store-control.toml"),control,0uL,true)
status("native-post-store-negative-status.toml",78)
val neg=events("native-post-store-negative.toml"); common(neg); inventories(neg,true)
val nf=neg.filterIsInstance<Fault>(); require(nf.size==2 && nf.map { it.offset }==listOf(0x4048uL,0x4040uL))
require(nf.all { control.word(it.pc)==it.opcode && it.opcode and 0xffc0001fuL==0xb9400009uL })
val nr=neg.filterIsInstance<Response>().single(); response(nf[0],nr,0xe1234567uL)
require(core(neg)==listOf(neg.filterIsInstance<Ready>().single(),neg.filterIsInstance<Open>().single(),neg.filterIsInstance<Request>().single(),neg.filterIsInstance<Mapping>().single(),nf[0],nr,nf[1],neg.filterIsInstance<Rejected>().single(),neg.filterIsInstance<Terminated>().single()))
println("private_post_store_controls = \"${if(inventoryFailure) "functional_capture_verified_inventory_failed" else "verified"}\"")
if(inventoryFailure) {
    status("native-helper-status.toml",3)
    for(name in listOf("native-events.toml","native-status.toml","native-app-pid.toml","native-before.txt","native-device.txt"))
        require(!Files.exists(run.resolve(name))) { "Unexpected stock observation: $name" }
    for(line in Files.readAllLines(run.resolve("evidence-sha256.txt"))) {
        require(line.length>66); val artifact=Path.of(line.substring(66)).normalize()
        require(artifact.startsWith(run) && hash(artifact)==line.take(64))
    }
    require(hash(run.resolve("installed.apk"))=="6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b")
    require(text("system-server-pid.toml").lineSequence().filter { it.isNotBlank() }.map { it.substringAfter("= ").toInt() }.toList().let { it.size==3 && it.distinct().size==1 })
    require(text("frida-detach-status.toml").trim()=="exit_code = 0")
    println("stock_device_responses = 0")
    println("stock_supervisor_started = false")
}
if(!controlsOnly) {
    // Reuse the captured admission verifier; its source and every input are in the sealed raw index.
    val p=ProcessBuilder("kotlin",run.resolve("source/VerifyNative.main.kts").toString(),run.toString(),"admission-only").redirectErrorStream(true).start()
    val output=p.inputStream.bufferedReader().readText(); require(p.waitFor()==0) { "Admission verification failed: $output" }; print(output)
    status("native-status.toml",0); status("native-helper-status.toml",0)
    require(hash(run.resolve("native-executed.elf"))==hash(controlBytes))
    require(text("result.toml").contains("mode = \"native\""))
    val apk=Files.readAllBytes(run.resolve("installed.apk"))
    require(hash(apk)=="6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b")
    val libraryName="lib/arm64-v8a/libscope-auklet.so"
    val lib=ZipFile(run.resolve("installed.apk").toFile()).use { z->z.getInputStream(z.getEntry(libraryName)).readBytes() }
    require(hash(lib)=="4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e")
    val elf=Elf(lib)
    fun a16(at:Int)=ByteBuffer.wrap(apk,at,2).order(ByteOrder.LITTLE_ENDIAN).short.toUShort().toInt()
    fun a32(at:Int)=ByteBuffer.wrap(apk,at,4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong()
    var at=0; var dataOffset: ULong?=null
    while(at+30<=apk.size && a32(at)==0x04034b50uL) {
        val nameSize=a16(at+26); val extra=a16(at+28); val data=at+30+nameSize+extra
        val name=apk.copyOfRange(at+30,at+30+nameSize).toString(Charsets.UTF_8)
        require(a16(at+6) and 8==0) { "ZIP descriptor requires explicit handling" }
        if(name==libraryName) { require(a16(at+8)==0); dataOffset=data.toULong(); break }
        at=data+a32(at+18).toInt()
    }
    val offset=requireNotNull(dataOffset)
    val r=events("native-events.toml"); val binding=r.filterIsInstance<Binding>().single()
    val maps=text("native-before.txt").lineSequence().map { it.trim().split(Regex("\\s+")) }.filter {
        it.size>=6 && it[1]=="r-xp" && it[2].toULongOrNull(16)==offset && it.last().endsWith("/base.apk")
    }.toList()
    val m=maps.single(); val range=m[0].split('-'); val seg=elf.segments.single { it.flags and 1uL!=0uL && it.offset==0uL }
    require(binding.base==range[0].toULong(16)-seg.address)
    require(binding.base+0x42a8f4uL<=range[1].toULong(16))
    val pid=n(text("native-app-pid.toml").substringAfter("= ").trim().toULong().toString(16))
    require(r.filterIsInstance<Ready>().single().pid==pid)
    positive(r,elf,binding.base,false)
    val sb=r.filterIsInstance<StoreBinding>().single()
    println("post_store_stock = \"verified\"")
    println("target_relative_pc = \"0x42a8f0\"")
    println("initial_global_value = \"0x${sb.initial.toString(16)}\"")
    println("final_global_value = \"0x0123456789abcdef\"")
    println("traced_threads = 1")
    for(i in r.filterIsInstance<Inventory>()) println("threads_${i.phase.replace('-','_')} = ${i.count}")
    println("process_wide_order_established = false")
}
