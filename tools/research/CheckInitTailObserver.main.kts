// Exercise the frozen observer verifier against isolated altered evidence copies.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size==2){"Usage: CheckInitTailObserver.main.kts RUN_DIRECTORY NEW_OUTPUT_DIRECTORY"}
val run=Path.of(args[0]).toAbsolutePath().normalize()
val out=Path.of(args[1]).toAbsolutePath().normalize()
require(Files.isDirectory(run)&&!Files.exists(out));Files.createDirectories(out)
val verifier=run.resolve("source/VerifyInitTailObserver.main.kts")
require(Files.isRegularFile(verifier))
val original=Files.readString(run.resolve("tail-59.toml"))
fun change(kind:String,ordinal:Int,key:String,value:String):String {
    val parts=original.split("[[events]]").toMutableList()
    val at=parts.indices.filter{parts[it].startsWith("\nkind = \"$kind\"\n")}[ordinal]
    val pattern=Regex("(?m)^${Regex.escape(key)} = \"([^\"]+)\"$")
    require(pattern.findAll(parts[at]).count()==1)
    parts[at]=parts[at].replace(pattern,"$key = \"$value\"")
    return parts.joinToString("[[events]]").also{require(it!=original)}
}
fun flip(kind:String,ordinal:Int,key:String):String {
    val block=original.split("[[events]]").filter{it.startsWith("\nkind = \"$kind\"\n")}[ordinal]
    val raw=Regex("(?m)^${Regex.escape(key)} = \"0x([0-9a-f]+)\"$").find(block)!!.groupValues[1].toULong(16)
    return change(kind,ordinal,key,"0x"+(raw xor 1uL).toString(16))
}
fun remove(kind:String,ordinal:Int):String {
    val parts=original.split("[[events]]").toMutableList()
    val at=parts.indices.filter{parts[it].startsWith("\nkind = \"$kind\"\n")}[ordinal]
    parts.removeAt(at);return parts.joinToString("[[events]]")
}
data class Case(val name:String,val altered:String,val pass:Boolean=false)
val cases=listOf(
    Case("accepted",original,true),
    Case("wrong-read-value",flip("tail-read",0,"value")),
    Case("changed-unrelated-register",flip("tail-read-registers",0,"x00")),
    Case("wrong-write-operand",flip("tail-write",0,"value")),
    Case("missing-parent-output",remove("tail-parent-output",6)),
    Case("changed-parent-output",flip("tail-parent-output",6,"actual")),
    Case("changed-parent-upper-half",change("tail-parent-output",6,"actual","0x100000345")),
    Case("missing-thread-reap",remove("group-reaped",0)),
    Case("wrong-checkpoint-pc",flip("tail-checkpoint",2,"pc")),
    Case("wrong-initial-clear",change("tail-debug-clear-after",0,"c00","0x1e5")),
    Case("changed-binding",flip("tail-binding",0,"actual_target")),
    Case("changed-summary",flip("tail-summary",0,"total_writes"))
)
fun quote(s:String)="\""+s.replace("\\","\\\\").replace("\"","\\\"")+"\""
fun hash(path:Path)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path)))
var correct=true
Files.newBufferedWriter(out.resolve("results.toml")).use { w ->
    w.appendLine("schema_version = \"mho900-lab.init-tail-observer-verifier-controls/1\"")
    w.appendLine("verifier_sha256 = ${quote(hash(verifier))}")
    w.appendLine("source_events_sha256 = ${quote(hash(run.resolve("tail-59.toml")))}")
    for(c in cases){
        val dir=out.resolve(c.name);Files.createDirectory(dir)
        Files.list(run).use { paths -> paths.filter{it.fileName.toString()!="tail-59.toml"}.forEach { Files.createSymbolicLink(dir.resolve(it.fileName),it) } }
        Files.writeString(dir.resolve("tail-59.toml"),c.altered)
        val command=listOf("kotlin",verifier.toString(),dir.toString(),"59")
        Files.writeString(dir.resolve("command.txt"),command.joinToString("\n")+"\n")
        val process=ProcessBuilder(command).redirectOutput(dir.resolve("stdout.toml").toFile()).redirectError(dir.resolve("stderr.txt").toFile()).start()
        val exit=process.waitFor();val ok=(exit==0)==c.pass
        Files.writeString(dir.resolve("exit.toml"),"exit_code = $exit\n")
        w.appendLine("\n[[cases]]");w.appendLine("name = ${quote(c.name)}");w.appendLine("expected_accept = ${c.pass}");w.appendLine("exit_code = $exit");w.appendLine("expected_result = $ok");w.flush()
        correct=correct&&ok
    }
}
require(correct){"An altered evidence case was accepted or valid evidence was rejected"}
println("result = \"accepted\"\ncases = ${cases.size}\nnegative_cases = ${cases.size-1}")
