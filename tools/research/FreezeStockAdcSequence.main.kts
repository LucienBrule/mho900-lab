// Freeze one stock prediction test; refuses replacement of an existing manifest.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.time.Instant
import java.util.HexFormat
require(args.size == 2) { "Usage: FreezeStockAdcSequence.main.kts NEW_MANIFEST TASK_CONTRACT" }
val out=Path.of(args[0]); require(!Files.exists(out))
val contract=args[1]; require(contract.matches(Regex("sha256:[0-9a-f]{64}")))
fun hash(p:Path):String { val d=MessageDigest.getInstance("SHA-256"); Files.newInputStream(p).use { s -> val b=ByteArray(65536); while(true){val n=s.read(b);if(n<0)break;d.update(b,0,n)} };return HexFormat.of().formatHex(d.digest()) }
data class Artifact(val path:String,val runPath:String)
val artifacts=mutableListOf<Artifact>()
fun add(path:String,runPath:String)=artifacts.add(Artifact(path,runPath))
Files.list(Path.of("tools/guest")).use { ps -> ps.sorted().filter { Files.isRegularFile(it) }.forEach { add(it.toString(),"source/${it.fileName}") } }
for(name in listOf("InspectCalibrationAssets.main.kts","FreezeStockAdcSequence.main.kts","FreezeFridaEnvironment.main.kts","BuildAdcSequenceProfile.main.kts","VerifyAdcSequenceImage.main.kts","InstantiateAdcCandidate.main.kts","VerifyAdcCandidate.main.kts")) add("tools/research/$name","source/$name")
Files.list(Path.of("experiments/adc-parameter-static")).use { ps -> ps.sorted().filter { it.toString().endsWith(".toml") }.forEach { add(it.toString(),"adc-parameter-static/${it.fileName}") } }
for(name in listOf("candidate.toml","sequence.tsv"))add("experiments/adc-candidate/$name","adc-candidate/$name")
add("experiments/adc-sequence/profile.toml","adc-sequence/profile.toml")
add("experiments/adc-sequence/private-run-03-results.toml","source/adc-sequence-private-results.toml")
add("experiments/guest-baseline/inputs.toml","source/baseline-inputs.toml")
add("experiments/guest-admission/inputs.toml","source/admission-inputs.toml")
add("experiments/calibration-filesystem/inputs.toml","source/calibration-filesystem-inputs.toml")
add("experiments/calibration-loaders/stock-inputs.toml","source/calibration-stock-inputs.toml")
add("experiments/adc-input-capture/decision.toml","source/adc-input-capture-decision.toml")
add("experiments/calibration-static/loader-candidate.toml","calibration-loader-candidate.toml")
add("experiments/adc-transcript/reference.tsv","reference.tsv")
add("experiments/adc-transcript/derivation.toml","derivation.toml")
add("experiments/spu-transcript/derivation.toml","spu-derivation.toml")
for(kind in listOf("adc","spu"))add("out/$kind-transcript/derived-01/$kind-stock.bin","$kind-stock.bin")
for((name,target)in listOf("stock-gate" to "remaining-stock-gate","rearm-profile" to "remaining-rearm-profile","grammar" to "remaining-grammar"))add("experiments/remaining-init/$name.toml","$target.toml")
for((name,target)in listOf("stock-gate" to "tail-stock-gate","candidate" to "tail-candidate","grammar" to "tail-grammar","controls-handoff" to "tail-control-fixture","handoff-profile" to "tail-handoff-profile"))add("experiments/init-tail/$name.toml","$target.toml")
add("experiments/group-observer/fixture.toml","group-fixture.toml")
add("local/guest-inputs/Sparrow.apk","stock-input.apk")
for(name in listOf("unrelated","different-signer","changed-bytes"))add("local/guest-inputs/admission-controls/$name.apk","admission-controls/$name.apk")
for(kind in listOf("lsb","vertical"))add("local/reversing/firmware-extracted/stock-0.26/firmware/data/default/cal_$kind.hex","calibration-source/firmware/data/default/cal_$kind.hex")
add("out/calibration-filesystem/build-04/ramdisk.img","fixture-ramdisk.img")
add("out/stock-adc-sequence-preparation/frida-environment-files.toml","source/frida-environment-files.toml")
val nativeDir="out/adc-sequence-profile/native-build02"
val native="$nativeDir/group-observer"
require(hash(Path.of(native))=="960b91e1b3cd7de8f49d47833c6e13ec43afcc597bb0d205c379f471a2bcda37")
require(hash(Path.of("experiments/adc-sequence/profile.toml"))=="1fd5ffcf09094da41bd7aa08ed60974b6a6f4c3be9ba7f0f92eebdab087d8abb")
add(native,"group-control.elf")
for(name in listOf("build-inputs.txt","adc-sequence-inputs.txt","compiler.txt","linker.txt","binary-sha256.txt"))add("$nativeDir/$name",name)
require(artifacts.map { it.runPath }.distinct().size==artifacts.size)
artifacts.forEach { a -> for(s in listOf(a.path,a.runPath))require(!Path.of(s).isAbsolute&&!s.split('/').contains(".."));require(Files.isRegularFile(Path.of(a.path))&&!Files.isSymbolicLink(Path.of(a.path))) }
val old=Files.readString(Path.of("experiments/adc-input-capture/stock-inputs.toml"))
val fixture=old.substringAfter("[derivative]").substringBefore("[[artifacts]]")
val body=buildString {
    append("schema_version = \"mho900-lab.adc-sequence-stock/1\"\nfrozen_at = \"${Instant.now()}\"\ntask = \"TASK.guest.adc-sequence-stock-run\"\ntask_contract = \"$contract\"\n")
    append("question = \"Does stock ADC initialization match the complete statically predicted sequence?\"\nmode = \"adcsequencemodel\"\nrun_id = \"stock-adc-sequence-01\"\nexpected_statuses = [192, 1794240, -1]\n")
    append("terminal_relative_pc = 0x333bac\nterminal_opcode = 0x5285070a\nterminal_instruction_executes = false\nnew_modeled_mmio_responses = 2\nnew_modeled_reads = 2\nnew_modeled_writes = 97\nexpected_operations = 99\nexpected_entry_guards = 175\nexpected_final_shadows = 33\nsynthetic_read_values = [0x11234, 0]\nadaptive_retry = false\nphysical_access = false\nphysical_instrument_access = false\n")
    append("stock_apk_sha256 = \"6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b\"\nstock_elf_sha256 = \"4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e\"\n")
    append("\n[native]\npath = \"$native\"\nsha256 = \"${hash(Path.of(native))}\"\nsource_sha256 = \"${hash(Path.of("tools/guest/group-observer.c"))}\"\nheader_sha256 = \"${hash(Path.of("tools/guest/calibration-loaders.h"))}\"\ncapture_header_sha256 = \"${hash(Path.of("tools/guest/adc-parameter-capture.h"))}\"\nprofile = 1\nloader_deadline_ms = 10000\n")
    append("\n[derivative]$fixture")
    append("\n[instrumentation]\npython_version = \"Python 3.12.13\"\nfrida_version = \"16.7.19\"\nfrida_tools_version = \"13.7.1\"\ninventory_sha256 = \"${hash(Path.of("out/stock-adc-sequence-preparation/frida-environment-files.toml"))}\"\n")
    artifacts.forEach { a -> append("\n[[artifacts]]\npath = \"${a.path}\"\nrun_path = \"${a.runPath}\"\nsha256 = \"${hash(Path.of(a.path))}\"\n") }
}
Files.createDirectories(out.toAbsolutePath().parent);Files.writeString(out,body)
println("manifest_sha256 = \"${hash(out)}\"\nartifacts = ${artifacts.size}")
