void hitMaps(TString buildfile = "build.root",
             TString output = "no_save.root") {
  TFile *in_file = TFile::Open(buildfile);
  TTree *ecal = in_file->Get<TTree>("ecal");
  TFile *file = in_file;
  if (output != "no_save.root") {
    // Let's not copy the whole file over.
    // gSystem->CopyFile(buildfile, output);
    file = TFile::Open(output, "create");
  }
  file->mkdir("hit_maps");
  file->GetDirectory("hit_maps")->cd();
  ecal->Draw("hit_y:hit_x >> hitMapSum(32, -90, 90, 32, -90, 90)", "",
             "colz,goff");
  for (Int_t i = 0; i < 15; i++) {
    ecal->Draw(
        TString::Format(
            "hit_y:hit_x >> hitMap_layer%02i(32, -90, 90, 32, -90, 90)", i),
        TString::Format("hit_z == %i", 15 * i), "colz,goff");
  }
  if (output == "no_save.root") {
    new TBrowser();
  } else {
    file->Write();
    file->Close();
  }
}
