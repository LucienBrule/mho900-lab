// Adjudicate the preserved initial redundant-clear negative without accepting it as a control pass.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
import java.nio.ByteBuffer
import java.nio.ByteOrder
require(args.size==1){"Usage: VerifyInitTailClearNegative.main.kts RUN_DIRECTORY"}
val run=Path.of(args[0]).toAbsolutePath().normalize()
fun bytes(name:String)=Files.readAllBytes(run.resolve(name));fun text(name:String)=Files.readString(run.resolve(name))
fun hash(b:ByteArray)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b));fun hash(name:String)=hash(bytes(name))
data class E(val kind:String,val f:Map<String,String>){fun s(k:String)=f.getValue(k);fun u(k:String)=s(k).removePrefix("0x").toULong(16)}
fun events(name:String)=text(name).split("[[events]]").drop(1).map{block->val pairs=block.lineSequence().filter{it.isNotBlank()}.map{line->val p=line.split(" = ",limit=2);require(p.size==2){"bad event line"};p[0] to p[1].removeSurrounding("\"")}.toList();require(pairs.map{it.first}.distinct().size==pairs.size);val f=pairs.toMap();E(f.getValue("kind"),f)}
data class R(val tid:ULong,val pc:ULong,val relative:ULong,val sp:ULong,val pstate:ULong,val x:List<ULong>)
fun regs(e:E)=R(e.u("tid"),e.u("pc"),e.u("relative_pc"),e.u("sp"),e.u("pstate"),(0..30).map{e.u("x"+it.toString().padStart(2,'0'))})
fun same(a:R,b:R)=a.tid==b.tid&&a.pc==b.pc&&a.sp==b.sp&&a.pstate==b.pstate&&a.x==b.x
fun completed(before:R,after:R,readValue:ULong?):Boolean { if(before.tid!=after.tid||after.pc!=before.pc+4uL||after.sp!=before.sp||after.pstate!=before.pstate)return false;return (0..30).all{i->after.x[i]==if(i==9&&readValue!=null)readValue else before.x[i]} }
data class Seg(val off:ULong,val va:ULong,val size:ULong,val flags:ULong)
class Elf(val b:ByteArray){fun u16(i:Int)=ByteBuffer.wrap(b,i,2).order(ByteOrder.LITTLE_ENDIAN).short.toUShort().toInt();fun u32(i:Int)=ByteBuffer.wrap(b,i,4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong();fun u64(i:Int)=ByteBuffer.wrap(b,i,8).order(ByteOrder.LITTLE_ENDIAN).long.toULong();val segs:List<Seg>
 init{require(b.take(6)==listOf(127,69,76,70,2,1).map{it.toByte()}&&u16(18)==183);segs=(0 until u16(56)).map{u64(32).toInt()+it*u16(54)}.filter{u32(it)==1uL}.map{Seg(u64(it+8),u64(it+16),u64(it+32),u32(it+4))}}
 fun word(va:ULong):ULong{val s=segs.single{va>=it.va&&va+4uL<=it.va+it.size};return u32((s.off+va-s.va).toInt())}
 fun symbol(name:String):ULong{val hs=(0 until u16(60)).map{u64(40).toInt()+it*u16(58)};val tab=hs.single{u32(it+4)==2uL};val strings=hs[u32(tab+40).toInt()];val matches=(0 until(u64(tab+32)/u64(tab+56)).toInt()).map{i->val p=u64(tab+24).toInt()+i*u64(tab+56).toInt();val a=u64(strings+24).toInt()+u32(p).toInt();var z=a;while(b[z]!=0.toByte())z++;String(b,a,z-a) to u64(p+8)}.filter{it.first==name};return matches.single().second}}

val nativeHash="e56d8a929de3455f5adb0aa14e9fed4d8c65eb2ebca9658b01c8f79216bb4d83"
require(hash("group-control.elf")==nativeHash&&hash("tail-59.elf")==nativeHash)
val elf=Elf(bytes("group-control.elf"))
require(text("tail-59-status.toml").trim()=="exit_code = 78")
require(text("result.toml").contains("inspection = \"failed\"")&&text("result.toml").contains("mode = \"tailcontrol\""))
require(!Files.exists(run.resolve("tail-60.toml")))
val es=events("tail-59.toml")
val mode=es.single{it.kind=="model-mode"};require(mode.s("scope")=="private"&&mode.u("arm")==59uL&&mode.u("tail")==1uL)
val b=es.single{it.kind=="model-binding"};val pid=b.u("pid");val shared=b.u("object")-48uL
val observer=es.single{it.kind=="ready"}.u("observer_pid")
val mapping=es.single{it.kind=="mapping-result"}.u("base")
require(shared and 4095uL==0uL&&mapping>0uL)
val oracle=Files.readAllLines(run.resolve("reference.tsv")).drop(1).map{it.split('\t')[6].removePrefix("0x").toULong(16)}
require(hash("reference.tsv")=="6b9f7b8cdfba8d99fa720b2771cd741f285a05d5f9a77f0aa7173fbf5a2e39c9")
require(hash("spu-private.bin")=="d55b7d70b4bcd1e3e95cd48fc7a7e791c2a16fc52cea32398b3799b94fb7aac6")
val spu=ByteBuffer.wrap(bytes("spu-private.bin")).order(ByteOrder.LITTLE_ENDIAN)
fun word(at:Int)=spu.getInt(at).toUInt().toULong()
val offsets=List(452){0x3000uL}+(0..7).map{word(1000+8*it)}+listOf(0x4004uL,0x4004uL,0x7034uL,0x7034uL)
val values=oracle+(0..7).map{word(1004+8*it)}+listOf(0x80000000uL,0uL,1uL,0uL)
val writes=es.filter{it.kind=="modeled-write"};require(writes.size==464)
for((i,e) in writes.withIndex()){
 require(e.u("index")==i.toULong()&&e.u("tid")==pid&&e.u("offset")==offsets[i]&&e.u("value")==values[i]&&e.u("width")==4uL)
 val p=es.indexOf(e);val before=regs(es.take(p).last{it.kind=="fault-registers"});val after=regs(es.subList(p+1,p+5).first{it.kind=="write-registers"})
 require(before.pc==elf.symbol("gm_write_pc")&&before.x[8]==mapping+offsets[i]&&before.x[9].toUInt().toULong()==values[i]&&completed(before,after,null))
}
require(es.filter{it.kind=="modeled-read"}.map{it.u("value")}==listOf(0xe1234567uL,0x89abcdefuL))
require(es.filter{it.kind=="remaining-checkpoint"}.map{it.u("index")}==(0..9).map{it.toULong()})
require(es.filter{it.kind=="remaining-checkpoint-guard"}.let{it.size==10&&it.all{g->g.u("match")==1uL}})
val slots=listOf(0xb78790uL,0xb7bb08uL,0xb7fb88uL,0xb83f18uL,0xb845c0uL,0xb86148uL,0xb86690uL,0xb86758uL,0xb86f98uL,0xb870a0uL,0xb87630uL,0xb883b8uL,0xb89e08uL,0xb8d288uL,0xb8de08uL,0xb8e118uL)
val targets=listOf("gm_tail_private","gm_tail_private","gm_write","gm_tail_private","gm_tail_private","gm_tail_private","gm_write","gm_tail_private","gm_tail_private","gm_tail_private","gm_tail_private","gm_first","gm_tail_private").map{elf.symbol(it)}+listOf(shared+2988uL,shared+2996uL,shared+2984uL)
val bindings=es.filter{it.kind=="tail-binding"};require(bindings.size==16)
bindings.forEachIndexed{i,e->require(e.s("phase")=="initial"&&e.u("index")==i.toULong()&&e.u("slot")==slots[i]&&e.u("actual_target")==targets[i]&&e.u("expected_target")==targets[i]&&e.u("match")==1uL)}
val states=es.filter{it.kind=="tail-state"};require(states.map{it.u("index")}==listOf(7uL,0uL,1uL,2uL,3uL,4uL,5uL,6uL))
val stateValues=listOf(0uL,0uL,8uL,900uL,8uL,900uL,1uL,shared+2848uL)
val stateObjects=listOf(2984uL,2988uL,1200uL,1204uL,1276uL,1280uL,2848uL,1300uL)
for(e in states){val i=e.u("index").toInt();require(e.s("phase")=="initial"&&e.u("actual")==stateValues[i]&&e.u("expected")==stateValues[i]&&e.u("object")==shared+stateObjects[i]&&e.u("match")==1uL)}
val names=listOf("tail-debug-before","tail-debug-clear-request","tail-debug-clear-set","tail-debug-clear-after","tail-rejected","tail-summary")
require(es.filter{it.kind.startsWith("tail-")&&it.kind !in setOf("tail-mode","tail-binding","tail-state")}.map{it.kind}==names)
fun dump(kind:String,size:ULong,control:ULong){val e=es.single{it.kind==kind};require(e.u("result")==0uL&&e.u("size")==size&&e.u("info")==0x606uL);for(i in 0..15){val n=i.toString().padStart(2,'0');require(e.u("a$n")==0uL&&e.u("c$n")==if(i==0)control else 0uL)}}
dump("tail-debug-before",264uL,0x1e5uL);dump("tail-debug-clear-request",24uL,0uL);dump("tail-debug-clear-after",264uL,0x1e5uL)
require(es.single{it.kind=="tail-debug-clear-set"}.u("result")==0uL)
val rejection=es.single{it.kind=="tail-rejected"};require(rejection.s("reason")=="debug-initial"&&rejection.s("stage")=="initial"&&rejection.u("tid")==pid&&rejection.u("actual")==0uL&&rejection.u("expected")==1uL)
for(k in listOf("reads","writes","checkpoint"))require(rejection.u(k)==0uL)
val lastFault=es.last{it.kind=="mapped-fault"};val faultRegs=regs(es.last{it.kind=="fault-registers"})
require(lastFault.u("tid")==pid&&lastFault.u("signal")==11uL&&lastFault.u("si_code")==2uL&&lastFault.u("offset")==4uL&&lastFault.u("address")==mapping+4uL&&lastFault.u("opcode")==0xb9400109uL)
require(faultRegs.pc==elf.symbol("gm_first_pc")&&faultRegs.x[8]==mapping+4uL)
val summary=es.single{it.kind=="tail-summary"};require(summary.u("private_metrics")==1uL&&summary.u("total_writes")==464uL)
for(k in listOf("reads","writes","checkpoints","atomic","calibration_executed","old_executed","clone_tid"))require(summary.u(k)==0uL)
val terminal=es.single{it.kind=="terminal-state"};require(terminal.u("responses")==2uL&&terminal.u("modeled_writes")==464uL&&terminal.u("value")==0x0123456789abcdefuL)
val tracked=es.filter{it.kind=="group-track"}.map{it.u("tid")};require(tracked.size==3&&tracked.toSet().size==3)
for(phase in listOf("before-ready","terminal")){
 val status=es.filter{it.kind=="thread-status"&&it.s("phase")==phase};require(status.size==if(phase=="terminal")3 else 2)
 require(status.all{"read_error" !in it.f&&it.u("tgid")==pid&&it.u("tracer_pid")==observer&&it.u("state")==0x74uL})
 if(phase=="terminal")require(status.map{it.u("tid")}.toSet()==tracked.toSet())
 val inventory=es.single{it.kind=="thread-inventory"&&it.s("phase")==phase};require(inventory.u("error")==0uL&&inventory.u("overflow")==0uL&&inventory.u("observed_count")==status.size.toULong())
}
val reaped=es.filter{it.kind=="group-reaped"};require(reaped.size==3&&reaped.map{it.u("tid")}.toSet()==tracked.toSet()&&reaped.all{it.u("status")==9uL})
val cleanup=es.last();require(cleanup.kind=="group-cleanup"&&cleanup.u("expected_count")==3uL&&cleanup.u("reaped_count")==3uL&&cleanup.u("wait_result").toLong()==-10L)
val pids=mutableListOf<Int>()
for((phase,n) in listOf("group" to 28,"spu" to 17,"remaining" to 20,"tail" to 2)){
 val ps=text("$phase-system-server.toml").lineSequence().filter{it.isNotBlank()}.map{it.substringAfter("= ").toInt()}.toList();require(ps.size==n);pids+=ps
 require(text("$phase-enforcing.txt").lineSequence().map{it.trim()}.filter{it.isNotBlank()}.toList()==listOf("Enforcing","Enforcing"))
 require(text("$phase-packages.txt").isBlank());require(listOf("Sparrow","frida","group-observer").none{it in text("$phase-processes-after.txt")})
}
require(pids.distinct().size==1)
val index=Files.readAllLines(run.resolve("evidence-sha256.txt"));for(line in index){val p=Path.of(line.substring(66)).normalize();require(p.startsWith(run)&&hash(Files.readAllBytes(p))==line.take(64))}
println("schema_version = \"mho900-lab.init-tail-clear-negative-verification/1\"\nresult = \"negative-evidence-verified\"\ncomplete_private_pass = false\ntail_responses = 0\nprefix_writes = 464\nreadback_control = 0x1e5\nreaped_threads = 3\nsystem_server_pid = ${pids.first()}\nsystem_server_samples = ${pids.size}\nindexed_artifacts = ${index.size}")
