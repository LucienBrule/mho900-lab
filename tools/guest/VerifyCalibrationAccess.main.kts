// Independent verifier for the bounded system_app calibration-file access probe.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 1) { "Usage: VerifyCalibrationAccess.main.kts RUN_DIRECTORY" }
val run = Path.of(args[0]).toAbsolutePath().normalize()
fun path(name: String) = run.resolve(name)
fun text(name: String) = Files.readString(path(name)).replace("\r\n", "\n")
fun bytes(name: String) = Files.readAllBytes(path(name))
fun lines(name: String) = text(name).lineSequence().filter { it.isNotBlank() }.toList()
fun hash(data: ByteArray) = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(data))
fun hash(name: String) = hash(bytes(name))
fun value(raw: String): String = raw.trim().removeSurrounding("\"")
fun simplePairs(content: String): List<Pair<String, String>> = content.lineSequence().filter { it.isNotBlank() && !it.startsWith('#') && !it.startsWith('[') }.map { line ->
    val p = line.split(" = ", limit = 2); require(p.size == 2) { "malformed TOML assignment" }; p[0] to value(p[1])
}.toList()
fun exactStatus(name: String): List<Pair<String, Int>> = lines(name).map { line ->
    val m = Regex("^([a-z0-9_]+) = ([0-9]+)$").matchEntire(line) ?: error("malformed command status")
    m.groupValues[1] to m.groupValues[2].toInt()
}
fun section(content: String, name: String): Map<String, String> {
    val body = content.substringAfter("[$name]\n", missingDelimiterValue = "").substringBefore("\n[")
    require(body.isNotEmpty()) { "missing [$name]" }
    val pairs = simplePairs(body); require(pairs.map { it.first }.distinct().size == pairs.size)
    return pairs.toMap()
}

val input = text("source/calibration-access-inputs.toml")
val probe = section(input, "probe")
val derivative = section(input, "derivative")
val apkHash = "f1aadc9fefc4278f86a9839a8917a2ce42ee5c1fedbd52562b5187ef2bd2dec0"
val signerHash = "c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8"
require(probe.getValue("apk_sha256") == apkHash && probe.getValue("signer_sha256") == signerHash)
require(probe.getValue("apk_path") == "out/calibration-access/build-01/calibration-access.apk")
require(probe.getValue("package") == "lab.mho900.calibration.access" && probe.getValue("expected_uid") == "1000" &&
    probe.getValue("expected_context") == "u:r:system_app:s0" && probe.getValue("report_schema") == "mho900-lab.calibration-access-probe/1" &&
    probe.getValue("requested_permissions") == "0")
require(derivative.getValue("sha256") == "98b4925f73aa77cd21a6d4e2a3f384056dba8b2d379162ad2c02f55f3a071398")
require(hash("fixture-ramdisk.img") == derivative.getValue("sha256"))
require(hash("access-control.apk") == apkHash && hash("access-installed.apk") == apkHash && bytes("access-control.apk").contentEquals(bytes("access-installed.apk")))
require(hash("source/ProbeActivity.kt") == "3604e60d2512460e2ac291bff02738c140b9f3e8b1d925d971914c9f993008b5")
require(hash("source/AndroidManifest.xml") == "3525782d8996d9e88bd23622479db69f5391ff0fd27b823f3e6a099b4d2dc16c")
val signature = text("access-signature.txt")
val certificateDigests = Regex("(?m)^Signer #[0-9]+ certificate SHA-256 digest: ([0-9a-f]{64})$").findAll(signature).map { it.groupValues[1] }.toList()
require(certificateDigests == listOf(signerHash))
require(text("access-before-packages.txt").isBlank())
require(lines("access-install.txt").count { it == "Success" } == 1)
val packageName = "lab.mho900.calibration.access"
val packageState = text("access-package-state.txt")
require(packageState.contains("Package [$packageName]") && Regex("(?m)^\\s*userId=1000\\s*$").containsMatchIn(packageState) &&
    packageState.contains("android.uid.system"))
