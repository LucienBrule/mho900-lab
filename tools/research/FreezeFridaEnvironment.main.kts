// Snapshot a separately staged local tool environment without following directory links.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size == 2) { "Usage: FreezeFridaEnvironment.main.kts TOOL_ROOT NEW_INVENTORY" }
val root = Path.of(args[0]).toAbsolutePath().normalize()
val out = Path.of(args[1]); require(!Files.exists(out))
fun version(vararg command:String):String { val p=ProcessBuilder(*command).redirectErrorStream(true).start();val result=p.inputStream.bufferedReader().readText().trim();require(p.waitFor()==0);return result }
val pythonVersion=version(root.resolve("venv/bin/python").toString(),"--version")
val fridaVersion=version(root.resolve("venv/bin/frida").toString(),"--version")
val toolsVersion=version(root.resolve("venv/bin/python").toString(),"-c","from importlib.metadata import version; print(version('frida-tools'))")
require(pythonVersion=="Python 3.12.13"&&fridaVersion=="16.7.19"&&toolsVersion=="13.7.1")
fun hash(p: Path): String { val d = MessageDigest.getInstance("SHA-256"); Files.newInputStream(p).use { s -> val b=ByteArray(65536); while(true){ val n=s.read(b); if(n<0)break; d.update(b,0,n) } }; return HexFormat.of().formatHex(d.digest()) }
val paths = Files.walk(root).use { all -> all.filter { Files.isRegularFile(it) && !it.toString().contains("/__pycache__/") && !it.toString().endsWith(".pyc") }.sorted().toList() }
require(paths.isNotEmpty())
val body = buildString {
    append("schema_version = \"mho900-lab.frida-environment/1\"\npython_version = \"$pythonVersion\"\nfrida_version = \"$fridaVersion\"\nfrida_tools_version = \"$toolsVersion\"\n")
    for(p in paths) { val name=root.relativize(p).toString(); require(!name.contains('"') && !name.contains('\n')); append("\n[[files]]\npath = \"$name\"\nsha256 = \"${hash(p)}\"\n") }
}
Files.createDirectories(out.toAbsolutePath().parent); Files.writeString(out, body)
println("files = ${paths.size}\ninventory_sha256 = \"${hash(out)}\"")
