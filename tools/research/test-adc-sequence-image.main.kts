import java.nio.file.Files
import java.nio.file.Path
require(args.size==3){"Usage: test-adc-sequence-image.main.kts NATIVE_ELF IMAGE_CHECK_TOML NEW_OUTPUT_DIRECTORY"}
val native=Path.of(args[0]);val report=Files.readString(Path.of(args[1]));val out=Path.of(args[2]);require(!Files.exists(out));Files.createDirectories(out)
fun offset(key:String)=Regex("(?m)^$key = ([0-9]+)$").find(report)!!.groupValues[1].toInt()
val original=Files.readAllBytes(native)
data class Case(val name:String,val mutation:Int?,val accepted:Boolean)
val cases=listOf(Case("positive",null,true),Case("changed-compiled-operand",offset("operations_file_offset")+12,false),
    Case("changed-compiled-guard-width",offset("guards_file_offset")+8,false),Case("interrupted-atomic-shape",offset("atomic_loop_file_offset")+4,false))
val results=StringBuilder("schema_version = \"mho900-lab.adc-sequence-image-controls/1\"\n")
for(c in cases){val bytes=original.copyOf();c.mutation?.let{bytes[it]=(bytes[it].toInt() xor 1).toByte()};val p=out.resolve("${c.name}.elf");Files.write(p,bytes)
    val pb=ProcessBuilder("kotlinc","-script","tools/research/VerifyAdcSequenceImage.main.kts","--",p.toString());pb.environment().remove("KOTLIN_RUNNER");pb.redirectOutput(out.resolve("${c.name}.toml").toFile());pb.redirectError(out.resolve("${c.name}.stderr").toFile())
    val rc=pb.start().waitFor();check((rc==0)==c.accepted){"${c.name} exit $rc"};results.append("\n[[cases]]\nname = \"${c.name}\"\nexpected_acceptance = ${c.accepted}\nexit_code = $rc\nmatched = true\n");println("${c.name}: $rc")
}
check(Files.readAllBytes(native).contentEquals(original));Files.writeString(out.resolve("results.toml"),results)
