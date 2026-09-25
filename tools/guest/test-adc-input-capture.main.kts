// Synthetic host controls for the capture-phase checker. No guest evidence is rewritten.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size==1){"Usage: test-adc-input-capture.main.kts NEW_OUTPUT"}
val out=Path.of(args[0]).toAbsolutePath();require(!Files.exists(out));Files.createDirectories(out)
val checker=Path.of("tools/guest/VerifyAdcInputCapture.main.kts").toAbsolutePath()
val base=0x70000000L;val arenaEnd=base+0x4000000L
val names=listOf("matrix","setting","drvparam","series","config","sample-entry","shadow-low","shadow-high","global-inputs")
val lengths=listOf(0xe60,0x1c71,0x10,0x12c,0x3c,8,0x3c,0x74,0x2c)
val slots=listOf(0xb8eea8,0xb8cb08,0xb8c9d0,0xb8b940,0xb8cae0,0xb8ec98,0xb8e680,0xb8da70,0xb8d288,0xb8de88,0xb8ed38,0xb8dd30,0xb8db70,0xb8d5b8,0xb8ddc0,0xb8ccd8)
val targets=listOf(0x9948bc,0x3cb45bc,0x3cb45a6,0x3cb457c,0x3cb45b8,0x3cb45ec,0x3cb45d8,0x3cb4534,0x3cb44fc,0xbe1138,0xbe1144,0xbe113c,0xbe1148,0xbe1140,0xbe114c,0xbe1150)
val widths=listOf(312,4,16,16,4,4,4,4,4,4,4,4,4,4,4,4)
val tables=listOf(0xb8f808,0xb8f808,0xb8f808,0xb8f908,0xb8fa08,0xb8fb08,0xb8fc08,0xb8fc08,0xb8fc08)
val configs=listOf(0xb8f40c,0xb8f40c,0xb8f478,0xb8f2c8,0xb8f3a0,0xb8f40c,0,0,0)
fun hex(v:Long)="0x"+v.toULong().toString(16)
fun fnv(b:ByteArray):ULong{var h=14695981039346656037uL;b.forEach{h=(h xor (it.toInt() and 255).toULong())*1099511628211uL};return h}
data class Case(val name:String,val accepted:Boolean)
val cases=listOf(Case("normal",true),Case("fallback",true),Case("substitution",true),Case("normalized",true),Case("bode",true),Case("altered-bytes-reindexed",false),Case("pointer",false),Case("address",false),Case("map",false),Case("bound",false),Case("missing-binding",false),Case("resume",false),Case("state",false),Case("summary",false),Case("missing-capture",false),Case("truncated",false),Case("unsigned-bound",false))
val results=StringBuilder("schema_version = \"mho900-lab.adc-input-host-controls/1\"\nguest_launched = false\n")
for(case in cases){
    val dir=out.resolve(case.name);Files.createDirectory(dir)
    val data=lengths.mapIndexed{i,n->ByteArray(n){(it*3+i).toByte()}}
    fun p32(i:Int,o:Int,v:Long){for(j in 0..3)data[i][o+j]=(v ushr (8*j)).toByte()}
    fun p64(i:Int,o:Int,v:Long){for(j in 0..7)data[i][o+j]=(v ushr (8*j)).toByte()}
    for(c in 0..3)for(j in 0..7)data[1][c*0xc0+0xb4+j]=0
    data[1][0xb4]=1;data[1][0x1c70]=if(case.name=="bode")1 else 0
    if(case.name=="normalized")for(c in 0..3)data[1][c*0xc0+0xb4]=1
    val mask=if(case.name in listOf("normalized","bode"))15 else 1
    val count=if(case.name=="normalized")4 else if(case.name=="bound")17 else if(case.name=="unsigned-bound")-1 else 16
    val normalized=if(mask>=count)0 else mask
    val row=if(case.name in listOf("fallback","substitution"))0 else 2
    val s0=if(case.name=="fallback")0xdead else 8;val s1=if(case.name=="fallback")0xbeef else if(case.name=="substitution")4000 else 900
    val effective=if(s1==4000)2000 else s1;val special=if(case.name=="substitution")1 else 0
    p32(3,0,s0.toLong());p32(3,4,s1.toLong());p32(8,12,special.toLong());p64(8,0,0x12340000L)
    for(i in 0..8){val o=12+32*i;p32(3,o,if(i==2||i==0&&case.name=="substitution")8 else (100+i).toLong());p32(3,o+4,if(i==2)900 else if(i==0&&case.name=="substitution")2000 else (200+i).toLong());p64(3,o+8,base+tables[i]);p32(3,o+16,count.toLong());p64(3,o+24,if(configs[i]==0)0 else base+configs[i])}
    val table=base+tables[row]+if(case.name=="pointer")1 else 0;val config=base+configs[row];p64(3,12+32*row+8,table)
    p64(2,8,2000000000);p32(4,0x20,31);p32(4,0x38,7);p32(5,4,4)
    val addresses=listOf(base+0x10c4f30+0x4e94,base+0x10bee58,base+0x10c4840,base+0xb8f4e4,config,table+16*normalized,base+0x3cb44fc,base+0x3cb457c,base+0xbe1128)
    val events=StringBuilder();fun e(kind:String,vararg fields:Pair<String,Long>,strings:List<Pair<String,String>> = emptyList()){events.append("\n[[events]]\nkind = \"$kind\"\n");fields.forEach{events.append("${it.first} = \"${hex(it.second)}\"\n")};strings.forEach{events.append("${it.first} = \"${it.second}\"\n")}}
    e("model-binding","base" to base);e("mapping-result","base" to 0x12340000L)
    for(i in 0..3){e("loader-checkpoint","index" to i.toLong(),"relative_pc" to 0x333ba8L,"opcode" to 0x97fb9b9eL);e("loader-checkpoint-registers","x00" to base+0x10c4f30)}
    repeat(5){e("loader-capture","index" to it.toLong())}
    e("adc-input-mode","arm" to 0,"profile" to 1,"file_count" to 9,"binding_count" to 16,"map_limit" to 2048,"map_byte_limit" to 262144,"raw_max" to 16384,"no_resume" to 1,strings=listOf("scope" to "stock"))
    val mapText="${base.toString(16)}-${arenaEnd.toString(16)} ${if(case.name=="map")"---p" else "rw-p"} 00000000 00:00 0\n"
    Files.writeString(dir.resolve("adc-input-maps.txt"),mapText)
    e("adc-input-maps","bytes" to mapText.toByteArray().size.toLong(),"records" to 1,"maximum_bytes" to 262144,"maximum_records" to 2048,"overflow" to 0,"read_error" to 0)
    fun map(i:Int,category:String,address:Long,length:Long){e("adc-input-map","index" to i.toLong(),"address" to address,"length" to length,"map_start" to base,"map_end" to arenaEnd,"readable" to 1,"match" to 1,strings=listOf("category" to category))}
    for(i in 0..15){map(i,"binding-slot",base+slots[i],8);if(case.name!="missing-binding"||i!=7)e("adc-input-binding","index" to i.toLong(),"slot" to base+slots[i],"actual_target" to base+targets[i],"expected_target" to base+targets[i],"target_width" to widths[i].toLong(),"relocation_type" to 0x401,"match" to 1);map(i,"binding-target",base+targets[i],widths[i].toLong())}
    for(i in listOf(0,1,2,3,6,7,8))map(i,"fixed",addresses[i],lengths[i].toLong())
    val record=addresses[3]+12+32*row
    e("adc-input-selector","selector0" to s0.toLong(),"selector1" to s1.toLong(),"effective_selector1" to effective.toLong(),"special_flag" to special.toLong(),"selected_index" to row.toLong(),"fallback" to if(case.name=="fallback")1 else 0,"record" to record)
    for(i in 0..1)e("adc-input-pointer","index" to row.toLong(),"site" to record+if(i==0)8 else 24,"actual" to if(i==0)table else config,"expected" to if(i==0)table else config,"relocation_type" to 0x101,"match" to 1,strings=listOf("category" to if(i==0)"table" else "config"))
    map(4,"config",config,60);map(5,"sample-entry",addresses[5],8)
    e("adc-input-state","sample_count" to count.toLong(),"raw_mask" to mask.toLong(),"normalized_mask" to normalized.toLong(),"mode" to if(case.name=="state")5 else 4,"config_adcs_delay" to 31,"config_point_time" to 7,"sample_rate" to 2000000000,"mapped_base_value" to 0x12340000)
    for(i in 0..8){if(case.name!="missing-capture"||i!=7)e("adc-input-capture","index" to i.toLong(),"address" to addresses[i]+if(case.name=="address"&&i==0)4 else 0,"length" to lengths[i].toLong(),"completed" to lengths[i].toLong(),"chunks" to 1,"result" to lengths[i].toLong(),"hash_fnv1a64" to fnv(data[i]).toLong(),"match" to 1,strings=listOf("name" to "adc-input-${names[i]}.bin"));if(case.name=="altered-bytes-reindexed"&&i==0)data[i][5]=(data[i][5].toInt() xor 1).toByte();Files.write(dir.resolve("adc-input-${names[i]}.bin"),if(case.name=="truncated"&&i==0)data[i].copyOf(data[i].size-1)else data[i])}
    if(case.name=="resume")e("runtime-resume","tid" to 1)
    e("adc-input-summary","captures" to 9,"requested_bytes" to 11565,"completed_bytes" to if(case.name=="summary")11564 else 11565,"bindings" to 16,"maps_observed" to 1,"selected_index" to row.toLong(),"fallback" to if(case.name=="fallback")1 else 0,"modeled_reads" to 0,"modeled_writes" to 0,"resumes" to 0)
    e("loader-summary");Files.writeString(dir.resolve("native-events.toml"),events);Files.write(dir.resolve("native-loader-terminal-adc.bin"),ByteArray(1936))
    val indexed=Files.list(dir).use{stream->stream.sorted().toList()};Files.writeString(dir.resolve("evidence-sha256.txt"),indexed.joinToString(""){p->HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(p)))+"  $p\n"})
    val pb=ProcessBuilder("kotlinc","-script",checker.toString(),"--",dir.toString());pb.environment().remove("KOTLIN_RUNNER");pb.redirectOutput(dir.resolve("verification.stdout").toFile());pb.redirectError(dir.resolve("verification.stderr").toFile());val rc=pb.start().waitFor()
    results.append("\n[[cases]]\nname = \"${case.name}\"\nexpected_accept = ${case.accepted}\nexit_code = $rc\nmatched = ${(rc==0)==case.accepted}\n")
    Files.writeString(out.resolve("results.toml"),results);require((rc==0)==case.accepted){"case ${case.name} exited $rc"}
}
println("All ${cases.size} capture-phase host controls matched.")
