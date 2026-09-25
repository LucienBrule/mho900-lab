// Check the declared local tool bytes before the disposable guest starts.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size == 2) { "Usage: VerifyFridaEnvironment.main.kts TOOL_ROOT INVENTORY" }
val root = Path.of(args[0]).toAbsolutePath().normalize()
val inventory = Path.of(args[1])
fun hash(p: Path): String { val d = MessageDigest.getInstance("SHA-256"); Files.newInputStream(p).use { s -> val b=ByteArray(65536); while(true){ val n=s.read(b); if(n<0)break; d.update(b,0,n) } }; return HexFormat.of().formatHex(d.digest()) }
fun field(s: String, k: String): String = Regex("(?m)^${Regex.escape(k)} = \"([^\"]+)\"$").findAll(s).toList().single().groupValues[1]
val body=Files.readString(inventory)
require(field(body,"schema_version")=="mho900-lab.frida-environment/1")
val declared=body.split("[[files]]").drop(1).map { b ->
    val name=field(b,"path"); val p=root.resolve(name).normalize()
    require(!Path.of(name).isAbsolute && p.startsWith(root) && Files.isRegularFile(p))
    require(hash(p)==field(b,"sha256")) { "tool input: $name" }; name
}
val actual=Files.walk(root).use { all -> all.filter { Files.isRegularFile(it) && !it.toString().contains("/__pycache__/") && !it.toString().endsWith(".pyc") }.map { root.relativize(it).toString() }.toList() }
require(declared.isNotEmpty() && declared.distinct().size==declared.size && declared.toSet()==actual.toSet()) { "tool inventory" }
require(listOf("server","venv/bin/python","venv/bin/frida").all { it in declared })
println("schema_version = \"mho900-lab.frida-environment-verification/1\"\nresult = \"accepted\"\nfiles = ${declared.size}\ninventory_sha256 = \"${hash(inventory)}\"")
