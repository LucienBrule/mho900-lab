#!/bin/sh
set -eu
ELF="$1"
CONTRACT="$2"
ROOT="$3"
CHECKER_SOURCE="$(dirname "$0")/VerifyAdcParameter.main.kts"
test ! -e "$ROOT"
mkdir -p "$ROOT/base"
for artifact_path in "$CONTRACT/"*.toml; do
  test -f "$artifact_path" && test ! -L "$artifact_path"
  cp "$artifact_path" "$ROOT/base/"
done
cp "$CHECKER_SOURCE" "$ROOT/VerifyAdcParameter.main.kts"
CHECKER="$ROOT/VerifyAdcParameter.main.kts"
shasum -a 256 "$CHECKER" > "$ROOT/checker-sha256.txt"
run_case() {
  name=$1
  expected=$2
  set +e
  kotlinc -script "$CHECKER" -- "$ELF" "$ROOT/$name/contract" > "$ROOT/$name/stdout.toml" 2> "$ROOT/$name/stderr.txt"
  status=$?
  set -e
  printf 'case = "%s"\nexpected = "%s"\nstatus = %s\n' "$name" "$expected" "$status" > "$ROOT/$name/result.toml"
  if [ "$expected" = accepted ]; then test "$status" -eq 0; else test "$status" -ne 0; fi
}
make_case() { mkdir -p "$ROOT/$1/contract"; cp "$ROOT/base/"*.toml "$ROOT/$1/contract/"; }
make_case positive
run_case positive accepted
make_case missing-main-node
perl -0777 -i -pe 's/\n\[\[nodes\]\]\nid = "reference".*?(?=\n\[\[nodes\]\])//s' "$ROOT/missing-main-node/contract/main-grammar.toml"
run_case missing-main-node rejected
make_case missing-main-call
perl -0777 -i -pe 's/\n\[\[calls\]\]\nowner = "_ZN16CCalibration_ADC15SetADCParameterEj"\npc = 0x33f038.*?(?=\n\[\[(?:calls|branches|ranges|tables)\]\])//s' "$ROOT/missing-main-call/contract/call-inventory.toml"
run_case missing-main-call rejected
make_case signedness
perl -0777 -i -pe 's/(id = "reference".*?signed = )true/${1}false/s' "$ROOT/signedness/contract/main-grammar.toml"
run_case signedness rejected
make_case field-base
perl -0777 -i -pe 's/(id = "reference".*?field_base = )0x8854/${1}0x8855/s' "$ROOT/field-base/contract/main-grammar.toml"
run_case field-base rejected
make_case loop-bound
perl -0777 -i -pe 's/(id = "core-offset".*?iteration_last_inclusive = )15/${1}14/s' "$ROOT/loop-bound/contract/main-grammar.toml"
run_case loop-bound rejected
make_case table-operand
perl -0777 -i -pe 's/(id = "delay-map".*?values = \[)0,4/${1}1,4/s' "$ROOT/table-operand/contract/stary-grammar.toml"
run_case table-operand rejected
make_case relocation
perl -0777 -i -pe 's/(index = 0\nname = "maskValue"\ngot_slot = )0xb8eea8/${1}0xb8eea0/s' "$ROOT/relocation/contract/helper-refinements.toml"
run_case relocation rejected
make_case range-hash
perl -0777 -i -pe 's/(name = "_ZN16CCalibration_ADC15SetADCParameterEj"\naddress = 0x33efe0\nsize = 3232\nsha256 = ")[0-9a-f]/${1}0/' "$ROOT/range-hash/contract/call-inventory.toml"
run_case range-hash rejected
make_case missing-helper-call
perl -0777 -i -pe 's/\n\[\[calls\]\]\nowner = "DevAcquireADC_SetADCReg".*?(?=\n\[\[(?:calls|branches|ranges|tables)\]\])//s' "$ROOT/missing-helper-call/contract/call-inventory.toml"
run_case missing-helper-call rejected
make_case missing-branch
perl -0777 -i -pe 's/\n\[\[branches\]\].*?(?=\n\[\[(?:calls|branches|ranges|tables)\]\])//s' "$ROOT/missing-branch/contract/call-inventory.toml"
run_case missing-branch rejected
make_case branch-successor
perl -0777 -i -pe 's/successors = \[0x33f078\]/successors = [0x33f07c]/' "$ROOT/branch-successor/contract/call-inventory.toml"
run_case branch-successor rejected
make_case resolved-target
perl -0777 -i -pe 's/resolved_target = 0x2801ec/resolved_target = 0x2801f0/' "$ROOT/resolved-target/contract/call-inventory.toml"
run_case resolved-target rejected
make_case integer-opcode
perl -0777 -i -pe 's/probe_add_opcode = 0x8b20c109/probe_add_opcode = 0x8b204109/' "$ROOT/integer-opcode/contract/integer-refinements.toml"
run_case integer-opcode rejected
cat > "$ROOT/summary.toml" <<'EOF'
schema_version = "mho900-lab.adc-parameter-review-controls/1"
result = "accepted"
positive_cases = 1
negative_cases = 13
negative_cases_rejected = 13
regular_independent_copies = true
guest_runs = 0
semantic_prose_automatically_proven = false
EOF
