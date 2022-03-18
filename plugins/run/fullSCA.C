void nSCAsFilled(TTree *ecal) {
  Int_t nhit_slab_min = ecal->GetMinimum("nhit_slab");
  Int_t nhit_slab_max = ecal->GetMaximum("nhit_slab");
  Int_t nscas = ecal->GetMaximum("hit_n_scas_filled");
  Int_t slab_min = ecal->GetMinimum("hit_slab");
  Int_t slab_max = ecal->GetMaximum("hit_slab");
  Int_t chip_max = ecal->GetMaximum("hit_chip");

  ecal->Draw(TString::Format(
                 "nhit_slab:hit_n_scas_filled >> perCoincidenceCount(%i, %.1f, "
                 "%.1f, %i, %.1f, %.1f)",
                 nscas, 0.5, nscas + 0.5, nhit_slab_max - nhit_slab_min + 1,
                 nhit_slab_min - 0.5, nhit_slab_max + 0.5),
             "", "goff");

  ecal->Draw(TString::Format("hit_slab:hit_n_scas_filled >> perLayer(%i, %.1f, "
                             "%.1f, %i, %.1f, %.1f)",
                             nscas, 0.5, nscas + 0.5, slab_max - slab_min + 1,
                             slab_min - 0.5, slab_max + 0.5),
             "", "goff");

  ecal->Draw(TString::Format("hit_slab*20+hit_chip:hit_n_scas_filled >> "
                             "perChip(%i, %.1f, %.1f, %i, %.1f, %.1f)",
                             nscas, 0.5, nscas + 0.5,
                             slab_max * 20 + chip_max + 1, -0.5,
                             slab_max * 20 + chip_max + 0.5),
             "", "goff");

  ecal->Draw(TString::Format("hit_chan:hit_n_scas_filled >> perChannel(%i, "
                             "%.1f, %.1f, 64, -0.5, 63.5)",
                             nscas, 0.5, nscas + 0.5),
             "", "goff");
}

void whichSCA(TTree *ecal) {
  Int_t nhit_slab_min = ecal->GetMinimum("nhit_slab");
  Int_t nhit_slab_max = ecal->GetMaximum("nhit_slab");
  Int_t sca_max = ecal->GetMaximum("hit_sca");
  Int_t slab_min = ecal->GetMinimum("hit_slab");
  Int_t slab_max = ecal->GetMaximum("hit_slab");
  Int_t chip_max = ecal->GetMaximum("hit_chip");
  ecal->Draw(TString::Format("nhit_slab:hit_sca >> sca_perCoincidenceCount(%i, "
                             "%.1f, %.1f, %i, %.1f, %.1f)",
                             sca_max + 1, -0.5, sca_max + 0.5,
                             nhit_slab_max - nhit_slab_min + 1,
                             nhit_slab_min - 0.5, nhit_slab_max + 0.5),
             "", "goff");
  ecal->Draw(
      TString::Format(
          "hit_slab:hit_sca >> sca_perLayer(%i, %.1f, %.1f, %i, %.1f, %.1f)",
          sca_max + 1, -0.5, sca_max + 0.5, slab_max - slab_min + 1,
          slab_min - 0.5, slab_max + 0.5),
      "", "goff");
  ecal->Draw(TString::Format("hit_slab*20+hit_chip:hit_sca >> sca_perChip(%i, "
                             "%.1f, %.1f, %i, %.1f, %.1f)",
                             sca_max + 1, -0.5, sca_max + 0.5,
                             slab_max * 20 + chip_max + 1, -0.5,
                             slab_max * 20 + chip_max + 0.5),
             "", "goff");
}

void beforeAnyFullSCA(TTree *ecal) {
  Int_t nhit_slab_min = ecal->GetMinimum("nhit_slab");
  Int_t nhit_slab_max = ecal->GetMaximum("nhit_slab");
  ecal->Draw(TString::Format("nhit_slab >> clean_nhit_slab(%i, %.1f, %.1f)",
                             nhit_slab_max - nhit_slab_min + 1,
                             nhit_slab_min - 0.5, nhit_slab_max + 0.5),
             "bcid < bcid_first_sca_full", "goff");
}

void fullSCA(TString buildfile = "build.root",
             TString output = "fullSCA.root") {
  TFile *in_file = TFile::Open(buildfile);
  TTree *ecal = in_file->Get<TTree>("ecal");
  // Let's not copy the whole file over.
  // gSystem->CopyFile(buildfile, output);
  TFile *file = TFile::Open(output, "create");
  file->mkdir("full_sca");
  file->GetDirectory("full_sca")->cd();
  nSCAsFilled(ecal);
  whichSCA(ecal);
  beforeAnyFullSCA(ecal);
  file->Write();
  file->Close();
}
