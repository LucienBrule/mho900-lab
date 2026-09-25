// Independent verifier for the bounded calibration filesystem experiment.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size in 1..2) { "Usage: VerifyCalibrationFilesystem.main.kts RUN_DIRECTORY [precondition|fixture|complete]" }
val run = Path.of(args[0]).toAbsolutePath().normalize()
val phase = args.getOrElse(1) { "complete" }
require(phase in setOf("precondition", "fixture", "complete")) { "unknown verification phase" }
fun path(name: String) = run.resolve(name)
fun text(name: String) = Files.readString(path(name)).replace("\r\n", "\n")
fun bytes(name: String) = Files.readAllBytes(path(name))
fun sha256(data: ByteArray) = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(data))
fun sha256(name: String) = sha256(bytes(name))
fun lines(name: String) = text(name).lineSequence().filter { it.isNotBlank() }.toList()

fun unescapeMount(s: String): String = s.replace("\\040", " ").replace("\\011", "\t")
    .replace("\\012", "\n").replace("\\134", "\\")
fun optionSet(s: String) = s.split(',').filter { it.isNotEmpty() }.toSet()
data class ProcMount(val source: String, val target: String, val type: String, val options: Set<String>)
fun procMounts(name: String): List<ProcMount> = lines(name).map { line ->
    val f = line.split(Regex(" +")); require(f.size == 6) { "malformed /proc/mounts row" }
    ProcMount(unescapeMount(f[0]), unescapeMount(f[1]), f[2], optionSet(f[3]))
}
data class MountInfo(val id: Int, val parent: Int, val root: String, val target: String,
                     val options: Set<String>, val optional: List<String>, val type: String,
                     val source: String, val superOptions: Set<String>)
fun mountInfo(name: String): List<MountInfo> = lines(name).map { line ->
    val halves = line.split(" - ", limit = 2); require(halves.size == 2) { "malformed mountinfo separator" }
    val l = halves[0].split(' '); val r = halves[1].split(' ')
    require(l.size >= 6 && r.size >= 3 && l[2].matches(Regex("[0-9]+:[0-9]+"))) { "malformed mountinfo row" }
    MountInfo(l[0].toInt(), l[1].toInt(), unescapeMount(l[3]), unescapeMount(l[4]), optionSet(l[5]),
        l.drop(6), r[0], unescapeMount(r[1]), optionSet(r[2]))
}
fun verifyRoot(mounts: List<ProcMount>, info: List<MountInfo>) {
    val m = mounts.single { it.target == "/" }
    require(m.source == "rootfs" && m.type == "rootfs" && "ro" in m.options && "rw" !in m.options)
    val i = info.single { it.target == "/" }
    require(i.root == "/" && i.source == "rootfs" && i.type == "rootfs" && "ro" in i.options && "rw" !in i.options)
}
data class StatRow(val path: String, val mode: Int, val uid: Int, val gid: Int)
fun stats(name: String): List<StatRow> = lines(name).map { line ->
    val f = line.split(Regex(" +")); require(f.size == 4) { "malformed stat row" }
    StatRow(f[0], f[1].toInt(), f[2].toInt(), f[3].toInt())
}
data class LabelRow(val path: String, val context: String)
fun labels(name: String): List<LabelRow> = lines(name).filterNot { it.startsWith("total ") }.map { line ->
    val f = line.trim().split(Regex(" +")); require(f.size >= 5 && (f[0].startsWith("d") || f[0].startsWith("-")))
    val context = f.firstOrNull { it.count { c -> c == ':' } >= 2 } ?: error("missing SELinux label")
    LabelRow(f.last(), context)
}
fun exactPairs(name: String): List<Pair<String, Int>> = lines(name).map { line ->
    val m = Regex("^([a-z0-9_]+) = ([0-9]+)$").matchEntire(line) ?: error("malformed status row")
    m.groupValues[1] to m.groupValues[2].toInt()
}
fun pids(): Int {
    val pairs = exactPairs("fixture-system-server.toml")
    require(pairs.map { it.first } == listOf("before", "after_root") && pairs.map { it.second }.distinct().size == 1)
    val pid = pairs.first().second; require(pid > 0)
    require(text("fixture-before-pid.txt").trim().toInt() == pid && text("fixture-after-root-pid.txt").trim().toInt() == pid)
    return pid
}
fun cleanInventory(processes: String, packages: String) {
    require(text(packages).isBlank())
    require(!Regex("Sparrow|frida|group-observer|com\\.rigol\\.scope").containsMatchIn(text(processes)))
}

