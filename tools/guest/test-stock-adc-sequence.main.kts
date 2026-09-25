// Host-only controls for VerifyStockAdcSequence.main.kts.
// Every generated tree is synthetic/replay-derived evidence, never a guest outcome.
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardCopyOption
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 1) { "Usage: test-stock-adc-sequence.main.kts NEW_OUTPUT" }
val repo = Path.of("").toAbsolutePath().normalize()
val output = Path.of(args[0]).toAbsolutePath().normalize()
require(!Files.exists(output)) { "NEW_OUTPUT must not exist" }
val stockSeed = repo.resolve("out/guest-admission/stock-adc-input-capture-01")
val privateSeed = repo.resolve("out/guest-admission/private-adc-sequence-03")
val verifier = repo.resolve("tools/guest/VerifyStockAdcSequence.main.kts")
val profile = repo.resolve("experiments/adc-sequence/profile.toml")
val profileHeader = repo.resolve("tools/guest/adc-sequence-profile.h")
val native = repo.resolve("out/adc-sequence-profile/native-build02/group-observer")
listOf(stockSeed, privateSeed).forEach { require(Files.isDirectory(it)) }
listOf(verifier, profile, profileHeader, native).forEach { require(Files.isRegularFile(it)) }

fun digest(bytes: ByteArray): String = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))
fun digest(path: Path): String = digest(Files.readAllBytes(path))
fun copyFresh(source: Path, target: Path) {
    Files.createDirectories(target.parent); Files.copy(source, target, StandardCopyOption.REPLACE_EXISTING)
    require(!Files.isSameFile(source, target)) { "hardlink/reused source: $target" }
}
fun eventBlocks(source: String): MutableList<String> = source.split("[[events]]").toMutableList()
fun isKind(block: String, kind: String): Boolean = block.lineSequence().any { it == "kind = \"$kind\"" }
fun mutateEvent(source: String, kind: String, occurrence: Int, field: String, value: String): String {
    val blocks = eventBlocks(source); var seen=0; var changed=0
    for (index in 1 until blocks.size) if (isKind(blocks[index], kind) && seen++ == occurrence) {
        val pattern=Regex("(?m)^${Regex.escape(field)} = .*$");require(pattern.containsMatchIn(blocks[index])){"$kind.$field"}
        blocks[index]=blocks[index].replace(pattern,"$field = $value");changed++
    }
    require(changed==1){"exact mutation $kind.$field"};return blocks.joinToString("[[events]]")
}
fun hex(value: ULong): String = "\"0x${value.toString(16).padStart(16,'0')}\""
fun fields(block: String): Map<String,String> = block.lineSequence().filter { " = " in it }.associate { line -> val pair=line.split(" = ",limit=2);pair[0] to pair[1].removeSurrounding("\"") }
fun ulong(value:String):ULong=value.removePrefix("0x").toULong(16)
fun setField(block:String,name:String,value:String):String { val p=Regex("(?m)^${Regex.escape(name)} = .*$");require(p.containsMatchIn(block)){"$name in ${fields(block)["kind"]}"};return block.replace(p,"$name = $value") }
fun event(kind:String, pairs:List<Pair<String,String>>):String="\nkind = \"$kind\"\n"+pairs.joinToString(""){(k,v)->"$k = $v\n"}

fun copyIndexedSeed(target: Path) {
    val lines=Files.readAllLines(stockSeed.resolve("evidence-sha256.txt"))
    lines.forEach { line ->
        require(line.length>66 && line.substring(64,66)=="  ");val source=Path.of(line.substring(66)).toAbsolutePath().normalize()
        require(source.startsWith(stockSeed) && digest(source)==line.take(64));copyFresh(source,target.resolve(stockSeed.relativize(source)))
    }
}

// Remaining construction is intentionally below the shared copy/parse primitives so every
// case traverses the production verifier with a complete independently copied evidence tree.

