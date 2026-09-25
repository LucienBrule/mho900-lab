// Synthetic host-only controls of the production tool-inventory checker.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size==1) { "Usage: test-frida-environment.main.kts NEW_OUTPUT" }
val out=Path.of(args[0]).toAbsolutePath();require(!Files.exists(out));Files.createDirectories(out)
val checker=Path.of("tools/guest/VerifyFridaEnvironment.main.kts").toAbsolutePath()
fun hash(b:ByteArray)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b))
val report=StringBuilder("schema_version = \"mho900-lab.frida-environment-controls/1\"\nguest_launched = false\nchecker_sha256 = \"${hash(Files.readAllBytes(checker))}\"\n")
for(case in listOf("complete","changed-server","missing-cli","extra-input")) {
    val dir=out.resolve(case);val root=dir.resolve("tools");Files.createDirectories(root.resolve("venv/bin"))
    val names=listOf("server","venv/bin/python","venv/bin/frida")
    for(name in names)Files.writeString(root.resolve(name),"synthetic $name\n")
    val inventory=dir.resolve("inventory.toml")
    Files.writeString(inventory,"schema_version = \"mho900-lab.frida-environment/1\"\n"+names.joinToString(""){"\n[[files]]\npath = \"$it\"\nsha256 = \"${hash(Files.readAllBytes(root.resolve(it)))}\"\n"})
    when(case) {
        "changed-server"->Files.writeString(root.resolve("server"),"changed\n")
        "missing-cli"->Files.delete(root.resolve("venv/bin/frida"))
        "extra-input"->Files.writeString(root.resolve("extra.py"),"unexpected\n")
    }
    val pb=ProcessBuilder("kotlinc","-script",checker.toString(),"--",root.toString(),inventory.toString())
    pb.environment().remove("KOTLIN_RUNNER");pb.redirectOutput(dir.resolve("stdout.txt").toFile());pb.redirectError(dir.resolve("stderr.txt").toFile())
    val rc=pb.start().waitFor();require((rc==0)==(case=="complete")) { "unexpected $case: $rc" }
    report.append("\n[[cases]]\nname = \"$case\"\nexit_code = $rc\nexpected_outcome = true\n")
    Files.writeString(out.resolve("results.toml"),report)
}
println("Tool inventory: one positive and three negatives matched")