val packagePath = lines("access-package-path.txt").single()
require(Regex("^package:/data/app/[A-Za-z0-9_.=-]+/base\\.apk$").matches(packagePath))
require(text("access-launch.txt").contains("Status: ok"))

val pid = text("access-pid.txt").trim().toInt(); require(pid > 0)
val procStatus = text("access-proc-status.txt")
fun procNumber(key: String) = procStatus.lineSequence().single { it.startsWith("$key:") }.substringAfter(':').trim().toInt()
require(procNumber("Pid") == pid && procNumber("Tgid") == pid)
val uidLine = procStatus.lineSequence().single { it.startsWith("Uid:") }.trim().split(Regex("\\s+")).drop(1)
require(uidLine == listOf("1000", "1000", "1000", "1000"))
val processLabel = text("access-proc-label.txt").trim('\u0000', '\r', '\n', ' ')
require(processLabel == "u:r:system_app:s0")

data class Table(val fields: Map<String, String>) {
    fun s(key: String) = fields.getValue(key)
    fun i(key: String) = s(key).toLong()
    fun b(key: String): Boolean { require(s(key) == "true" || s(key) == "false"); return s(key) == "true" }
}
val reportText = text("access-report.toml")
val reportRootPairs = simplePairs(reportText.substringBefore("[[directories]]"))
require(reportRootPairs.map { it.first }.distinct().size == reportRootPairs.size)
val reportRoot = reportRootPairs.toMap()
require(reportRoot.keys == setOf("schema_version", "result", "pid", "uid", "process_label"))
require(reportRoot.getValue("schema_version") == "mho900-lab.calibration-access-probe/1" && reportRoot.getValue("result") == "observed")
require(reportRoot.getValue("pid").toInt() == pid && reportRoot.getValue("uid") == "1000" && reportRoot.getValue("process_label") == processLabel)
fun tables(marker: String, until: String? = null): List<Table> {
    val region = reportText.substringAfter("[[$marker]]", missingDelimiterValue = "").let { if (until == null) it else it.substringBefore("[[$until]]") }
    require(region.isNotEmpty()) { "missing $marker tables" }
    return region.split("[[$marker]]").map { block ->
        val pairs = simplePairs(block); require(pairs.isNotEmpty() && pairs.map { it.first }.distinct().size == pairs.size)
        Table(pairs.toMap())
    }
}
val directories = tables("directories", "files")
val expectedDirs = listOf("/rigol", "/rigol/data", "/rigol/data/default")
require(directories.size == 3)
directories.forEachIndexed { index, d ->
    require(d.fields.keys == setOf("index", "path", "stat_ok", "mode", "size", "errno"))
    require(d.i("index") == index.toLong() && d.s("path") == expectedDirs[index] && d.b("stat_ok") && d.i("errno") == 0L)
    require(d.i("mode") and 0xf000L == 0x4000L && d.i("mode") and 0x1ffL == 0x1edL && d.i("size") >= 0L)
}
val files = tables("files")
data class ExpectedFile(val path: String, val size: Long, val sha256: String)
val expectedFiles = listOf(
    ExpectedFile("/rigol/data/default/cal_lsb.hex", 220, "ee8fcfad06a5c3a18a265b0a46c2385c487bab4dcf5c04a398647358750bc4a2"),
    ExpectedFile("/rigol/data/default/cal_vertical.hex", 1794268, "ad347e84e76e258ecb894c77fd22e089c35e817e8052340c6ac3d3b8b4cce55c"))
val fileKeys = setOf("index", "path", "expected_size", "stat_ok", "stat_mode", "stat_size", "stat_errno", "open_ok", "open_errno",
    "read_attempted", "read_ok", "read_bytes", "read_errno", "sha256", "close_attempted", "close_ok", "close_errno")
