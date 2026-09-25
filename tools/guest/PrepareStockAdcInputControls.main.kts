import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size==3){"Usage: PrepareStockAdcInputControls.main.kts PRIOR_STOCK_RUN PHASE_CONTROLS NEW_OUTPUT"}
val repo=Path.of("").toAbsolutePath();val source=Path.of(args[0]).toAbsolutePath();val out=Path.of(args[2]).toAbsolutePath();require(!Files.exists(out));Files.createDirectory(out);val run=out.resolve("base");Files.createDirectory(run)
fun hash(b:ByteArray)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b))
fun copy(a:Path,b:Path){require(Files.isRegularFile(a)&&!Files.isSymbolicLink(a));Files.createDirectories(b.parent);require(!Files.exists(b));val p=ProcessBuilder("/bin/cp","-c",a.toString(),b.toString()).start();require(p.waitFor()==0);require(Files.getAttribute(b,"unix:nlink").toString()=="1"&&Files.getAttribute(a,"unix:ino")!=Files.getAttribute(b,"unix:ino"))}
val originals=Files.readAllLines(source.resolve("evidence-sha256.txt")).associate{val p=Path.of(it.substring(66));require(p.startsWith(source)&&hash(Files.readAllBytes(p))==it.take(64));p to it.take(64)}
originals.keys.forEach{copy(it,run.resolve(source.relativize(it)))}
fun write(name:String,bytes:ByteArray){val p=run.resolve(name);Files.createDirectories(p.parent);if(Files.exists(p))require(Files.getAttribute(p,"unix:nlink").toString()=="1");Files.write(p,bytes)}
fun write(name:String,text:String)=write(name,text.toByteArray())
fun from(name:String,src:String)=write(name,Files.readAllBytes(repo.resolve(src)))
val old=Files.readString(run.resolve("native-events.toml"));val model=old.split("[[events]]").single{it.contains("kind = \"model-binding\"")};val mapping=old.split("[[events]]").single{it.contains("kind = \"mapping-result\"")}
fun value(block:String,k:String)=Regex("(?m)^$k = \"0x([0-9a-f]+)\"$").find(block)!!.groupValues[1].toULong(16)
val base=value(model,"base");val mapped=value(mapping,"base");val delta=base-0x70000000uL
val fixture=Path.of(args[1]).toAbsolutePath().resolve("normal")
val names=listOf("matrix","setting","drvparam","series","config","sample-entry","shadow-low","shadow-high","global-inputs")
for(name in names){val b=Files.readAllBytes(fixture.resolve("adc-input-$name.bin"));fun get64(o:Int):ULong{var v=0uL;for(j in 0..7)v=v or ((b[o+j].toInt() and 255).toULong() shl (8*j));return v};fun put64(o:Int,v:ULong){for(j in 0..7)b[o+j]=(v shr (8*j)).toByte()};if(name=="series")for(i in 0..8)for(field in listOf(8,24)){val o=12+32*i+field;val v=get64(o);if(v!=0uL)put64(o,v+delta)};if(name=="global-inputs")put64(0,mapped);write("adc-input-$name.bin",b)}
val maps="${base.toString(16)}-${(base+0x4000000uL).toString(16)} rw-p 00000000 00:00 0\n";write("adc-input-maps.txt",maps)
var phase=Files.readString(fixture.resolve("native-events.toml")).split("[[events]]").dropWhile{!it.contains("kind = \"adc-input-mode\"")}.takeWhile{!it.contains("kind = \"loader-summary\"")}.joinToString(""){"[[events]]$it"}
phase=Regex("0x[0-9a-f]+").replace(phase){m->val v=m.value.substring(2).toULong(16);if(v in 0x70000000uL..0x74000000uL)"0x"+(v+delta).toString(16) else m.value}
fun update(kind:String,key:String,value:ULong,index:Int?=null){val blocks=phase.split("[[events]]").toMutableList();val at=blocks.indices.single{i->blocks[i].contains("kind = \"$kind\"")&&(index==null||Regex("(?m)^index = \"0x${index.toString(16)}\"$").containsMatchIn(blocks[i]))};blocks[at]=Regex("(?m)^$key = .+$").replace(blocks[at],"$key = \"0x${value.toString(16)}\"");phase=blocks.joinToString("[[events]]")}
update("adc-input-maps","bytes",maps.toByteArray().size.toULong());update("adc-input-state","mapped_base_value",mapped)
fun fnv(b:ByteArray):ULong{var h=14695981039346656037uL;b.forEach{h=(h xor (it.toInt() and 255).toULong())*1099511628211uL};return h}
for(i in names.indices)update("adc-input-capture","hash_fnv1a64",fnv(Files.readAllBytes(run.resolve("adc-input-${names[i]}.bin"))),i)
val oldBlocks=old.split("[[events]]").toMutableList();val at=oldBlocks.indexOfFirst{it.contains("kind = \"loader-summary\"")};require(at>0);oldBlocks.add(at,phase.removePrefix("[[events]]"));val mi=oldBlocks.indexOfFirst{it.contains("kind = \"model-mode\"")};oldBlocks[mi]+="adc_inputs = \"0x1\"\n";write("native-events.toml",oldBlocks.joinToString("[[events]]"))
Files.list(repo.resolve("tools/guest")).use{it.filter{p->Files.isRegularFile(p)}.forEach{p->from("source/${p.fileName}",repo.relativize(p).toString())}}
for(name in listOf("group-control.elf","group-executed.elf"))from(name,"out/adc-input-capture/native-build03/group-observer")
for(name in listOf("build-inputs.txt","binary-sha256.txt"))from(name,"out/adc-input-capture/native-build03/$name")
Files.list(repo.resolve("experiments/adc-parameter-static")).use{it.filter{p->p.toString().endsWith(".toml")}.forEach{p->from("adc-parameter-static/${p.fileName}",repo.relativize(p).toString())}}
from("source/adc-input-capture-decision.toml","experiments/adc-input-capture/decision.toml")
for(name in listOf("adc-input-capture-inputs.toml","calibration-stock-runtime-inputs.toml"))from("source/$name","experiments/adc-input-capture/stock-inputs.toml")
write("adc-input-pulls.toml",(names+"maps").joinToString(""){"$it = 0\n"})
write("result.toml",Files.readString(run.resolve("result.toml")).replace("mode = \"loadermodel\"","mode = \"adcinputmodel\""))
write("userdata-staging.toml","""source_sha256 = "effba4cc839206b25dee05455f6c49b9fad0ca90d524812fd4bbc5d3c02636d2"
staged_sha256 = "effba4cc839206b25dee05455f6c49b9fad0ca90d524812fd4bbc5d3c02636d2"
source_identity = "1:1:1"
staged_identity = "1:2:1"
independent_inode = true
staged_link_count = 1
minimum_free_kib = 2097152
free_kib_before = 3000000
free_kib_after = 3000000
""")
val indexed=Files.walk(run).use{it.filter{p->Files.isRegularFile(p)}.sorted().toList()};write("evidence-sha256.txt",indexed.joinToString(""){hash(Files.readAllBytes(it))+"  $it\n"})
originals.forEach{(p,d)->require(hash(Files.readAllBytes(p))==d)}
Files.writeString(out.resolve("preparation.toml"),"kind = \"synthetic-host-only\"\nguest_launched = false\noriginal_index_verified_before_and_after = true\nindependent_copies = true\n")
println("Prepared synthetic full-profile control")
