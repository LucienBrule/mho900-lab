// Offline process-snapshot gate; the raw command statuses remain part of the evidence.
import java.nio.file.Files
import java.nio.file.Path
require(args.size==1)
val run=Path.of(args[0])
fun text(name:String)=Files.readString(run.resolve(name))
fun status(part:String):Int {
    val raw=text("native-snapshot-$part-status.toml").trim()
    require(raw.startsWith("exit_code = "))
    return raw.substringAfter("= ").toInt()
}
val composite=status("composite")
println("composite_exit = $composite")
for(part in listOf("cmdline","label","maps")) {
    require(status(part)==0) { "$part command failed: ${status(part)}" }
    require(text("native-snapshot-$part-error.txt").isBlank()) { "$part error output" }
}
require(text("native-snapshot-cmdline.txt").substringBefore('\u0000')=="com.rigol.scope")
require(text("native-snapshot-label.txt").trim('\u0000','\r','\n',' ')=="u:r:system_app:s0")
data class Mapping(val start:ULong,val end:ULong,val permissions:String,val offset:ULong,val file:String)
val line=Regex("^([0-9a-f]+)-([0-9a-f]+) ([r-][w-][x-][ps]) ([0-9a-f]+) [0-9a-f]+:[0-9a-f]+ [0-9]+(?:\\s+(.*))?$")
val raw=text("native-snapshot-maps.txt")
require(raw.endsWith('\n')) { "Incomplete maps line" }
val mappings=raw.lineSequence().filter { it.isNotBlank() }.map {
    val g=requireNotNull(line.matchEntire(it.trimEnd())) { "Invalid maps row" }.groupValues
    Mapping(g[1].toULong(16),g[2].toULong(16),g[3],g[4].toULong(16),g[5])
}.toList()
require(mappings.isNotEmpty() && mappings.all { it.end>it.start })
require(mappings.zipWithNext().all { (a,b)->a.end<=b.start })
require(mappings.single { it.permissions=="r-xp" && it.offset==0xf05000uL && it.file.contains("com.rigol.scope") && it.file.endsWith("/base.apk") }.let { it.end-it.start>=0x42a8f4uL })
require(mappings.any { it.file=="[stack]" })
println("individual_commands_verified = 3")
println("map_rows = ${mappings.size}")
println("stock_snapshot = \"verified\"")
