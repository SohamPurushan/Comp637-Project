; ModuleID = '/work/null_deref_@alias-bad.bc'
source_filename = "null_deref_@alias-bad.c"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-unknown-linux-gnu"

@.str = private unnamed_addr constant [8 x i8] c"c = %c\0A\00", align 1

; Function Attrs: noinline nounwind uwtable
define dso_local i32 @main(i32 %argc, i8** %argv) #0 !dbg !11 {
entry:
  %retval = alloca i32, align 4
  %argc.addr = alloca i32, align 4
  %argv.addr = alloca i8**, align 8
  %tab = alloca [1 x i8*], align 8
  %c = alloca i8, align 1
  store i32 0, i32* %retval, align 4
  store i32 %argc, i32* %argc.addr, align 4
  call void @llvm.dbg.declare(metadata i32* %argc.addr, metadata !18, metadata !DIExpression()), !dbg !19
  store i8** %argv, i8*** %argv.addr, align 8
  call void @llvm.dbg.declare(metadata i8*** %argv.addr, metadata !20, metadata !DIExpression()), !dbg !21
  call void @llvm.dbg.declare(metadata [1 x i8*]* %tab, metadata !22, metadata !DIExpression()), !dbg !26
  %0 = bitcast [1 x i8*]* %tab to i8*, !dbg !26
  %1 = call i8* @memset(i8* %0, i32 0, i64 8), !dbg !26
  call void @llvm.dbg.declare(metadata i8* %c, metadata !27, metadata !DIExpression()), !dbg !28
  %arrayidx = getelementptr inbounds [1 x i8*], [1 x i8*]* %tab, i64 0, i64 0, !dbg !29
  %2 = load i8*, i8** %arrayidx, align 8, !dbg !29
  %3 = load i8, i8* %2, align 1, !dbg !30
  store i8 %3, i8* %c, align 1, !dbg !28
  %4 = load i8, i8* %c, align 1, !dbg !31
  %conv = sext i8 %4 to i32, !dbg !31
  %call = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([8 x i8], [8 x i8]* @.str, i64 0, i64 0), i32 %conv), !dbg !32
  ret i32 0, !dbg !33
}

; Function Attrs: nofree nosync nounwind readnone speculatable willreturn
declare void @llvm.dbg.declare(metadata, metadata, metadata) #1

; Function Attrs: argmemonly nofree nounwind willreturn writeonly
declare void @llvm.memset.p0i8.i64(i8* nocapture writeonly, i8, i64, i1 immarg) #2

declare dso_local i32 @printf(i8*, ...) #3

; Function Attrs: noinline nounwind uwtable
define dso_local i8* @memset(i8* %dst, i32 %s, i64 %count) #0 !dbg !34 {
entry:
  %dst.addr = alloca i8*, align 8
  %s.addr = alloca i32, align 4
  %count.addr = alloca i64, align 8
  %a = alloca i8*, align 8
  store i8* %dst, i8** %dst.addr, align 8
  call void @llvm.dbg.declare(metadata i8** %dst.addr, metadata !42, metadata !DIExpression()), !dbg !43
  store i32 %s, i32* %s.addr, align 4
  call void @llvm.dbg.declare(metadata i32* %s.addr, metadata !44, metadata !DIExpression()), !dbg !45
  store i64 %count, i64* %count.addr, align 8
  call void @llvm.dbg.declare(metadata i64* %count.addr, metadata !46, metadata !DIExpression()), !dbg !47
  call void @llvm.dbg.declare(metadata i8** %a, metadata !48, metadata !DIExpression()), !dbg !49
  %0 = load i8*, i8** %dst.addr, align 8, !dbg !50
  store i8* %0, i8** %a, align 8, !dbg !49
  br label %while.cond, !dbg !51

while.cond:                                       ; preds = %while.body, %entry
  %1 = load i64, i64* %count.addr, align 8, !dbg !52
  %dec = add i64 %1, -1, !dbg !52
  store i64 %dec, i64* %count.addr, align 8, !dbg !52
  %cmp = icmp ugt i64 %1, 0, !dbg !53
  br i1 %cmp, label %while.body, label %while.end, !dbg !51

while.body:                                       ; preds = %while.cond
  %2 = load i32, i32* %s.addr, align 4, !dbg !54
  %conv = trunc i32 %2 to i8, !dbg !54
  %3 = load i8*, i8** %a, align 8, !dbg !55
  %incdec.ptr = getelementptr inbounds i8, i8* %3, i32 1, !dbg !55
  store i8* %incdec.ptr, i8** %a, align 8, !dbg !55
  store i8 %conv, i8* %3, align 1, !dbg !56
  br label %while.cond, !dbg !51, !llvm.loop !57

while.end:                                        ; preds = %while.cond
  %4 = load i8*, i8** %dst.addr, align 8, !dbg !59
  ret i8* %4, !dbg !60
}

attributes #0 = { noinline nounwind uwtable "frame-pointer"="all" "min-legal-vector-width"="0" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+cx8,+fxsr,+mmx,+sse,+sse2,+x87" "tune-cpu"="generic" }
attributes #1 = { nofree nosync nounwind readnone speculatable willreturn }
attributes #2 = { argmemonly nofree nounwind willreturn writeonly }
attributes #3 = { "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+cx8,+fxsr,+mmx,+sse,+sse2,+x87" "tune-cpu"="generic" }

!llvm.dbg.cu = !{!0, !3}
!llvm.module.flags = !{!5, !6, !7, !8, !9}
!llvm.ident = !{!10, !10}