require(files.size == 2)
val outcomes = files.mapIndexed { index, f ->
    val expected = expectedFiles[index]
    require(f.fields.keys == fileKeys && f.i("index") == index.toLong() && f.s("path") == expected.path && f.i("expected_size") == expected.size)
    if (f.b("stat_ok")) {
        require(f.i("stat_errno") == 0L && f.i("stat_mode") and 0xf000L == 0x8000L && f.i("stat_mode") and 0x1ffL == 0x1a4L && f.i("stat_size") == expected.size)
    } else require(f.i("stat_mode") == 0L && f.i("stat_size") == 0L && f.i("stat_errno") == 13L)
    if (!f.b("open_ok")) {
        require(f.i("open_errno") == 13L && !f.b("read_attempted") && !f.b("read_ok") && f.i("read_bytes") == 0L &&
            f.i("read_errno") == 0L && f.s("sha256").isEmpty() && !f.b("close_attempted") && !f.b("close_ok") && f.i("close_errno") == 0L)
        "denied"
    } else {
        require(f.i("open_errno") == 0L && f.b("read_attempted") && f.b("close_attempted") && f.b("close_ok") && f.i("close_errno") == 0L)
        if (f.b("read_ok")) {
            require(f.i("read_errno") == 0L && f.i("read_bytes") == expected.size && f.s("sha256") == expected.sha256)
            "readable"
        } else {
            require(f.i("read_errno") == 13L && f.i("read_bytes") in 0..expected.size && f.s("sha256").isEmpty())
            "denied"
        }
    }
}
val observedAccess = when { outcomes.all { it == "readable" } -> "readable"; outcomes.all { it == "denied" } -> "denied"; else -> "mixed" }
require(text("access-audit-logcat.txt").contains("MhoCalibrationAccess") && text("access-audit-logcat.txt").contains("probe-complete report=report.toml"))

val statusKeys = listOf("fixture_exit", "before_packages", "install", "package_state", "package_path", "installed_pull", "launch", "pid",
    "proc_status", "proc_label", "report_pull", "audit_logcat", "audit_dmesg", "force_stop", "uninstall", "final_packages", "final_processes",
    "final_labels", "final_lsb_pull", "final_vertical_pull")
val statuses = exactStatus("access-command-status.toml")
require(statuses.map { it.first } == statusKeys)
statuses.forEach { (key, code) -> if (key == "audit_dmesg") require(code >= 0) else require(code == 0) }
require(text("access-final-packages.txt").isBlank() && !Regex("lab\\.mho900\\.calibration\\.access|Sparrow|group-observer|frida").containsMatchIn(text("access-final-processes.txt")))
fun labelRows(name: String): List<Pair<String, String>> = lines(name).filterNot { it.startsWith("total ") }.map { line ->
    val fields = line.trim().split(Regex("\\s+")); require(fields.size >= 5)
    val context = fields.firstOrNull { it.count { c -> c == ':' } >= 2 } ?: error("missing SELinux context")
    fields.last() to context
}
val labelPaths = expectedDirs + expectedFiles.map { it.path }
val labelContexts = List(3) { "u:object_r:tmpfs:s0" } + List(2) { "u:object_r:su_tmpfs:s0" }
for (name in listOf("fixture-after-labels.txt", "access-final-labels.txt")) {
    val observed = labelRows(name)
    require(observed.map { it.first } == labelPaths && observed.map { it.second } == labelContexts)
}
require(text("access-final-labels.txt") == text("fixture-after-labels.txt"))
expectedFiles.forEach { f ->
    val id = if (f.size == 220L) "lsb" else "vertical"
    require(hash("access-final-$id.bin") == f.sha256 && bytes("access-final-$id.bin").contentEquals(bytes("calibration-$id-stock.bin")))
}

