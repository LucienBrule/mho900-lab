// Independent verifier for the stock first-three calibration-loader observation.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
import java.util.zip.ZipFile

require(args.size==1){"Usage: VerifyStockCalibrationLoaders.main.kts RUN_DIRECTORY"}
val run=Path.of(args[0]).toAbsolutePath().normalize();val stock=true
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

val candidateHash="54554db2ff6e0948fcf4476d54ebde60877503f641c7eaac68e94cf4b1b19666"
val grammarHash="54c3cd02634e020c20c69b5f3aeee8990740eba5aed69628bbc15f7a36bbde1b"
val controlsHash="a4083d2cefc96508630c1dec05f4c9e1914afa294dca0d8c73b58d0a0b459e0b"
val handoffHash="05fa1d0ae6d771c5616cf09c2241d0ea282607c7b1a9e8caaf4d2b90402fc0cb"
val gateHash="230528f0afd95f219911ed1ff7382c77be6b34a4391a53d12b369f4d48338e66"
require(hash("tail-candidate.toml")==candidateHash&&hash("tail-grammar.toml")==grammarHash&&hash("tail-control-fixture.toml")==controlsHash&&hash("tail-handoff-profile.toml")==handoffHash&&hash("tail-stock-gate.toml")==gateHash){"tail artifact pin"}
require(hash("source/group-observer.c")=="0c070a8c1683cc2be45eb02cdf4b2ecdc0b50651f95b805edb81273ae5cb4a86")
require(hash("source/calibration-loaders.h")=="78320d758756a0c7483bd29caf916251e93ab66b5a3883c4415e3cce0d4fd548")
require(hash("source/VerifySnapshot.main.kts")=="983f369ff59f9c1b703c0d1c81a89522a06a8d56c2f238ad2aa5240a5cb6e86c")
require(hash("source/VerifyNative.main.kts")=="871292de7cdbb7e43004ae7dcee302ec5b9ff94d1f23c5a481de3403eeba58b1")
require(hash("source/VerifyCalibrationFilesystem.main.kts")=="6247912ee7ac1f9975a6154b8d414c1acaea64b23e1b9ef77b20c78b2d410228")
val stockInputs=text("source/calibration-stock-inputs.toml")
fun section(name:String):String { val marker="[$name]";val start=stockInputs.indexOf(marker);require(start>=0);val tail=stockInputs.substring(start+marker.length);val end=Regex("(?m)^\\[").find(tail)?.range?.first?:tail.length;return tail.substring(0,end) }
fun field(body:String,name:String)=Regex("(?m)^"+Regex.escape(name)+" = \\\"([^\\\"]+)\\\"$").find(body)?.groupValues?.get(1)?:error("missing $name")
val nativeInput=section("native")
require(field(nativeInput,"sha256")=="3c045ce88aeebf61da55e6026216995bbf562bf5ddd12560b9e4ce4296df40fa")
require(field(nativeInput,"source_sha256")=="0c070a8c1683cc2be45eb02cdf4b2ecdc0b50651f95b805edb81273ae5cb4a86")
require(field(nativeInput,"header_sha256")=="78320d758756a0c7483bd29caf916251e93ab66b5a3883c4415e3cce0d4fd548")
for(required in listOf("schema_version = \"mho900-lab.calibration-stock-inputs/1\"","task = \"TASK.guest.calibration-stock-loaders\"","task_contract = \"sha256:0b4b493549842ea82268d2debbdcc7a43078c88bc8544fdb86cd5f932c487a07\"","mode = \"loadermodel\"","run_id = \"stock-calibration-loaders-01\"","expected_statuses = [192, 1794240, -1]","terminal_relative_pc = 0x333ba8","terminal_opcode = 0x97fb9b9e","terminal_instruction_executes = false","new_modeled_mmio_responses = 0","adaptive_retry = false","profile = \"system-app-data\"","expected_directory_context = \"u:object_r:tmpfs:s0\"","original_file_context = \"u:object_r:su_tmpfs:s0\"","expected_file_context = \"u:object_r:system_app_data_file:s0\"","terminal_adc_equals_entry_required = true","terminal_whole_group_convergence_required = true"))require(required in stockInputs)
require(hash("calibration-loader-candidate.toml")=="6f84cda746319f02b701065bdbfe27b8e051d26b5b6a2eacba8309f85ae3dcb3")
val buildInputs=text("build-inputs.txt")
require(buildInputs.contains("0c070a8c1683cc2be45eb02cdf4b2ecdc0b50651f95b805edb81273ae5cb4a86")&&buildInputs.contains("78320d758756a0c7483bd29caf916251e93ab66b5a3883c4415e3cce0d4fd548"))
require(hash("build-inputs.txt")=="f07b5c3f6a226735527c719f3f87583b1c88aa62f9bdb354b7e4f65c350bfda1")
require(hash("binary-sha256.txt")=="f329040aeeee40e7d257d72bd0be0d11bf8921736e417c53e6414e796419b468")
val binaryDigest = Regex("([0-9a-f]{64})  .+").matchEntire(text("binary-sha256.txt").trim())
    ?.groupValues?.get(1) ?: error("invalid binary digest record")
fun expectFields(body: String, expected: Map<String, String>) {
    for ((key, value) in expected) {
        val rows = Regex("(?m)^" + Regex.escape(key) + " = (.+)$").findAll(body).toList()
        require(rows.size == 1 && rows.single().groupValues[1] == value) { "input contract: $key" }
    }
}
expectFields(stockInputs.substringBefore("\n["), mapOf(
    "mode" to "\"loadermodel\"", "run_id" to "\"stock-calibration-loaders-01\"",
    "expected_statuses" to "[192, 1794240, -1]", "terminal_relative_pc" to "0x333ba8",
    "terminal_opcode" to "0x97fb9b9e", "terminal_instruction_executes" to "false",
    "new_modeled_mmio_responses" to "0", "adaptive_retry" to "false", "physical_instrument_access" to "false"))
expectFields(section("derivative"), mapOf(
    "sha256" to "\"98b4925f73aa77cd21a6d4e2a3f384056dba8b2d379162ad2c02f55f3a071398\""))
expectFields(section("fixture"), mapOf(
    "profile" to "\"system-app-data\"", "policy_changed" to "false",
    "file_modes" to "\"0644\"", "directory_modes" to "\"0755\"",
    "expected_directory_context" to "\"u:object_r:tmpfs:s0\"",
    "original_file_context" to "\"u:object_r:su_tmpfs:s0\"",
    "expected_file_context" to "\"u:object_r:system_app_data_file:s0\""))
expectFields(section("observation"), mapOf(
    "entry_captures" to "[\"lsb\", \"adc\"]", "terminal_captures" to "[\"lsb\", \"adc\", \"vertical\"]",
    "entry_adc_zero_is_required" to "false", "terminal_adc_equals_entry_required" to "true",
    "terminal_whole_group_convergence_required" to "true"))
require(hash("fixture-ramdisk.img") == field(section("derivative"), "sha256"))

