// Independent verifier for the stock ADC-input capture observation.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
import java.util.zip.ZipFile

require(args.size==2){"Usage: VerifyStockAdcSequence.main.kts RUN_DIRECTORY FROZEN_MANIFEST_SHA256"}
val run=Path.of(args[0]).toAbsolutePath().normalize();val stock=true
val consumedPaths=mutableSetOf<Path>()
fun resolved(name:String):Path=run.resolve(name).toAbsolutePath().normalize().also{require(it.startsWith(run));consumedPaths.add(it)}
fun bytes(name:String)=Files.readAllBytes(resolved(name));fun text(name:String)=Files.readString(resolved(name))
fun hash(b:ByteArray)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b));fun hash(name:String)=hash(bytes(name))
class E(val kind:String,val f:Map<String,String>){fun s(k:String)=f.getValue(k);fun u(k:String)=s(k).removePrefix("0x").toULong(16)}
fun events(name:String)=text(name).split("[[events]]").drop(1).map{block->val pairs=block.lineSequence().filter{it.isNotBlank()}.map{line->val p=line.split(" = ",limit=2);require(p.size==2){"bad event line"};p[0] to p[1].removeSurrounding("\"")}.toList();require(pairs.map{it.first}.distinct().size==pairs.size);val f=pairs.toMap();E(f.getValue("kind"),f)}
data class R(val tid:ULong,val pc:ULong,val relative:ULong,val sp:ULong,val pstate:ULong,val x:List<ULong>)
fun regs(e:E)=R(e.u("tid"),e.u("pc"),e.u("relative_pc"),e.u("sp"),e.u("pstate"),(0..30).map{e.u("x"+it.toString().padStart(2,'0'))})
fun same(a:R,b:R)=a.tid==b.tid&&a.pc==b.pc&&a.relative==b.relative&&a.sp==b.sp&&a.pstate==b.pstate&&a.x==b.x
fun completed(before:R,after:R,readValue:ULong?):Boolean { if(before.tid!=after.tid||after.pc!=before.pc+4uL||after.sp!=before.sp||after.pstate!=before.pstate)return false;return (0..30).all{i->after.x[i]==if(i==9&&readValue!=null)readValue else before.x[i]} }
data class Seg(val off:ULong,val va:ULong,val size:ULong,val flags:ULong)
class Little(private val data:ByteArray){fun u8(at:Int):Int{require(at in data.indices);return data[at].toInt()and 255};fun u32(at:Int):ULong{require(at>=0&&at+4<=data.size);return ByteBuffer.wrap(data,at,4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong()};fun u64(at:Int):ULong{require(at>=0&&at+8<=data.size);return ByteBuffer.wrap(data,at,8).order(ByteOrder.LITTLE_ENDIAN).long.toULong()}}
data class Mapping(val start:ULong,val end:ULong,val readable:Boolean)
fun parseMaps(name:String):List<Mapping>{val data=bytes(name);require(data.size<=262144);val lines=data.toString(Charsets.UTF_8).lineSequence().filter{it.isNotBlank()}.toList();require(lines.size in 1..2048);return lines.map{line->val c=line.trim().split(Regex("\\s+"),limit=6);require(c.size>=5);val b=c[0].split('-',limit=2);require(b.size==2&&c[1].length==4);Mapping(b[0].toULong(16),b[1].toULong(16),c[1][0]=='r')}}
fun add(a:ULong,b:ULong):ULong{val value=a+b;require(value>=a);return value}
fun contained(maps:List<Mapping>,address:ULong,length:ULong):Boolean{val end=add(address,length);return maps.any{it.readable&&address>=it.start&&end<=it.end}}
class Elf(val b:ByteArray){fun u16(i:Int)=ByteBuffer.wrap(b,i,2).order(ByteOrder.LITTLE_ENDIAN).short.toUShort().toInt();fun u32(i:Int)=ByteBuffer.wrap(b,i,4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong();fun u64(i:Int)=ByteBuffer.wrap(b,i,8).order(ByteOrder.LITTLE_ENDIAN).long.toULong();val segs:List<Seg>
 init{require(b.take(6)==listOf(127,69,76,70,2,1).map{it.toByte()}&&u16(18)==183);segs=(0 until u16(56)).map{u64(32).toInt()+it*u16(54)}.filter{u32(it)==1uL}.map{Seg(u64(it+8),u64(it+16),u64(it+32),u32(it+4))}}
 fun word(va:ULong):ULong{val s=segs.single{va>=it.va&&va+4uL<=it.va+it.size};return u32((s.off+va-s.va).toInt())}
 fun symbol(name:String):ULong{val hs=(0 until u16(60)).map{u64(40).toInt()+it*u16(58)};val tab=hs.single{u32(it+4)==2uL};val strings=hs[u32(tab+40).toInt()];val matches=(0 until(u64(tab+32)/u64(tab+56)).toInt()).map{i->val p=u64(tab+24).toInt()+i*u64(tab+56).toInt();val a=u64(strings+24).toInt()+u32(p).toInt();var z=a;while(b[z]!=0.toByte())z++;String(b,a,z-a) to u64(p+8)}.filter{it.first==name};return matches.single().second}}
data class ApOperation(val index:Int,val sequenceIndex:ULong,val read:Boolean,val offset:ULong,val value:ULong)
data class ApGuard(val index:Int,val source:Int,val offset:ULong,val width:Int,val expected:ULong)
data class ApProfile(val operations:List<ApOperation>,val guards:List<ApGuard>,val finals:List<ApGuard>)
fun number(value:String)=if(value.startsWith("0x"))value.removePrefix("0x").toULong(16)else value.toULong()
fun profile():ApProfile{
    val source=text("adc-sequence/profile.toml")
    fun blocks(marker:String,until:String?):List<Map<String,String>>{val region=source.substringAfter(marker).let{if(until==null)it else it.substringBefore(until)};return region.split(marker).filter{it.isNotBlank()}.map{block->block.lineSequence().takeWhile{!it.startsWith("[[")}.filter{it.contains(" = ")}.associate{line->val p=line.split(" = ",limit=2);p[0] to p[1].removeSurrounding("\"")}}}
    val sourceIndex=listOf("ADC_RECORD","SETTING","DRV","CONFIG","SAMPLE","LOW","HIGH","GLOBAL","SERIES","MASK")
    val guards=blocks("[[guards]]","[[operations]]").map{row->ApGuard(number(row.getValue("index")).toInt(),sourceIndex.indexOf(row.getValue("source")),number(row.getValue("offset")),number(row.getValue("width")).toInt(),number(row.getValue("expected_bits")))}
    val operations=blocks("[[operations]]",null).map{row->val read=row.getValue("kind")=="R32";ApOperation(number(row.getValue("index")).toInt(),number(row.getValue("sequence_index")),read,number(row.getValue("offset")),number(row.getValue(if(read)"synthetic_value" else "value")))}
    val header=text("source/adc-sequence-profile.h").substringAfter("ap_final_shadows[AP_FINAL_SHADOWS]").substringAfter('{').substringBefore("};")
    val finals=Regex("\\{(\\d+)U,0x([0-9a-f]+)U(?:L)?,(\\d+)U,0x([0-9a-f]+)U(?:L)?}").findAll(header).mapIndexed{i,m->val g=m.groupValues;ApGuard(i,g[1].toInt(),g[2].toULong(16),g[3].toInt(),g[4].toULong(16))}.toList()
    return ApProfile(operations,guards,finals)
}
val frozenManifestDigest=args[1].lowercase()
require(Regex("[0-9a-f]{64}").matches(frozenManifestDigest))
val manifestName="source/adc-sequence-stock-inputs.toml"
require(hash(manifestName)==frozenManifestDigest) { "frozen manifest digest" }
val stockInputs=text(manifestName)
fun section(name:String):String { val marker="[$name]";val start=stockInputs.indexOf(marker);require(start>=0);val tail=stockInputs.substring(start+marker.length);val end=Regex("(?m)^\\[").find(tail)?.range?.first?:tail.length;return tail.substring(0,end) }
fun field(body:String,name:String)=Regex("(?m)^"+Regex.escape(name)+" = \\\"([^\\\"]+)\\\"$").find(body)?.groupValues?.get(1)?:error("missing $name")
fun expectFields(body:String,expected:Map<String,String>){for((key,value)in expected){val rows=Regex("(?m)^"+Regex.escape(key)+" = (.+)$").findAll(body).toList();require(rows.size==1&&rows.single().groupValues[1]==value){"input contract: $key"}}}
val manifestHead=stockInputs.substringBefore("\n[")
expectFields(manifestHead,mapOf("schema_version" to "\"mho900-lab.adc-sequence-stock/1\"","mode" to "\"adcsequencemodel\"","run_id" to "\"stock-adc-sequence-01\"","terminal_relative_pc" to "0x333bac","terminal_opcode" to "0x5285070a","terminal_instruction_executes" to "false","new_modeled_mmio_responses" to "2","new_modeled_reads" to "2","new_modeled_writes" to "97","expected_operations" to "99","expected_entry_guards" to "175","expected_final_shadows" to "33","synthetic_read_values" to "[0x11234, 0]","adaptive_retry" to "false","physical_access" to "false","physical_instrument_access" to "false","stock_apk_sha256" to "\"6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b\"","stock_elf_sha256" to "\"4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e\""))
data class Artifact(val path:String,val runPath:String,val sha256:String)
val artifacts=stockInputs.split("[[artifacts]]").drop(1).map{block->
    val body=block.lineSequence().takeWhile{!it.startsWith("[")}.filter{it.contains(" = ")}.associate{line->val p=line.split(" = ",limit=2);p[0] to p[1].removeSurrounding("\"")}
    val path=body.getValue("path");Artifact(path,body["run_path"]?:path,body.getValue("sha256"))
}
require(artifacts.isNotEmpty()&&artifacts.map{it.path}.distinct().size==artifacts.size&&artifacts.map{it.runPath}.distinct().size==artifacts.size)
val artifactByPath=artifacts.associateBy{it.path}
val artifactByRunPath=artifacts.associateBy{it.runPath}
artifacts.forEach{artifact->for(value in listOf(artifact.path,artifact.runPath))require(!Path.of(value).isAbsolute&&!value.split('/').contains(".."));val staged=resolved(artifact.runPath);require(Files.isRegularFile(staged)&&!Files.isSymbolicLink(staged));require(Regex("[0-9a-f]{64}").matches(artifact.sha256));require(hash(artifact.runPath)==artifact.sha256){"manifest artifact: ${artifact.runPath}"}}
fun requireArtifact(path:String,runPath:String=path):Artifact{val artifact=artifactByPath.getValue(path);require(artifact.runPath==runPath);return artifact}
val captureNativeSha256="960b91e1b3cd7de8f49d47833c6e13ec43afcc597bb0d205c379f471a2bcda37"
requireArtifact("out/adc-sequence-profile/native-build02/group-observer","group-control.elf").also{require(it.sha256==captureNativeSha256)}
requireArtifact("experiments/adc-sequence/profile.toml","adc-sequence/profile.toml").also{require(it.sha256=="1fd5ffcf09094da41bd7aa08ed60974b6a6f4c3be9ba7f0f92eebdab087d8abb")}
requireArtifact("tools/guest/VerifyStockAdcSequence.main.kts","source/VerifyStockAdcSequence.main.kts")
requireArtifact("tools/guest/adc-sequence-profile.h","source/adc-sequence-profile.h")
requireArtifact("tools/guest/adc-sequence-observer.h","source/adc-sequence-observer.h")
requireArtifact("local/guest-inputs/Sparrow.apk","stock-input.apk").also{require(it.sha256=="6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b")}
require(artifactByRunPath.getValue("source/frida-environment-files.toml").sha256=="26b507ddb5b372c2a87ccd08ef5af21a3a20b1a540496b03fa848912fa7bdc80")
require(bytes(manifestName).contentEquals(bytes("source/calibration-stock-runtime-inputs.toml")))
val nativeInput=section("native")
require(field(nativeInput,"sha256")==captureNativeSha256)
val binaryDigest=Regex("([0-9a-f]{64})  .+").matchEntire(text("binary-sha256.txt").trim())?.groupValues?.get(1)?:error("invalid binary digest record")
expectFields(text("frida-tooling-verification.toml"),mapOf("schema_version" to "\"mho900-lab.frida-environment-verification/1\"","result" to "\"accepted\"","files" to "721","inventory_sha256" to "\"26b507ddb5b372c2a87ccd08ef5af21a3a20b1a540496b03fa848912fa7bdc80\""))
expectFields(text("frida-prerequisite.toml"),mapOf("schema_version" to "\"mho900-lab.frida-prerequisite/1\"","mode" to "\"adcsequencemodel\"","required" to "true","server_verified" to "true","cli_version" to "\"16.7.19\""))
val requiredPackages=text("frida-required-packages.txt").lineSequence().filter{it.isNotBlank()}.toList();val observedPackages=text("frida-observed-packages.txt").lineSequence().filter{it.isNotBlank()}.toList();val pinnedPackages=text("frida-packages.txt").lineSequence().filter{it.isNotBlank()}.toList();require(requiredPackages.size==7&&requiredPackages==requiredPackages.sorted()&&requiredPackages==observedPackages&&requiredPackages==pinnedPackages.sorted())

fun verify(){
 require(hash("group-control.elf")==captureNativeSha256)
 val arm=-1;val prefix="native";require(text("native-status.toml").trim()=="exit_code = 78")
	 val binary=bytes("group-control.elf");require(hash(binary)==captureNativeSha256&&hash(binary)==binaryDigest);require(hash(if(stock)"group-executed.elf" else "tail-$arm.elf")==hash(binary));val control=Elf(binary)
	 val es=events(if(stock)"native-events.toml" else "$prefix.toml");require(es.isNotEmpty());val mode=es.single{it.kind=="model-mode"};require(mode.s("scope")=="stock"&&mode.u("continuation")==1uL&&mode.u("transcript")==1uL&&mode.u("spu")==1uL&&mode.u("remaining")==1uL&&mode.u("tail")==1uL&&mode.u("loaders")==1uL&&mode.u("adc_inputs")==1uL&&mode.u("profile")==1uL)
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
 val oracle=Files.readAllLines(resolved("reference.tsv")).drop(1).mapIndexed{i,line->val f=line.split('\t');require(f.size==7&&f[0].toInt()==i);f[6].removePrefix("0x").toULong(16)};require(oracle.size==452);val spu=ByteBuffer.wrap(bytes(if(stock)"spu-stock.bin" else "spu-private.bin")).order(ByteOrder.LITTLE_ENDIAN);val su32:(Int)->ULong={i->spu.getInt(i).toUInt().toULong()};val prefixOffsets=List(452){0x3000uL}+(0..7).map{su32(1000+8*it)}+listOf(0x4004uL,0x4004uL,0x7034uL,0x7034uL);val prefixValues=oracle+(0..7).map{su32(1004+8*it)}+listOf(0x80000000uL,0uL,1uL,0uL);require(prefixOffsets.size==464);val prefixWritePc=base+0x27043cuL;modeledWrites.take(464).forEachIndexed{i,e->require(e.u("offset")==prefixOffsets[i]&&e.u("value")==prefixValues[i]);val p=es.indexOf(e);val fault=es.subList(0,p).last{it.kind=="mapped-fault"};val before=regs(es.subList(0,p).last{it.kind=="fault-registers"});val afterEvent=es.subList(p+1,(p+5).coerceAtMost(es.size)).first{it.kind=="write-registers"};require(fault.u("tid")==pid&&fault.u("signal")==11uL&&fault.u("si_code")==2uL&&fault.u("address")==es.single{it.kind=="mapping-result"}.u("base")+prefixOffsets[i]&&fault.u("offset")==prefixOffsets[i]&&fault.u("opcode")==0xb9000109uL&&before.pc==prefixWritePc&&before.x[8]==fault.u("address")&&before.x[9].toUInt().toULong()==prefixValues[i]&&completed(before,regs(afterEvent),null))}
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
 val remainingSummary=es.single{it.kind=="remaining-summary"};require(remainingSummary.u("private_metrics")==0uL&&remainingSummary.u("scu_object")==base+0x3cb4620uL&&remainingSummary.u("scu_value")==0uL&&remainingSummary.u("la_object")==base+0x106d4d8uL&&remainingSummary.u("la_value")==0uL&&remainingSummary.u("cached_object")==base+0xbb127cuL&&remainingSummary.u("cached_value")==0xfffffff9uL&&remainingSummary.u("checkpoints")==10uL&&remainingSummary.u("remaining_writes")==4uL&&remainingSummary.u("total_writes")==563uL&&remainingSummary.u("atomic")==0uL&&remainingSummary.u("device_io")==0uL&&remainingSummary.u("old_executed")==0uL&&remainingSummary.u("clone_tid")==0uL)
 val summary=es.single{it.kind=="tail-summary"};val er=10;val ew=2;val ec=3;require(summary.u("private_metrics")==0uL&&summary.u("reads")==er.toULong()&&summary.u("writes")==ew.toULong()&&summary.u("checkpoints")==ec.toULong()&&summary.u("total_writes")==563uL&&summary.u("calibration_executed")==0uL&&summary.u("clone_tid")==0uL&&summary.u("atomic")==0uL&&summary.u("old_executed")==0uL)
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
    val convergences=es.filter{it.kind=="loader-terminal-converge"};require(convergences.size==2);val converge=convergences.first();require(converge.u("stopping_tid")==pid&&
        es.indexOf(converge)<es.indexOf(captures[2])&&es.subList(es.indexOf(loaderCps.last()),es.indexOf(captures[2])).none{it.kind=="runtime-resume"})
    val firstConvergenceEvents=es.subList(es.indexOf(converge),es.indexOf(captures[2]));val convergenceInterrupts=firstConvergenceEvents.filter{it.kind=="loader-terminal-interrupt"};val convergenceStops=firstConvergenceEvents.filter{it.kind=="terminal-interrupt-stop"}
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
    require(es.filter { it.kind.startsWith("loader-") }.map { it.kind }.take(expectedLoaderKinds.size) == expectedLoaderKinds) {
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

    val ap=profile();require(ap.operations.size==99&&ap.operations.count{it.read}==2&&ap.guards.size==175&&ap.finals.size==33)
    val adcMode=es.single{it.kind=="adc-input-mode"};require(adcMode.s("scope")=="stock"&&adcMode.u("arm")==0uL&&adcMode.u("profile")==1uL&&adcMode.u("file_count")==9uL&&adcMode.u("binding_count")==16uL&&adcMode.u("map_limit")==2048uL&&adcMode.u("map_byte_limit")==262144uL&&adcMode.u("raw_max")==16384uL&&adcMode.u("no_resume")==1uL)
    val adcNames=listOf("matrix","setting","drvparam","series","config","sample-entry","shadow-low","shadow-high","global-inputs");val adcLengths=listOf(0xe60,0x1c71,0x10,0x12c,0x3c,8,0x3c,0x74,0x2c)
    val adcCaptures=es.filter{it.kind=="adc-input-capture"};require(adcCaptures.size==9)
    fun fnv(data:ByteArray):ULong{var h=14695981039346656037uL;for(v in data){h=h xor(v.toInt()and 255).toULong();h*=1099511628211uL};return h}
    adcNames.forEachIndexed{i,name->val data=bytes("adc-input-$name.bin");val e=adcCaptures[i];require(data.size==adcLengths[i]&&e.u("index")==i.toULong()&&e.s("name")=="adc-input-$name.bin"&&e.u("length")==data.size.toULong()&&e.u("completed")==data.size.toULong()&&e.u("hash_fnv1a64")==fnv(data)&&e.u("match")==1uL)}
    val adcBindings=es.filter{it.kind=="adc-input-binding"};require(adcBindings.size==16&&adcBindings.map{it.u("index")}==(0..15).map{it.toULong()})
    val adcSlots=listOf(0xb8eea8uL,0xb8cb08uL,0xb8c9d0uL,0xb8b940uL,0xb8cae0uL,0xb8ec98uL,0xb8e680uL,0xb8da70uL,0xb8d288uL,0xb8de88uL,0xb8ed38uL,0xb8dd30uL,0xb8db70uL,0xb8d5b8uL,0xb8ddc0uL,0xb8ccd8uL);val adcTargets=listOf(0x9948bcuL,0x3cb45bcuL,0x3cb45a6uL,0x3cb457cuL,0x3cb45b8uL,0x3cb45ecuL,0x3cb45d8uL,0x3cb4534uL,0x3cb44fcuL,0xbe1138uL,0xbe1144uL,0xbe113cuL,0xbe1148uL,0xbe1140uL,0xbe114cuL,0xbe1150uL);val adcWidths=listOf(312uL,4uL,16uL,16uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL,4uL)
    adcBindings.forEachIndexed{i,e->require(e.u("slot")==base+adcSlots[i]&&e.u("expected_target")==base+adcTargets[i]&&e.u("actual_target")==base+adcTargets[i]&&e.u("target_width")==adcWidths[i]&&e.u("relocation_type")==0x401uL&&e.u("match")==1uL)}
    val maps=parseMaps("adc-input-maps.txt");val adcMapEvent=es.single{it.kind=="adc-input-maps"};val mapData=bytes("adc-input-maps.txt");require(adcMapEvent.u("bytes")==mapData.size.toULong()&&adcMapEvent.u("records")==maps.size.toULong()&&adcMapEvent.u("maximum_bytes")==262144uL&&adcMapEvent.u("maximum_records")==2048uL&&adcMapEvent.u("overflow")==0uL&&adcMapEvent.u("read_error")==0uL)
    val adcMapChecks=es.filter{it.kind=="adc-input-map"};require(adcMapChecks.size==41)
    adcMapChecks.forEach{e->val address=e.u("address");val length=e.u("length");val enclosing=maps.firstOrNull{address>=it.start&&add(address,length)<=it.end};require(e.u("map_start")== (enclosing?.start?:0uL)&&e.u("map_end")== (enclosing?.end?:0uL)&&e.u("readable")== (if(enclosing?.readable==true)1uL else 0uL)&&e.u("match")== (if(contained(maps,address,length))1uL else 0uL))}
    val setting=Little(bytes("adc-input-setting.bin"));val series=Little(bytes("adc-input-series.bin"));val globals=Little(bytes("adc-input-global-inputs.bin"));var channelMask=0;for(channel in 0..3)if((0..7).any{setting.u8(channel*0xc0+0xb4+it)and 1!=0})channelMask=channelMask or(1 shl channel);if(setting.u8(0x1c70)and 1!=0)channelMask=15
    val selector0=series.u32(0);val selector1=series.u32(4);val special=globals.u32(12);val effective=if(selector1==4000uL&&special==1uL)2000uL else selector1;val selected=(0..8).firstOrNull{series.u32(12+32*it)==selector0&&series.u32(16+32*it)==effective};require(selected==2);val row=12+32*selected;val tablePointer=series.u64(row+8);val configPointer=series.u64(row+24);val bound=series.u32(row+16);require(bound in 1uL..16uL);val normalized=if(channelMask.toULong()>bound-1uL)0uL else channelMask.toULong();require(tablePointer==base+0xb8f808uL&&configPointer==base+0xb8f478uL&&globals.u64(0)==mapping)
    val expectedMapKeys=buildList<Pair<String,Int>>{for(i in 0..15){add("binding-slot" to i);add("binding-target" to i)};for(i in listOf(0,1,2,3,6,7,8))add("fixed" to i);add("config" to 4);add("sample-entry" to 5)};require(adcMapChecks.map{it.s("category") to it.u("index").toInt()}==expectedMapKeys)
    adcMapChecks.take(32).forEachIndexed{i,e->val bindingIndex=i/2;if(i%2==0)require(e.u("address")==base+adcSlots[bindingIndex]&&e.u("length")==8uL)else require(e.u("address")==base+adcTargets[bindingIndex]&&e.u("length")==adcWidths[bindingIndex])}
    val adcCaptureAddresses=listOf(base+0x10c9dc4uL,base+0x10bee58uL,base+0x10c4840uL,base+0xb8f4e4uL,configPointer,tablePointer+16uL*normalized,base+0x3cb44fcuL,base+0x3cb457cuL,base+0xbe1128uL);adcCaptures.forEachIndexed{i,e->require(e.u("address")==adcCaptureAddresses[i])};adcMapChecks.drop(32).forEachIndexed{i,e->val captureIndex=listOf(0,1,2,3,6,7,8,4,5)[i];require(e.u("address")==adcCaptureAddresses[captureIndex]&&e.u("length")==adcLengths[captureIndex].toULong())}
    val selector=es.single{it.kind=="adc-input-selector"};require(selector.u("selector0")==selector0&&selector.u("selector1")==selector1&&selector.u("effective_selector1")==effective&&selector.u("special_flag")==special&&selector.u("selected_index")==2uL&&selector.u("fallback")==0uL&&selector.u("record")==base+0xb8f4e4uL+76uL)
    val pointers=es.filter{it.kind=="adc-input-pointer"};require(pointers.size==2);pointers.forEachIndexed{i,e->val pointer=if(i==0)tablePointer else configPointer;require(e.s("category")== (if(i==0)"table" else "config")&&e.u("index")==2uL&&e.u("site")==base+0xb8f4e4uL+76uL+(if(i==0)8uL else 24uL)&&e.u("actual")==pointer&&e.u("expected")==pointer&&e.u("relocation_type")==0x101uL&&e.u("match")==1uL)}
    val adcState=es.single{it.kind=="adc-input-state"};val config=Little(bytes("adc-input-config.bin"));val sample=Little(bytes("adc-input-sample-entry.bin"));val drv=Little(bytes("adc-input-drvparam.bin"));require(adcState.u("sample_count")==bound&&adcState.u("raw_mask")==channelMask.toULong()&&adcState.u("normalized_mask")==normalized&&adcState.u("mode")==sample.u32(4)&&adcState.u("config_adcs_delay")==config.u32(0x20)&&adcState.u("config_point_time")==config.u32(0x38)&&adcState.u("sample_rate")==drv.u64(8)&&adcState.u("mapped_base_value")==mapping)
    val adcSummary=es.single{it.kind=="adc-input-summary"};require(adcSummary.u("captures")==9uL&&adcSummary.u("requested_bytes")==11565uL&&adcSummary.u("completed_bytes")==11565uL&&adcSummary.u("selected_index")==2uL&&adcSummary.u("fallback")==0uL&&adcSummary.u("modeled_reads")==0uL&&adcSummary.u("modeled_writes")==0uL&&adcSummary.u("resumes")==0uL&&adcSummary.u("bindings")==16uL)
    val sourceBase=listOf(base+0x10cd734uL,base+0x10bee58uL,base+0x10c4840uL,base+0xb8f478uL,base+0xb8f808uL,base+0x3cb44fcuL,base+0x3cb457cuL,base+0xbe1128uL,base+0xb8f4e4uL,base+0x9948bcuL)
    val rawSource=mapOf(0 to bytes("native-loader-terminal-adc.bin"),1 to bytes("adc-input-setting.bin"),2 to bytes("adc-input-drvparam.bin"),3 to bytes("adc-input-config.bin"),4 to bytes("adc-input-sample-entry.bin"),5 to bytes("adc-input-shadow-low.bin"),6 to bytes("adc-input-shadow-high.bin"),7 to bytes("adc-input-global-inputs.bin"),8 to bytes("adc-input-series.bin"))
    fun rawValue(data:ByteArray,offset:Int,width:Int):ULong{require(offset>=0&&offset+width<=data.size);var value=0uL;for(i in 0 until width)value=value or((data[offset+i].toInt()and 255).toULong() shl(8*i));return value}
    mapOf(1 to 1,2 to 2,8 to 3,3 to 4,4 to 5,5 to 6,6 to 7,7 to 8).forEach{(source,capture)->require(adcCaptures[capture].u("address")==sourceBase[source])}
    val apMode=es.single{it.kind=="adc-sequence-mode"};require(apMode.s("scope")=="stock"&&apMode.u("arm")==0uL&&apMode.u("operations")==99uL&&apMode.u("guards")==175uL&&apMode.u("final_shadows")==33uL&&apMode.u("synthetic0")==0x11234uL&&apMode.u("synthetic1")==0uL&&apMode.u("return_pc")==base+0x333bacuL&&apMode.u("stock_return_relative")==0x333bacuL&&apMode.u("sleep_observation")==0uL)
    val entryGuards=es.filter{it.kind=="adc-sequence-entry-guard"};require(entryGuards.size==175)
    entryGuards.forEachIndexed{i,e->val g=ap.guards[i];require(g.index==i&&e.u("index")==i.toULong()&&e.u("source")==g.source.toULong()&&e.u("offset")==g.offset&&e.u("address")==sourceBase[g.source]+g.offset&&e.u("width")==g.width.toULong()&&e.u("actual")==g.expected&&e.u("expected")==g.expected&&e.u("read_ok")==1uL&&e.u("match")==1uL);rawSource[g.source]?.let{require(rawValue(it,g.offset.toInt(),g.width)==g.expected)};if(g.source==9)require(g.width==4&&elf.word(0x9948bcuL+g.offset)==g.expected)}
    val apBinding=es.single{it.kind=="adc-sequence-entry-binding"};require(apBinding.u("selected_row")==2uL&&apBinding.u("expected_row")==2uL&&apBinding.u("mapped_base")==mapping&&apBinding.u("expected_mapping")==mapping)
    val apEntryRegs=regs(es.single{it.kind=="adc-sequence-entry-registers"});require(apEntryRegs.tid==pid&&apEntryRegs.relative==0x333ba8uL&&same(apEntryRegs,regs(loaderDebugRegs.last())))
    val apDebugBefore=es.filter{it.kind=="adc-sequence-debug-before"};val apDebugRequest=es.filter{it.kind=="adc-sequence-debug-request"};val apDebugSet=es.filter{it.kind=="adc-sequence-debug-set"};val apDebugAfter=es.filter{it.kind=="adc-sequence-debug-after"};require(apDebugBefore.size==2&&apDebugRequest.size==2&&apDebugSet.size==2&&apDebugAfter.size==2)
    dump(apDebugBefore[0],0uL,0x1e5uL,false);dump(apDebugRequest[0],base+0x333bacuL,0x1e5uL,true);require(apDebugSet[0].u("result")==0uL);dump(apDebugAfter[0],base+0x333bacuL,0x1e4uL,false)
    val apResume=es.single{it.kind=="adc-sequence-resume-group"};require(apResume.u("threads")==tracked.size.toULong()&&apResume.u("leader")==pid)
    val accesses=es.filter{it.kind=="adc-sequence-access"};val transfers=es.filter{it.kind=="adc-sequence-write"||it.kind=="adc-sequence-read"};val beforeRegs=es.filter{it.kind=="adc-sequence-before-registers"};val afterRegs=es.filter{it.kind=="adc-sequence-after-registers"};require(accesses.size==99&&transfers.size==99&&beforeRegs.size==99&&afterRegs.size==99)
    require(elf.word(0x270604uL)==0xb9400109uL&&elf.word(0x27043cuL)==0xb9000109uL)
    ap.operations.forEachIndexed{i,op->val access=accesses[i];val transfer=transfers[i];val before=regs(beforeRegs[i]);val after=regs(afterRegs[i]);val pc=base+(if(op.read)0x270604uL else 0x27043cuL);val opcode=if(op.read)0xb9400109uL else 0xb9000109uL
        require(op.index==i&&access.u("index")==i.toULong()&&access.u("tid")==pid&&access.u("signal")==11uL&&access.u("si_code")==2uL&&access.u("address")==mapping+op.offset&&access.u("offset")==op.offset&&access.u("pc")==pc&&access.u("opcode")==opcode)
        if(!op.read)require(access.u("operand").toUInt().toULong()==op.value)
        require(transfer.kind==(if(op.read)"adc-sequence-read" else "adc-sequence-write")&&transfer.u("index")==i.toULong()&&transfer.u("sequence_index")==op.sequenceIndex&&transfer.u("tid")==pid&&transfer.u("offset")==op.offset&&transfer.u("value")==op.value&&transfer.u("width")==4uL&&transfer.u("synthetic_response")==if(op.read)1uL else 0uL)
        require(before.tid==pid&&after.tid==pid&&before.pc==pc&&before.relative==pc-base&&after.relative==before.relative+4uL&&before.x[8]==mapping+op.offset&&before.x[9].toUInt().toULong()==access.u("operand").toUInt().toULong()&&completed(before,after,if(op.read)op.value else null))
        val accessAt=es.indexOf(access);val fault=es[accessAt-2];val faultRegs=es[accessAt-1];require(fault.kind=="mapped-fault"&&fault.u("tid")==pid&&fault.u("signal")==11uL&&fault.u("si_code")==2uL&&fault.u("address")==mapping+op.offset&&fault.u("offset")==op.offset&&fault.u("opcode")==opcode&&faultRegs.kind=="fault-registers"&&same(regs(faultRegs),before));require(es[accessAt+1]===beforeRegs[i]&&es[accessAt+2]===transfer&&es[accessAt+3]===afterRegs[i]);val resumed=es[accessAt+4];require(resumed.kind=="runtime-resume"&&resumed.u("tid")==pid&&resumed.u("operation")==7uL)
    }
    val apReturn=es.single{it.kind=="adc-sequence-return"};require(apReturn.u("tid")==pid&&apReturn.u("pc")==base+0x333bacuL&&apReturn.u("expected_pc")==base+0x333bacuL&&apReturn.u("si_code")==4uL&&apReturn.u("address")==base+0x333bacuL&&apReturn.u("opcode")==0x5285070auL&&apReturn.u("status")==0uL&&apReturn.u("operations")==99uL&&elf.word(0x333bacuL)==0x5285070auL)
    val apReturnRegs=regs(es.single{it.kind=="adc-sequence-return-registers"});require(apReturnRegs.tid==pid&&apReturnRegs.pc==base+0x333bacuL&&apReturnRegs.relative==0x333bacuL&&apReturnRegs.x[0].toUInt()==0u)
    val finalGuards=es.filter{it.kind=="adc-sequence-final-shadow"};require(finalGuards.size==33)
    finalGuards.forEachIndexed{i,e->val g=ap.finals[i];require(e.u("index")==i.toULong()&&e.u("source")==g.source.toULong()&&e.u("offset")==g.offset&&e.u("address")==sourceBase[g.source]+g.offset&&e.u("width")==g.width.toULong()&&e.u("actual")==g.expected&&e.u("expected")==g.expected&&e.u("read_ok")==1uL&&e.u("match")==1uL)}
    val secondConverge=convergences.last();val secondConvergeAt=es.indexOfLast{it.kind=="loader-terminal-converge"};require(secondConverge.u("stopping_tid")==pid&&es.indexOf(apReturn)<secondConvergeAt&&secondConvergeAt<es.indexOf(finalGuards.first()))
    val secondSlice=es.subList(secondConvergeAt,es.indexOf(finalGuards.first()));val secondInterrupts=secondSlice.filter{it.kind=="loader-terminal-interrupt"};val secondStops=secondSlice.filter{it.kind=="terminal-interrupt-stop"};require(secondInterrupts.map{it.u("tid")}.toSet()==tracked.toSet()-pid&&secondStops.map{it.u("tid")}.toSet()==tracked.toSet()-pid)
    dump(apDebugBefore[1],base+0x333bacuL,0x1e4uL,false);dump(apDebugRequest[1],0uL,0uL,true);require(apDebugSet[1].u("result")==0uL);dump(apDebugAfter[1],0uL,0x1e5uL,false)
    val apFinalRegs=regs(es.single{it.kind=="adc-sequence-final-registers"});require(apFinalRegs.tid==pid&&apFinalRegs.relative==0x333bacuL&&same(apReturnRegs,apFinalRegs))
    val apComplete=es.single{it.kind=="adc-sequence-complete"};require(apComplete.u("return_instruction_executed")==0uL)
    val apSummary=es.single{it.kind=="adc-sequence-summary"};require(apSummary.u("operations")==99uL&&apSummary.u("writes")==97uL&&apSummary.u("reads")==2uL&&apSummary.u("private_metrics")==0uL&&apSummary.u("worker_ack")==0uL&&apSummary.u("atomic")==0uL&&apSummary.u("raw0")==0uL&&apSummary.u("raw1")==0uL&&apSummary.u("protocol0")==0uL&&apSummary.u("protocol1")==0uL&&apSummary.u("private_reads")==0uL&&apSummary.u("old_executed")==0uL)
    val expectedApKinds=buildList<String>{add("adc-sequence-mode");repeat(175){add("adc-sequence-entry-guard")};add("adc-sequence-entry-binding");addAll(listOf("adc-sequence-debug-before","adc-sequence-debug-request","adc-sequence-debug-set","adc-sequence-debug-after","adc-sequence-entry-registers","adc-sequence-resume-group"));ap.operations.forEach{op->add("adc-sequence-access");add("adc-sequence-before-registers");add(if(op.read)"adc-sequence-read" else "adc-sequence-write");add("adc-sequence-after-registers")};addAll(listOf("adc-sequence-return","adc-sequence-return-registers"));repeat(33){add("adc-sequence-final-shadow")};addAll(listOf("adc-sequence-debug-before","adc-sequence-debug-request","adc-sequence-debug-set","adc-sequence-debug-after","adc-sequence-final-registers","adc-sequence-complete","adc-sequence-summary"))};require(es.filter{it.kind.startsWith("adc-sequence-")}.map{it.kind}==expectedApKinds)
    require(es.none{it.kind=="adc-sequence-rejected"})
    val phaseResumes=es.subList(es.indexOf(apResume)+1,es.indexOf(apReturn)).filter{it.kind=="runtime-resume"};require(phaseResumes.size==tracked.size+99&&phaseResumes.take(tracked.size).map{it.u("tid")}.toSet()==tracked.toSet()&&phaseResumes.take(tracked.size).all{it.u("operation")==7uL}&&phaseResumes.drop(tracked.size).all{it.u("tid")==pid&&it.u("operation")==7uL})
    require(es.subList(es.indexOf(apReturn),es.size).none{it.kind=="runtime-resume"})
    val q=es.single{it.kind=="terminal-quiesce"};require(q.u("stopping_tid")==pid&&es.indexOf(apSummary)<es.indexOf(q));val terminalTids=inventory("terminal",q.u("stopping_tid"));require(terminalTids==tracked.toSet());val terminalState=es.single{it.kind=="terminal-state"};require(es.indexOf(q)<es.indexOf(terminalState)&&terminalState.u("object")==obj&&terminalState.u("value")==0x0123456789abcdefuL&&terminalState.u("responses")==2uL&&terminalState.u("modeled_writes")==563uL);require(es.none{it.kind in setOf("terminal-cleanup-deadline","unexpected-runtime-signal")});val cleanup=es.single{it.kind=="group-cleanup"};val reaped=es.filter{it.kind=="group-reaped"};require(reaped.size==cleanup.u("reaped_count").toInt()&&cleanup.u("expected_count")==cleanup.u("reaped_count")&&cleanup.u("wait_result").toLong()==-10L&&reaped.all{it.u("status")==9uL}&&reaped.map{it.u("tid")}.toSet()==terminalTids&&reaped.map{it.u("tid")}.distinct().size==reaped.size&&es.last()==cleanup)
    require(text("native-status.toml").trim()=="exit_code = 78")
    require(hash("group-control.elf")==captureNativeSha256&&bytes("group-control.elf").contentEquals(bytes("group-executed.elf")))
    val result=text("result.toml");expectFields(result,mapOf("schema_version" to "\"mho900-lab.guest-run/1\"","run_id" to "\"stock-adc-sequence-01\"","boot" to "\"completed\"","mode" to "\"adcsequencemodel\"","inspection" to "\"completed\"","runner_exit" to "0","final_health_attempted" to "true","initial_index_exit" to "0"))
    expectFields(text("cleanup-status.toml"),mapOf("emulator_console_exit" to "0","adb_server_exit" to "0"))
    expectFields(text("runner-command-status.toml"),mapOf("boot_getprop_exit" to "0","boot_kernel_exit" to "0","final_logcat_exit" to "0"))
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
    zeroStatus("adc-input-pulls.toml",listOf("matrix","setting","drvparam","series","config","sample-entry","shadow-low","shadow-high","global-inputs","maps"))
    val staged=text("userdata-staging.toml")
    expectFields(staged,mapOf("source_sha256" to "\"effba4cc839206b25dee05455f6c49b9fad0ca90d524812fd4bbc5d3c02636d2\"","staged_sha256" to "\"effba4cc839206b25dee05455f6c49b9fad0ca90d524812fd4bbc5d3c02636d2\"","independent_inode" to "true","staged_link_count" to "1","minimum_free_kib" to "2097152"))
    require(field(staged,"source_identity").substringBeforeLast(':')!=field(staged,"staged_identity").substringBeforeLast(':'))
    for(name in listOf("free_kib_before","free_kib_after"))require(Regex("(?m)^$name = ([0-9]+)$").find(staged)!!.groupValues[1].toLong()>=2097152)
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
    val helperConsumed=listOf(
        "admission-hook.txt","control-unrelated.txt","control-different-signer.txt","control-changed-bytes.txt","unhooked-stock.txt","detached-stock-update.txt","install.txt","installed-signature.txt","control-changed-bytes-signature.txt","zygote-maps.txt","process-labels.txt","application-logcat.txt","activities.txt","crash-logcat.txt","frida-detach-status.toml","frida-inspection.txt","scan-package-oatdump.txt","packages.xml","app-pid.txt","native-before.txt",
        "native-snapshot-composite-status.toml","native-snapshot-composite-error.txt","native-snapshot-composite.txt","native-snapshot-cmdline-status.toml","native-snapshot-cmdline-error.txt","native-snapshot-cmdline.txt","native-snapshot-label-status.toml","native-snapshot-label-error.txt","native-snapshot-label.txt","native-snapshot-maps-status.toml","native-snapshot-maps-error.txt","native-snapshot-maps.txt",
        "fixture-before-mounts.txt","fixture-before-mountinfo.txt","fixture-before-stat.txt","fixture-before-labels.txt","fixture-before-empty.txt","fixture-before-pid.txt","fixture-after-root-pid.txt","fixture-enforcing.txt","fixture-processes-before.txt","fixture-packages-before.txt","fixture-command-status.toml","fixture-after-mounts.txt","fixture-after-mountinfo.txt","fixture-after-stat.txt","fixture-after-labels.txt","fixture-absent-paths.txt","calibration-lsb-stock.bin","calibration-lsb-roundtrip.bin","calibration-vertical-stock.bin","calibration-vertical-roundtrip.bin","fixture-result.toml","calibration-loader-candidate.toml"
    )
    helperConsumed.forEach{require(Files.isRegularFile(resolved(it))&&!Files.isSymbolicLink(resolved(it)))}
    val indexLines=Files.readAllLines(run.resolve("evidence-sha256.txt"));val indexed=indexLines.map{line->require(line.length>66&&line.substring(64,66)=="  ");val file=Path.of(line.substring(66)).toAbsolutePath().normalize();require(file.startsWith(run)&&Files.isRegularFile(file)&&!Files.isSymbolicLink(file)&&hash(Files.readAllBytes(file))==line.take(64));file};require(indexed.distinct().size==indexed.size)
    val consumed=artifacts.map{run.resolve(it.runPath).toAbsolutePath().normalize()}+consumedPaths
    require(consumed.all{it in indexed})
}
verify()
println("schema_version = \"mho900-lab.stock-adc-sequence-verification/1\"")
println("result = \"accepted\"")
println("operations = 99")
println("writes = 97")
println("synthetic_reads = 2")
println("terminal_relative_pc = \"0x333bac\"")