fun buildFixture(target:Path) {
    Files.createDirectories(target);copyIndexedSeed(target)
    copyFresh(verifier,target.resolve("source/VerifyStockAdcSequence.main.kts"));copyFresh(profile,target.resolve("adc-sequence/profile.toml"));copyFresh(profileHeader,target.resolve("source/adc-sequence-profile.h"))
    copyFresh(repo.resolve("tools/guest/adc-sequence-observer.h"),target.resolve("source/adc-sequence-observer.h"));copyFresh(stockSeed.resolve("installed.apk"),target.resolve("stock-input.apk"))
    copyFresh(native,target.resolve("group-control.elf"));copyFresh(native,target.resolve("group-executed.elf"))
    Files.writeString(target.resolve("binary-sha256.txt"),"${digest(native)}  ${native.toAbsolutePath().normalize()}\n")
    copyFresh(repo.resolve("out/stock-adc-sequence-preparation/frida-environment-files.toml"),target.resolve("source/frida-environment-files.toml"));copyFresh(repo.resolve("out/stock-adc-sequence-preparation/frida-tooling-verification.toml"),target.resolve("frida-tooling-verification.toml"));copyFresh(privateSeed.resolve("frida-prerequisite.toml"),target.resolve("frida-prerequisite.toml"))
    val prerequisite=repo.resolve("out/stock-adc-sequence-preparation/actual-prerequisite02")
    listOf("frida-required-packages.txt", "frida-observed-packages.txt").forEach { name -> copyFresh(prerequisite.resolve(name), target.resolve(name)) }
    copyFresh(stockSeed.resolve("frida-packages.txt"),target.resolve("frida-packages.txt"))
    val stockText=Files.readString(stockSeed.resolve("native-events.toml"));val stockBlocks=stockText.split("[[events]]").drop(1)
    val stockEvent=stockBlocks.map(::fields);val binding=stockEvent.single{it["kind"]=="model-binding"};val pid=ulong(binding.getValue("pid"));val base=ulong(binding.getValue("base"));val mapping=ulong(stockEvent.single{it["kind"]=="mapping-result"}.getValue("base"))
    val tracked=stockEvent.filter{it["kind"]=="group-track"}.map{ulong(it.getValue("tid"))};require(pid in tracked)
    val stockCut=stockText.indexOf("\n[[events]]\nkind = \"terminal-quiesce\"");require(stockCut>0);val stockHead=stockText.substring(0,stockCut);var cleanup=stockText.substring(stockCut)
    cleanup=mutateEvent(cleanup,"terminal-state",0,"modeled_writes",hex(563uL));cleanup=mutateEvent(cleanup,"remaining-summary",0,"total_writes",hex(563uL));cleanup=mutateEvent(cleanup,"tail-summary",0,"total_writes",hex(563uL))
    val privateText=Files.readString(privateSeed.resolve("adcseq-101.toml"));val privateBlocks=privateText.split("[[events]]").drop(1);val privateFields=privateBlocks.map(::fields)
    val privatePid=ulong(privateFields.single{it["kind"]=="model-mode"}.getValue("pid"));val privateMapping=ulong(privateFields.single{it["kind"]=="mapping-result"}.getValue("base"));val phaseStart=privateFields.indexOfFirst{it["kind"]=="adc-sequence-mode"};val phaseEnd=privateFields.indexOfFirst{it["kind"]=="terminal-quiesce"};require(phaseStart>0&&phaseEnd>phaseStart)
    val sourceBases=listOf(0x10cd734uL,0x10bee58uL,0x10c4840uL,0xb8f478uL,0xb8f808uL,0x3cb44fcuL,0x3cb457cuL,0xbe1128uL,0xb8f4e4uL,0x9948bcuL).map{base+it}
    val stockReturn=base+0x333bacuL;val stockWrite=base+0x27043cuL;val stockRead=base+0x270604uL
    val lastLoader=stockBlocks.last{isKind(it,"loader-debug-registers")}
    var operationIndex=0
    val generated=mutableListOf<String>()
    fun common(block:String):String=block.replace(hex(privatePid),hex(pid)).replace(hex(privateMapping),hex(mapping))
    for(index in phaseStart until phaseEnd) {
        var block=common(privateBlocks[index]);val f=fields(block);val kind=f.getValue("kind")
        if(kind in setOf("runtime-wait","runtime-resume","loader-terminal-interrupt","terminal-interrupt-stop"))continue
        when(kind){
            "adc-sequence-mode"->{block=setField(block,"scope","\"stock\"");block=setField(block,"arm",hex(0uL));block=setField(block,"return_pc",hex(stockReturn))}
            "adc-sequence-entry-guard","adc-sequence-final-shadow"->{val source=ulong(f.getValue("source")).toInt();val offset=ulong(f.getValue("offset"));block=setField(block,"address",hex(sourceBases[source]+offset))}
            "adc-sequence-entry-binding"->{block=setField(block,"mapped_base",hex(mapping));block=setField(block,"expected_mapping",hex(mapping))}
            "adc-sequence-debug-before","adc-sequence-debug-request","adc-sequence-debug-after"->{val a=ulong(f.getValue("a00"));val replacement=when(a){0uL->0uL;else->stockReturn};block=setField(block,"a00",hex(replacement))}
            "adc-sequence-entry-registers"->{block=setField(lastLoader,"kind","\"adc-sequence-entry-registers\"")}
            "adc-sequence-resume-group"->{block=setField(block,"threads",hex(tracked.size.toULong()));block=setField(block,"leader",hex(pid))}
            "mapped-fault"->{val offset=ulong(f.getValue("offset"));block=setField(block,"tid",hex(pid));block=setField(block,"address",hex(mapping+offset))}
            "fault-registers"->{val previous=generated.last{isKind(it,"mapped-fault")};val pf=fields(previous);val read=pf.getValue("opcode").removePrefix("0x").toULong(16)==0xb9400109uL;val pc=if(read)stockRead else stockWrite;block=setField(block,"tid",hex(pid));block=setField(block,"pc",hex(pc));block=setField(block,"relative_pc",hex(pc-base));block=setField(block,"x08","\"${pf.getValue("address")}\"")}
            "adc-sequence-access"->{val op=operationIndex;val offset=ulong(f.getValue("offset"));val read=f.getValue("opcode").removePrefix("0x").toULong(16)==0xb9400109uL;block=setField(block,"tid",hex(pid));block=setField(block,"address",hex(mapping+offset));block=setField(block,"pc",hex(if(read)stockRead else stockWrite));operationIndex=op+1}
            "adc-sequence-before-registers","adc-sequence-after-registers"->{val op=if(kind.endsWith("before-registers"))operationIndex-1 else operationIndex-1;val access=generated.lastOrNull{isKind(it,"adc-sequence-access") }?:error("access");val af=fields(access);val pc=ulong(af.getValue("pc"))+(if(kind.endsWith("after-registers"))4uL else 0uL);block=setField(block,"tid",hex(pid));block=setField(block,"pc",hex(pc));block=setField(block,"relative_pc",hex(pc-base));block=setField(block,"x08",af.getValue("address").let{if(it.startsWith("\""))it else "\"$it\""})}
            "adc-sequence-write","adc-sequence-read"->{block=setField(block,"tid",hex(pid))}
            "adc-sequence-return"->{listOf("tid" to pid,"pc" to stockReturn,"expected_pc" to stockReturn,"address" to stockReturn,"opcode" to 0x5285070auL).forEach{(k,v)->block=setField(block,k,hex(v))}}
            "adc-sequence-return-registers","adc-sequence-final-registers"->{block=setField(block,"tid",hex(pid));block=setField(block,"pc",hex(stockReturn));block=setField(block,"relative_pc",hex(0x333bacuL))}
            "loader-terminal-converge"->{block=setField(block,"stopping_tid",hex(pid));generated+=block;tracked.filter{it!=pid}.forEach{tid->generated+=event("loader-terminal-interrupt",listOf("tid" to hex(tid),"result" to hex(0uL)));generated+=event("terminal-interrupt-stop",listOf("tid" to hex(tid),"status" to hex(0x80057fuL)))};continue}
            "adc-sequence-summary"->{for(name in listOf("private_metrics","worker_ack","atomic","raw0","raw1","protocol0","protocol1","private_reads","old_executed"))block=setField(block,name,hex(0uL))}
        }
        generated+=block
        if(kind=="adc-sequence-resume-group")tracked.forEach{tid->generated+=event("runtime-resume",listOf("tid" to hex(tid),"operation" to hex(7uL)))}
        if(kind=="adc-sequence-after-registers")generated+=event("runtime-resume",listOf("tid" to hex(pid),"operation" to hex(7uL)))
    }
    require(operationIndex==99)
    Files.writeString(target.resolve("native-events.toml"),stockHead+generated.joinToString("[[events]]",prefix="[[events]]")+cleanup)
    Files.writeString(target.resolve("native-status.toml"),"exit_code = 78\n")
    Files.writeString(target.resolve("result.toml"),Files.readString(target.resolve("result.toml")).replace("run_id = \"stock-adc-input-capture-01\"","run_id = \"stock-adc-sequence-01\"").replace("mode = \"adcinputmodel\"","mode = \"adcsequencemodel\""))
    Files.writeString(target.resolve("frida-prerequisite.toml"),"""schema_version = "mho900-lab.frida-prerequisite/1"
mode = "adcsequencemodel"
required = true
server_verified = true
cli_version = "16.7.19"
""")
    val manifest=buildString{append("""schema_version = "mho900-lab.adc-sequence-stock/1"
mode = "adcsequencemodel"
run_id = "stock-adc-sequence-01"
terminal_relative_pc = 0x333bac
terminal_opcode = 0x5285070a
terminal_instruction_executes = false
new_modeled_mmio_responses = 2
new_modeled_reads = 2
new_modeled_writes = 97
expected_operations = 99
expected_entry_guards = 175
expected_final_shadows = 33
synthetic_read_values = [0x11234, 0]
adaptive_retry = false
physical_access = false
physical_instrument_access = false
stock_apk_sha256 = "6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b"
stock_elf_sha256 = "4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e"

[native]
sha256 = "${digest(native)}"
""");listOf(Triple("out/adc-sequence-profile/native-build02/group-observer","group-control.elf",target.resolve("group-control.elf")),Triple("experiments/adc-sequence/profile.toml","adc-sequence/profile.toml",target.resolve("adc-sequence/profile.toml")),Triple("tools/guest/VerifyStockAdcSequence.main.kts","source/VerifyStockAdcSequence.main.kts",target.resolve("source/VerifyStockAdcSequence.main.kts")),Triple("tools/guest/adc-sequence-profile.h","source/adc-sequence-profile.h",target.resolve("source/adc-sequence-profile.h")),Triple("tools/guest/adc-sequence-observer.h","source/adc-sequence-observer.h",target.resolve("source/adc-sequence-observer.h")),Triple("local/guest-inputs/Sparrow.apk","stock-input.apk",target.resolve("stock-input.apk")),Triple("source/frida-environment-files.toml","source/frida-environment-files.toml",target.resolve("source/frida-environment-files.toml"))).forEach{(path,runPath,file)->append("\n[[artifacts]]\npath = \"$path\"\nrun_path = \"$runPath\"\nsha256 = \"${digest(file)}\"\n")}}
    Files.writeString(target.resolve("source/adc-sequence-stock-inputs.toml"),manifest);Files.writeString(target.resolve("source/calibration-stock-runtime-inputs.toml"),manifest)
    rebuildIndex(target)
}

