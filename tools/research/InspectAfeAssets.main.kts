// Inventory only the four AFE paths in a supplied extracted corpus, without reading a device.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size==2){"Usage: InspectAfeAssets.main.kts EXTRACTED_STOCK_ROOT NEW_OUTPUT"}
val root=Path.of(args[0]);val out=Path.of(args[1]);require(Files.isDirectory(root.resolve("firmware/data/default"))&&!Files.exists(out))
val records=buildString{
 append("schema_version = \"mho900-lab.afe-asset-inventory/1\"\nclassification = \"provided-extracted-corpus-only\"\nphysical_presence_established = false\n")
 for(name in listOf("cal_afe_zero.hex","cal_afe_bandwidth.hex"))for(prefix in listOf("firmware/data/","firmware/data/default/")){
  val relative=prefix+name;val p=root.resolve(relative);append("\n[[assets]]\npath = \"$relative\"\npresent = ${Files.exists(p)}\n")
  if(Files.exists(p)){require(Files.isRegularFile(p));val b=Files.readAllBytes(p);append("bytes = ${b.size}\nsha256 = \"${HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b))}\"\n")}
 }
}
Files.createDirectories(out.toAbsolutePath().parent);Files.writeString(out,records);print(records)
