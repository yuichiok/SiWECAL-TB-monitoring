void hitMaps(TString buildfile = "build.root",
             TString output = "hitMaps.root") {
  TFile *in_file = TFile::Open(buildfile);
  TTree *ecal = in_file->Get<TTree>("ecal");
  // Let's not copy the whole file over.
  // gSystem->CopyFile(buildfile, output);
  TFile *file = TFile::Open(output, "create");
  file->mkdir("hit_maps");
  file->GetDirectory("hit_maps")->cd();
  Int_t slab_min = ecal->GetMinimum("hit_slab");
  Int_t slab_max = ecal->GetMaximum("hit_slab");
  Int_t chip_min = ecal->GetMinimum("hit_chip");
  Int_t chip_max = ecal->GetMaximum("hit_chip");
  ecal->Draw(TString::Format("hit_slab:hit_chip >> hitMapChipLevel(%i, %.1f, "
                             "%.1f, %i, %.1f, %.1f)",
                             chip_max - chip_min + 1, chip_min - 0.5,
                             chip_max + 0.5, slab_max - slab_min + 1,
                             slab_min - 0.5, slab_max + 0.5),
             "(hit_isHit == 1)", "goff");
  ecal->Draw(TString::Format("hit_slab*20+hit_chip:hit_chan >> hitMapLong(64, "
                             "-0.5, 63.5, %i, %.1f, %.1f)",
                             slab_max * 20 + chip_max + 1, -0.5,
                             slab_max * 20 + chip_max + 0.5),
             "(hit_isHit == 1)", "goff");
  ecal->Draw(
      TString::Format("hit_chip*20+hit_slab:hit_chan >> hitMapLongReversed(64, "
                      "-0.5, 63.5, %i, %.1f, %.1f)",
                      chip_max * 20 + slab_max + 1, -0.5,
                      chip_max * 20 + slab_max + 0.5),
      "(hit_isHit == 1)", "goff");
  ecal->Draw(
      TString::Format(
          "hit_chip:hit_chan >> hitMapSum(64, -0.5, 63.5, %i, %.1f, %.1f)",
          chip_max - chip_min + 1, chip_min - 0.5, chip_max + 0.5),
      "(hit_isHit == 1)", "goff");
  for (Int_t i_slab = slab_min; i_slab <= slab_max; i_slab++) {
    ecal->Draw(TString::Format("hit_chip:hit_chan >> hitMap_layer%02i(64, "
                               "-0.5, 63.5, %i, %.1f, %.1f)",
                               i_slab, chip_max - chip_min + 1, chip_min - 0.5,
                               chip_max + 0.5),
               TString::Format("(hit_slab == %i) && (hit_isHit == 1)", i_slab),
               "goff");
  }
  file->Write();
  file->Close();
}
