void hitMapsXY(TString buildfile = "build.root",
               TString output = "hitMapsXY.root") {
  TFile *in_file = TFile::Open(buildfile);
  TTree *ecal = in_file->Get<TTree>("ecal");
  // Let's not copy the whole file over.
  // gSystem->CopyFile(buildfile, output);
  TFile *file = TFile::Open(output, "create");
  file->mkdir("hit_maps_xy");
  file->GetDirectory("hit_maps_xy")->cd();
  // 88 = 5.5 * 16. The small gap in the center is not visualized here.
  // -148.5 = 88 - 60.5. FEV13 has shifted position in x (60mm).
  // 60.5 = 11 * 5.5 to match cells in y.
  ecal->Draw("hit_y:hit_x >> hitMapXYSum(43, -148.5, 88, 32, -88, 88)", "",
             "goff");
  Int_t slab_max = ecal->GetMaximum("hit_slab");
  for (Int_t i_slab = ecal->GetMinimum("hit_slab"); i_slab <= slab_max;
       i_slab++) {
    ecal->Draw(
        TString::Format(
            "hit_y:hit_x >> hitMapXY_layer%02i(43, -148.5, 88, 32, -88, 88)",
            i_slab),
        TString::Format("hit_slab == %i", i_slab), "goff");
  }
  file->Write();
  file->Close();
}
