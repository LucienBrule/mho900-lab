// Offline verification of bounded thread-set discovery and cleanup.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size in 1..2) { "Usage: VerifyCoverage.main.kts RUN_DIRECTORY [0|1|stock]" }
val run=Path.of(args[0]).toAbsolutePath().normalize()
val stock=args.getOrNull(1)=="stock"
fun text(name:String)=Files.readString(run.resolve(name))
fun hash(file:Path)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(file)))
val binaryHash=hash(run.resolve("coverage-control.elf"))
require(binaryHash==text("binary-sha256.txt").take(64))
data class Event(val kind:String,val fields:Map<String,String>) {
    fun s(key:String)=fields.getValue(key)
    fun u(key:String)=s(key).removePrefix("0x").toULong(16)
}
fun events(name:String):List<Event> = text(name).split("[[events]]").drop(1).map {
    val pairs=it.lineSequence().filter { it.isNotBlank() }.map {
        val p=it.split(" = ",limit=2); require(p.size==2); p[0] to p[1].removeSurrounding("\"")
    }.toList()
    require(pairs.map { it.first }.distinct().size==pairs.size)
    val f=pairs.toMap(); Event(f.getValue("kind"),f)
}
data class ThreadState(var live:Boolean=true,var stopped:Boolean=false,var traced:Boolean=false)
data class Identity(val tgid:ULong,val tracer:ULong,val state:ULong)
val arms=if(stock) listOf(-1) else if(args.size==2) listOf(args[1].toInt().also { require(it in 0..1) }) else listOf(0,1)
for(arm in arms) {
    val prefix=if(stock) "native" else "coverage-$arm"
    require(text("$prefix-status.toml").trim()=="exit_code = 0")
    require(hash(run.resolve(if(stock) "coverage-executed.elf" else "coverage-$arm.elf"))==binaryHash)
    val r=events(if(stock) "native-events.toml" else "$prefix.toml")
    val mode=r.first(); require(mode.kind=="coverage-mode" && mode.s("scope")==if(stock) "stock" else "private")
    if(!stock) require(mode.u("arm")==arm.toULong())
    val setup=r[1]; require(setup.kind=="group-setup")
    val pid=setup.u("pid"); val observer=setup.u("observer_pid")
    require(pid==mode.u("pid") && pid>1uL && observer>1uL && pid!=observer && setup.u("options")==0x100008uL)
    require(setup.u("thread_limit")==128uL && setup.u("pass_limit")==16uL && setup.u("event_limit")==256uL && setup.u("deadline_ms")==10000uL)
    val tracked=linkedMapOf<ULong,ThreadState>(); val identities=mutableMapOf<ULong,Identity>()
    val pendingStops=mutableSetOf<ULong>(); val waitStatus=mutableMapOf<ULong,ULong>()
    val enumerations=mutableListOf<Set<ULong>>(); var enumerating=false; var currentPass=0uL
    var listed=linkedSetOf<ULong>(); var stoppedAtStart=setOf<ULong>(); var finalStoppedAtStart=setOf<ULong>()
    var waitIndex=0uL; var covered=false; var cleaned=false; var late:ULong?=null
    var converged=mutableSetOf<ULong>(); var finalSet=setOf<ULong>(); val reaped=mutableSetOf<ULong>()
    for(e in r.drop(2)) {
        require(!cleaned) { "Events after cleanup" }
        when(e.kind) {
            "enumeration-start"->{
                require(!covered && !enumerating && e.u("pass")==enumerations.size.toULong() && enumerations.size<16)
                enumerating=true; currentPass=e.u("pass"); listed=linkedSetOf()
                stoppedAtStart=tracked.filterValues { it.live && it.traced && it.stopped }.keys.toSet()
            }
            "enumerated"->{ require(enumerating && e.u("pass")==currentPass && listed.add(e.u("tid")) && listed.size<=128) }
            "enumeration-end"->{
                require(enumerating && e.u("pass")==currentPass && e.u("count")==listed.size.toULong() && pid in listed)
                enumerating=false; enumerations.add(listed.toSet()); finalStoppedAtStart=stoppedAtStart
            }
            "private-late-thread"->{
                require(!stock && arm==1 && !enumerating && enumerations.size==1 && late==null && e.u("pass")==0uL)
                late=e.u("tid"); require(late !in enumerations[0] && e.u("creator_tid")==mode.u("fixture_existing_tid"))
            }
            "group-identity"->{
                require(!covered && !enumerating)
                val tid=e.u("tid"); val id=Identity(e.u("tgid"),e.u("tracer_pid"),e.u("state"))
                require(id.tgid==pid && id.tracer in setOf(0uL,observer) && id.state>0uL)
                identities[tid]=id
                if(id.tracer==observer) tracked[tid]?.traced=true
                when(e.s("phase")) {
                    "before-seize"->require(tid in enumerations.last())
                    "auto-stop","clone-child","seize-race"->require(id.tracer==observer)
                    "converged"->{
                        require(id.tracer==observer && id.state==0x74uL && tid in enumerations.last())
                        require(tracked[tid]?.let { it.live && it.stopped && it.traced }==true && converged.add(tid))
                    }
                    else->error("Unknown identity phase")
                }
            }
            "group-track"->{
                require(!covered && tracked.size<128); val tid=e.u("tid"); require(tid !in tracked && tid in identities)
                tracked[tid]=ThreadState(stopped=pendingStops.remove(tid),traced=identities.getValue(tid).tracer==observer)
            }
            "group-seize"->{
                val tid=e.u("tid"); val t=tracked.getValue(tid); require(!covered && t.live && !t.stopped && e.u("options")==0x100008uL)
                val rc=e.u("result").toLong(); require(rc in listOf(0L,-1L,-3L))
                if(rc==0L) { require(identities.getValue(tid).tracer==0uL); t.traced=true }
            }
            "group-interrupt"->{
                val t=tracked.getValue(e.u("tid")); require(!covered && t.live && t.traced && e.u("result").toLong() in listOf(0L,-5L))
            }
            "group-wait"->{
                require(!covered && e.u("index")==waitIndex++ && waitIndex<=256uL)
                val tid=e.u("tid"); val status=e.u("status"); waitStatus[tid]=status
                if(status and 255uL==127uL) {
                    require(status in listOf(0x80057fuL,0x3057fuL))
                    val t=tracked[tid]
                    if(t==null) require(pendingStops.add(tid))
                    else { require(t.live && t.traced && !t.stopped); t.stopped=true }
                } else require(tid in tracked)
            }
            "group-clone"->{
                val parent=e.u("parent_tid"); val child=e.u("new_tid")
                require(!covered && waitStatus[parent]==0x3057fuL && tracked.getValue(parent).stopped && child!=parent && child!=observer)
            }
            "group-exit"->{
                val t=tracked.getValue(e.u("tid")); require(!covered && t.live && e.u("status")==waitStatus[e.u("tid")])
                require(e.u("status") and 255uL!=127uL); t.live=false; t.stopped=false
            }
            "group-vanished"->{
                require(!covered && e.u("result").toLong() in listOf(-2L,-3L))
                tracked[e.u("tid")]?.let { it.live=false; it.stopped=false }
            }
            "group-covered"->{
                require(!covered && !enumerating && pendingStops.isEmpty())
                finalSet=enumerations.last(); require(finalSet==converged && finalSet==tracked.filterValues { it.live }.keys)
                require(finalSet==finalStoppedAtStart && finalSet.all { tracked.getValue(it).let { t->t.traced && t.stopped } })
                require(e.u("pid")==pid && e.u("observer_pid")==observer && e.u("count")==finalSet.size.toULong() && e.u("passes")==enumerations.size.toULong())
                covered=true
            }
            "group-reaped"->{
                val tid=e.u("tid"); require(covered && tid in finalSet && reaped.add(tid) && e.u("status")==9uL)
            }
            "group-cleanup"->{
                require(covered && reaped==finalSet && e.u("expected_count")==finalSet.size.toULong() && e.u("reaped_count")==finalSet.size.toULong() && e.u("wait_result").toLong()==-10L)
                cleaned=true
            }
            else->error("Unexpected coverage event: ${e.kind}")
        }
    }
    require(covered && cleaned && enumerations.size>=2)
    if(!stock) {
        val initial=setOf(pid,mode.u("fixture_existing_tid")); require(enumerations[0]==initial)
        if(arm==0) require(late==null && finalSet==initial && enumerations.size==2)
        else require(late!=null && finalSet==initial+late && enumerations.size==3 && enumerations[1]==finalSet)
        require(r.none { it.kind in setOf("group-clone","group-exit","group-vanished") })
    } else require(pid==text("native-app-pid.toml").substringAfter("= ").trim().toULong())
    println("${if(stock) "stock" else "arm_$arm"}_coverage = \"verified\"")
    println("${if(stock) "stock" else "arm_$arm"}_threads = ${finalSet.size}")
    println("${if(stock) "stock" else "arm_$arm"}_passes = ${enumerations.size}")
    println("${if(stock) "stock" else "arm_$arm"}_clone_events = ${r.count { it.kind=="group-clone" }}")
}
if(args.size==1 || stock) {
    for(line in Files.readAllLines(run.resolve("evidence-sha256.txt"))) {
        require(line.length>66); val artifact=Path.of(line.substring(66)).normalize()
        require(artifact.startsWith(run) && hash(artifact)==line.take(64))
    }
    if(!stock) {
        require(text("result.toml").contains("mode = \"discovery\"") && text("result.toml").contains("inspection = \"completed\""))
        require(text("coverage-packages.txt").isBlank())
        require(text("coverage-enforcing.txt").lineSequence().filter { it.isNotBlank() }.toList()==listOf("Enforcing","Enforcing"))
        val pids=text("coverage-system-server.toml").lineSequence().filter { it.isNotBlank() }.map { it.substringAfter("= ").toInt() }.toList()
        require(pids.size==4 && pids.distinct().size==1)
        require(!text("coverage-processes-after.txt").contains("thread-coverage"))
        println("system_server_pid = ${pids.first()}")
        println("stock_application_run = false")
    } else {
        require(text("result.toml").contains("mode = \"coverage\""))
        for(script in listOf("VerifySnapshot.main.kts","VerifyNative.main.kts")) {
            val command=mutableListOf("kotlin",run.resolve("source/$script").toString(),run.toString())
            if(script=="VerifyNative.main.kts") command.add("admission-only")
            val p=ProcessBuilder(command).redirectErrorStream(true).start()
            val output=p.inputStream.bufferedReader().readText(); require(p.waitFor()==0) { "$script failed: $output" }; print(output)
        }
        for(name in listOf("coverage-device-before.toml","coverage-device-after.toml")) require(text(name).trim()=="device_absent = true")
        require(text("native-final-enforcing.txt").trim()=="Enforcing")
        val finalPid=text("native-final-system-server.txt").trim().toInt()
        require(text("system-server-pid.toml").lineSequence().filter { it.isNotBlank() }.all { it.substringAfter("= ").toInt()==finalPid })
        println("modeled_device_responses = 0")
    }
    println("evidence_index = \"verified\"")
}