!0 = distinct !DICompileUnit(language: DW_LANG_C99, file: !1, producer: "clang version 13.0.1 (https://github.com/llvm/llvm-project.git 75e33f71c2dae584b13a7d1186ae0a038ba98838)", isOptimized: false, runtimeVersion: 0, emissionKind: FullDebug, enums: !2, splitDebugInlining: false, nameTableKind: None)
!1 = !DIFile(filename: "null_deref_@alias-bad.c", directory: "/src")
!2 = !{}
!3 = distinct !DICompileUnit(language: DW_LANG_C99, file: !4, producer: "clang version 13.0.1 (https://github.com/llvm/llvm-project.git 75e33f71c2dae584b13a7d1186ae0a038ba98838)", isOptimized: false, runtimeVersion: 0, emissionKind: FullDebug, enums: !2, splitDebugInlining: false, nameTableKind: None)
!4 = !DIFile(filename: "/tmp/klee_src/runtime/Freestanding/memset.c", directory: "/tmp/klee_build130stp_z3/runtime/Freestanding")
!5 = !{i32 7, !"Dwarf Version", i32 4}
!6 = !{i32 2, !"Debug Info Version", i32 3}
!7 = !{i32 1, !"wchar_size", i32 4}
!8 = !{i32 7, !"uwtable", i32 1}
!9 = !{i32 7, !"frame-pointer", i32 2}
!10 = !{!"clang version 13.0.1 (https://github.com/llvm/llvm-project.git 75e33f71c2dae584b13a7d1186ae0a038ba98838)"}
!11 = distinct !DISubprogram(name: "main", scope: !1, file: !1, line: 16, type: !12, scopeLine: 17, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition, unit: !0, retainedNodes: !2)
!12 = !DISubroutineType(types: !13)
!13 = !{!14, !14, !15}
!14 = !DIBasicType(name: "int", size: 32, encoding: DW_ATE_signed)
!15 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !16, size: 64)
!16 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !17, size: 64)
!17 = !DIBasicType(name: "char", size: 8, encoding: DW_ATE_signed_char)
!18 = !DILocalVariable(name: "argc", arg: 1, scope: !11, file: !1, line: 16, type: !14)
!19 = !DILocation(line: 16, column: 14, scope: !11)
!20 = !DILocalVariable(name: "argv", arg: 2, scope: !11, file: !1, line: 16, type: !15)
!21 = !DILocation(line: 16, column: 26, scope: !11)
!22 = !DILocalVariable(name: "tab", scope: !11, file: !1, line: 18, type: !23)
!23 = !DICompositeType(tag: DW_TAG_array_type, baseType: !16, size: 64, elements: !24)
!24 = !{!25}
!25 = !DISubrange(count: 1)
!26 = !DILocation(line: 18, column: 8, scope: !11)
!27 = !DILocalVariable(name: "c", scope: !11, file: !1, line: 19, type: !17)
!28 = !DILocation(line: 19, column: 8, scope: !11)
!29 = !DILocation(line: 19, column: 14, scope: !11)
!30 = !DILocation(line: 19, column: 12, scope: !11)
!31 = !DILocation(line: 20, column: 21, scope: !11)
!32 = !DILocation(line: 20, column: 2, scope: !11)
!33 = !DILocation(line: 21, column: 2, scope: !11)
!34 = distinct !DISubprogram(name: "memset", scope: !35, file: !35, line: 12, type: !36, scopeLine: 12, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition, unit: !3, retainedNodes: !2)
!35 = !DIFile(filename: "klee_src/runtime/Freestanding/memset.c", directory: "/tmp")
!36 = !DISubroutineType(types: !37)
!37 = !{!38, !38, !14, !39}
!38 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: null, size: 64)
!39 = !DIDerivedType(tag: DW_TAG_typedef, name: "size_t", file: !40, line: 46, baseType: !41)
!40 = !DIFile(filename: "llvm-130-install_O_D_A/lib/clang/13.0.1/include/stddef.h", directory: "/tmp")
!41 = !DIBasicType(name: "long unsigned int", size: 64, encoding: DW_ATE_unsigned)
!42 = !DILocalVariable(name: "dst", arg: 1, scope: !34, file: !35, line: 12, type: !38)
!43 = !DILocation(line: 12, column: 20, scope: !34)
!44 = !DILocalVariable(name: "s", arg: 2, scope: !34, file: !35, line: 12, type: !14)
!45 = !DILocation(line: 12, column: 29, scope: !34)
!46 = !DILocalVariable(name: "count", arg: 3, scope: !34, file: !35, line: 12, type: !39)
!47 = !DILocation(line: 12, column: 39, scope: !34)
!48 = !DILocalVariable(name: "a", scope: !34, file: !35, line: 13, type: !16)
!49 = !DILocation(line: 13, column: 9, scope: !34)
!50 = !DILocation(line: 13, column: 13, scope: !34)
!51 = !DILocation(line: 14, column: 3, scope: !34)
!52 = !DILocation(line: 14, column: 15, scope: !34)
!53 = !DILocation(line: 14, column: 18, scope: !34)
!54 = !DILocation(line: 15, column: 12, scope: !34)
!55 = !DILocation(line: 15, column: 7, scope: !34)
!56 = !DILocation(line: 15, column: 10, scope: !34)
!57 = distinct !{!57, !51, !54, !58}
!58 = !{!"llvm.loop.mustprogress"}
!59 = !DILocation(line: 16, column: 10, scope: !34)
!60 = !DILocation(line: 16, column: 3, scope: !34)