fun verify(){
 require(hash("group-control.elf")=="3c045ce88aeebf61da55e6026216995bbf562bf5ddd12560b9e4ce4296df40fa")
 val arm=-1;val prefix="native";require(text("native-status.toml").trim()=="exit_code = 78")
	 val binary=bytes("group-control.elf");require(hash(binary)=="3c045ce88aeebf61da55e6026216995bbf562bf5ddd12560b9e4ce4296df40fa"&&hash(binary)==binaryDigest);require(hash(if(stock)"group-executed.elf" else "tail-$arm.elf")==hash(binary));val control=Elf(binary)
	 val es=events(if(stock)"native-events.toml" else "$prefix.toml");require(es.isNotEmpty());val mode=es.single{it.kind=="model-mode"};require(mode.s("scope")=="stock"&&mode.u("continuation")==1uL&&mode.u("transcript")==1uL&&mode.u("spu")==1uL&&mode.u("remaining")==1uL&&mode.u("tail")==1uL&&mode.u("loaders")==1uL&&mode.u("profile")==1uL)
 val binding=es.single{it.kind=="model-binding"};val pid=binding.u("pid");val base=binding.u("base");val obj=binding.u("object");val shared=0uL;require(hash("installed.apk")=="6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b");val libraryBytes=ZipFile(run.resolve("installed.apk").toFile()).use{z->z.getInputStream(z.getEntry("lib/arm64-v8a/libscope-auklet.so")).readBytes()};require(hash(libraryBytes)=="4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e");val elf=Elf(libraryBytes);require(binding.u("target")==base+0x42a8f0uL&&obj==base+0xbbccf0uL&&binding.u("got_slot")==base+0xb8d758uL&&binding.u("first_pc")==base+0x270604uL&&binding.u("second_pc")==base+0x270604uL&&binding.u("write_pc")==base+0x27043cuL&&binding.u("write_opcode")==0xb9000109uL);require(pid==text("native-app-pid.toml").substringAfter("= ").trim().toULong());val executableMap=text("native-snapshot-maps.txt").lineSequence().map{it.trim().split(Regex("\\s+"))}.single{it.size>=6&&it[1]=="r-xp"&&it[2].toULong(16)==0xf05000uL&&it.last().endsWith("/base.apk")};val executableSegment=elf.segs.single{it.off==0uL&&it.flags and 1uL!=0uL};require(base==executableMap[0].substringBefore('-').toULong(16)-executableSegment.va)
 val readyEvent=es.single{it.kind=="ready"};val observer=readyEvent.u("observer_pid");require(readyEvent.u("pid")==pid&&readyEvent.u("stopping_tid")==pid)
 val input=es.single{it.kind=="transcript-input"};require(es.first()==input&&input.u("profile")==1uL&&input.u("write_count")==452uL&&input.u("total_size")==bytes("adc-stock.bin").size.toULong()&&input.u("table_count")==111uL&&input.u("binding_count")==11uL&&input.u("shadow_count")==2uL&&input.u("write_offset")==0x3000uL&&input.u("write_width")==4uL)
 val tailMode=es.single{it.kind=="tail-mode"};require(tailMode.s("debug_profile")=="inherited-direct-arm-v1"&&tailMode.u("read_count")==10uL&&tailMode.u("write_count")==2uL&&tailMode.u("checkpoint_count")==3uL&&tailMode.u("binding_count")==16uL&&tailMode.u("deadline_ms")==10000uL)
 // The inherited prefix is independently pinned by exact modeled read/write ledgers.
 require(es.take(4).map{it.kind}==listOf("transcript-input","transcript-input-accepted","spu-input","spu-input-accepted"))
 require(es.take(4).all{it.u("profile")==1uL})
 require(es[0].u("total_size")==bytes("adc-stock.bin").size.toULong()&&es[0].u("write_count")==452uL&&es[1].u("write_count")==452uL)
 require(es[0].u("table_count")==111uL&&es[0].u("binding_count")==11uL&&es[0].u("shadow_count")==2uL&&es[0].u("write_offset")==0x3000uL&&es[0].u("write_width")==4uL)
 require(es[2].u("total_size")==1064uL&&es[2].u("write_count")==8uL&&es[3].u("write_count")==8uL&&es[2].u("binding_count")==15uL&&es[2].u("series_count")==9uL&&es[2].u("sample_count")==3uL&&es[2].u("shadow_count")==4uL&&es[2].u("repeat_count")==2uL)
 require(hash("reference.tsv")=="6b9f7b8cdfba8d99fa720b2771cd741f285a05d5f9a77f0aa7173fbf5a2e39c9"&&hash("spu-stock.bin")=="34ee0cb515117c91adc89ed065a66628e8f52283d0863a4b7f87b6cfb23be9a6"&&hash("adc-stock.bin")=="42138210921f16b38a4627de3601cd9330bd413638bd96414e69a1a3d47592e7")
 val mappingEvent=es.single{it.kind=="mapping-result"};require(mappingEvent.u("protection")==0uL);val mapping=mappingEvent.u("base")
 val modeledReads=es.filter{it.kind=="modeled-read"};require(modeledReads.map{it.u("index") to it.u("value")}==listOf(0uL to 0xe1234567uL,1uL to 0x89abcdefuL));modeledReads.forEachIndexed{i,e->val p=es.indexOf(e);val fault=es.subList(0,p).last{it.kind=="mapped-fault"};val before=regs(es.subList(0,p).last{it.kind=="fault-registers"});val afterEvent=es.subList(p+1,(p+4).coerceAtMost(es.size)).first{it.kind=="response-registers"};val expectedOffset=listOf(0x4048uL,0x4044uL)[i];val expectedPc=binding.u(if(i==0)"first_pc" else "second_pc");require(fault.u("tid")==pid&&fault.u("signal")==11uL&&fault.u("si_code")==2uL&&fault.u("address")==mapping+expectedOffset&&fault.u("offset")==expectedOffset&&fault.u("opcode")==0xb9400109uL&&before.pc==expectedPc&&before.x[8]==fault.u("address")&&completed(before,regs(afterEvent),e.u("value")))}
 val modeledWrites=es.filter{it.kind=="modeled-write"};val tailWrites=es.filter{it.kind=="tail-write"};if(stock)require(tailWrites.size==2);val expectedTotal=466;require(modeledWrites.size==expectedTotal);require(modeledWrites.map{it.u("index")}==(0 until modeledWrites.size).map{it.toULong()});require(modeledWrites.all{it.u("tid")==pid&&it.u("width")==4uL})
 val oracle=Files.readAllLines(run.resolve("reference.tsv")).drop(1).mapIndexed{i,line->val f=line.split('\t');require(f.size==7&&f[0].toInt()==i);f[6].removePrefix("0x").toULong(16)};require(oracle.size==452);val spu=ByteBuffer.wrap(bytes(if(stock)"spu-stock.bin" else "spu-private.bin")).order(ByteOrder.LITTLE_ENDIAN);val su32:(Int)->ULong={i->spu.getInt(i).toUInt().toULong()};val prefixOffsets=List(452){0x3000uL}+(0..7).map{su32(1000+8*it)}+listOf(0x4004uL,0x4004uL,0x7034uL,0x7034uL);val prefixValues=oracle+(0..7).map{su32(1004+8*it)}+listOf(0x80000000uL,0uL,1uL,0uL);require(prefixOffsets.size==464);val prefixWritePc=base+0x27043cuL;modeledWrites.take(464).forEachIndexed{i,e->require(e.u("offset")==prefixOffsets[i]&&e.u("value")==prefixValues[i]);val p=es.indexOf(e);val fault=es.subList(0,p).last{it.kind=="mapped-fault"};val before=regs(es.subList(0,p).last{it.kind=="fault-registers"});val afterEvent=es.subList(p+1,(p+5).coerceAtMost(es.size)).first{it.kind=="write-registers"};require(fault.u("tid")==pid&&fault.u("signal")==11uL&&fault.u("si_code")==2uL&&fault.u("address")==es.single{it.kind=="mapping-result"}.u("base")+prefixOffsets[i]&&fault.u("offset")==prefixOffsets[i]&&fault.u("opcode")==0xb9000109uL&&before.pc==prefixWritePc&&before.x[8]==fault.u("address")&&before.x[9].toUInt().toULong()==prefixValues[i]&&completed(before,regs(afterEvent),null))}
 val tailOffsets=listOf(4uL,0uL,0x401cuL,0x14a0uL,0x14a4uL,0x1498uL,0x14acuL,0x14b4uL,0x1008uL,0x1210uL);val tailValues=listOf(0xa1123456uL,0xbbaa0078uL,0x10203040uL,0xa5a50021uL,0xb6b61234uL,0xc7c72345uL,0xd8d83456uL,0xe9e94567uL,0x20000000uL,62500uL);val writeOffsets=listOf(0x1428uL,0x1000uL);val writeValues=listOf(0x646euL,0uL)
 val readPc=if(stock)base+0x270604uL else control.symbol("gm_first_pc");val writePc=if(stock)base+0x27043cuL else control.symbol("gm_write_pc");require(elf.word(readPc-base)==0xb9400109uL&&elf.word(writePc-base)==0xb9000109uL)
 val reads=es.filter{it.kind=="tail-read"};require(reads.size==10&&es.count{it.kind=="tail-read-registers"}==reads.size);reads.forEachIndexed{i,e->require(e.u("tid")==pid&&e.u("index")==i.toULong()&&e.u("offset")==tailOffsets[i]&&e.u("value")==tailValues[i]&&e.u("width")==4uL&&e.u("pc")==readPc&&e.u("opcode")==0xb9400109uL);val p=es.indexOf(e);val fault=es.subList(0,p).last{it.kind=="mapped-fault"};val before=regs(es.subList(0,p).last{it.kind=="fault-registers"});val after=regs(es[p+1]);require(fault.u("tid")==pid&&fault.u("signal")==11uL&&fault.u("si_code")==2uL&&fault.u("address")==mapping+tailOffsets[i]&&fault.u("offset")==tailOffsets[i]&&before.x[8]==fault.u("address")&&es[p+1].kind=="tail-read-registers"&&before.pc==readPc&&completed(before,after,tailValues[i]))}
 tailWrites.forEachIndexed{i,e->require(i<2&&e.u("tid")==pid&&e.u("index")==i.toULong()&&e.u("global_index")==464uL+i.toULong()&&e.u("offset")==writeOffsets[i]&&e.u("value")==writeValues[i]&&e.u("width")==4uL&&e.u("pc")==writePc&&e.u("opcode")==0xb9000109uL);val p=es.indexOf(e);val fault=es.subList(0,p).last{it.kind=="mapped-fault"};val before=regs(es.subList(0,p).last{it.kind=="fault-registers"});val after=regs(es[p+1]);require(fault.u("tid")==pid&&fault.u("signal")==11uL&&fault.u("si_code")==2uL&&fault.u("address")==mapping+writeOffsets[i]&&fault.u("offset")==writeOffsets[i]&&before.x[8]==fault.u("address")&&before.x[9].toUInt().toULong()==writeValues[i]&&es[p+1].kind=="write-registers"&&before.pc==writePc&&completed(before,after,null));val mw=modeledWrites[464+i];require(mw.u("offset")==writeOffsets[i]&&mw.u("value")==writeValues[i])}
 // Binding/state values are recomputed from fixed stock offsets or the private ELF/layout.
 val slots=listOf(0xb78790uL,0xb7bb08uL,0xb7fb88uL,0xb83f18uL,0xb845c0uL,0xb86148uL,0xb86690uL,0xb86758uL,0xb86f98uL,0xb870a0uL,0xb87630uL,0xb883b8uL,0xb89e08uL,0xb8d288uL,0xb8de08uL,0xb8e118uL);val targets=listOf(0x272844uL,0x272244uL,0x27dcf0uL,0x273484uL,0x2851b4uL,0x277d08uL,0x272c2cuL,0x27357cuL,0x285374uL,0x27d448uL,0x2e5228uL,0x272c5cuL,0x2852c4uL,0x3cb44fcuL,0x3cb4540uL,0x3cb4550uL)
 val privateTargets=listOf("gm_tail_private","gm_tail_private","gm_write","gm_tail_private","gm_tail_private","gm_tail_private","gm_write","gm_tail_private","gm_tail_private","gm_tail_private","gm_tail_private","gm_first","gm_tail_private").map{control.symbol(it)}+listOf(shared+2988uL,shared+2996uL,shared+2984uL)
 val bindingEvents=es.filter{it.kind=="tail-binding"};val expectedBindingPhases=when(arm){in 60..62->emptyList();67->listOf("initial" to 1);in 63..66,68,75->listOf("initial" to 16);else->listOf("initial" to 16,"checkpoint0" to 16)};require(bindingEvents.map{it.s("phase")}==expectedBindingPhases.flatMap{(phase,n)->List(n){phase}});expectedBindingPhases.forEach{(phase,n)->require(bindingEvents.filter{it.s("phase")==phase}.map{it.u("index")}==(0 until n).map{it.toULong()})};bindingEvents.forEach{e->val i=e.u("index").toInt();val expected=if(stock)base+targets[i] else privateTargets[i];val actual=expected+(if(!stock&&arm==67&&i==0)1uL else 0uL);require(i in 0..15&&e.u("slot")==slots[i]&&e.u("expected_target")==expected&&e.u("actual_target")==actual&&e.u("match")== (if(actual==expected)1uL else 0uL))}
 val states=es.filter{it.kind=="tail-state"};states.forEach{e->val i=e.u("index").toInt();val phase=e.s("phase");if(phase=="write0"||phase=="write1"){val wi=if(phase=="write0")0 else 1;val stateObject=if(stock)base+listOf(0x3cb4550uL,0x3cb44fcuL)[wi]else shared+listOf(2984uL,2988uL)[wi];require(i==8+wi&&e.u("object")==stateObject&&e.u("expected")==writeValues[wi]&&e.u("actual")==writeValues[wi]&&e.u("match")==1uL)}else{require(phase in setOf("initial","checkpoint0")&&i in 0..7);val expected=listOf(0uL,0uL,8uL,900uL,8uL,900uL,1uL,if(stock)base+0xb8f478uL else shared+2848uL)[i];val bad=!stock&&((arm==64&&phase=="initial"&&i==0)||(arm==65&&phase=="initial"&&i==1)||(arm==66&&phase=="initial"&&i==6)||(arm==74&&phase=="checkpoint0"&&i==6));val actual=if(bad)if(i==0||i==1)1uL else 0uL else expected;require(e.u("expected")==expected&&e.u("actual")==actual&&e.u("match")== (if(bad)0uL else 1uL));val expectedObject=if(stock)listOf(base+0x3cb4550uL,base+0x3cb44fcuL,base+0xb8f4e4uL,base+0xb8f4e8uL,base+0xb8f530uL,base+0xb8f534uL,base+0xb8f4e0uL,base+0xb8f548uL)[i]else listOf(shared+2984uL,shared+2988uL,shared+1200uL,shared+1204uL,shared+1276uL,shared+1280uL,shared+2848uL,shared+1300uL)[i];require(e.u("object")==expectedObject)}}
 val expectedStateTokens=listOf("initial:7")+(0..6).map{"initial:$it"}+listOf("write0:8","checkpoint0:7")+(0..6).map{"checkpoint0:$it"}+listOf("write1:9");require(states.map{"${it.s("phase")}:${it.u("index")}"}==expectedStateTokens){"tail state sequence"}
 // Three checkpoint traps and every debug transition are tied to raw PCs/opcodes/registers.
 val acceptedCp=3;val failedCp=!stock&&arm in setOf(68,69,70,74);val emittedCp=acceptedCp+(if(failedCp)1 else 0);val cps=es.filter{it.kind=="tail-checkpoint"};require(cps.size==emittedCp);val privatePcs=listOf("gm_it_cp0","gm_it_cp1","gm_it_cp2").map{control.symbol(it)};val stockPcs=listOf(0x2e547cuL,0x2e55a8uL,0x2e57f8uL);val stockOps=listOf(0x340008eauL,0x900035a9uL,0x97fc6696uL);val countPairs=listOf(3uL to 1uL,10uL to 2uL,10uL to 2uL)
 cps.forEachIndexed{i,e->val pc=if(stock)base+stockPcs[i]else privatePcs[i];val op=if(stock)stockOps[i]else 0xd503201fuL;require(e.u("index")==i.toULong()&&e.u("tid")==pid&&e.u("signal")==5uL&&e.u("si_code")==4uL&&e.u("address")==pc&&e.u("pc")==pc&&e.u("relative_pc")== (if(stock)stockPcs[i]else 0uL) &&e.u("opcode")==op&&e.u("expected_pc")==pc&&e.u("expected_opcode")==op&&e.u("reads")==countPairs[i].first&&e.u("writes")==countPairs[i].second&&elf.word(pc-base)==op);val p=es.indexOf(e);val before=regs(es[p+1]);require(es[p+1].kind=="tail-checkpoint-registers"&&before.pc==pc);val guard=es.subList(p+2,es.size).first{it.kind=="tail-checkpoint-guard"};val good=i<acceptedCp;require(guard.u("index")==i.toULong()&&guard.u("reads")==countPairs[i].first&&guard.u("writes")==countPairs[i].second&&guard.u("match")== (if(good)1uL else 0uL) &&guard.u("atomic")== (if(stock)0uL else(i+1).toULong()));if(good){val afterEvent=es.subList(es.indexOf(guard)+1,es.size).first{it.kind=="tail-debug-registers"};require(same(before,regs(afterEvent)))}}
 require(cps.indices.all{i->val r=regs(es[es.indexOf(cps[i])+1]);i==2||(i==0&&r.x[10]==1uL)||(i==1&&r.x[0].toUInt()==0u)})
 val outputs=es.filter{it.kind=="tail-parent-output"};val outputExpected=listOf(0x12345678uL,0x10203040uL,0x21uL,0x345uL,0x234uL,0x456uL,0x167uL,0uL,1uL,0x20000000uL,0uL,0x646euL);val outputWidths=listOf(4uL,4uL,4uL,8uL,8uL,8uL,8uL,4uL,1uL,4uL,4uL,4uL);outputs.forEach{e->val cp=e.u("checkpoint").toInt();val i=e.u("index").toInt();val bad=!stock&&((arm==68&&cp==0&&i==0)||(arm==69&&cp==1&&i==3)||(arm==70&&cp==1&&i==8));val actual=if(!stock&&arm==69&&cp==1&&i==3)outputExpected[i] xor 0x100000000uL else outputExpected[i]+if(bad)if(i==8)ULong.MAX_VALUE else 1uL else 0uL;val cpRegs=regs(es[es.indexOf(cps[cp])+1]);val objectExpected=if(stock)when(i){0->cpRegs.x[29]-0x48uL;1->cpRegs.x[29]-0x4cuL;in 2..7->cpRegs.x[29]-listOf(0x50uL,0x58uL,0x60uL,0x68uL,0x70uL,0x74uL)[i-2];8->cpRegs.x[29]-0x78uL;9->base+0x3cb4540uL;10->base+0x3cb44fcuL;else->base+0x3cb4550uL}else when(i){0->shared+3000uL;1->shared+3004uL;in 2..7->shared+3008uL+8uL*(i-2).toULong();8->shared+3056uL;9->shared+2996uL;10->shared+2988uL;else->shared+2984uL};require(e.u("object")==objectExpected&&e.u("width")==outputWidths[i]&&e.u("expected")==outputExpected[i]&&e.u("actual")==actual&&e.u("match")== (if(bad)0uL else 1uL))}
 val expectedOutputTokens=buildList<String>{if(stock||arm in setOf(59,68,69,70,71,72,73,74)){val end0=if(arm==68)1 else 11;for(i in listOf(0,1,11).filter{it<=end0||it==11&&end0==11})add("0:$i")};if(stock||arm in setOf(59,69,70,71,72)){val end1=when(arm){69->3;70->8;else->11};for(i in 0..end1)add("1:$i")};if(stock||arm in setOf(59,72)){for(i in 0..11)add("2:$i")}};require(outputs.map{"${it.u("checkpoint")}:${it.u("index")}"}==expectedOutputTokens){"tail parent output sequence"}
 val tokens=es.filter{it.kind in setOf("tail-read","tail-write","tail-checkpoint")}.map{when(it.kind){"tail-read"->"R${it.u("index")}";"tail-write"->"W${it.u("index")}";else->"CP${it.u("index")}"}};val canonical=listOf("R0","R1","R2","W0","CP0","R3","R4","R5","R6","R7","W1","R8","R9","CP1","CP2");val expectedTokenCount=when{stock||arm in setOf(59,72)->15;arm in 60..62||arm in 64..67||arm==75->0;arm==63->3;arm in setOf(68,74)->5;arm in setOf(69,70,71)->14;arm==73->5;else->error("arm")};require(tokens==canonical.take(expectedTokenCount)){"tail operation order"}
 fun dump(e:E,address:ULong,controlWord:ULong,request:Boolean){require(e.u("result")==0uL&&e.u("size")== (if(request)24uL else 264uL) &&e.u("info")==0x606uL&&e.u("a00")==address&&e.u("c00")==controlWord);for(i in 1..15){val n=i.toString().padStart(2,'0');require(e.u("a$n")==0uL&&e.u("c$n")==0uL)}}
 val effectivePcs=stockPcs.map{base+it};val effectiveOps=stockOps;val privateP0=privatePcs[0];val prepBefore=es.filter{it.kind=="tail-debug-prep-before"};val prepReq=es.filter{it.kind=="tail-debug-prep-arm-request"};val prepSet=es.filter{it.kind=="tail-debug-prep-arm-set"};val prepAfter=es.filter{it.kind=="tail-debug-prep-arm-after"};val prepReady=es.filter{it.kind=="tail-debug-prep-ready"};val prepRegs=es.filter{it.kind=="tail-debug-prep-registers"}
 if(arm==75){dump(prepBefore.single(),0uL,0x1e5uL,false);dump(prepReq.single(),privateP0,0x1e5uL,true);require(prepSet.single().u("result")==0uL);dump(prepAfter.single(),privateP0,0x1e4uL,false);val pr=prepReady.single();require(pr.u("checkpoint")==0uL&&pr.u("tid")==pid&&pr.u("target")==privateP0&&pr.u("opcode")==0xd503201fuL);val firstFault=regs(es.take(es.indexOf(bindingEvents.first())).last{it.kind=="fault-registers"});require(same(firstFault,regs(prepRegs.single())))}else require(listOf(prepBefore,prepReq,prepSet,prepAfter,prepReady,prepRegs).all{it.isEmpty()})
 val befores=es.filter{it.kind=="tail-debug-before"};val clears=es.filter{it.kind=="tail-debug-clear-request"};val clearSets=es.filter{it.kind=="tail-debug-clear-set"};val clearAfter=es.filter{it.kind=="tail-debug-clear-after"};val armReq=es.filter{it.kind=="tail-debug-arm-request"};val armSets=es.filter{it.kind=="tail-debug-arm-set"};val armAfter=es.filter{it.kind=="tail-debug-arm-after"};val ready=es.filter{it.kind=="tail-debug-ready"};val initialDebug=if(reads.isNotEmpty()||arm==75)1 else 0;val cycles=initialDebug+acceptedCp;require(befores.size==cycles&&clears.size==acceptedCp&&clearSets.size==acceptedCp&&clearAfter.size==acceptedCp);val expectedArms=(if(initialDebug==1&&arm!=75)1 else 0)+(0 until acceptedCp).count{it<2};require(armReq.size==expectedArms&&armSets.size==expectedArms&&armAfter.size==expectedArms&&ready.size==expectedArms)
 if(initialDebug==1)dump(befores[0],if(arm==75)privateP0 else 0uL,if(arm==75)0x1e4uL else 0x1e5uL,false)
 for(i in 0 until acceptedCp){val beforeIndex=initialDebug+i;val previous=effectivePcs[i];dump(befores[beforeIndex],previous,0x1e4uL,false);dump(clears[i],0uL,0uL,true);require(clearSets[i].u("result")==0uL);dump(clearAfter[i],0uL,0x1e5uL,false)}
 armReq.forEachIndexed{i,e->val pc=effectivePcs[i];dump(e,pc,0x1e5uL,true);require(armSets[i].u("result")==0uL);dump(armAfter[i],pc,0x1e4uL,false);require(ready[i].u("checkpoint")==i.toULong()&&ready[i].u("tid")==pid&&ready[i].u("target")==pc&&ready[i].u("opcode")==effectiveOps[i])}
 val normalInitialRegisters=if(initialDebug==1&&arm!=75)1 else 0;if(normalInitialRegisters==1){val firstFault=regs(es.take(es.indexOf(reads[0])).last{it.kind=="fault-registers"});require(same(firstFault,regs(es.single{it.kind=="tail-initial-debug-registers"})))};require(es.count{it.kind=="tail-initial-debug-registers"}==normalInitialRegisters&&es.count{it.kind=="tail-debug-registers"}==acceptedCp)
 val debugKinds=setOf("tail-debug-prep-before","tail-debug-prep-arm-request","tail-debug-prep-arm-set","tail-debug-prep-arm-after","tail-debug-prep-registers","tail-debug-prep-ready","tail-debug-before","tail-debug-clear-request","tail-debug-clear-set","tail-debug-clear-after","tail-debug-arm-request","tail-debug-arm-set","tail-debug-arm-after","tail-debug-ready","tail-initial-debug-registers","tail-debug-registers");val expectedDebugKinds=buildList<String>{if(arm==75)addAll(listOf("tail-debug-prep-before","tail-debug-prep-arm-request","tail-debug-prep-arm-set","tail-debug-prep-arm-after","tail-debug-prep-registers","tail-debug-prep-ready"));if(initialDebug==1){add("tail-debug-before");if(arm!=75)addAll(listOf("tail-debug-arm-request","tail-debug-arm-set","tail-debug-arm-after","tail-debug-ready","tail-initial-debug-registers"))};for(i in 0 until acceptedCp){addAll(listOf("tail-debug-before","tail-debug-clear-request","tail-debug-clear-set","tail-debug-clear-after"));if(i<2)addAll(listOf("tail-debug-arm-request","tail-debug-arm-set","tail-debug-arm-after","tail-debug-ready"));add("tail-debug-registers")}};require(es.filter{it.kind in debugKinds}.map{it.kind}==expectedDebugKinds){"tail debug stage order"}
 require(es.none{it.kind in setOf("tail-rejected","tail-deadline","tail-access-rejected")})
 val remainingSummary=es.single{it.kind=="remaining-summary"};require(remainingSummary.u("private_metrics")==0uL&&remainingSummary.u("scu_object")==base+0x3cb4620uL&&remainingSummary.u("scu_value")==0uL&&remainingSummary.u("la_object")==base+0x106d4d8uL&&remainingSummary.u("la_value")==0uL&&remainingSummary.u("cached_object")==base+0xbb127cuL&&remainingSummary.u("cached_value")==0xfffffff9uL&&remainingSummary.u("checkpoints")==10uL&&remainingSummary.u("remaining_writes")==4uL&&remainingSummary.u("total_writes")==466uL&&remainingSummary.u("atomic")==0uL&&remainingSummary.u("device_io")==0uL&&remainingSummary.u("old_executed")==0uL&&remainingSummary.u("clone_tid")==0uL)
 val summary=es.single{it.kind=="tail-summary"};val er=10;val ew=2;val ec=3;require(summary.u("private_metrics")== (if(stock)0uL else 1uL) &&summary.u("reads")==er.toULong()&&summary.u("writes")==ew.toULong()&&summary.u("checkpoints")==ec.toULong()&&summary.u("total_writes")==464uL+ew.toULong()&&summary.u("calibration_executed")==0uL&&summary.u("clone_tid")==0uL);if(!stock){val atomic=when{arm==59||arm==72->3;arm in 69..71->2;arm==68||arm==73||arm==74->1;else->0};require(summary.u("atomic")==atomic.toULong()&&summary.u("old_executed")== (if(arm==72)1uL else 0uL))}else require(summary.u("atomic")==0uL&&summary.u("old_executed")==0uL)
 fun inventory(phase:String,stopping:ULong):Set<ULong>{val status=es.filter{it.kind=="thread-status"&&it.s("phase")==phase};val inv=es.single{it.kind=="thread-inventory"&&it.s("phase")==phase};val tids=status.map{it.u("tid")};require(tids.distinct().size==tids.size&&status.all{"read_error" !in it.f&&it.u("tgid")==pid&&it.u("tracer_pid")==observer&&it.u("state")==0x74uL});require(inv.u("pid")==pid&&inv.u("observer_pid")==observer&&inv.u("stopping_tid")==stopping&&inv.u("observed_count")==status.size.toULong()&&inv.u("overflow")==0uL&&inv.u("error")==0uL&&inv.u("directory_flags")==0x4000uL&&inv.u("error_operation")==0uL&&inv.u("error_result")==0uL);return tids.toSet()}
 val beforeTids=inventory("before-ready",pid);require(pid in beforeTids)
 require(beforeTids.size>=21)
 val clones=es.filter{it.kind=="runtime-clone"};require(clones.map{it.u("new_tid")}.distinct().size==clones.size&&clones.all{it.u("parent_tid") in es.filter{t->t.kind=="group-track"}.map{t->t.u("tid")}.toSet()&&es.indexOf(it)<es.indexOf(reads.first())})
 val tracked=es.filter{it.kind=="group-track"}.map{it.u("tid")};require(tracked.distinct().size==tracked.size&&tracked.toSet()==beforeTids+clones.map{it.u("new_tid")}.toSet())
 require(es.none{it.kind in setOf("remaining-clone","tail-clone")})
 require(es.last().kind=="group-cleanup")
 require(es.none{it.kind in setOf("error","group-failure","remaining-rejected","remaining-deadline","remaining-clone","unexpected-runtime-signal")})
 require(es.none{it.kind in setOf("tail-rejected","tail-deadline")})
 val riBefore=es.filter{it.kind=="remaining-debug-before"};val riClearReq=es.filter{it.kind=="remaining-debug-clear-request"};val riClearSet=es.filter{it.kind=="remaining-debug-clear-set"};val riClearAfter=es.filter{it.kind=="remaining-debug-clear-after"};val riArmReq=es.filter{it.kind=="remaining-debug-arm-request"};val riArmSet=es.filter{it.kind=="remaining-debug-arm-set"};val riArmAfter=es.filter{it.kind=="remaining-debug-arm-after"};val riReady=es.filter{it.kind=="remaining-debug-ready"};require(listOf(riBefore,riClearReq,riClearSet,riClearAfter).all{it.size==11}&&listOf(riArmReq,riArmSet,riArmAfter,riReady).all{it.size==10}&&es.count{it.kind=="remaining-initial-debug-registers"}==1);require(riClearSet.all{it.u("result")==0uL}&&riArmSet.all{it.u("result")==0uL})
 val priorPc=listOf(0x2955b8uL,0x2955bcuL,0x2728e0uL,0x2ad0b8uL,0x2ad574uL,0x2ad578uL,0x2acfc8uL,0x2ad120uL,0x2ad6ecuL,0x2728ecuL);val priorOp=listOf(0x97fdef02uL,0xb9000fe0uL,0x385ff3a9uL,0xd101c3ffuL,0x97fd8f13uL,0xb90017e0uL,0xb90017e0uL,0xf94007e8uL,0xb9001be0uL,0x14000023uL)
 riBefore.forEachIndexed{i,e->dump(e,if(i==0)0uL else base+priorPc[i-1],if(i==0)0uL else 0x1e4uL,false);dump(riClearReq[i],0uL,0uL,true);dump(riClearAfter[i],0uL,if(i==0)0x1e4uL else 0x1e5uL,false)}
 riArmReq.forEachIndexed{i,e->val target=base+priorPc[i];dump(e,target,0x1e5uL,true);dump(riArmAfter[i],target,0x1e4uL,false);require(riReady[i].u("checkpoint")==i.toULong()&&riReady[i].u("tid")==pid&&riReady[i].u("target")==target&&riReady[i].u("opcode")==priorOp[i])}
 val secondRemainingWrite=es.filter{it.kind=="remaining-write"}.single{it.u("index")==1uL};val lastRemainingWriteRegisters=es.subList(es.indexOf(secondRemainingWrite)+1,es.size).first{it.kind=="write-registers"};require(same(regs(lastRemainingWriteRegisters),regs(es.single{it.kind=="remaining-initial-debug-registers"})))
 val priorCheckpoints=es.filter{it.kind=="remaining-checkpoint"};val priorRegisters=es.filter{it.kind=="remaining-checkpoint-registers"};val priorGuards=es.filter{it.kind=="remaining-checkpoint-guard"};val priorAfter=es.filter{it.kind=="remaining-debug-registers"};require(priorCheckpoints.size==10&&priorRegisters.size==10&&priorGuards.size==10&&priorAfter.size==10)
 priorCheckpoints.forEachIndexed{i,e->val pc=base+priorPc[i];require(e.u("index")==i.toULong()&&e.u("tid")==pid&&e.u("signal")==5uL&&e.u("si_code")==4uL&&e.u("address")==pc&&e.u("pc")==pc&&e.u("relative_pc")==priorPc[i]&&e.u("opcode")==priorOp[i]&&e.u("expected_pc")==pc&&e.u("expected_opcode")==priorOp[i]&&elf.word(priorPc[i])==priorOp[i]);val r=regs(priorRegisters[i]);require(r.tid==pid&&r.pc==pc&&same(r,regs(priorAfter[i])));val g=priorGuards[i];require(g.u("index")==i.toULong()&&g.u("match")==1uL&&g.u("atomic")==0uL&&g.u("x0")==r.x[0]&&g.u("x1")==r.x[1]&&g.u("cached_object")==base+0xbb127cuL&&g.u("bool_object")== (if(i==2)r.x[29]-1uL else 0uL) &&g.u("la_object")==base+0x106d4d8uL);val cached=g.u("cached_value");val boolean=g.u("bool_value");val la=g.u("la_value");val contractMatch=when(i){0->r.x[0]==base+0x99814fuL&&r.x[1]==1uL;1,5->r.x[0].toUInt().toInt()<0;2->r.x[0].toUInt()==0xffffffffu&&boolean==0uL;3->r.x[0]==base+0x998f93uL&&r.x[1]==5uL&&cached.toUInt().toInt()<0;4->r.x[0]==base+0x99364buL&&r.x[1]==0x802uL;6,8->r.x[0].toUInt()==0xfffffffdu;7->r.x[0].toUInt()==0xfffffff9u;else->r.x[0].toUInt()==0xffffffffu&&cached==0xfffffff9uL&&la==0uL};require(contractMatch)}
 for(cp in cps){val i=cp.u("index").toInt();val r=regs(es[es.indexOf(cp)+1]);if(i==1)require(r.x[0].toUInt()==0u)}
 if(reads.isNotEmpty())require(es.indexOf(befores.first())<es.indexOf(reads.first()))
	 val checkpointGuards=es.filter{it.kind=="tail-checkpoint-guard"}
	 for(i in 1 until cycles)require(es.indexOf(befores[i])>es.indexOf(checkpointGuards[i-1]))

    // The loader continuation starts at the stopped tail CP2 and adds no MMIO model.
    val loaderMode=es.single{it.kind=="loader-mode"}
    require(loaderMode.s("scope")=="stock"&&loaderMode.u("profile")==1uL&&
        loaderMode.s("debug_profile")=="inherited-direct-arm-v1"&&
        loaderMode.u("arm")==0uL&&loaderMode.u("checkpoint_count")==4uL&&loaderMode.u("capture_count")==5uL&&
        loaderMode.u("binding_count")==6uL&&loaderMode.u("deadline_ms")==10000uL)
    require(es.indexOf(loaderMode)<es.indexOf(es.first{it.kind=="runtime-resume"}))

    val loaderSlots=listOf(0xb7c000uL,0xb79558uL,0xb7d7a8uL,0xb7f4d8uL,0xb77ba8uL,0xb808c0uL)
    val loaderTargets=listOf(0x2e5a40uL,0x2e5a4cuL,0x333afcuL,0x366e4cuL,0x366c20uL,0x33eac8uL)
    val loaderBindings=es.filter{it.kind=="loader-binding"}
    require(loaderBindings.map{it.u("index")}==(0..5).map{it.toULong()})
    loaderBindings.forEachIndexed{i,e->require(e.u("slot")==base+loaderSlots[i]&&
        e.u("expected_target")==base+loaderTargets[i]&&e.u("actual_target")==base+loaderTargets[i]&&e.u("match")==1uL)}

    val objectOffsets=listOf(0x10bee40uL,0x10c4f18uL,0x10c4f30uL,0x10cded8uL)
    val destinationOffsets=listOf(0x10cded8uL,0x10cd734uL,0x1151638uL)
    val destinationLengths=listOf(192uL,1936uL,0x1b60c0uL)
    val layouts=es.filter{it.kind=="loader-layout"};require(layouts.size==7)
    layouts.take(4).forEachIndexed{i,e->require(e.s("category")=="object"&&
        e.s("evidence_kind")=="derived-fixed-layout"&&e.u("index")==i.toULong()&&
        e.u("address")==base+objectOffsets[i]&&e.u("expected_address")==base+objectOffsets[i]&&
        e.u("length")==0uL&&e.u("expected_length")==0uL&&e.u("match")==1uL)}
    layouts.drop(4).forEachIndexed{i,e->require(e.s("category")=="destination"&&
        e.u("index")==i.toULong()&&e.u("address")==base+destinationOffsets[i]&&
        e.u("expected_address")==base+destinationOffsets[i]&&e.u("length")==destinationLengths[i]&&
        e.u("expected_length")==destinationLengths[i]&&e.u("match")==1uL)}

    val loaderPcs=listOf(0x333b78uL,0x333b84uL,0x333b9cuL,0x333ba8uL)
    val loaderOps=listOf(0xb90077e0uL,0xb90077e0uL,0xb90077e0uL,0x97fb9b9euL)
    val loaderStatuses=listOf(192,0x1b60c0,-1)
    // Each stock loader returns through W0, so the captured X0 has zero upper bits.
    require(elf.word(0x366f44uL) == 0xb94007e0uL && elf.word(0x366f50uL) == 0xd65f03c0uL)
    require(elf.word(0x366e20uL) == 0xb9400be0uL && elf.word(0x366e30uL) == 0xd65f03c0uL)
    require(elf.word(0x33ebd8uL) == 0xb9400fe0uL && elf.word(0x33ebe4uL) == 0xd65f03c0uL)
    val loaderCps=es.filter{it.kind=="loader-checkpoint"};require(loaderCps.size==4)
    loaderCps.forEachIndexed{i,e->
        val pc=base+loaderPcs[i];require(e.u("index")==i.toULong()&&e.u("tid")==pid&&
            e.u("signal")==5uL&&e.u("si_code")==4uL&&e.u("address")==pc&&e.u("pc")==pc&&
            e.u("relative_pc")==loaderPcs[i]&&e.u("opcode")==loaderOps[i]&&
            e.u("expected_pc")==pc&&e.u("expected_opcode")==loaderOps[i]&&elf.word(loaderPcs[i])==loaderOps[i])
        val r=regs(es[es.indexOf(e)+1]);require(es[es.indexOf(e)+1].kind=="loader-checkpoint-registers"&&r.pc==pc)
        val exactStatus=if(i<2)loaderStatuses[i].toULong() else ULong.MAX_VALUE;require(e.u("status")==exactStatus)
        if(i<3)require(r.x[0]==if(i<2)exactStatus else 0xffffffffuL)
        if(i==3)require(r.x[0]==base+0x10c4f30uL&&r.x[1]==0uL)
    }
    val statusEvents=es.filter{it.kind=="loader-status"};require(statusEvents.size==3)
    statusEvents.forEachIndexed{i,e->val v=if(i<2)loaderStatuses[i].toULong() else ULong.MAX_VALUE;require(e.u("index")==i.toULong()&&e.u("width")==4uL&&e.u("actual")==v&&e.u("expected")==v&&e.u("match")==1uL)}

    val loaderBefore=es.filter{it.kind=="loader-debug-before"}
    val loaderClearReq=es.filter{it.kind=="loader-debug-clear-request"}
    val loaderClearSet=es.filter{it.kind=="loader-debug-clear-set"}
    val loaderClearAfter=es.filter{it.kind=="loader-debug-clear-after"}
    val loaderArmReq=es.filter{it.kind=="loader-debug-arm-request"}
    val loaderArmSet=es.filter{it.kind=="loader-debug-arm-set"}
    val loaderArmAfter=es.filter{it.kind=="loader-debug-arm-after"}
    val loaderReady=es.filter{it.kind=="loader-debug-ready"}
    val loaderDebugRegs=es.filter{it.kind=="loader-debug-registers"}
    require(loaderBefore.size==5&&loaderClearReq.size==4&&loaderClearSet.size==4&&loaderClearAfter.size==4&&
        loaderArmReq.size==4&&loaderArmSet.size==4&&loaderArmAfter.size==4&&loaderReady.size==4&&loaderDebugRegs.size==5)
    dump(loaderBefore[0],0uL,0x1e5uL,false)
    loaderArmReq.forEachIndexed{i,e->val pc=base+loaderPcs[i];dump(e,pc,0x1e5uL,true);require(loaderArmSet[i].u("result")==0uL);dump(loaderArmAfter[i],pc,0x1e4uL,false);require(loaderReady[i].u("checkpoint")==i.toULong()&&loaderReady[i].u("tid")==pid&&loaderReady[i].u("target")==pc&&loaderReady[i].u("opcode")==loaderOps[i])}
    for(i in 0..3){val pc=base+loaderPcs[i];dump(loaderBefore[i+1],pc,0x1e4uL,false);dump(loaderClearReq[i],0uL,0uL,true);require(loaderClearSet[i].u("result")==0uL);dump(loaderClearAfter[i],0uL,0x1e5uL,false)}
    require(same(regs(es.last{it.kind=="tail-checkpoint-registers"}),regs(loaderDebugRegs[0])))
    loaderCps.forEachIndexed{i,e->require(same(regs(es[es.indexOf(e)+1]),regs(loaderDebugRegs[i+1])))}

    val captureNames=listOf("loader-entry-lsb.bin","loader-entry-adc.bin","loader-terminal-lsb.bin","loader-terminal-adc.bin","loader-terminal-vertical.bin")
    val hostCaptureNames=captureNames.map{"native-$it"}
    val captureAddresses=listOf(destinationOffsets[0],destinationOffsets[1],destinationOffsets[0],destinationOffsets[1],destinationOffsets[2]).map{base+it}
    val captureLengths=listOf(192uL,1936uL,192uL,1936uL,0x1b60c0uL)
    val captureChunks=listOf(1uL,1uL,1uL,1uL,28uL)
    val captureResults=listOf(192uL,1936uL,192uL,1936uL,0x60c0uL)
    val captures=es.filter{it.kind=="loader-capture"};require(captures.size==5)
    captures.forEachIndexed{i,e->require(e.u("index")==i.toULong()&&e.s("phase")== (if(i<2)"entry" else "terminal") &&
        e.s("name")==captureNames[i]&&e.u("address")==captureAddresses[i]&&e.u("length")==captureLengths[i]&&
        e.u("completed")==captureLengths[i]&&e.u("chunks")==captureChunks[i]&&e.u("result")==captureResults[i]&&
        e.u("pattern")==0uL&&e.u("match")==1uL)}
    hostCaptureNames.forEachIndexed{i,n->require(bytes(n).size.toULong()==captureLengths[i])}
    require(hash(hostCaptureNames[2])=="ed4d4016974a509c55530c8573c7e0ef1cb9c28d65536310c13ec8a437c52907")
    require(hash(hostCaptureNames[4])=="1835df35ca11f040c15988e7cdb150198e98688e2472c0b608377b9a2357139b")
    require(bytes(hostCaptureNames[1]).contentEquals(bytes(hostCaptureNames[3])))

    require(es.none{it.kind in setOf("loader-rejected","loader-deadline","loader-access-rejected","loader-clone","error","group-failure","unexpected-runtime-signal","terminal-cleanup-deadline")})
    val loaderSummary=es.single{it.kind=="loader-summary"}
    require(loaderSummary.u("checkpoints")==4uL&&loaderSummary.u("captures")==5uL&&
        loaderSummary.u("modeled_reads")==0uL&&loaderSummary.u("modeled_writes")==0uL&&
        loaderSummary.u("atomic")==0uL&&loaderSummary.u("old_executed")==0uL&&loaderSummary.u("clone_tid")==0uL)
    val converge=es.single{it.kind=="loader-terminal-converge"};require(converge.u("stopping_tid")==pid&&
        es.indexOf(converge)<es.indexOf(captures[2])&&es.subList(es.indexOf(loaderCps.last()),es.size).none{it.kind=="runtime-resume"})
    val convergenceInterrupts=es.filter{it.kind=="loader-terminal-interrupt"};val convergenceStops=es.filter{it.kind=="terminal-interrupt-stop"}
    require(convergenceInterrupts.map{it.u("tid")}.toSet()==tracked.toSet()-pid&&convergenceInterrupts.map{it.u("tid")}.distinct().size==convergenceInterrupts.size&&convergenceInterrupts.all{it.u("result").toLong() in listOf(0L,-5L)})
    require(convergenceStops.map{it.u("tid")}.toSet()==tracked.toSet()-pid&&convergenceStops.map{it.u("tid")}.distinct().size==convergenceStops.size&&convergenceStops.all{it.u("status")==0x80057fuL})
    (convergenceInterrupts + convergenceStops).forEach { e ->
        require(es.indexOf(e) > es.indexOf(converge) && es.indexOf(e) < es.indexOf(captures[2]))
    }
    convergenceStops.forEach { stop ->
        require(es.indexOf(convergenceInterrupts.single { it.u("tid") == stop.u("tid") }) < es.indexOf(stop))
    }
    val armKinds = listOf("loader-debug-arm-request", "loader-debug-arm-set",
        "loader-debug-arm-after", "loader-debug-ready")
    val clearKinds = listOf("loader-debug-before", "loader-debug-clear-request",
        "loader-debug-clear-set", "loader-debug-clear-after")
    val expectedLoaderKinds = mutableListOf("loader-mode")
    expectedLoaderKinds += List(6) { "loader-binding" } + List(7) { "loader-layout" }
    expectedLoaderKinds += List(2) { "loader-capture" }
    expectedLoaderKinds += listOf("loader-debug-before") + armKinds + "loader-debug-registers"
    for (i in 0..3) {
        expectedLoaderKinds += listOf("loader-checkpoint", "loader-checkpoint-registers")
        if (i < 3) expectedLoaderKinds += "loader-status"
        expectedLoaderKinds += clearKinds
        if (i < 3) expectedLoaderKinds += armKinds
        expectedLoaderKinds += "loader-debug-registers"
    }
    expectedLoaderKinds += "loader-terminal-converge"
    expectedLoaderKinds += List(tracked.size - 1) { "loader-terminal-interrupt" }
    expectedLoaderKinds += List(3) { "loader-capture" } + "loader-summary"
    require(es.filter { it.kind.startsWith("loader-") }.map { it.kind } == expectedLoaderKinds) {
        "loader event order differs from the frozen native protocol"
    }
    require(es.indexOf(cps.last()) < es.indexOf(es.last { it.kind == "tail-debug-registers" }) &&
        es.indexOf(es.last { it.kind == "tail-debug-registers" }) < es.indexOf(loaderBindings.first()))
    val rotationStarts = listOf(cps.last()) + loaderCps
    rotationStarts.forEachIndexed { i, start ->
        require(es.subList(es.indexOf(start), es.indexOf(loaderDebugRegs[i]) + 1)
            .none { it.kind == "runtime-resume" && it.u("tid") == pid })
    }
    require(es.indexOf(loaderBindings.first())<es.indexOf(layouts.first())&&es.indexOf(layouts.last())<es.indexOf(captures[0])&&
        es.indexOf(captures[1])<es.indexOf(loaderArmReq[0])&&es.indexOf(loaderArmAfter[0])<es.indexOf(loaderCps[0]))
    for(i in 0..2)require(es.indexOf(loaderCps[i])<es.indexOf(loaderArmReq[i+1])&&es.indexOf(loaderArmAfter[i+1])<es.indexOf(loaderCps[i+1]))
    require(es.indexOf(loaderCps[3])<es.indexOf(converge)&&es.indexOf(converge)<es.indexOf(captures[2])&&
        es.indexOf(captures[2])<es.indexOf(captures[3])&&es.indexOf(captures[3])<es.indexOf(captures[4])&&
        es.indexOf(captures[4])<es.indexOf(loaderSummary))

	 val q=es.single{it.kind=="terminal-quiesce"};require(q.u("stopping_tid")==pid&&loaderCps.last().u("pc")==base+0x333ba8uL&&es.indexOf(loaderSummary)<es.indexOf(q));val terminalTids=inventory("terminal",q.u("stopping_tid"));require(terminalTids==tracked.toSet());val terminalState=es.single{it.kind=="terminal-state"};require(es.indexOf(q)<es.indexOf(terminalState)&&terminalState.u("object")==obj&&terminalState.u("value")==0x0123456789abcdefuL&&terminalState.u("responses")==2uL&&terminalState.u("modeled_writes")==466uL);require(es.none{it.kind in setOf("terminal-cleanup-deadline","unexpected-runtime-signal")});val cleanup=es.single{it.kind=="group-cleanup"};val reaped=es.filter{it.kind=="group-reaped"};require(reaped.size==cleanup.u("reaped_count").toInt()&&cleanup.u("expected_count")==cleanup.u("reaped_count")&&cleanup.u("wait_result").toLong()==-10L&&reaped.all{it.u("status")==9uL}&&reaped.map{it.u("tid")}.toSet()==terminalTids&&reaped.map{it.u("tid")}.distinct().size==reaped.size&&es.last()==cleanup)
    require(text("native-status.toml").trim()=="exit_code = 78")
    require(hash("group-control.elf")=="3c045ce88aeebf61da55e6026216995bbf562bf5ddd12560b9e4ce4296df40fa"&&bytes("group-control.elf").contentEquals(bytes("group-executed.elf")))
    require(text("result.toml").contains("mode = \"loadermodel\"")&&text("result.toml").contains("inspection = \"completed\""))
    require(text("native-enforcing.txt").trim()=="Enforcing"&&text("native-final-enforcing.txt").trim()=="Enforcing"&&text("final-enforcing.txt").trim()=="Enforcing")
    require(text("loader-final-package.txt").isBlank()&&text("final-packages.txt").isBlank())
    require(text("loader-labelled-absent.txt").isBlank()&&text("loader-final-absent.txt").isBlank())
    require(text("loader-labelled-stat.txt")==text("fixture-after-stat.txt")&&text("loader-final-stat.txt")==text("fixture-after-stat.txt"))
    fun labels(name: String, fileType: String = "system_app_data_file") {
        val rows = text(name).lineSequence().filter { it.isNotBlank() }.map { it.trim().split(Regex("\\s+")) }.toList()
        val paths = listOf("/rigol", "/rigol/data", "/rigol/data/default",
            "/rigol/data/default/cal_lsb.hex", "/rigol/data/default/cal_vertical.hex")
        require(rows.size == 5 && rows.map { it.last() } == paths)
        rows.forEachIndexed { i, row ->
            val contexts = row.filter { it.startsWith("u:object_r:") }
            require(contexts == listOf("u:object_r:${if (i < 3) "tmpfs" else fileType}:s0"))
        }
    }
    labels("fixture-after-labels.txt", "su_tmpfs")
    labels("loader-labelled-labels.txt");labels("loader-final-labels.txt")
    require(hash("loader-final-lsb.bin")=="ee8fcfad06a5c3a18a265b0a46c2385c487bab4dcf5c04a398647358750bc4a2")
    require(hash("loader-final-vertical.bin")=="ad347e84e76e258ecb894c77fd22e089c35e817e8052340c6ac3d3b8b4cce55c")
    fun zeroStatus(name:String,keys:List<String>){val pairs=text(name).lineSequence().filter{it.isNotBlank()}.map{line->val p=line.split(" = ",limit=2);require(p.size==2);p[0] to p[1].toInt()}.toList();require(pairs.map{it.first}==keys&&pairs.all{if(name=="loader-command-status.toml"&&it.first=="audit_dmesg")it.second>=0 else it.second==0})}
    zeroStatus("loader-command-status.toml",listOf("fixture_exit","label_lsb","label_vertical","label_inventory","label_metadata","label_absent","stock_helper_exit","audit_logcat","audit_dmesg","force_stop","before_removal","uninstall","final_package","final_labels","final_stat","final_lsb_pull","final_vertical_pull","final_absent"))
    zeroStatus("native-loader-pulls.toml",listOf("entry-lsb","entry-adc","terminal-lsb","terminal-adc","terminal-vertical"))
    zeroStatus("final-health-status.toml",listOf("pid_exit","enforcing_exit","processes_exit","packages_exit","final_health_helper_exit"))
    require(text("native-helper-status.toml").trim() == "exit_code = 0")
    require(text("probe-result.toml").lineSequence().filter { it.isNotBlank() }.toList() ==
        listOf("install = \"admitted\"", "launch = \"attempted\""))
    require(text("loader-before-removal-package.txt").trim() == "package:com.rigol.scope")
    require(text("loader-fixture-verification.toml").contains("result = \"accepted\""))
    run {
        val builder=ProcessBuilder("kotlin",run.resolve("source/VerifyCalibrationFilesystem.main.kts").toString(),run.toString(),"fixture").redirectErrorStream(true)
        builder.environment().remove("KOTLIN_RUNNER");val process=builder.start();val output=process.inputStream.bufferedReader().readText()
        require(process.waitFor()==0){"VerifyCalibrationFilesystem fixture failed: $output"};System.err.print(output)
    }
    val finalPid=text("final-system-server.txt").trim().toULong();require(text("native-final-system-server.txt").trim().toULong()==finalPid)
    val pidPairs=Regex("(?m)^([a-z0-9_]+) = (\\d+)$").findAll(text("system-server-pid.toml")).map{it.groupValues[1] to it.groupValues[2].toULong()}.toList()
    require(pidPairs.map{it.first}==listOf("before","after","after_observation")&&pidPairs.all{it.second==finalPid})
    val fixturePidPairs=Regex("(?m)^([a-z0-9_]+) = (\\d+)$").findAll(text("fixture-system-server.toml")).map{it.groupValues[1] to it.groupValues[2].toULong()}.toList()
    require(fixturePidPairs.map{it.first}==listOf("before","after_root")&&fixturePidPairs.all{it.second==finalPid})
    for(script in listOf("VerifySnapshot.main.kts","VerifyNative.main.kts")){
        val command=mutableListOf("kotlin",run.resolve("source/$script").toString(),run.toString())
        if(script=="VerifyNative.main.kts")command.add("admission-next-access")
        val builder=ProcessBuilder(command).redirectErrorStream(true);builder.environment().remove("KOTLIN_RUNNER")
        val process=builder.start();val output=process.inputStream.bufferedReader().readText();require(process.waitFor()==0){"$script failed: $output"};System.err.print(output)
    }
    require(!Regex("Sparrow|frida|group-observer").containsMatchIn(text("final-processes.txt")))
    val indexLines=Files.readAllLines(run.resolve("evidence-sha256.txt"));val indexed=indexLines.map{line->require(line.length>66&&line.substring(64,66)=="  ");val file=Path.of(line.substring(66)).toAbsolutePath().normalize();require(file.startsWith(run)&&Files.isRegularFile(file)&&hash(Files.readAllBytes(file))==line.take(64));file};require(indexed.distinct().size==indexed.size)
    val consumed=hostCaptureNames+listOf("source/VerifyStockCalibrationLoaders.main.kts","native-helper-status.toml","probe-result.toml","loader-before-removal-package.txt","native-events.toml","native-status.toml","group-control.elf","group-executed.elf","binary-sha256.txt","build-inputs.txt","installed.apk","adc-stock.bin","spu-stock.bin","reference.tsv","tail-candidate.toml","tail-grammar.toml","tail-control-fixture.toml","tail-handoff-profile.toml","tail-stock-gate.toml","calibration-loader-candidate.toml","source/calibration-stock-inputs.toml","source/group-observer.c","source/calibration-loaders.h","source/VerifySnapshot.main.kts","source/VerifyNative.main.kts","source/VerifyCalibrationFilesystem.main.kts","loader-command-status.toml","native-loader-pulls.toml","loader-fixture-verification.toml","loader-labelled-labels.txt","loader-labelled-stat.txt","loader-labelled-absent.txt","loader-final-labels.txt","loader-final-stat.txt","loader-final-absent.txt","loader-final-lsb.bin","loader-final-vertical.bin","native-enforcing.txt","native-final-enforcing.txt","final-enforcing.txt","loader-final-package.txt","final-packages.txt","final-processes.txt","system-server-pid.toml","fixture-system-server.toml","native-final-system-server.txt","final-system-server.txt","final-health-status.toml","result.toml","fixture-before-mounts.txt","fixture-before-mountinfo.txt","fixture-before-stat.txt","fixture-before-labels.txt","fixture-before-empty.txt","fixture-before-pid.txt","fixture-after-root-pid.txt","fixture-enforcing.txt","fixture-processes-before.txt","fixture-packages-before.txt","fixture-command-status.toml","fixture-after-mounts.txt","fixture-after-mountinfo.txt","fixture-after-stat.txt","fixture-after-labels.txt","fixture-absent-paths.txt","calibration-lsb-stock.bin","calibration-lsb-roundtrip.bin","calibration-vertical-stock.bin","calibration-vertical-roundtrip.bin","fixture-result.toml","fixture-ramdisk.img")
    require(consumed.all{run.resolve(it).toAbsolutePath().normalize() in indexed})
}
verify()
println("schema_version = \"mho900-lab.stock-calibration-loaders-verification/1\"")
println("result = \"accepted\"")
println("mode = \"loader-stock\"")
println("filesystem_fixture = \"verified\"")
println("snapshot_admission = \"verified\"")