fun rebuildIndex(target:Path){val index=target.resolve("evidence-sha256.txt");val files=Files.walk(target).use{s->s.filter{Files.isRegularFile(it)&&it!=index}.sorted().toList()};Files.writeString(index,files.joinToString("\n",postfix="\n"){"${digest(it)}  ${it.toAbsolutePath().normalize()}"})}
fun manifestDigest(target:Path)=digest(target.resolve("source/adc-sequence-stock-inputs.toml"))
fun invoke(target:Path,label:String):Pair<Int,String>{val p=ProcessBuilder("kotlinc","-script",verifier.toString(),"--",target.toString(),manifestDigest(target)).apply{environment().remove("KOTLIN_RUNNER")}.start();val stdout=p.inputStream.bufferedReader().readText();val stderr=p.errorStream.bufferedReader().readText();val code=p.waitFor();Files.writeString(target.resolve("verifier-$label.stdout"),stdout);Files.writeString(target.resolve("verifier-$label.stderr"),stderr);return code to(stdout+stderr)}

fun rewrite(target:Path,name:String,transform:(String)->String){val path=target.resolve(name);val before=Files.readString(path);val after=transform(before);require(after!=before){"no mutation: $name"};Files.writeString(path,after)}
fun flipByte(target:Path,name:String){val path=target.resolve(name);val bytes=Files.readAllBytes(path);require(bytes.isNotEmpty());bytes[0]=(bytes[0].toInt() xor 1).toByte();Files.write(path,bytes)}
fun dropIndexRow(target:Path,name:String){rewrite(target,"evidence-sha256.txt"){text->val kept=text.lineSequence().filter{it.isNotBlank()&&!it.endsWith("/$name")}.toList();require(kept.size==text.lineSequence().count{it.isNotBlank()}-1);kept.joinToString("\n",postfix="\n")}}

