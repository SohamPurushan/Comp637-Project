; ModuleID = '/work/null_deref_scope.bc'
source_filename = "null_deref_scope.c"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-unknown-linux-gnu"

; Function Attrs: noinline nounwind uwtable
define dso_local i32 @execute(double* %b) #0 !dbg !14 {
entry:
  %b.addr = alloca double*, align 8
  %k = alloca double, align 8
  store double* %b, double** %b.addr, align 8
  call void @llvm.dbg.declare(metadata double** %b.addr, metadata !17, metadata !DIExpression()), !dbg !18
  call void @llvm.dbg.declare(metadata double* %k, metadata !19, metadata !DIExpression()), !dbg !20
  %0 = load double*, double** %b.addr, align 8, !dbg !21
  %1 = load double, double* %0, align 8, !dbg !22
  store double %1, double* %k, align 8, !dbg !20
  %2 = load double, double* %k, align 8, !dbg !23
  %conv = fptosi double %2 to i32, !dbg !24
  ret i32 %conv, !dbg !25
}

; Function Attrs: nofree nosync nounwind readnone speculatable willreturn
declare void @llvm.dbg.declare(metadata, metadata, metadata) #1

; Function Attrs: noinline nounwind uwtable
define dso_local i32 @main(i32 %argc, i8** %argv) #0 !dbg !26 {
entry:
  %retval = alloca i32, align 4
  %argc.addr = alloca i32, align 4
  %argv.addr = alloca i8**, align 8
  %t = alloca double*, align 8
  store i32 0, i32* %retval, align 4
  store i32 %argc, i32* %argc.addr, align 4
  call void @llvm.dbg.declare(metadata i32* %argc.addr, metadata !32, metadata !DIExpression()), !dbg !33
  store i8** %argv, i8*** %argv.addr, align 8
  call void @llvm.dbg.declare(metadata i8*** %argv.addr, metadata !34, metadata !DIExpression()), !dbg !35
  call void @llvm.dbg.declare(metadata double** %t, metadata !36, metadata !DIExpression()), !dbg !37
  store double* null, double** %t, align 8, !dbg !37
  %0 = load double*, double** %t, align 8, !dbg !38
  %call = call i32 @execute(double* %0), !dbg !39
  ret i32 0, !dbg !40
}

attributes #0 = { noinline nounwind uwtable "frame-pointer"="all" "min-legal-vector-width"="0" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+cx8,+fxsr,+mmx,+sse,+sse2,+x87" "tune-cpu"="generic" }
attributes #1 = { nofree nosync nounwind readnone speculatable willreturn }

!llvm.dbg.cu = !{!0}
!llvm.module.flags = !{!8, !9, !10, !11, !12}
!llvm.ident = !{!13}

!0 = distinct !DICompileUnit(language: DW_LANG_C99, file: !1, producer: "clang version 13.0.1 (https://github.com/llvm/llvm-project.git 75e33f71c2dae584b13a7d1186ae0a038ba98838)", isOptimized: false, runtimeVersion: 0, emissionKind: FullDebug, enums: !2, retainedTypes: !3, splitDebugInlining: false, nameTableKind: None)
!1 = !DIFile(filename: "null_deref_scope.c", directory: "/src")
!2 = !{}
!3 = !{!4, !5, !7}
!4 = !DIBasicType(name: "int", size: 32, encoding: DW_ATE_signed)
!5 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !6, size: 64)
!6 = !DIBasicType(name: "double", size: 64, encoding: DW_ATE_float)
!7 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: null, size: 64)
!8 = !{i32 7, !"Dwarf Version", i32 4}
!9 = !{i32 2, !"Debug Info Version", i32 3}
!10 = !{i32 1, !"wchar_size", i32 4}
!11 = !{i32 7, !"uwtable", i32 1}
!12 = !{i32 7, !"frame-pointer", i32 2}
!13 = !{!"clang version 13.0.1 (https://github.com/llvm/llvm-project.git 75e33f71c2dae584b13a7d1186ae0a038ba98838)"}
!14 = distinct !DISubprogram(name: "execute", scope: !1, file: !1, line: 16, type: !15, scopeLine: 16, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition, unit: !0, retainedNodes: !2)
!15 = !DISubroutineType(types: !16)
!16 = !{!4, !5}
!17 = !DILocalVariable(name: "b", arg: 1, scope: !14, file: !1, line: 16, type: !5)
!18 = !DILocation(line: 16, column: 21, scope: !14)
!19 = !DILocalVariable(name: "k", scope: !14, file: !1, line: 17, type: !6)
!20 = !DILocation(line: 17, column: 9, scope: !14)
!21 = !DILocation(line: 17, column: 14, scope: !14)
!22 = !DILocation(line: 17, column: 13, scope: !14)
!23 = !DILocation(line: 18, column: 14, scope: !14)
!24 = !DILocation(line: 18, column: 9, scope: !14)
!25 = !DILocation(line: 18, column: 2, scope: !14)
!26 = distinct !DISubprogram(name: "main", scope: !1, file: !1, line: 22, type: !27, scopeLine: 23, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition, unit: !0, retainedNodes: !2)
!27 = !DISubroutineType(types: !28)
!28 = !{!4, !4, !29}
!29 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !30, size: 64)
!30 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !31, size: 64)
!31 = !DIBasicType(name: "char", size: 8, encoding: DW_ATE_signed_char)
!32 = !DILocalVariable(name: "argc", arg: 1, scope: !26, file: !1, line: 22, type: !4)
!33 = !DILocation(line: 22, column: 14, scope: !26)
!34 = !DILocalVariable(name: "argv", arg: 2, scope: !26, file: !1, line: 22, type: !29)
!35 = !DILocation(line: 22, column: 26, scope: !26)
!36 = !DILocalVariable(name: "t", scope: !26, file: !1, line: 24, type: !5)
!37 = !DILocation(line: 24, column: 10, scope: !26)
!38 = !DILocation(line: 25, column: 10, scope: !26)
!39 = !DILocation(line: 25, column: 2, scope: !26)
!40 = !DILocation(line: 26, column: 2, scope: !26)