val beforeMounts = procMounts("fixture-before-mounts.txt")
val beforeInfo = mountInfo("fixture-before-mountinfo.txt")
verifyRoot(beforeMounts, beforeInfo)
require(beforeMounts.none { it.target == "/rigol" } && beforeInfo.none { it.target == "/rigol" })
val beforeStats = stats("fixture-before-stat.txt")
require(beforeStats.map { it.path } == listOf("/", "/rigol"))
require(beforeStats[1] == StatRow("/rigol", 755, 0, 0))
require(text("fixture-before-empty.txt").isBlank())
require(labels("fixture-before-labels.txt").map { it.path } == listOf("/", "/rigol"))
val stablePid = pids()
require(lines("fixture-enforcing.txt") == listOf("Enforcing"))
cleanInventory("fixture-processes-before.txt", "fixture-packages-before.txt")
val preKeys = listOf("before_pid", "enforcing", "packages", "processes", "adb_root", "wait_device", "after_root_pid",
    "before_mounts", "before_mountinfo", "before_stat", "before_labels", "before_empty")
val statuses = exactPairs("fixture-command-status.toml")
require(statuses.take(preKeys.size).map { it.first } == preKeys && statuses.take(preKeys.size).all { it.second == 0 })

if (phase == "precondition") {
    require(statuses.size == preKeys.size) { "future fixture commands ran before precondition verification" }
    println("schema_version = \"mho900-lab.calibration-filesystem-verification/1\"\nresult = \"accepted\"\nphase = \"precondition\"")
    kotlin.system.exitProcess(0)
}

val allKeys = preKeys + listOf("mount", "mkdir", "push_lsb", "push_vertical", "modes", "absent_paths",
    "after_mounts", "after_mountinfo", "after_stat", "after_labels", "pull_lsb", "pull_vertical")
require(statuses.map { it.first } == allKeys && statuses.all { it.second == 0 })
val afterMounts = procMounts("fixture-after-mounts.txt")
val afterInfo = mountInfo("fixture-after-mountinfo.txt")
verifyRoot(afterMounts, afterInfo)
val mounted = afterMounts.single { it.target == "/rigol" }
val mountedInfo = afterInfo.single { it.target == "/rigol" }
require(mounted.source == "tmpfs" && mounted.type == "tmpfs" && mountedInfo.root == "/" && mountedInfo.source == "tmpfs" && mountedInfo.type == "tmpfs")
val requiredMountOptions = setOf("rw", "nosuid", "nodev", "noexec")
val forbiddenMountOptions = setOf("ro", "suid", "dev", "exec")
require(requiredMountOptions.all { it in mounted.options } && forbiddenMountOptions.none { it in mounted.options })
require(requiredMountOptions.all { it in mountedInfo.options } && forbiddenMountOptions.none { it in mountedInfo.options })
val mountOptions = mounted.options + mountedInfo.options + mountedInfo.superOptions
fun sizeBytes(value: String): Long {
    val m = Regex("([0-9]+)([kKmM]?)").matchEntire(value) ?: error("bad tmpfs size")
    val factor = when (m.groupValues[2].lowercase()) { "" -> 1L; "k" -> 1024L; "m" -> 1024L * 1024L; else -> error("size suffix") }
    return Math.multiplyExact(m.groupValues[1].toLong(), factor)
}
val sizes = mountOptions.filter { it.startsWith("size=") }.map { sizeBytes(it.substringAfter('=')) }
require(sizes.isNotEmpty() && sizes.all { it == 4L * 1024L * 1024L })
val expectedPaths = listOf("/rigol", "/rigol/data", "/rigol/data/default",
    "/rigol/data/default/cal_lsb.hex", "/rigol/data/default/cal_vertical.hex")