val checkerAtStart=digest(verifier)
Files.createDirectories(output)
val positive=output.resolve("positive-synthetic");buildFixture(positive);val(posCode,posText)=invoke(positive,"positive")
require(posCode==0){"positive rejected:\n$posText"};require("result = \"accepted\"" in posText&&"operations = 99" in posText&&"writes = 97" in posText&&"synthetic_reads = 2" in posText&&"terminal_relative_pc = \"0x333bac\"" in posText)

data class Corruption(val name:String,val reindex:Boolean=true,val mutate:(Path)->Unit)
val corruptions=listOf(
    Corruption("write-value"){t->rewrite(t,"native-events.toml"){mutateEvent(it,"adc-sequence-write",0,"value",hex(0xfeeduL))}},
    Corruption("read-value"){t->rewrite(t,"native-events.toml"){mutateEvent(it,"adc-sequence-read",0,"value",hex(0xfeeduL))}},
    Corruption("register-transition"){t->rewrite(t,"native-events.toml"){mutateEvent(it,"adc-sequence-after-registers",0,"x09",hex(0xfeeduL))}},
    Corruption("entry-guard"){t->rewrite(t,"native-events.toml"){mutateEvent(it,"adc-sequence-entry-guard",0,"actual",hex(0xfeeduL))}},
    Corruption("raw-capture"){t->flipByte(t,"adc-input-config.bin")},
    Corruption("final-shadow"){t->rewrite(t,"native-events.toml"){mutateEvent(it,"adc-sequence-final-shadow",0,"actual",hex(0xfeeduL))}},
    Corruption("thread-cleanup"){t->rewrite(t,"native-events.toml"){mutateEvent(it,"group-cleanup",0,"reaped_count",hex(0uL))}},
    Corruption("precise-pc"){t->rewrite(t,"native-events.toml"){mutateEvent(it,"adc-sequence-access",0,"pc",hex(1uL))}},
    Corruption("frozen-profile-index",false){t->rewrite(t,"adc-sequence/profile.toml"){it+"\n# changed frozen artifact\n"}},
    Corruption("wrong-run-identity"){t->listOf("source/adc-sequence-stock-inputs.toml","source/calibration-stock-runtime-inputs.toml").forEach{name->rewrite(t,name){it.replace("run_id = \"stock-adc-sequence-01\"","run_id = \"wrong-run\"")}}},
    Corruption("system-server-health"){t->rewrite(t,"native-final-system-server.txt"){(it.trim().toULong()+1uL).toString()+"\n"}},
    Corruption("tool-packages"){t->rewrite(t,"frida-observed-packages.txt"){it.replaceFirst("colorama==0.4.6","colorama==0.4.5")}},
    Corruption("unindexed-raw-consumed",false){t->dropIndexRow(t,"adc-input-config.bin")},
    Corruption("unindexed-admission-hook",false){t->dropIndexRow(t,"admission-hook.txt")}
)
corruptions.forEach{c->val target=output.resolve("negative-${c.name}");buildFixture(target);c.mutate(target);if(c.reindex)rebuildIndex(target);val(code,text)=invoke(target,c.name);require(code!=0){"negative accepted: ${c.name}\n$text"}}
require(digest(verifier)==checkerAtStart){"checker changed during controls"}
Files.writeString(output.resolve("results.toml"),buildString{
    append("schema_version = \"mho900-lab.stock-adc-sequence-host-controls/1\"\n")
    append("classification = \"fully-synthetic-replay-derived-host-fixtures\"\n")
    append("guest_runs = 0\npositive = 1\nnegative = ${corruptions.size}\n")
    append("checker_sha256 = \"$checkerAtStart\"\nstock_seed_sha256 = \"${digest(stockSeed.resolve("evidence-sha256.txt"))}\"\nprivate_seed_sha256 = \"${digest(privateSeed.resolve("evidence-sha256.txt"))}\"\n")
    append("native_sha256 = \"${digest(native)}\"\nprofile_sha256 = \"${digest(profile)}\"\n")
    corruptions.forEach{append("\n[[negative]]\nname = \"${it.name}\"\nresult = \"rejected\"\n")}
})
println("stock ADC sequence host controls passed: 1 positive, ${corruptions.size} targeted negatives; checker $checkerAtStart")
