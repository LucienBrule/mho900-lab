// Offline review of the completed stock capture. Never rewrites its original index.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size==2){"Usage: ReviewAdcInputEvidence.main.kts STOCK_RUN NEW_REVIEW_OUTPUT"}
val repo=Path.of("").toAbsolutePath().normalize();val run=Path.of(args[0]).toAbsolutePath().normalize();val out=Path.of(args[1]).toAbsolutePath().normalize()
require(run.startsWith(repo)&&out.startsWith(repo)&&!out.startsWith(run)&&!Files.exists(out));Files.createDirectories(out)
fun hash(b:ByteArray)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b))
fun hash(p:Path)=hash(Files.readAllBytes(p))
fun text(name:String)=Files.readString(run.resolve(name))
val indexPath=run.resolve("evidence-sha256.txt")
val originalIndex="3a2bf54e81415e7e7733060d964de14a809c05ae70ec3946505ae454d9d1ffae"
require(hash(indexPath)==originalIndex)
val verifier=run.resolve("source/VerifyStockAdcInputs.main.kts")
require(hash(verifier)=="d1580db76854905dd98f51673c74133d1ddbc57292c2d562978fea580773313d")
val core=run.resolve("source/VerifyAdcInputCapture.main.kts")
require(hash(core)=="cc6fbe8e2e0bab9c78b6908e7d014ca100be078d9481a36f76baee76c38d9401")
val indexed=Files.readAllLines(indexPath).map{line->
    require(line.length>66&&line.substring(64,66)=="  ")
    val p=Path.of(line.substring(66)).toAbsolutePath().normalize()
    require(p.startsWith(run)&&Files.isRegularFile(p)&&!Files.isSymbolicLink(p)&&hash(p)==line.take(64));p
}
require(indexed.size==325&&indexed.distinct().size==325)
val staticPins=mapOf(
    "scope.toml" to "170b6b99f14143944c9a682ac56bf8680c33480dc2bca0328f3c6ac4ff3d0f09",
    "main-grammar.toml" to "65e346f18029530832ed7f684199d20a04812ad033cd7f4d0561b73b9a142c2c",
    "stary-grammar.toml" to "9ea7bd9d912dd0d5ab5c243469f32ee0ed5de866c59f4a5f4f8830063b2f73b0",
    "stary-refinements.toml" to "368a10344670f3346e6c04fb4ac0f8eb9ff2eb3510faa3463a202c39fe8a81bc",
    "integer-refinements.toml" to "d268a5b111373edbe78501ef7ff6e1fb28496fc3ebf1f5c99ce8f55e189c5355",
    "helper-grammar.toml" to "b74b4edeb422ac85b9a0b3ab96a13caf276a28d27dc227f0259b7a2ddbc28bc9",
    "helper-refinements.toml" to "709c4b340b74b71e32f7ff7338d3af2c2425d9cb9e2b4575310b2a93a668ac71",
    "getter-inputs.toml" to "9daa0d606744a98f0fd96bfd0962dc324934caab09530f43fb2faacae44cf3f8")
val supplemental=staticPins.map{(name,digest)->val p=run.resolve("adc-parameter-static/$name");require(hash(p)==digest&&p !in indexed);p}
val source=Files.readString(verifier)
val consumed=Regex("\"([^\"]+)\"").findAll(source.substringAfter("val consumed=hostCaptureNames+listOf(").substringBefore(")\n")).map{run.resolve(it.groupValues[1])}.toList()+
    listOf("entry-lsb","entry-adc","terminal-lsb","terminal-adc","terminal-vertical").map{run.resolve("native-loader-$it.bin")}+
    listOf("run-admission.sh","admission-runtime.sh","admission-label.sh","admission-loadermodel.sh","group-probe.sh","stage-userdata.sh","VerifyAdcInputCapture.main.kts").map{run.resolve("source/$it")}
require(consumed.filter{it !in indexed}.toSet()==supplemental.toSet())
require(consumed.all{it in indexed||it in supplemental})
fun fields(block:String):Map<String,String>{val pairs=block.lineSequence().filter{it.isNotBlank()}.map{val p=it.split(" = ",limit=2);require(p.size==2);p[0] to p[1].removeSurrounding("\"")}.toList();require(pairs.map{it.first}.distinct().size==pairs.size);return pairs.toMap()}
fun u(e:Map<String,String>,key:String)=e.getValue(key).removePrefix("0x").toULong(16)
val events=text("native-events.toml").split("[[events]]").drop(1).map{fields(it)}
val names=listOf("matrix","setting","drvparam","series","config","sample-entry","shadow-low","shadow-high","global-inputs").map{"adc-input-$it.bin"}
val sizes=listOf(0xe60,0x1c71,0x10,0x12c,0x3c,8,0x3c,0x74,0x2c)
val captures=events.filter{it["kind"]=="adc-input-capture"};require(captures.size==9)
fun fnv(bytes:ByteArray):ULong{var h=14695981039346656037uL;for(b in bytes)h=(h xor (b.toInt() and 255).toULong())*1099511628211uL;return h}
captures.forEachIndexed{i,e->val p=run.resolve(names[i]);val bytes=Files.readAllBytes(p);require(p in indexed&&bytes.size==sizes[i]);require(u(e,"index")==i.toULong()&&e["name"]==names[i]&&u(e,"length")==sizes[i].toULong()&&u(e,"completed")==sizes[i].toULong()&&u(e,"hash_fnv1a64")==fnv(bytes))}
val before=(indexed+supplemental).associateWith{hash(it)}
fun checkFrozen(script:Path,label:String,expected:Int):String{
    val pb=ProcessBuilder("kotlinc","-script",script.toString(),"--",run.toString());pb.environment().remove("KOTLIN_RUNNER")
    pb.redirectOutput(out.resolve("$label.stdout").toFile());pb.redirectError(out.resolve("$label.stderr").toFile())
    val rc=pb.start().waitFor();require(rc==expected){"$label exit $rc"};return Files.readString(out.resolve("$label.stderr"))
}
checkFrozen(core,"capture-phase",0)
val fullError=checkFrozen(verifier,"frozen-full",3)
require(fullError.contains("VerifyStockAdcInputs.main.kts:371")&&fullError.contains("control_outcome = \"complete-snapshot\""))
require(hash(indexPath)==originalIndex);before.forEach{(p,d)->require(hash(p)==d)}
val review="""schema_version = "mho900-lab.adc-input-offline-review/1"
result = "consumed-coverage-reviewed-with-original-index-limitation"
source_run = "${repo.relativize(run)}"
frozen_full_result = "rejected-at-final-index-coverage"
frozen_full_exit = 3
frozen_capture_phase_exit = 0
original_index_sha256 = "$originalIndex"
original_index_unchanged = true
original_run_files_unchanged = true
original_index_entries = 325
separately_pinned_static_contracts = 8
all_consumed_files_covered_by_review = true
raw_capture_files = 9
raw_capture_bytes = 11565
native_capture_checksums_verified = true
guest_launched = false
physical_behavior_validated = false
scope = "A separate offline completeness review; the original frozen experiment remains rejected."
"""+before.keys.sorted().joinToString(""){p->"\n[[reviewed_artifacts]]\npath = \"${run.relativize(p)}\"\nsha256 = \"${before.getValue(p)}\"\ncoverage = \"${if(p in indexed)"original-index" else "separate-frozen-static-pin"}\"\n"}
Files.writeString(out.resolve("review.toml"),review)
println("Reviewed ${before.size} artifacts without altering the original index or frozen rejection")