val afterStats = stats("fixture-after-stat.txt")
require(afterStats.map { it.path } == expectedPaths)
afterStats.forEachIndexed { i, row -> require(row.mode == (if (i < 3) 755 else 644) && row.uid == 0 && row.gid == 0) }
require(labels("fixture-after-labels.txt").map { it.path } == expectedPaths)
require(text("fixture-absent-paths.txt").isBlank())
data class Asset(val id: String, val size: Int, val hash: String)
val assets = listOf(
    Asset("lsb", 220, "ee8fcfad06a5c3a18a265b0a46c2385c487bab4dcf5c04a398647358750bc4a2"),
    Asset("vertical", 1794268, "ad347e84e76e258ecb894c77fd22e089c35e817e8052340c6ac3d3b8b4cce55c"))
assets.forEach { a ->
    val stock = bytes("calibration-${a.id}-stock.bin"); val roundtrip = bytes("calibration-${a.id}-roundtrip.bin")
    require(stock.size == a.size && sha256(stock) == a.hash && roundtrip.contentEquals(stock))
}
require(sha256("calibration-loader-candidate.toml") == "6f84cda746319f02b701065bdbfe27b8e051d26b5b6a2eacba8309f85ae3dcb3")
val fixture = text("fixture-result.toml")
require(fixture.contains("result = \"installed-and-roundtrip-matched\"") && fixture.contains("stock_files = 2") &&
    fixture.contains("absent_paths = 4") && fixture.contains("stock_application_access_observed = false"))
if (phase == "fixture") {
    println("schema_version = \"mho900-lab.calibration-filesystem-verification/1\"\nresult = \"accepted\"\nphase = \"fixture\"")
    kotlin.system.exitProcess(0)
}
val result = text("result.toml")
require(result.contains("mode = \"filesystem\"") && result.contains("inspection = \"completed\""))
val health = exactPairs("final-health-status.toml")
require(health.map { it.first } == listOf("pid_exit", "enforcing_exit", "processes_exit", "packages_exit", "final_health_helper_exit") && health.all { it.second == 0 })
require(text("final-system-server.txt").trim().toInt() == stablePid && lines("final-enforcing.txt") == listOf("Enforcing"))
cleanInventory("final-processes.txt", "final-packages.txt")

val indexRows = lines("evidence-sha256.txt").map { line ->
    require(line.length > 66 && line.substring(64, 66) == "  " && line.take(64).matches(Regex("[0-9a-f]{64}")))
    val indexed = Path.of(line.substring(66)).let { if (it.isAbsolute) it else run.resolve(it) }.toAbsolutePath().normalize()
    require(indexed.startsWith(run) && Files.isRegularFile(indexed) && sha256(Files.readAllBytes(indexed)) == line.take(64))
    indexed
}
require(indexRows.distinct().size == indexRows.size)
val required = setOf("fixture-before-mounts.txt", "fixture-before-mountinfo.txt", "fixture-before-stat.txt", "fixture-before-labels.txt",
    "fixture-before-empty.txt", "fixture-system-server.toml", "fixture-command-status.toml", "fixture-after-mounts.txt",
    "fixture-after-mountinfo.txt", "fixture-after-stat.txt", "fixture-after-labels.txt", "fixture-absent-paths.txt",
    "calibration-lsb-stock.bin", "calibration-lsb-roundtrip.bin", "calibration-vertical-stock.bin", "calibration-vertical-roundtrip.bin",
    "calibration-loader-candidate.toml", "fixture-result.toml", "final-system-server.txt", "final-enforcing.txt",
    "final-processes.txt", "final-packages.txt", "final-health-status.toml", "result.toml",
    "source/calibration-filesystem-inputs.toml", "fixture-ramdisk.img")
require(required.all { run.resolve(it).toAbsolutePath().normalize() in indexRows })
val indexedImages = indexRows.filter { it.fileName.toString().endsWith(".img") }
val fixtureImage = run.resolve("fixture-ramdisk.img").toAbsolutePath().normalize()
require(indexedImages == listOf(fixtureImage) && sha256(Files.readAllBytes(fixtureImage)) ==
    "98b4925f73aa77cd21a6d4e2a3f384056dba8b2d379162ad2c02f55f3a071398")

println("schema_version = \"mho900-lab.calibration-filesystem-verification/1\"\nresult = \"accepted\"\nphase = \"complete\"\nfinal_health = \"verified\"")
