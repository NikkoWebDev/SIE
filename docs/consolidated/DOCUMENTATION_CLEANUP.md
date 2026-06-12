# Documentation Cleanup Summary

## Files to Keep (Essential)

1. **claude.md** - Main project documentation (authoritative reference)
2. **bugs.md** - Active bug tracking 
3. **Implementation plans** - For tracking progress on fixes
4. **BACKEND.md, DATABASE.md** - Technical specifications
5. **concepto_diseño.md** - Design system documentation
6. **forui.md** - UI component documentation

## Files to Remove/Archive

1. **_archive/legacy/info.md** - Legacy documentation from v0.5
2. **base/DESIGN.md** - Duplicated design concepts
3. **Optimization.md** - Can be consolidated with performance notes
4. **Others.md** - Can be consolidated into main documentation
5. **Vyntra/src/assets/brand/** - Design files that are now outdated

## Files to Condense

The following files contain overlapping information and should be consolidated:

- Optimization.md + Others.md → Main documentation
- Multiple design documentation files → concepto_diseño.md
- Legacy documentation → _archive folder

## Recommended Action Plan

1. Keep the consolidated documentation as the single source of truth
2. Archive legacy documentation in a separate folder
3. Focus on current Vyntra documentation only
4. Remove redundant design files that are now outdated