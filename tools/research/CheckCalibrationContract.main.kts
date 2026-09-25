import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 4) { "Usage: CheckCalibrationContract.main.kts STOCK_ELF CONTRACT_DIRECTORY VERIFIER_KTS OUTPUT_DIRECTORY" }
val elf = Path.of(args[0]).toAbsolutePath()
val source = Path.of(args[1]).toAbsolutePath()
val verifier = Path.of(args[2]).toAbsolutePath()
val output = Path.of(args[3]).toAbsolutePath()
require(!Files.exists(output)); Files.createDirectories(output)
data class Mutation(val name:String,val file:String,val old:String,val replacement:String,val expected:Int)
val cases=listOf(
 Mutation("accepted","","","",0),
 Mutation("direct-target-label","call-inventory.toml","symbol = \"UNRESOLVED\"\nresolved_target = 0x252a0c\ndefined = false\nexpanded = false","symbol = \"_Z12Drv_GetScopev\"\nresolved_target = 0x2e5a40\ndefined = true\nexpanded = true",3),
 Mutation("range-byte-hash","call-inventory.toml","sha256 = \"50d0478e110c488dcd2ae46366a5605dca3a2eaa69250b3fdf3f2f4b0c55872b\"","sha256 = \"00d0478e110c488dcd2ae46366a5605dca3a2eaa69250b3fdf3f2f4b0c55872b\"",3),
 Mutation("call-opcode","call-inventory.toml","pc = 0x333ba8\nopcode = 0x97fb9b9e","pc = 0x333ba8\nopcode = 0x97fb9b9f",3),
 Mutation("loop-bound","dispatcher.toml","adc_stray_selectors = [0,1,2,3]","adc_stray_selectors = [0,1,2]",3),
 Mutation("loader-size","loaders.toml","bytes=1936","bytes=1935",3),
 Mutation("early-field-width","adc-initial-state.toml","adc_offset = 0x8854\npayload_offset = 0x50\nwidth = 2","adc_offset = 0x8854\npayload_offset = 0x50\nwidth = 4",3),
 Mutation("wrong-plt-slot","call-inventory.toml","relocation_slot = 0xb83078","relocation_slot = 0xb83080",3),
 Mutation("bss-placement","adc-initial-state.toml","file_backed_end = 0xbe0e00","file_backed_end = 0xbe0e08",3),
 Mutation("gain-entry","review-refinements.toml","entries = [[0,0],[1,1]","entries = [[0,1],[1,1]",3),
 Mutation("missing-call","call-inventory.toml","SPECIAL_MISSING_CALL","",3),
 Mutation("altered-edge","dispatcher.toml","from = \"sync_delay\"\nto = \"data_line\"","from = \"sync_delay\"\nto = \"input_delay\"",3)
)
fun copyTree(dst:Path){Files.createDirectories(dst);Files.list(source).use{stream->stream.filter{Files.isRegularFile(it)}.forEach{Files.copy(it,dst.resolve(it.fileName))}}}
fun q(s:String)="\""+s.replace("\\","\\\\").replace("\"","\\\"")+"\""
data class Result(val m:Mutation,val exit:Int)
fun sha(p:Path)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(p)))
val results=mutableListOf<Result>()
for(m in cases){val dir=output.resolve(m.name);copyTree(dir);if(m.file.isNotEmpty()){val p=dir.resolve(m.file);val s=Files.readString(p);val changed=if(m.name=="missing-call"){val begin=s.indexOf("[[calls]]");val end=s.indexOf("[[calls]]",begin+9);require(begin>=0&&end>begin);s.substring(0,begin)+s.substring(end)}else s.replaceFirst(m.old,m.replacement);require(changed!=s){"anchor ${m.name}"};Files.writeString(p,changed);val result=dir.resolve("results.toml");val rs=Files.readString(result);val originalHash=sha(source.resolve(m.file));val newHash=sha(p);val rp="experiments/calibration-static/${m.file}";if(rs.contains("path = \"$rp\"")){require(rs.contains("sha256 = \"$originalHash\"")){"pin ${m.name}"};Files.writeString(result,rs.replaceFirst("sha256 = \"$originalHash\"","sha256 = \"$newHash\""))}}
 val cmd=listOf("kotlinc","-script",verifier.toString(),"--",elf.toString(),dir.toString());val proc=ProcessBuilder(cmd).start();val stdout=proc.inputStream.readBytes();val stderr=proc.errorStream.readBytes();val exit=proc.waitFor();Files.write(output.resolve("${m.name}.stdout"),stdout);Files.write(output.resolve("${m.name}.stderr"),stderr);Files.writeString(output.resolve("${m.name}.exit"),"$exit\n");Files.writeString(output.resolve("${m.name}.command"),cmd.joinToString(" ")+"\n");require(exit==m.expected){"${m.name}: expected ${m.expected}, got $exit"};results+=Result(m,exit)}
Files.newBufferedWriter(output.resolve("results.toml")).use{w->w.appendLine("schema_version = \"mho900-lab.calibration-contract-verifier-controls/1\"");w.appendLine("all_expected_exits = true");for(r in results){w.appendLine("\n[[cases]]");w.appendLine("name = ${q(r.m.name)}");w.appendLine("expected_exit = ${r.m.expected}");w.appendLine("actual_exit = ${r.exit}");w.appendLine("stdout = ${q(r.m.name+".stdout")}");w.appendLine("stderr = ${q(r.m.name+".stderr")}")}}
println("result = \"accepted\"")
println("cases = ${results.size}")
