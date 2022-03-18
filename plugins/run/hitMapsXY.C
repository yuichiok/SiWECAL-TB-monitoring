void hitMapsXY(TString buildfile = "build.root",
               TString output = "hitMapsXY.root") {
  TFile *in_file = TFile::Open(buildfile);
  TTree *ecal = in_file->Get<TTree>("ecal");
  // Let's not copy the whole file over.
  // gSystem->CopyFile(buildfile, output);
  TFile *file = TFile::Open(output, "create");
  file->mkdir("hit_maps_xy");
  file->GetDirectory("hit_maps_xy")->cd();
  ecal->Draw("hit_y:hit_x >> hitMapXYSum(32, -90, 90, 32, -90, 90)", "",
             "goff");
  Int_t slab_max = ecal->GetMaximum("hit_slab");
  for (Int_t i_slab = ecal->GetMinimum("hit_slab"); i_slab <= slab_max;
       i_slab++) {
    ecal->Draw(
        TString::Format(
            "hit_y:hit_x >> hitMapXY_layer%02i(32, -90, 90, 32, -90, 90)",
            i_slab),
        TString::Format("hit_slab == %i", i_slab), "goff");
  }
  file->Write();
  file->Close();
}
