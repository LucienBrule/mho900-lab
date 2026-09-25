// Mutate fresh small host controls; never link or write the original capture.
import java.nio.file.Files
import java.nio.file.Path
require(args.size==2){"Usage: test-adc-candidate.main.kts CANDIDATE_DIRECTORY NEW_OUTPUT_DIRECTORY"}
val source=Path.of(args[0]);val out=Path.of(args[1]);require(!Files.exists(out));Files.createDirectories(out)
val manifest=Files.readString(source.resolve("candidate.toml"));val sequence=Files.readString(source.resolve("sequence.tsv"))
data class Fixture(val name:String,val manifest:String,val sequence:String,val accepted:Boolean=false)
fun change(text:String,from:String,to:String):String{require(text.contains(from));return text.replaceFirst(from,to)}
val fixtures=listOf(
    Fixture("positive",manifest,sequence,true),
    Fixture("wrong-operand-both-forms",change(manifest,"value = 0x5097020","value = 0x5097021"),change(sequence,"0x5097020","0x5097021")),
    Fixture("missing-operation",manifest.replace(Regex("\\n\\[\\[operations]]\\nindex = 149\\n[^\\[]+"),"\n"),sequence.lineSequence().filterNot{it.startsWith("149\t")}.joinToString("\n")),
    Fixture("wrong-order",manifest,sequence.replace("7\tCORE_GAIN\tW32\t0x3000\t0x5150000","7\tCORE_GAIN\tW32\t0x3000\t0x5350000")),
    Fixture("wrong-signed-field",change(manifest,"type = \"s16\"","type = \"u16\""),sequence),
    Fixture("wrong-runtime-width",change(manifest,"type = \"s64\"","type = \"u64\""),sequence),
    Fixture("invented-read-response",change(manifest,"value_class = \"HARDWARE-RETURNED-UNOBSERVED\"","value_class = \"HARDWARE-RETURNED-UNOBSERVED\"\nvalue = 0x10000"),sequence),
    Fixture("wrong-sleep",change(manifest,"microseconds = 20000","microseconds = 10000"),change(sequence,"STARY\tSLEEP\t-\t20000","STARY\tSLEEP\t-\t10000")),
    Fixture("wrong-shadow",change(manifest,"final = [22272, 18176]","final = [0, 0]"),sequence),
    Fixture("stale-input-pin",change(manifest,"b34cf1a86a01dc54cbc14e28de60989352579423224e7ddfb8096d1990b0810b","0000000000000000000000000000000000000000000000000000000000000000"),sequence),
    Fixture("wrong-return-boundary",change(manifest,"post_return_pc = 0x333bac","post_return_pc = 0x333ba8"),sequence),
    Fixture("wrong-mask",change(manifest,"value = 0x2720","value = 0x2721"),sequence),
    Fixture("broken-shadow-chain",change(manifest,"before = 22305","before = 0"),sequence))
val result=StringBuilder("schema_version = \"mho900-lab.adc-candidate-controls/1\"\n")
for(f in fixtures){val dir=out.resolve(f.name);Files.createDirectory(dir);Files.writeString(dir.resolve("candidate.toml"),f.manifest);Files.writeString(dir.resolve("sequence.tsv"),f.sequence)
    val pb=ProcessBuilder("kotlinc","-script","tools/research/VerifyAdcCandidate.main.kts","--",dir.toString());pb.environment().remove("KOTLIN_RUNNER")
    pb.redirectOutput(dir.resolve("verification.toml").toFile());pb.redirectError(dir.resolve("verification.stderr").toFile())
    val rc=pb.start().waitFor();check((rc==0)==f.accepted){"unexpected result ${f.name}: $rc"}
    result.append("\n[[cases]]\nname = \"${f.name}\"\nexpected_acceptance = ${f.accepted}\nexit_code = $rc\nmatched = true\n")
    println("${f.name}: expected ${if(f.accepted)"acceptance" else "rejection"}, exit $rc")
}
check(Files.readString(source.resolve("candidate.toml"))==manifest&&Files.readString(source.resolve("sequence.tsv"))==sequence)
Files.writeString(out.resolve("results.toml"),result)
