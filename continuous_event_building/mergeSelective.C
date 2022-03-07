void mergeSelective(
  TString current_build="build.root",
  TString new_build_part="build_dat001.root",
  TString tree_name="ecal"
) {
  //------------------------------------
  // From the new file, only use the ecal TTree.
  //------------------------------------
  TFileMerger *fm;
  fm = new TFileMerger(kFALSE);
  fm->OutputFile(current_build, "UPDATE");
  fm->AddFile(new_build_part);
  fm->AddObjectNames(tree_name);
  // Must add new merging flag on top of the the default ones.
  Int_t default_mode = TFileMerger::kAll | TFileMerger::kIncremental;
  Int_t mode = default_mode | TFileMerger::kOnlyListed;
  fm->PartialMerge(mode);
  fm->Reset();
  delete fm;
}