val fixtureVerifier = run.resolve("source/VerifyCalibrationFilesystem.main.kts")
require(hash(Files.readAllBytes(fixtureVerifier)) == "6247912ee7ac1f9975a6154b8d414c1acaea64b23e1b9ef77b20c78b2d410228")
val process = ProcessBuilder("kotlinc", "-script", fixtureVerifier.toString(), "--", run.toString(), "fixture").apply {
    environment().remove("KOTLIN_RUNNER")
}.start()
val fixtureOutput = process.inputStream.bufferedReader().readText(); val fixtureError = process.errorStream.bufferedReader().readText()
require(process.waitFor() == 0 && fixtureOutput.contains("result = \"accepted\"") && fixtureOutput.contains("phase = \"fixture\"") && fixtureError.isBlank())
require(text("access-fixture-verification.toml").contains("result = \"accepted\"") && text("access-fixture-verification.stderr").isBlank())

val pidPairs = exactStatus("fixture-system-server.toml")
require(pidPairs.map { it.first } == listOf("before", "after_root") && pidPairs.map { it.second }.distinct().size == 1)
val stablePid = pidPairs.first().second
val health = exactStatus("final-health-status.toml")
require(health.map { it.first } == listOf("pid_exit", "enforcing_exit", "processes_exit", "packages_exit", "final_health_helper_exit") && health.all { it.second == 0 })
require(text("final-system-server.txt").trim().toInt() == stablePid && lines("final-enforcing.txt") == listOf("Enforcing") && text("final-packages.txt").isBlank())
require(!Regex("lab\\.mho900\\.calibration\\.access|Sparrow|group-observer|frida").containsMatchIn(text("final-processes.txt")))
val result = text("result.toml")
require(result.contains("mode = \"fileaccess\"") && result.contains("inspection = \"completed\""))

val indexRows = lines("evidence-sha256.txt").map { line ->
    require(line.length > 66 && line.substring(64, 66) == "  " && line.take(64).matches(Regex("[0-9a-f]{64}")))
    val p = Path.of(line.substring(66)).let { if (it.isAbsolute) it else run.resolve(it) }.toAbsolutePath().normalize()
    require(p.startsWith(run) && Files.isRegularFile(p) && hash(Files.readAllBytes(p)) == line.take(64)); p
}
require(indexRows.distinct().size == indexRows.size)
val required = setOf("access-control.apk", "access-installed.apk", "access-signature.txt", "access-package-state.txt", "access-package-path.txt",
    "access-pid.txt", "access-proc-status.txt", "access-proc-label.txt", "access-report.toml", "access-launch.txt", "access-audit-logcat.txt",
    "access-audit-dmesg.txt", "access-final-packages.txt", "access-final-processes.txt", "access-final-labels.txt", "access-final-lsb.bin",
    "access-final-vertical.bin", "access-command-status.toml", "final-health-status.toml", "final-system-server.txt", "final-enforcing.txt",
    "final-processes.txt", "final-packages.txt", "source/calibration-access-inputs.toml", "source/ProbeActivity.kt", "source/AndroidManifest.xml",
    "source/VerifyCalibrationAccess.main.kts", "source/VerifyCalibrationFilesystem.main.kts", "fixture-ramdisk.img", "result.toml", "access-before-packages.txt", "access-install.txt",
    "access-installed-pull.txt", "access-report-pull.txt", "access-force-stop.txt", "access-uninstall.txt", "access-final-lsb-pull.txt",
    "access-final-vertical-pull.txt", "access-fixture-verification.toml", "access-fixture-verification.stderr")
require(required.all { run.resolve(it).toAbsolutePath().normalize() in indexRows })

println("schema_version = \"mho900-lab.calibration-access-verification/1\"")
println("result = \"accepted\"")
println("observation = \"complete\"")
println("observed_access = \"$observedAccess\"")
files.forEachIndexed { index, f ->
    println("file_${index}_stat = \"${if (f.b("stat_ok")) "success" else "denied"}\"")
    println("file_${index}_open = \"${if (f.b("open_ok")) "success" else "denied"}\"")
    println("file_${index}_read = \"${outcomes[index]}\"")
}
