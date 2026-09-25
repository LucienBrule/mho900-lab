// Exercise the production index function, then independently validate required inputs.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size==1){"Usage: test-admission-index.main.kts NEW_OUTPUT"}
val out=Path.of(args[0]).toAbsolutePath();require(!Files.exists(out));Files.createDirectories(out)
val runtime=Path.of("tools/guest/admission-runtime.sh").toAbsolutePath()
fun digest(b:ByteArray)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b))
val nested=listOf("scope","main-grammar","stary-grammar","stary-refinements","integer-refinements","helper-grammar","helper-refinements","getter-inputs").map{"adc-parameter-static/$it.toml"}+listOf("adc-candidate/candidate.toml","adc-candidate/sequence.tsv","adc-sequence/profile.toml")
val expected=(nested+listOf("result.toml","source/control.sh","source/frida-environment-files.toml","frida-tooling-verification.toml","calibration-source/firmware/data/default/cal_lsb.hex","calibration-source/firmware/data/default/cal_vertical.hex","admission-controls/changed-bytes.apk","stock-input.apk")).associateWith{"fixture = \"$it\"\n".toByteArray()}
fun verify(dir:Path){
    val lines=Files.readAllLines(dir.resolve("evidence-sha256.txt"))
    val paths=lines.map{line->require(line.length>66&&line.substring(64,66)=="  ");val p=Path.of(line.substring(66)).normalize();require(p.startsWith(dir)&&Files.isRegularFile(p)&&!Files.isSymbolicLink(p));require(digest(Files.readAllBytes(p))==line.take(64)){"indexed hash"};p}
    require(paths.distinct().size==paths.size){"duplicate entry"}
    expected.forEach{(name,bytes)->val p=dir.resolve(name);require(p in paths){"required input absent: $name"};require(digest(Files.readAllBytes(p))==digest(bytes)){"frozen input: $name"}}
}
val cases=listOf("complete","missing-static-file","changed-after-index","changed-and-reindexed","duplicate-index")
val report=StringBuilder("schema_version = \"mho900-lab.admission-index-controls/1\"\nindexer = \"production runner_index\"\nruntime_sha256 = \"${digest(Files.readAllBytes(runtime))}\"\nguest_launched = false\n")
for(case in cases){
    val dir=out.resolve(case);Files.createDirectory(dir)
    expected.forEach{(name,bytes)->if(case!="missing-static-file"||name!=nested[0]){val p=dir.resolve(name);Files.createDirectories(p.parent);Files.write(p,bytes)}}
    if(case=="changed-and-reindexed")Files.writeString(dir.resolve(nested[0]),"fixture = \"changed\"\n")
    val pb=ProcessBuilder("sh","-c","set -eu; . \"\$1\"; run=\$2; runner_index","index-control",runtime.toString(),dir.toString());pb.redirectOutput(out.resolve("$case.stdout").toFile());pb.redirectError(out.resolve("$case.stderr").toFile());val rc=pb.start().waitFor();require(rc==0)
    if(case=="changed-after-index")Files.writeString(dir.resolve(nested[0]),"fixture = \"changed\"\n")
    if(case=="duplicate-index"){val p=dir.resolve("evidence-sha256.txt");val text=Files.readString(p);Files.writeString(p,text+text.substringBefore('\n')+"\n")}
    val failure=runCatching{verify(dir)}.exceptionOrNull();val accepted=failure==null
    require(accepted==(case=="complete")){"unexpected $case: $failure"}
    report.append("\n[[cases]]\nname = \"$case\"\nindexer_exit = $rc\nverification_accepted = $accepted\nexpected_outcome = true\n")
    Files.writeString(out.resolve("results.toml"),report)
}
println("Actual runner index: one positive and four negatives matched")
