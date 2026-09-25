// Exercise VerifyInitTail with one accepted grammar and four isolated damaged copies.
import java.nio.file.Files
import java.nio.file.Path

require(args.size==4){"Usage: CheckInitTailVerifier.main.kts STOCK_ELF GRAMMAR_TOML VERIFIER_KTS NEW_OUTPUT_DIRECTORY"}
val elf=Path.of(args[0]).toAbsolutePath().normalize()
val grammar=Path.of(args[1]).toAbsolutePath().normalize()
val verifier=Path.of(args[2]).toAbsolutePath().normalize()
val output=Path.of(args[3]).toAbsolutePath().normalize()
require(Files.isRegularFile(elf)&&Files.isRegularFile(grammar)&&Files.isRegularFile(verifier))
require(!Files.exists(output)){"Output directory already exists"};Files.createDirectories(output)
val source=Files.readString(grammar)
data class Case(val name:String,val expectedExit:Int,val mutation:String,val text:String)
fun removeTable(text:String,header:String,nextHeader:String):String { val begin=text.indexOf(header);require(begin>=0){"missing mutation anchor $header"};val end=text.indexOf(nextHeader,begin+header.length);require(end>=0){"missing following table"};return text.substring(0,begin)+text.substring(end+1) }
val cases=listOf(
 Case("accepted",0,"none",source),
 Case("missing-r1210",3,"remove self_clock access table",removeTable(source,"[[accesses]]\nid = \"self_clock\"","\n[[accesses]]")),
 Case("flattened-fallback",3,"remove FALLBACK_SELECT to BRAM edge",removeTable(source,"[[edges]]\nfrom = \"FALLBACK_SELECT\"\nto = \"BRAM\"","\n[[edges]]")),
 Case("bad-access-opcode",3,"change self_clock call opcode by one",source.replaceFirst("call_opcode = 0x97fe913e","call_opcode = 0x97fe913f").also{require(it!=source)}),
 Case("bad-retry-bound",3,"change last_ready read_pairs from 201 to 200",source.replaceFirst("name = \"last_ready\"\nready_at = 201\nread_pairs = 201","name = \"last_ready\"\nready_at = 201\nread_pairs = 200").also{require(it!=source)})
)
fun quote(s:String)="\""+s.replace("\\","\\\\").replace("\"","\\\"")+"\""
data class Result(val case:Case,val exit:Int,val command:String)
val results=mutableListOf<Result>()
for(c in cases){val casePath=output.resolve("${c.name}.grammar.toml");Files.writeString(casePath,c.text);val command=listOf("kotlinc","-script",verifier.toString(),"--",elf.toString(),casePath.toString());val process=ProcessBuilder(command).start();val stdout=process.inputStream.readBytes();val stderr=process.errorStream.readBytes();val exit=process.waitFor();Files.write(output.resolve("${c.name}.stdout"),stdout);Files.write(output.resolve("${c.name}.stderr"),stderr);Files.writeString(output.resolve("${c.name}.exit"),"$exit\n");Files.writeString(output.resolve("${c.name}.command"),command.joinToString(" ")+"\n");require(exit==c.expectedExit){"${c.name}: expected ${c.expectedExit}, got $exit"};results+=Result(c,exit,command.joinToString(" "))}
Files.newBufferedWriter(output.resolve("results.toml")).use{w->w.appendLine("schema_version = \"mho900-lab.init-tail-verifier-control/1\"");w.appendLine("cases = ${results.size}");w.appendLine("all_expected_exits = true");for(r in results){w.appendLine("\n[[results]]");w.appendLine("name = ${quote(r.case.name)}");w.appendLine("mutation = ${quote(r.case.mutation)}");w.appendLine("command = ${quote(r.command)}");w.appendLine("expected_exit = ${r.case.expectedExit}");w.appendLine("actual_exit = ${r.exit}");w.appendLine("grammar = ${quote("${r.case.name}.grammar.toml")}");w.appendLine("stdout = ${quote("${r.case.name}.stdout")}");w.appendLine("stderr = ${quote("${r.case.name}.stderr")}")}}
println("schema_version = \"mho900-lab.init-tail-verifier-control/1\"")
println("result = \"accepted\"")
println("cases = ${results.size}")
println("output = \"$output\"")
